"""shared パッケージ: jjとjjrvの共有契約

Neo4jスキーマ定義、共有データ型、接続設定を提供する。
jjとjjrvは直接のコード依存を持たず、このパッケージで定義された
スキーマ契約のみを共有する。

依存方向:
  services/ → shared/  (OK)
  jjrv/   → shared/  (OK)
  shared/  → services/ (禁止)
  shared/  → jjrv/   (禁止)

[READMEへ戻る](../README.md)
"""

from .config import Neo4jConfig
from .neo4j_schema import LABEL_TO_RELTYPE, NodeLabel, RelType
from .types import Neo4jNodeData, Neo4jRelationData

__all__ = [
    "LABEL_TO_RELTYPE",
    "Neo4jConfig",
    "Neo4jNodeData",
    "Neo4jRelationData",
    "NodeLabel",
    "RelType",
]
