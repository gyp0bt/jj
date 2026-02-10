"""バージョン関係パーサー

同一type+indexのノードをグループ化し、version順にnext_version関係と
same_index_group関係を構築する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class VersionRelationParser(AbstractFileParser):
    """サブバージョン関係とグループ関係を構築するパーサー

    同一type/indexのノードをグループ化し:
    - version順にnext_version関係を作成
    - 同一グループ内のsame_index_group関係を作成
    """

    priority = 20

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # type + index でノードをグループ化
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in graph.nodes:
            node_type = node.type
            index = graph.get_node_index(node)
            if index:
                groups[(node_type, index)].append(node)

        for (_node_type, _index), group_nodes in groups.items():
            if len(group_nodes) < 2:
                continue

            def get_version_key(n: Node) -> tuple[int, str]:
                ver = graph.get_node_version(n)
                if not ver:
                    ver = "1"
                try:
                    return (0, str(int(ver)).zfill(10))
                except (ValueError, TypeError):
                    return (1, str(ver))

            sorted_nodes = sorted(group_nodes, key=get_version_key)

            # サブバージョン関係を作成（version順にリンク）
            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="next_version",
                        node1_id=prev_node.id,
                        node2_id=next_node.id,
                    )
                )

            # グループ関係を作成
            representative = sorted_nodes[0]
            for member in sorted_nodes[1:]:
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="same_index_group",
                        node1_id=representative.id,
                        node2_id=member.id,
                    )
                )

        return graph
