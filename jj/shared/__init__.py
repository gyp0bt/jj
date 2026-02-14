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

from .neo4j_schema import NodeLabel, RelType, LABEL_TO_RELTYPE
from .types import Neo4jNodeData, Neo4jRelationData
from .config import Neo4jConfig

__all__ = [
    "NodeLabel",
    "RelType",
    "LABEL_TO_RELTYPE",
    "Neo4jNodeData",
    "Neo4jRelationData",
    "Neo4jConfig",
]
