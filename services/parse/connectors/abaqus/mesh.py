"""Abaqusメッシュユーティリティ（後方互換）

このモジュールはplugins.abaqus.parse.meshからre-exportしています。
新規コードでは plugins.abaqus.parse.mesh を直接importしてください。
"""

from plugins.abaqus.parse.mesh import (
    _safe_import_pymesh,
    extract_element_quality_stats,
    extract_material_elset_mapping,
    extract_mesh_stats,
    extract_mesh_topology_groups,
)

__all__ = [
    "_safe_import_pymesh",
    "extract_element_quality_stats",
    "extract_material_elset_mapping",
    "extract_mesh_stats",
    "extract_mesh_topology_groups",
]
