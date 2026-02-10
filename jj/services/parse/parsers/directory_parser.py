"""ディレクトリ関係パーサー

フォルダベースのcontains関係とroot directoryノードを構築する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser
from services.parse.file_parse import FileParse, FileType

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class DirectoryRelationParser(AbstractFileParser):
    """フォルダベースの関連付け（contains）を構築

    2種類のディレクトリノードを生成する:
    1. 命名規則に合致するディレクトリ（go_idx1_v1/等）→ type="{fileType}_directory"
    2. ファイルノードを含む全ディレクトリ（reports/等）→ type="directory"

    いずれもcontains関係でディレクトリ内のファイルとリンクする。
    命名規則合致ディレクトリは同名入力ファイルとhas_output関係も作成する。
    """

    priority = 50

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions
        handled_dir_paths: set[str] = set()

        # --- (1) 命名規則に合致するディレクトリ ---
        named_dirs = self._scan_directories(graph)

        for dir_path in named_dirs:
            rel_path = graph.safe_relative_path(dir_path)
            dirname = dir_path.name
            parser = FileParse(dirname)

            dir_tags = parser.get_tags()
            if "root.directory" not in dir_tags:
                dir_tags.append("root.directory")

            dir_props: dict[str, Any] = {
                "path": rel_path,
                "tags": dir_tags,
            }
            idx_val = parser.get_index()
            ver_val = parser.get_version()
            idx_key = graph.config.vocab.get("idx", "index")
            ver_key = graph.config.vocab.get("v", "version")
            if idx_val:
                dir_props[idx_key] = idx_val
            if ver_val:
                dir_props[ver_key] = ver_val
            for pk, pv in parser.get_props().items():
                tk = graph.config.vocab.get(pk, pk)
                tv = graph.config.vocab.get(str(pv), str(pv))
                dir_props[tk] = tv

            dir_node = Node(
                id=graph.next_node_id(),
                type=parser.get_file_type().value + "_directory",
                name=dirname,
                format="directory",
                properties=dir_props,
            )
            graph.add_node(dir_node)
            handled_dir_paths.add(rel_path.replace("\\", "/").rstrip("/"))

            # ディレクトリ内のファイルをcontains関係でリンク
            dir_prefix = rel_path.replace("\\", "/").rstrip("/") + "/"
            for node in list(graph.nodes):
                if node.id == dir_node.id:
                    continue
                node_path = node.properties.get("path", "").replace("\\", "/")
                while node_path.startswith("./"):
                    node_path = node_path[2:]
                if node_path.startswith(dir_prefix):
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="contains",
                            node1_id=dir_node.id,
                            node2_id=node.id,
                        )
                    )

            # 同名の入力ファイルとhas_output関係を作成
            for node in list(graph.nodes):
                ext = f".{node.format}" if node.format else ""
                if ext.lower() not in input_extensions:
                    continue
                if node.name == dirname:
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="has_output",
                            node1_id=node.id,
                            node2_id=dir_node.id,
                        )
                    )

        # --- (2) ファイルノードを含む全ディレクトリ ---
        parent_dirs: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            node_path = node.properties.get("path", "").replace("\\", "/")
            while node_path.startswith("./"):
                node_path = node_path[2:]
            if "/" in node_path:
                parent_dir = node_path.rsplit("/", 1)[0]
                parent_dirs[parent_dir].append(node)

        for dir_rel_path, child_nodes in sorted(parent_dirs.items()):
            if dir_rel_path in handled_dir_paths:
                continue

            dirname = (
                dir_rel_path.rsplit("/", 1)[-1]
                if "/" in dir_rel_path
                else dir_rel_path
            )

            dir_node = Node(
                id=graph.next_node_id(),
                type="directory",
                name=dirname,
                format="directory",
                properties={
                    "path": dir_rel_path,
                    "tags": ["root.directory"],
                },
            )
            graph.add_node(dir_node)
            handled_dir_paths.add(dir_rel_path)

            for child_node in child_nodes:
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="contains",
                        node1_id=dir_node.id,
                        node2_id=child_node.id,
                    )
                )

        # --- (3) ディレクトリ階層構造のcontains関係 ---
        # ignore以外のディレクトリ間で親→子のcontains関係を構築
        dir_node_by_path: dict[str, Node] = {}
        for node in graph.nodes:
            if node.format != "directory":
                continue
            node_path = node.properties.get("path", "").replace("\\", "/").rstrip("/")
            if node_path and node_path != ".":
                dir_node_by_path[node_path] = node

        for dir_path, dir_node in dir_node_by_path.items():
            parent_path = dir_path.rsplit("/", 1)[0] if "/" in dir_path else ""
            parent_node = dir_node_by_path.get(parent_path)
            if parent_node:
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="contains",
                        node1_id=parent_node.id,
                        node2_id=dir_node.id,
                    )
                )

        return graph

    @staticmethod
    def _scan_directories(graph: ProjectGraph) -> list:
        """命名規則に合致するディレクトリをスキャン"""
        from pathlib import Path

        default_exclude = {".git", ".jj", "__pycache__", "node_modules", ".venv"}

        dirs_found: list[Path] = []
        for root, dirs, _ in os.walk(graph.project_root):
            dirs[:] = [d for d in dirs if d not in default_exclude]

            root_path = Path(root)
            for dirname in dirs:
                dir_path = root_path / dirname
                rel_path = graph.safe_relative_path(dir_path)

                if graph.config.ignore.should_ignore(rel_path):
                    continue

                parser = FileParse(dirname)
                if parser.get_file_type() != FileType.UNKNOWN:
                    dirs_found.append(dir_path)

        return sorted(dirs_found)


class RootDirectoryParser(AbstractFileParser):
    """root directoryをNode化

    プロジェクトルート直下のファイルに対して、
    root directoryノードを作成しcontains関係を構築する。
    """

    priority = 98

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        root_children: list[Node] = []
        for node in graph.nodes:
            path = node.properties.get("path", "")
            if not path:
                continue
            if node.format == "directory":
                continue
            if "/" not in path:
                root_children.append(node)

        if not root_children:
            return graph

        project_name = graph.config.project_name
        if not project_name:
            project_name = graph.project_root.name

        root_node = Node(
            id=graph.next_node_id(),
            type="directory",
            name=project_name,
            format="directory",
            properties={
                "path": ".",
                "tags": ["root", "directory"],
                "verbose_name": project_name,
            },
        )
        graph.add_node(root_node)

        for child in root_children:
            graph.add_relation(
                Relation(
                    id=graph.next_relation_id(),
                    label="contains",
                    node1_id=root_node.id,
                    node2_id=child.id,
                )
            )

        # ルート直下のディレクトリノードもcontainsでリンク
        for node in graph.nodes:
            if node.format != "directory" or node.id == root_node.id:
                continue
            path = node.properties.get("path", "").replace("\\", "/")
            if not path or path == ".":
                continue
            # ルート直下 = パスに "/" を含まない
            if "/" not in path:
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="contains",
                        node1_id=root_node.id,
                        node2_id=node.id,
                    )
                )

        return graph
