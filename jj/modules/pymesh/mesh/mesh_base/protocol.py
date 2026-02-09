# pymesh/mesh/mesh_base/protocol.py
from __future__ import annotations

from typing import Protocol, runtime_checkable, Iterable, Literal, Optional

import numpy as np
from numpy.typing import NDArray

from ..grandpa import NodesDict, ElementsDict, NsetDict, ElsetDict
from ...typing import NodeCoordArray


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
        name: Optional[str | list[str]] = None,
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray: ...

    def get_element_array_dict(
        self,
        mode: Literal["type", "num_nodes"],
        name: Optional[str | list[str]] = None,
    ) -> dict[str | int, NDArray]: ...

    # --- ラベル・削除系 ---
    def drop_elements_with_labels(self, labels: Iterable[int]) -> None: ...

    def drop_nodes(self, labels: Iterable[int]) -> None: ...

    def drop_unreferenced_nodes(self) -> None: ...

    # --- 座標更新 ---
    def update_node_coord_with_array(
        self, node_coord_array: NodeCoordArray
    ) -> None: ...

    # --- 他 ---
    def get_node_coord(self) -> dict[int, np.ndarray]: ...
    def update_node_coord(self, node_coord: dict[int, np.ndarray]) -> None: ...
    def get_element_coord_array(
        self, name: Optional[str | list[str]] = None
    ) -> NodeCoordArray: ...
