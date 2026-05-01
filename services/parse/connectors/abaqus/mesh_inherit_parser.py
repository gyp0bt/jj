"""Abaqusメッシュ継承パーサー（後方互換）

このモジュールはplugins.abaqus.parse.mesh_inherit_parserからre-exportしています。
新規コードでは plugins.abaqus.parse.mesh_inherit_parser を直接importしてください。
"""

from plugins.abaqus.parse.mesh_inherit_parser import MeshInheritParser

__all__ = ["MeshInheritParser"]
