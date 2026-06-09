from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeCategory(str, Enum):
    """ノードの分類カテゴリ

    全てのNodeは以下の4カテゴリのいずれかに属する:
    - FILE: ディスク上の物理ファイル
    - DIRECTORY: ディスク上の物理ディレクトリ
    - DATA: ファイルやディレクトリではない論理データ
    - REPOSITORY: File/Directory/Data/Relationの集合体
    """

    FILE = "file"
    DIRECTORY = "directory"
    DATA = "data"
    REPOSITORY = "repository"


class Node(BaseModel):
    id: int
    type: str
    name: str
    format: str
    properties: dict[str, Any] = Field(default_factory=dict)
    category: NodeCategory = NodeCategory.FILE


class Relation(BaseModel):
    id: int
    label: str
    node1_id: int
    node2_id: int


class GraphModel(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)

    @classmethod
    def empty(cls) -> GraphModel:
        return cls(nodes=[], relations=[])
