"""Abaqusバージョン差分パーサー

前バージョンとのキーワードブロック差分をpropertyに追加する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class AbaqusDiffParser(AbstractFileParser):
    """前バージョンとのキーワードブロック差分をpropertyに追加

    同一type+indexのinpファイルをバージョン順に並べ、
    隣接するバージョン間でAbaqusキーワードブロックの差分を計算する。
    """

    priority = 90
    requires_full = True

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        from services.parse.connectors.abaqus import (
            diff_abq_blocks,
            format_diff_blocks_markdown,
            format_diff_summary_table,
        )
        from services.parse.connectors.abaqus import (
            read_inp as abq_read_inp,
        )

        input_extensions = graph.config.file_relations.input_extensions

        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue
            if ext.lower() != ".inp":
                continue
            index = graph.get_node_index(node)
            if index:
                groups[(node.type, index)].append(node)

        for (_node_type, _index), group_nodes in groups.items():
            if len(group_nodes) < 2:
                continue

            def get_ver_key(n: Node) -> tuple[int, str]:
                ver = graph.get_node_version(n)
                if not ver:
                    ver = "1"
                try:
                    return (0, str(int(ver)).zfill(10))
                except (ValueError, TypeError):
                    return (1, str(ver))

            sorted_nodes = sorted(group_nodes, key=get_ver_key)

            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]

                prev_path = graph.project_root / prev_node.properties.get("path", "")
                next_path = graph.project_root / next_node.properties.get("path", "")

                if not prev_path.exists() or not next_path.exists():
                    continue

                try:
                    prev_abq = abq_read_inp(str(prev_path), verbose=False)
                    next_abq = abq_read_inp(str(next_path), verbose=False)
                    diffs = diff_abq_blocks(prev_abq, next_abq)

                    if diffs:
                        prev_file = prev_node.properties.get("path", prev_node.name)
                        next_node.properties["diff_from"] = prev_file
                        next_node.properties["diff_summary"] = (
                            format_diff_summary_table(diffs)
                        )
                        next_node.properties["diff_details"] = (
                            format_diff_blocks_markdown(diffs)
                        )
                except Exception:
                    continue

        return graph
