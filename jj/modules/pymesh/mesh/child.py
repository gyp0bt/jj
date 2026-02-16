from dataclasses import dataclass

import numpy as np

from ..misc.matrix import get_jacobian
from ..typing import Coordinate


@dataclass
class BaseChildComponent:
    label: int


@dataclass
class Node(BaseChildComponent):
    nset: str
    label: int
    x: float | None = None
    y: float | None = None
    z: float | None = None
    scalars: dict[str, float] | None = None

    def get_coord(self) -> Coordinate:
        return np.array([self.x, self.y, self.z])


@dataclass
class Element(BaseChildComponent):
    elset: str
    label: int
    type: str
    node_id_list: list[int]
    nodes_list: list[Node] | None = None
    field_scalars: dict[str, float] | None = None

    def get_coord(self) -> Coordinate:
        """要素の重心座標を返す."""
        if self.nodes_list is None:
            raise AttributeError("nodes_list must be set to get element coordinate")
        coord = np.array([node.get_coord() for node in self.nodes_list])  # (Nnode, 3)
        return coord.mean(axis=0)  # (3,)

    def get_determinant_of_jacobian(self):
        if self.nodes_list is None:
            raise AttributeError("nodes_list must be set to get element coordinate")
        if len(self.nodes_list) != 8:
            raise ValueError("nodes_list length must be 8")

        coord = np.array([node.get_coord() for node in self.nodes_list])

        J = get_jacobian(coord, 0.0, 0.0, 0.0)
        return np.linalg.det(J)
