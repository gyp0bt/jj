"""Enrichment-onlyノードフィルタ

.sta, .msg, .datノードをグラフから除外する。
これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
ノード自体はグラフから除外する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# .sta, .msg, .dat はNode化せず情報のみgo_*.inpに割り当てる対象拡張子
_ENRICHMENT_ONLY_EXTENSIONS: frozenset[str] = frozenset({".sta", ".msg", ".dat"})


class EnrichmentOnlyFilter(AbstractFileParser):
    """enrichment-onlyノード（.sta, .msg, .dat）をグラフから除外

    これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
    ノード自体はグラフから除外する。.odbは残す。
    """

    priority = 99

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        excluded_ids: set[int] = set()

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in _ENRICHMENT_ONLY_EXTENSIONS:
                excluded_ids.add(node.id)

        if excluded_ids:
            graph.remove_nodes(excluded_ids)

        return graph
