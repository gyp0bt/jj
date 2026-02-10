"""Enrichment-onlyノードフィルタ

.sta, .msg, .datノードをグラフから除外する。
これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
ノード自体はグラフから除外する。

results/ディレクトリ内のファイルも情報のみ読み取り対象のため除外する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# .sta, .msg, .dat はNode化せず情報のみgo_*.inpに割り当てる対象拡張子
_ENRICHMENT_ONLY_EXTENSIONS: frozenset[str] = frozenset({".sta", ".msg", ".dat"})

# 情報のみ読み取り、Node化しないディレクトリ名
_INFO_ONLY_DIRECTORIES: frozenset[str] = frozenset({"results"})


def _is_in_info_only_directory(path: str) -> bool:
    """ノードのパスがinfo-onlyディレクトリ内かを判定"""
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    return any(part in _INFO_ONLY_DIRECTORIES for part in parts[:-1])


class EnrichmentOnlyFilter(AbstractFileParser):
    """enrichment-onlyノード（.sta, .msg, .dat, results/配下）をグラフから除外

    これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
    ノード自体はグラフから除外する。.odbは残す。
    results/ディレクトリ内のファイルも情報のみ読み取り対象として除外する。
    """

    priority = 99

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        excluded_ids: set[int] = set()

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in _ENRICHMENT_ONLY_EXTENSIONS:
                excluded_ids.add(node.id)
                continue

            # results/ディレクトリ内のファイルも除外
            node_path = node.properties.get("path", "")
            if node_path and _is_in_info_only_directory(node_path):
                excluded_ids.add(node.id)

        if excluded_ids:
            graph.remove_nodes(excluded_ids)

        return graph
