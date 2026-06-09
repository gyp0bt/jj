"""MeshInheritParser 互換re-export

status-088で実体をservices/parse/connectors/abaqus/mesh_inherit_parser.pyに移動。
既存のimportの後方互換のためre-exportを残す。
Abaqusプラグインのregister()経由で自動登録される。

[READMEへ戻る](../../../../README.md)
"""

# 実体はAbaqusプラグインに移動済み。import互換のためre-export。
# 注意: このモジュールのimportだけではパーサー自動登録は発動しない
# (既にAbaqusプラグイン経由で登録済みのため二重登録を避ける)。
from plugins.abaqus.parse.mesh_inherit_parser import MeshInheritParser  # noqa: F401
