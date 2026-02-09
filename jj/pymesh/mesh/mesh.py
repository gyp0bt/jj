# pymesh/mesh/mesh.py
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import numpy as np
from numpy.typing import ArrayLike, DTypeLike, NDArray

from .mesh_base.core import CoreMesher
from .mesh_base.decorater import CountMethodsMeta
from .mesh_base.ops_domain import DomainOpsMixin


class Mesher(DomainOpsMixin, CoreMesher, metaclass=CountMethodsMeta):
    """全部載せMesherクラス"""
