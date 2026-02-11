"""Neo4jコネクタ: GraphModelをNeo4jデータベースにエクスポート

GraphModelのノードとリレーションをNeo4jに投入する。
既存データのupsert（存在すれば更新、なければ作成）に対応。

接続設定:
  - .jj/config/config.yaml の neo4j セクション
  - またはデフォルト値（bolt://localhost:7687, neo4j/password）

使用方法:
  connector = Neo4jConnector(project_root="/path/to/project")
  connector.export_graph(graph)
  connector.close()

Neo4jが利用不可の場合:
  export_cypher() でCypherクエリファイルとしてエクスポート可能

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jj_types import GraphModel, Node, Relation
from shared.neo4j_schema import (
    NodeLabel,
    get_neo4j_label,
    get_neo4j_reltype,
)
from shared.config import Neo4jConfig
from services.export import AbstractExporter


def _sanitize_property_value(value: Any) -> Any:
    """Neo4jに格納可能な型に変換する

    Neo4jが受け付ける型: bool, int, float, str, list[上記]
    dict等の複合型はJSON文字列に変換する。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # リスト内の要素もサニタイズ
        sanitized = []
        for item in value:
            s = _sanitize_property_value(item)
            if s is not None:
                sanitized.append(s)
        # Neo4jのリストは同一型でなければならない
        # 混在型の場合はJSON文字列化
        if sanitized and not _is_homogeneous_list(sanitized):
            return json.dumps(value, ensure_ascii=False, default=str)
        return sanitized if sanitized else None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    # その他の型は文字列化
    return str(value)


def _is_homogeneous_list(items: list) -> bool:
    """リスト内の要素が同一型かどうかを判定"""
    if not items:
        return True
    first_type = type(items[0])
    # int/floatは互換性あり
    numeric_types = (int, float)
    if first_type in numeric_types:
        return all(isinstance(x, numeric_types) for x in items)
    return all(type(x) == first_type for x in items)


def _build_node_properties(
    node: Node, project: str
) -> dict[str, Any]:
    """NodeからNeo4j用のプロパティ辞書を構築"""
    props: dict[str, Any] = {
        "jj_id": node.id,
        "name": node.name,
        "type": node.type,
        "format": node.format,
        "project": project,
    }

    for key, value in node.properties.items():
        sanitized = _sanitize_property_value(value)
        if sanitized is not None:
            # Neo4jのプロパティキーとして安全な名前に変換
            safe_key = key.replace("-", "_").replace(" ", "_")
            props[safe_key] = sanitized

    return props


def _escape_cypher_string(value: str) -> str:
    """Cypher文字列リテラル用のエスケープ"""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def _format_cypher_value(value: Any) -> str:
    """値をCypherリテラルにフォーマット"""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return f'"{_escape_cypher_string(value)}"'
    if isinstance(value, list):
        items = ", ".join(_format_cypher_value(v) for v in value)
        return f"[{items}]"
    return f'"{_escape_cypher_string(str(value))}"'


