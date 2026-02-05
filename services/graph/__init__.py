"""GraphService: プロジェクトフォルダのパースとグラフデータ管理

このモジュールはjjのコアとなるグラフ機能を提供します。
- プロジェクトフォルダのスキャンとファイル解析
- GraphModelへの変換
- サブバージョン関係・グループ関係の構築
- グラフデータの保存・読み込み

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

from jj_types import GraphModel, Node, Relation
from services.storage import GraphStorage
from services.parse.file_parse import FileParse, FileType, DEFAULT_EXTENSIONS
from config import GraphConfig


class GraphService:
    """プロジェクトのグラフデータを管理するサービス"""

    def __init__(
        self,
        project_root: Path | str | None = None,
        storage: GraphStorage | None = None,
        config: GraphConfig | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.storage = storage or GraphStorage()
        self.config = config or GraphConfig.load(self.project_root)
        self._node_id_counter = 0
        self._relation_id_counter = 0

    def _next_node_id(self) -> int:
        self._node_id_counter += 1
        return self._node_id_counter

    def _next_relation_id(self) -> int:
        self._relation_id_counter += 1
        return self._relation_id_counter

    def scan_files(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
    ) -> list[Path]:
        """プロジェクトルートからファイルをスキャン

        Args:
            extensions: 対象拡張子（デフォルト: DEFAULT_EXTENSIONS）
            exclude_dirs: 除外するディレクトリ名（ignore設定とマージ）

        Returns:
            スキャンされたファイルパスのリスト
        """
        ext_set = set(extensions or DEFAULT_EXTENSIONS)
        # デフォルトの除外ディレクトリ
        default_exclude = {".git", ".jj", "__pycache__", "node_modules", ".venv"}
        exclude_set = set(exclude_dirs or default_exclude)

        files: list[Path] = []
        for root, dirs, filenames in os.walk(self.project_root):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in exclude_set]

            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                rel_path = self._safe_relative_path(file_path)

                # ignore設定でチェック
                if self.config.ignore.should_ignore(rel_path):
                    continue

                # 拡張子チェック
                lower_name = filename.lower()
                if any(lower_name.endswith(ext.lower()) for ext in ext_set):
                    files.append(file_path)

        return sorted(files)

    def file_to_node(self, file_path: Path) -> Node:
        """ファイルパスからNodeを生成"""
        parser = FileParse(file_path)
        file_type = parser.get_file_type()
        props = parser.get_props()
        tags = parser.get_tags()

        # 相対パスを安全に生成（Windows対応）
        rel_path = self._safe_relative_path(file_path)
        filename = file_path.name

        # path-type-mapからタイプを取得（設定が優先）
        config_type = self.config.path_type_map.get_type(rel_path, filename)
        resolved_type = config_type if config_type else file_type.value

        # path-property-mapからプロパティを取得
        config_props = self.config.path_property_map.get_properties(rel_path)

        # path-tag-mapからタグを取得
        config_tags = self.config.path_tag_map.get_tags(rel_path)

        # vocabを使ってpropsのキーを変換
        translated_props: dict[str, Any] = {}
        for key, value in props.items():
            translated_key = self.config.vocab.get(key, key)
            translated_props[translated_key] = value

        # 日付を取得
        date_formatted = parser.get_date_formatted()

        properties: dict[str, Any] = {
            "path": rel_path,
            "index": parser.get_index(),
            "version": parser.get_version(),
            "tags": tags + config_tags,
            **translated_props,
            **config_props,  # 設定からのプロパティが優先
        }

        # 日付がある場合のみ追加
        if date_formatted:
            properties["date"] = date_formatted

        return Node(
            id=self._next_node_id(),
            type=resolved_type,
            name=parser.get_basename(),
            format=parser._split_extension()[1].lstrip("."),
            properties=properties,
        )

    def _safe_relative_path(self, file_path: Path) -> str:
        """Windowsでも安全に相対パスを生成

        Args:
            file_path: 対象ファイルパス

        Returns:
            POSIX形式の相対パス文字列
        """
        try:
            resolved = file_path.resolve()
            rel = resolved.relative_to(self.project_root)
            # 常にPOSIX形式（/）で返す
            return rel.as_posix()
        except ValueError:
            # relative_toが失敗した場合（異なるドライブ等）
            return file_path.as_posix()

    def parse_project(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
    ) -> GraphModel:
        """プロジェクトをパースしてGraphModelを生成

        Args:
            extensions: 対象拡張子
            exclude_dirs: 除外ディレクトリ

        Returns:
            生成されたGraphModel
        """
        files = self.scan_files(extensions=extensions, exclude_dirs=exclude_dirs)

        nodes: list[Node] = []
        node_by_path: dict[str, Node] = {}

        # ノード生成
        for file_path in files:
            node = self.file_to_node(file_path)
            nodes.append(node)
            node_by_path[node.properties.get("path", "")] = node

        # リレーション生成
        relations: list[Relation] = []

        # サブバージョン関係とグループ関係を構築
        version_relations, group_relations = self._build_version_and_group_relations(nodes)
        relations.extend(version_relations)
        relations.extend(group_relations)

        # 入力-結果関係を構築
        result_relations = self._build_result_relations(nodes)
        relations.extend(result_relations)

        # アセット関係を構築
        asset_relations = self._build_asset_relations(nodes)
        relations.extend(asset_relations)

        # includes関係を構築（inpファイルの*includeディレクティブ）
        includes_relations = self._build_includes_relations(nodes, node_by_path)
        relations.extend(includes_relations)

        return GraphModel(nodes=nodes, relations=relations)

    def _build_version_and_group_relations(
        self, nodes: list[Node]
    ) -> tuple[list[Relation], list[Relation]]:
        """サブバージョン関係とグループ関係を構築

        同一type/indexのノードをグループ化し、version順にサブバージョン関係を作成

        Args:
            nodes: ノードのリスト

        Returns:
            (サブバージョン関係のリスト, グループ関係のリスト)
        """
        version_relations: list[Relation] = []
        group_relations: list[Relation] = []

        # type + index でノードをグループ化
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in nodes:
            node_type = node.type
            index = node.properties.get("index", "")
            if index:  # indexがあるノードのみグループ化
                groups[(node_type, index)].append(node)

        for (node_type, index), group_nodes in groups.items():
            if len(group_nodes) < 2:
                continue

            # version順にソート（versionが空の場合は"1"として扱う）
            def get_version_key(n: Node) -> tuple[int, str]:
                ver = n.properties.get("version", "")
                # versionが空の場合はデフォルトで"1"として扱う
                if not ver:
                    ver = "1"
                # 数値として解釈できる場合は数値でソート
                try:
                    return (0, str(int(ver)).zfill(10))
                except (ValueError, TypeError):
                    return (1, str(ver))

            sorted_nodes = sorted(group_nodes, key=get_version_key)

            # サブバージョン関係を作成（version順にリンク）
            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]
                version_relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="next_version",
                        node1_id=prev_node.id,
                        node2_id=next_node.id,
                    )
                )

            # グループ関係を作成（すべてのノードを同一グループとしてリンク）
            # 最初のノードをグループの代表として、他のノードとリンク
            representative = sorted_nodes[0]
            for member in sorted_nodes[1:]:
                group_relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="same_index_group",
                        node1_id=representative.id,
                        node2_id=member.id,
                    )
                )

        return version_relations, group_relations

    def _build_result_relations(self, nodes: list[Node]) -> list[Relation]:
        """入力ファイルと結果ファイルの関係を構築

        同じbasename（go_idx1_w5_t20等）を持つファイルのうち、
        入力ファイル（.inp）と結果ファイル（.odb, .sta, .csv等）の間に
        result_of関係を作成します。

        Args:
            nodes: ノードのリスト

        Returns:
            result_of関係のリスト
        """
        relations: list[Relation] = []

        # 設定から拡張子を取得
        input_extensions = self.config.file_relations.input_extensions
        result_extensions = self.config.file_relations.result_extensions

        # basenameでノードをグループ化
        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in nodes:
            # ディレクトリ部分を除外してbasenameでグループ化
            basename = node.name
            by_basename[basename].append(node)

        for basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            # 入力ファイルと結果ファイルを分離
            input_nodes = []
            result_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in result_extensions:
                    result_nodes.append(node)

            # 入力ファイルと結果ファイルの間にresult_of関係を作成
            for input_node in input_nodes:
                for result_node in result_nodes:
                    # 同じindex/propsを持つ場合のみリンク
                    if self._nodes_have_same_props(input_node, result_node):
                        relations.append(
                            Relation(
                                id=self._next_relation_id(),
                                label="result_of",
                                node1_id=result_node.id,  # 結果ファイル
                                node2_id=input_node.id,    # 入力ファイル
                            )
                        )

        return relations

    def _build_asset_relations(self, nodes: list[Node]) -> list[Relation]:
        """アセットファイルと入力ファイルの関係を構築

        同じbasename（mesh等）を持つファイルのうち、
        アセットファイル（.modfem, .stl等）と入力ファイル（.inp）の間に
        derived_from関係を作成します。

        例: mesh.modfem → derived_from → mesh.inp

        Args:
            nodes: ノードのリスト

        Returns:
            derived_from関係のリスト
        """
        relations: list[Relation] = []

        # 設定から拡張子を取得
        input_extensions = self.config.file_relations.input_extensions
        asset_extensions = self.config.file_relations.asset_extensions

        # basenameでノードをグループ化
        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in nodes:
            basename = node.name
            by_basename[basename].append(node)

        for basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            # 入力ファイルとアセットファイルを分離
            input_nodes = []
            asset_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in asset_extensions:
                    asset_nodes.append(node)

            # アセットファイルと入力ファイルの間にderived_from関係を作成
            for input_node in input_nodes:
                for asset_node in asset_nodes:
                    # 同じindex/propsを持つ場合のみリンク
                    if self._nodes_have_same_props(input_node, asset_node):
                        relations.append(
                            Relation(
                                id=self._next_relation_id(),
                                label="derived_from",
                                node1_id=input_node.id,    # 入力ファイル
                                node2_id=asset_node.id,    # アセットファイル（元データ）
                            )
                        )

        return relations

    def _build_includes_relations(
        self, nodes: list[Node], node_by_path: dict[str, Node]
    ) -> list[Relation]:
        """inpファイルの*includeディレクティブを解析してincludes関係を構築

        Args:
            nodes: ノードのリスト
            node_by_path: パスからノードへのマッピング

        Returns:
            includes関係のリスト
        """
        relations: list[Relation] = []

        # *includeパターン
        include_pattern = re.compile(r"^\*include\s*,\s*input\s*=\s*(.+)$", re.IGNORECASE)

        # 入力ファイルの拡張子
        input_extensions = self.config.file_relations.input_extensions

        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue

            # ファイルパスを取得
            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            # ファイルを読み込んで*includeを解析
            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("**"):
                            continue

                        match = include_pattern.match(line)
                        if match:
                            include_path = match.group(1).strip()
                            # インクルードファイル名を取得（パス情報から相対パスを解決）
                            include_filename = Path(include_path).name

                            # node_by_pathからインクルード先を検索
                            # パス全体またはファイル名で検索
                            target_node = None

                            # まず完全パスで検索
                            for path, n in node_by_path.items():
                                if path.endswith(include_path) or Path(path).name == include_filename:
                                    target_node = n
                                    break

                            if target_node:
                                relations.append(
                                    Relation(
                                        id=self._next_relation_id(),
                                        label="includes",
                                        node1_id=node.id,          # インクルード元
                                        node2_id=target_node.id,   # インクルード先
                                    )
                                )
            except (OSError, IOError):
                # ファイル読み込みエラーは無視
                continue

        return relations

    def _nodes_have_same_props(self, node1: Node, node2: Node) -> bool:
        """2つのノードが同じ主要プロパティを持つかチェック

        Args:
            node1: ノード1
            node2: ノード2

        Returns:
            同じ主要プロパティを持つ場合True
        """
        # 比較対象のプロパティキー（index, 数値パラメータ等）
        compare_keys = {"index", "w", "t", "番号"}

        for key in compare_keys:
            val1 = node1.properties.get(key, "")
            val2 = node2.properties.get(key, "")
            # 両方に値があり、異なる場合はFalse
            if val1 and val2 and val1 != val2:
                return False

        return True

    def load(self, filename: Optional[str] = None) -> GraphModel:
        """グラフデータを読み込み"""
        return self.storage.load(self.project_root, filename)

    def save(self, graph: GraphModel, filename: Optional[str] = None) -> Path:
        """グラフデータを保存"""
        return self.storage.save(self.project_root, graph, filename)

    def parse_and_save(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
        filename: Optional[str] = None,
    ) -> tuple[GraphModel, Path]:
        """プロジェクトをパースして保存

        Returns:
            (生成されたGraphModel, 保存先パス)
        """
        graph = self.parse_project(extensions=extensions, exclude_dirs=exclude_dirs)
        path = self.save(graph, filename)
        return graph, path

    def get_nodes_by_type(self, graph: GraphModel, node_type: str) -> list[Node]:
        """タイプでノードをフィルタリング"""
        return [n for n in graph.nodes if n.type == node_type]

    def get_node_by_id(self, graph: GraphModel, node_id: int) -> Optional[Node]:
        """IDでノードを取得"""
        for node in graph.nodes:
            if node.id == node_id:
                return node
        return None

    def get_relations_for_node(self, graph: GraphModel, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return [
            r
            for r in graph.relations
            if r.node1_id == node_id or r.node2_id == node_id
        ]

    def summary(self, graph: GraphModel) -> dict[str, Any]:
        """グラフのサマリーを生成"""
        type_counts: dict[str, int] = {}
        for node in graph.nodes:
            type_counts[node.type] = type_counts.get(node.type, 0) + 1

        return {
            "total_nodes": len(graph.nodes),
            "total_relations": len(graph.relations),
            "nodes_by_type": type_counts,
        }
