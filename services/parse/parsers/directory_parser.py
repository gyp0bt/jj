"""ディレクトリ関係パーサー

フォルダベースのcontains関係とroot directoryノードを構築する。

ディレクトリ階層は最終階層まで辿るのがデフォルト動作。
config の directory-max-depth または CLI --max-depth で制限可能。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser
from services.parse.file_parse import FileParse, FileType

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


def _depth_of(path: str) -> int:
    """パスの深さ（"/"区切りの階層数）を返す

    例: "a" → 1, "a/b" → 2, "a/b/c" → 3
    """
    if not path or path == ".":
        return 0
    return path.count("/") + 1


class DirectoryRelationParser(AbstractFileParser):
    """フォルダベースの関連付け（contains）を構築

    3種類のディレクトリ処理を行う:
    1. 命名規則に合致するディレクトリ（go_idx1_v1/等）→ type="{fileType}_directory"
    2. ファイルノードを含む全ディレクトリ + 中間ディレクトリ → type="directory"
    3. ディレクトリ間の親→子 contains関係

    directory-max-depth設定:
    - None（デフォルト）: 最終階層まで全ディレクトリをNode化
    - 1: ルート直下のディレクトリのみ
    - 2: ルート直下 + その子ディレクトリまで
    """

    priority = 50

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = set(graph.config.file_relations.input_extensions)
        # ソルバープロファイルの入力拡張子をマージ
        for profile in graph.config.solver_profiles.values():
            input_extensions.update(profile.input_extensions)
        max_depth = graph.config.directory_max_depth  # None = 無制限
        handled_dir_paths: set[str] = set()

        # --- (1) 命名規則に合致するディレクトリ ---
        named_dirs = self._scan_directories(graph, max_depth=max_depth)

        for dir_path in named_dirs:
            rel_path = graph.safe_relative_path(dir_path)
            dirname = dir_path.name
            parser = FileParse(dirname)

            dir_props: dict[str, Any] = {
                "path": rel_path,
            }
            idx_val = parser.get_index()
            ver_val = parser.get_version()
            if idx_val:
                dir_props["index"] = idx_val
            if ver_val:
                dir_props["version"] = ver_val
            for pk, pv in parser.get_props().items():
                dir_props[pk] = pv

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

        # --- (2) ファイルノードを含む全ディレクトリ + 中間ディレクトリ ---
        # ファイルの直接の親ディレクトリだけでなく、中間ディレクトリも全て収集
        parent_dirs: dict[str, list[Node]] = defaultdict(list)
        all_dir_paths: set[str] = set()  # 中間ディレクトリ含む全パス

        for node in graph.nodes:
            if node.format == "directory":
                continue
            node_path = node.properties.get("path", "").replace("\\", "/")
            while node_path.startswith("./"):
                node_path = node_path[2:]
            if "/" in node_path:
                parent_dir = node_path.rsplit("/", 1)[0]
                parent_dirs[parent_dir].append(node)

                # 中間ディレクトリも登録（最終階層まで）
                parts = parent_dir.split("/")
                for i in range(len(parts)):
                    intermediate = "/".join(parts[: i + 1])
                    all_dir_paths.add(intermediate)

        # max_depthフィルタを適用
        if max_depth is not None:
            all_dir_paths = {p for p in all_dir_paths if _depth_of(p) <= max_depth}

        # 直接の親 + 中間ディレクトリ の両方をNode化
        for dir_rel_path in sorted(all_dir_paths):
            if dir_rel_path in handled_dir_paths:
                continue

            dirname = dir_rel_path.rsplit("/", 1)[-1] if "/" in dir_rel_path else dir_rel_path

            dir_node = Node(
                id=graph.next_node_id(),
                type="directory",
                name=dirname,
                format="directory",
                properties={
                    "path": dir_rel_path,
                },
            )
            graph.add_node(dir_node)
            handled_dir_paths.add(dir_rel_path)

            # このディレクトリの直接の子ファイルのみcontains関係でリンク
            for child_node in parent_dirs.get(dir_rel_path, []):
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="contains",
                        node1_id=dir_node.id,
                        node2_id=child_node.id,
                    )
                )

        # --- (3) ディレクトリ階層構造のcontains関係 ---
        # 全ディレクトリノード間で親→子のcontains関係を構築
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
    def _scan_directories(graph: ProjectGraph, *, max_depth: int | None = None) -> list:
        """命名規則に合致するディレクトリをスキャン

        Args:
            graph: ProjectGraph
            max_depth: ディレクトリの最大深さ（None=無制限）
        """
        exclude_dirs = graph.config.parse_defaults.exclude_dirs

        dirs_found: list[Path] = []
        for root, dirs, _ in os.walk(graph.project_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            root_path = Path(root)
            for dirname in dirs:
                dir_path = root_path / dirname
                rel_path = graph.safe_relative_path(dir_path)

                if graph.config.ignore.should_ignore(rel_path):
                    continue

                # max_depthチェック
                if max_depth is not None:
                    depth = _depth_of(rel_path.replace("\\", "/"))
                    if depth > max_depth:
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
