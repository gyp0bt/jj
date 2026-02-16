"""Enrichment-onlyノードフィルタ

.sta, .msg, .datノードをグラフから除外する。
これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
ノード自体はグラフから除外する。

results/ディレクトリ直下のファイルも情報のみ読み取り対象のため除外する。
ただしresults/のサブディレクトリ内のファイル（例: results/step0_frame10/*.png）は
結果可視化画像として残す。

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
    """ノードのパスがinfo-onlyディレクトリ直下かを判定

    results/直下のファイル（例: results/foo.json）は除外対象。
    results/のサブディレクトリ内のファイル（例: results/step0_frame10/foo.png）は
    除外しない（ノードとして残す）。
    """
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    # ファイル名を除いたディレクトリパーツを取得
    dir_parts = parts[:-1]
    for i, part in enumerate(dir_parts):
        if part in _INFO_ONLY_DIRECTORIES:
            # info-onlyディレクトリの直下（深さ1）のみ除外
            # サブディレクトリ（深さ2+）は除外しない
            depth = len(dir_parts) - i - 1
            if depth == 0:
                return True
    return False


class EnrichmentOnlyFilter(AbstractFileParser):
    """enrichment-onlyノード（.sta, .msg, .dat, results/直下）をグラフから除外

    これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
    ノード自体はグラフから除外する。.odbは残す。
    results/直下のファイルも情報のみ読み取り対象として除外する。
    results/のサブディレクトリ内のファイルはノードとして残す。
    """

    priority = 99

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        excluded_ids: set[int] = set()

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in _ENRICHMENT_ONLY_EXTENSIONS:
                excluded_ids.add(node.id)
                continue

            # results/直下のファイルのみ除外（サブディレクトリは残す）
            node_path = node.properties.get("path", "")
            if node_path and _is_in_info_only_directory(node_path):
                excluded_ids.add(node.id)

        if excluded_ids:
            graph.remove_nodes(excluded_ids)

        return graph
