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

        properties: dict[str, Any] = {
            "path": rel_path,
            "index": parser.get_index(),
            "version": parser.get_version(),
            "tags": tags + config_tags,
            **translated_props,
            **config_props,  # 設定からのプロパティが優先
        }

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

            # version順にソート（versionがない場合は空文字として扱う）
            def get_version_key(n: Node) -> tuple[int, str]:
                ver = n.properties.get("version", "")
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
