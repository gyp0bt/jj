"""GraphService: プロジェクトフォルダのパースとグラフデータ管理

このモジュールはjjのコアとなるグラフ機能を提供します。
- プロジェクトフォルダのスキャンとファイル解析
- GraphModelへの変換
- グラフデータの保存・読み込み

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional

from jj_types import GraphModel, Node, Relation
from services.storage import GraphStorage
from services.parse.file_parse import FileParse, FileType, DEFAULT_EXTENSIONS


class GraphService:
    """プロジェクトのグラフデータを管理するサービス"""

    def __init__(
        self,
        project_root: Path | str | None = None,
        storage: GraphStorage | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.storage = storage or GraphStorage()
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
            exclude_dirs: 除外するディレクトリ名

        Returns:
            スキャンされたファイルパスのリスト
        """
        ext_set = set(extensions or DEFAULT_EXTENSIONS)
        exclude_set = set(exclude_dirs or {".git", ".jj", "__pycache__", "node_modules", ".venv"})

        files: list[Path] = []
        for root, dirs, filenames in os.walk(self.project_root):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in exclude_set]

            root_path = Path(root)
            for filename in filenames:
                # 拡張子チェック
                lower_name = filename.lower()
                if any(lower_name.endswith(ext.lower()) for ext in ext_set):
                    files.append(root_path / filename)

        return sorted(files)

    def file_to_node(self, file_path: Path) -> Node:
        """ファイルパスからNodeを生成"""
        parser = FileParse(file_path)
        file_type = parser.get_file_type()
        props = parser.get_props()
        tags = parser.get_tags()

        # 相対パスを安全に生成（Windows対応）
        rel_path = self._safe_relative_path(file_path)

        properties: dict[str, Any] = {
            "path": rel_path,
            "index": parser.get_index(),
            "version": parser.get_version(),
            "tags": tags,
            **props,
        }

        return Node(
            id=self._next_node_id(),
            type=file_type.value,
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

        # TODO: リレーション生成（includesなど）は今後拡張

        return GraphModel(nodes=nodes, relations=[])

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
