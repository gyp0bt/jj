# pymesh/mesh/mesh_base/protocol.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from ...typing import NodeCoordArray
from ..grandpa import ElementsDict, ElsetDict, NodesDict, NsetDict


@runtime_checkable
class MesherCoreProtocol(Protocol):
    """DomainOpsMixin 等が依存してよい Mesher のコアインターフェース."""

    nodes_data: NodesDict
    elements_data: ElementsDict
    nset_data: NsetDict
    elset_data: ElsetDict

    # --- ノード関連 ---
    def get_node_coord_array(
        self,
        name: str | None = None,
    ) -> NodeCoordArray: ...

    # --- 要素関連 ---
    def get_element_array(
        self,
        name: str | list[str] | None = None,
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray: ...

    def get_element_array_dict(
        self,
        mode: Literal["type", "num_nodes"],
        name: str | list[str] | None = None,
    ) -> dict[str | int, NDArray]: ...

    # --- ラベル・削除系 ---
    def drop_elements_with_labels(self, labels: Iterable[int]) -> None: ...

    def drop_nodes(self, labels: Iterable[int]) -> None: ...

    def drop_unreferenced_nodes(self) -> None: ...

    # --- 座標更新 ---
    def update_node_coord_with_array(self, node_coord_array: NodeCoordArray) -> None: ...

    # --- 他 ---
    def get_node_coord(self) -> dict[int, np.ndarray]: ...
    def update_node_coord(self, node_coord: dict[int, np.ndarray]) -> None: ...
    def get_element_coord_array(self, name: str | list[str] | None = None) -> NodeCoordArray: ...
