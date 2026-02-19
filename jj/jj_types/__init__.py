from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeCategory(str, Enum):
    """ノードの分類カテゴリ

    全てのNodeは以下の5カテゴリのいずれかに属する:
    - FILE: ディスク上の物理ファイル
    - DIRECTORY: ディスク上の物理ディレクトリ
    - DATA: ファイルやディレクトリではない論理データ
    - REPOSITORY: File/Directory/Data/Relationの集合体
    - RUN: 入力→処理→出力の実行単位
    """

    FILE = "file"
    DIRECTORY = "directory"
    DATA = "data"
    REPOSITORY = "repository"
    RUN = "run"


# Run構造的リレーションラベル定数
RUN_INPUT = "run_input"
RUN_OUTPUT = "run_output"
RUN_MEDIA = "run_media"

# Run構造的リレーションラベルの集合（判定用）
RUN_RELATION_LABELS = frozenset({RUN_INPUT, RUN_OUTPUT, RUN_MEDIA})


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
