from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: int
    type: str
    name: str
    format: str
    properties: dict[str, Any] = Field(default_factory=dict)


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
