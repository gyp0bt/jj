"""共有データ型 - Neo4j投入用の拡張型

jj_typesのNode/Relation/GraphModelをベースに、
Neo4j投入に必要な追加情報を持つデータ型を定義する。

[READMEへ戻る](../README.md)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Neo4jNodeData(BaseModel):
    """Neo4jに投入するノードデータ"""

    label: str  # NodeLabel値（JJFile, JJMaterial等）
    jj_id: int  # jj内部ID
    name: str
    node_type: str  # jjのNode.type
    node_format: str  # jjのNode.format
    project: str  # jjプロジェクトパス
    properties: dict[str, Any] = Field(default_factory=dict)


class Neo4jRelationData(BaseModel):
    """Neo4jに投入するリレーションデータ"""

    rel_type: str  # RelType値（INCLUDES, HAS_OUTPUT等）
    source_jj_id: int
    target_jj_id: int
    project: str
    properties: dict[str, Any] = Field(default_factory=dict)
