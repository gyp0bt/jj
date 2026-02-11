"""Abaqusバージョン差分パーサー

前バージョンとのキーワードブロック差分をdiffノードとして生成する。
diff情報はノードとして作成し、新旧ノードへのrelationを持つ。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class AbaqusDiffParser(AbstractFileParser):
    """前バージョンとの差分をdiffノードとして生成

    同一type+indexのinpファイルをバージョン順に並べ、
    隣接するバージョン間でAbaqusキーワードブロックの差分を計算する。
    差分が存在する場合、diffノードを作成し:
    - diff_from relation: diffノード → 旧ノード
    - diff_to relation: diffノード → 新ノード
    """

    priority = 90
    requires_full = True

    @staticmethod
    def _get_or_parse_inp(graph: ProjectGraph, file_path: str) -> object:
        """read_inp()結果をキャッシュから取得、なければパースしてキャッシュに保存"""
        from services.parse.connectors.abaqus import read_inp as abq_read_inp

        cached = graph.get_cached_abq_data(file_path)
        if cached is not None:
            return cached
        abq = abq_read_inp(file_path, verbose=False)
        graph.set_cached_abq_data(file_path, abq)
        return abq

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        from services.parse.connectors.abaqus import (
            diff_abq_blocks,
            format_diff_blocks_markdown,
            format_diff_summary_table,
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
                    prev_abq = self._get_or_parse_inp(graph, str(prev_path))
                    next_abq = self._get_or_parse_inp(graph, str(next_path))
                    diffs = diff_abq_blocks(prev_abq, next_abq)

                    # 差分がなくてもdiffノードを作成する（差分なしの記録として）
                    prev_file = prev_node.properties.get("path", prev_node.name)
                    next_file = next_node.properties.get("path", next_node.name)

                    diff_node_name = f"diff_{prev_node.name}_vs_{next_node.name}"
                    has_diffs = bool(diffs)

                    diff_props: dict = {
                        "diff_from": prev_file,
                        "diff_to": next_file,
                        "has_diffs": has_diffs,
                        "source_type": _node_type,
                        "source_index": _index,
                    }

                    if has_diffs:
                        diff_props["diff_summary"] = format_diff_summary_table(diffs)
                        diff_props["diff_details"] = format_diff_blocks_markdown(diffs)
                    else:
                        diff_props["diff_summary"] = "差分なし"
                        diff_props["diff_details"] = "差分なし"

                    diff_node = Node(
                        id=graph.next_node_id(),
                        type="version_diff",
                        name=diff_node_name,
                        format="diff",
                        properties=diff_props,
                    )
                    graph.add_node(diff_node)

                    # diff_from relation: diffノード → 旧ノード
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="diff_from",
                            node1_id=diff_node.id,
                            node2_id=prev_node.id,
                        )
                    )

                    # diff_to relation: diffノード → 新ノード
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="diff_to",
                            node1_id=diff_node.id,
                            node2_id=next_node.id,
                        )
                    )

                except Exception:
                    continue

        return graph
