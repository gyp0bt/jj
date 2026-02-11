"""Abaqusメッシュパーサー

pymeshを使ってメッシュ統計情報をノードのプロパティに付与する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)


class AbaqusMeshParser(AbstractFileParser):
    """pymeshを使ってメッシュ統計情報をノードのプロパティに付与

    pymeshによる.inp読み込みは重いため、--fullオプション時のみ実行する。

    mesh_qualityが付加されないケースの原因:
    - get_element_node_coord_array()がNone/空を返す（要素タイプ未対応）
    - 品質メトリクス計算がすべてのモードで失敗（2D要素等）
    - NaN率100%で有効な統計値が得られない
    デバッグログ（DEBUG level）で詳細を確認可能。
    """

    priority = 80
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
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            # タイムスタンプ差分: 変更されていなければスキップ
            if not graph.is_file_modified(str(file_path)):
                logger.debug(f"Skipping unchanged file: {node.name}")
                continue

            # キャッシュからABQDataを取得（または新規パースしてキャッシュに保存）
            cached_abq = self._get_or_parse_inp(graph, str(file_path))

            stats = extract_mesh_stats(
                file_path, verbose=False, cached_abq_data=cached_abq
            )
            if stats is None:
                logger.debug(f"extract_mesh_stats returned None for {node.name}")
                continue

            if stats.get("node_count"):
                node.properties["mesh_node_count"] = stats["node_count"]
            if stats.get("element_count"):
                node.properties["mesh_element_count"] = stats["element_count"]
            if stats.get("element_types"):
                node.properties["mesh_element_types"] = stats["element_types"]
            if stats.get("elset_summary"):
                node.properties["mesh_elset_summary"] = stats["elset_summary"]
            if stats.get("quality"):
                node.properties["mesh_quality"] = stats["quality"]
            else:
                logger.debug(
                    f"mesh_quality not computed for {node.name} "
                    f"(node_count={stats.get('node_count', 0)}, "
                    f"element_count={stats.get('element_count', 0)})"
                )

        return graph
