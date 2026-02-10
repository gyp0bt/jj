"""Abaqusメッシュパーサー

pymeshを使ってメッシュ統計情報をノードのプロパティに付与する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class AbaqusMeshParser(AbstractFileParser):
    """pymeshを使ってメッシュ統計情報をノードのプロパティに付与"""

    priority = 80

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        from jj.services.parse.connectors.abaqus.mesh import extract_mesh_stats

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            stats = extract_mesh_stats(file_path, verbose=False)
            if stats is None:
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

        return graph
