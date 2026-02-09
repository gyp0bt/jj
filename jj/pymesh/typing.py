from typing import Any

import numpy as np
from numpy.typing import DTypeLike, NDArray

__all__ = [
    "Coordinate",
    "CoordinateDict",
    "node_coord_array_dtype",
    "NodeCoordArray",
]

Coordinate = NDArray[np.float32]
# CoordinateDict = Dict[str, NDArray[np.float32]]
CoordinateDict = dict[int, NDArray[np.float32]]
node_coord_array_dtype: DTypeLike = np.dtype(
    [("label", "int32"), ("x", "float32"), ("y", "float32"), ("z", "float32")]
)
NodeCoordArray = NDArray[node_coord_array_dtype]


def name_to_name_list(name: str | list[str]) -> list[str]:
    if not isinstance(name, list):
        name = [name]
    return name