class Neo4jConnector:
    """jj GraphModel → Neo4j 書き込み / Cypherエクスポート

    Neo4jドライバが利用可能な場合はデータベースに直接書き込む。
    利用不可の場合はCypherクエリファイルとしてエクスポートする。
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        config: Neo4jConfig | None = None,
    ):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.project = self.project_root.name
        self.config = config or Neo4jConfig.from_jj_config(self.project_root)
        self._driver = None

    def _get_driver(self):
        """Neo4jドライバを遅延初期化"""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.user, self.config.password),
                )
            except ImportError:
                raise ImportError(
                    "neo4jパッケージがインストールされていません。\n"
                    "pip install neo4j>=5.0.0 を実行してください。"
                )
        return self._driver

    def close(self) -> None:
        """Neo4jドライバを閉じる"""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def export_graph(
        self,
        graph: GraphModel,
        clear_project: bool = False,
    ) -> dict[str, int]:
        """GraphModelをNeo4jにupsert

        Args:
            graph: エクスポートするグラフデータ
            clear_project: 既存のプロジェクトデータを削除してから投入

        Returns:
            {"nodes_created": N, "nodes_updated": N,
             "relations_created": N, "relations_updated": N}
        """
        driver = self._get_driver()
        stats = {
            "nodes_created": 0,
            "nodes_updated": 0,
            "relations_created": 0,
            "relations_updated": 0,
        }

        with driver.session(database=self.config.database) as session:
            if clear_project:
                self._clear_project_data(session)

            # ノードのupsert（バッチ処理）
            node_stats = self._upsert_nodes(session, graph.nodes)
            stats["nodes_created"] = node_stats["created"]
            stats["nodes_updated"] = node_stats["updated"]

            # リレーションのupsert（バッチ処理）
            rel_stats = self._upsert_relations(session, graph.relations)
            stats["relations_created"] = rel_stats["created"]
            stats["relations_updated"] = rel_stats["updated"]

        return stats

    def _clear_project_data(self, session) -> None:
        """プロジェクトに紐づく全ノードとリレーションを削除"""
        session.run(
            "MATCH (n) WHERE n.project = $project DETACH DELETE n",
            project=self.project,
        )

    def _upsert_nodes(
        self, session, nodes: list[Node]
    ) -> dict[str, int]:
        """ノードをバッチでupsert"""
        stats = {"created": 0, "updated": 0}

        # ラベル別にグループ化してバッチ処理
        label_groups: dict[str, list[dict[str, Any]]] = {}
        for node in nodes:
            label = get_neo4j_label(node.type)
            props = _build_node_properties(node, self.project)
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(props)

        for label, props_list in label_groups.items():
            # UNWIND を使ったバッチupsert
            # MERGE on (project, jj_id) → SET properties
            query = (
                f"UNWIND $props AS p "
                f"MERGE (n:{label} {{project: p.project, jj_id: p.jj_id}}) "
                f"ON CREATE SET n += p "
                f"ON MATCH SET n += p "
                f"RETURN "
                f"  sum(CASE WHEN n.name = p.name THEN 0 ELSE 1 END) AS updated, "
                f"  count(n) AS total"
            )
            result = session.run(query, props=props_list)
            record = result.single()
            if record:
                total = record["total"]
                stats["created"] += total
                # Note: ON CREATE/ON MATCH区別は厳密にはcounters経由
                # ここでは全件をcreatedとしてカウント
                # (upsertなので区別は参考値)

        return stats

    def _upsert_relations(
        self, session, relations: list[Relation]
    ) -> dict[str, int]:
        """リレーションをバッチでupsert"""
        stats = {"created": 0, "updated": 0}

        # リレーションタイプ別にグループ化
        type_groups: dict[str, list[dict[str, Any]]] = {}
        for rel in relations:
            rel_type = get_neo4j_reltype(rel.label)
            rel_data = {
                "source_jj_id": rel.node1_id,
                "target_jj_id": rel.node2_id,
                "project": self.project,
                "jj_rel_id": rel.id,
            }
            if rel_type not in type_groups:
                type_groups[rel_type] = []
            type_groups[rel_type].append(rel_data)

        for rel_type, rels_data in type_groups.items():
            # ソース・ターゲットのラベルを限定しないMATCH
            # （異なるラベルのノード間のリレーションも存在するため）
            query = (
                f"UNWIND $rels AS r "
                f"MATCH (a {{project: r.project, jj_id: r.source_jj_id}}) "
                f"MATCH (b {{project: r.project, jj_id: r.target_jj_id}}) "
                f"MERGE (a)-[rel:{rel_type} {{project: r.project}}]->(b) "
                f"SET rel.jj_rel_id = r.jj_rel_id "
                f"RETURN count(rel) AS total"
            )
            result = session.run(query, rels=rels_data)
            record = result.single()
            if record:
                stats["created"] += record["total"]

        return stats

    def export_cypher(
        self,
        graph: GraphModel,
        output_path: Path | str | None = None,
        clear_project: bool = False,
    ) -> Path:
        """GraphModelをCypherクエリファイルとしてエクスポート

        Neo4jが利用不可の場合の代替手段。
        生成されたCypherファイルはNeo4j Browserやcypher-shellで実行可能。

        Args:
            graph: エクスポートするグラフデータ
            output_path: 出力先ファイルパス（デフォルト: .jj/storage/export.cypher）
            clear_project: プロジェクトデータ削除クエリを含めるか

        Returns:
            書き込まれたファイルパス
        """
        if output_path is None:
            output_path = self.project_root / ".jj" / "storage" / "export.cypher"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        lines.append(f"// jj Neo4j Export: {self.project}")
        lines.append(f"// Nodes: {len(graph.nodes)}, Relations: {len(graph.relations)}")
        lines.append("")

        if clear_project:
            lines.append("// プロジェクトデータの削除")
            project_escaped = _escape_cypher_string(self.project)
            lines.append(
                f'MATCH (n) WHERE n.project = "{project_escaped}" DETACH DELETE n;'
            )
            lines.append("")

        # ノード作成
        lines.append("// === ノード ===")
        for node in graph.nodes:
            label = get_neo4j_label(node.type)
            props = _build_node_properties(node, self.project)
            props_str = ", ".join(
                f"{k}: {_format_cypher_value(v)}" for k, v in props.items()
            )
            merge_key = f'project: "{_escape_cypher_string(self.project)}", jj_id: {node.id}'
            lines.append(
                f"MERGE (n:{label} {{{merge_key}}}) SET n += {{{props_str}}};"
            )

        lines.append("")
        lines.append("// === リレーション ===")
        for rel in graph.relations:
            rel_type = get_neo4j_reltype(rel.label)
            project_escaped = _escape_cypher_string(self.project)
            lines.append(
                f'MATCH (a {{project: "{project_escaped}", jj_id: {rel.node1_id}}}), '
                f'(b {{project: "{project_escaped}", jj_id: {rel.node2_id}}}) '
                f'MERGE (a)-[:{rel_type} {{project: "{project_escaped}", jj_rel_id: {rel.id}}}]->(b);'
            )

        lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    def verify_connection(self) -> bool:
        """Neo4j接続を確認

        Returns:
            接続成功ならTrue
        """
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            return True
        except Exception:
            return False

    def get_project_stats(self) -> dict[str, int]:
        """プロジェクトのノード・リレーション数を取得"""
        driver = self._get_driver()
        with driver.session(database=self.config.database) as session:
            result = session.run(
                "MATCH (n) WHERE n.project = $project "
                "RETURN labels(n)[0] AS label, count(n) AS count",
                project=self.project,
            )
            node_counts = {record["label"]: record["count"] for record in result}

            result = session.run(
                "MATCH ()-[r]->() WHERE r.project = $project "
                "RETURN type(r) AS type, count(r) AS count",
                project=self.project,
            )
            rel_counts = {record["type"]: record["count"] for record in result}

        return {
            "nodes": node_counts,
            "relations": rel_counts,
            "total_nodes": sum(node_counts.values()),
            "total_relations": sum(rel_counts.values()),
        }


class Neo4jExporter(AbstractExporter):
    """Neo4jデータベース直接エクスポーター（AbstractExporterサブクラス）

    Neo4jConnectorをラップし、AbstractExporterレジストリに登録する。
    """

    format = "neo4j"
    priority = 30

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """Neo4jエクスポート

        kwargs:
            project_root: Path - プロジェクトルート
            clear_project: bool - 既存データを削除するか
            neo4j_uri: str | None - Neo4j接続URI
            neo4j_user: str | None - ユーザー名
            neo4j_password: str | None - パスワード
        """
        project_root = kwargs.get("project_root")
        clear_project = kwargs.get("clear_project", False)

        neo4j_config = Neo4jConfig.from_jj_config(
            Path(project_root) if project_root else Path.cwd()
        )
        # CLIオプションで上書き
        if kwargs.get("neo4j_uri"):
            neo4j_config.uri = kwargs["neo4j_uri"]
        if kwargs.get("neo4j_user"):
            neo4j_config.user = kwargs["neo4j_user"]
        if kwargs.get("neo4j_password"):
            neo4j_config.password = kwargs["neo4j_password"]

        connector = Neo4jConnector(project_root=project_root, config=neo4j_config)
        try:
            stats = connector.export_graph(graph, clear_project=clear_project)
            return {
                "uri": neo4j_config.uri,
                "stats": stats,
                "node_count": stats["nodes_created"],
                "relation_count": stats["relations_created"],
                "clear_project": clear_project,
                "direct": True,
            }
        finally:
            connector.close()


class CypherExporter(AbstractExporter):
    """Cypherファイルエクスポーター（AbstractExporterサブクラス）

    Neo4jConnector.export_cypher()をラップし、AbstractExporterレジストリに登録する。
    """

    format = "cypher"
    priority = 31

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """Cypherエクスポート

        kwargs:
            project_root: Path - プロジェクトルート
            clear_project: bool - 削除クエリを含めるか
            output_file: str | None - 出力ファイルパス
        """
        project_root = kwargs.get("project_root")
        clear_project = kwargs.get("clear_project", False)
        output_file = kwargs.get("output_file")

        connector = Neo4jConnector(project_root=project_root)
        try:
            output_path = connector.export_cypher(
                graph,
                output_path=output_file,
                clear_project=clear_project,
            )
            return {
                "output_path": output_path,
                "node_count": len(graph.nodes),
                "relation_count": len(graph.relations),
                "clear_project": clear_project,
                "direct": False,
            }
        finally:
            connector.close()
