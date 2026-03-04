from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Iterator
from functools import wraps
from io import StringIO
from typing import (
    Any,
    Generic,
    Literal,
    TypeVar,
    Union,
)

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

from ..typing import node_coord_array_dtype
from .child import BaseChildComponent, Element, Node
from .misc import is_empty_array

TParent = TypeVar("TParent", bound="BaseParentComponent")
TChild = TypeVar("TChild", bound=BaseChildComponent)


class BaseParentComponent(Generic[TChild], metaclass=ABCMeta):
    dtype = "int32"

    def __init__(
        self,
        data: NDArray,
        options: dict[str, Any],
    ):
        self.data = data
        self.options = options

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})(data={self.data[:5]}\n...\n{self.data[-5:]})"

    def __iter__(self) -> Iterator[NDArray | tuple[float]]:
        yield from iter(self.data)

    def __getitem__(self, label: int) -> TChild:
        return self.get_child(label=label)

    def get_child(self, label: int) -> TChild:
        if not isinstance(label, int):
            label = int(label)
        for i in iter(self):
            if i[0] == label:
                return self.make_child(data=i)
        raise AttributeError(f"{self.__class__.__name__}({self.name}) has no child index '{label}'")

    def sort_labels(self) -> NDArray | None:
        indices = np.argsort(self.data[:, 0])
        self.data = self.data[indices]
        return self.data

    def iter_children(self) -> Iterable[TChild]:
        for i in self.data:
            yield self.make_child(data=i)

    def iter_labels(self) -> Iterable[int]:
        for i in self.data:
            yield i[0]

    def get_labels(self) -> list[int]:
        return list(self.iter_labels())

    def get_children(self) -> list[TChild]:
        return list(self.iter_children())

    @abstractmethod
    def make_child(self, data: ArrayLike) -> TChild:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @classmethod
    def from_array(
        cls: type[TParent],
        arr: ArrayLike | NDArray | list[float] | None,
        options: dict[str, Any],
    ) -> TParent:
        instance = cls(data=np.array([]), options={})
        instance.options = options
        instance.append_array(arr=arr)
        return instance

    def append_array(self, arr: ArrayLike | NDArray | list[float] | None) -> NDArray:
        if not is_empty_array(self.data):
            arr = np.array(arr, dtype=self.dtype)
            self.data = np.append(self.data, arr, axis=0)
        else:
            try:
                self.data = np.array(arr, dtype=self.dtype)
            except Exception:
                self.data = np.array(arr, dtype="U16")
        return self.data

    @classmethod
    def from_dict(cls: type[TParent], data: dict[int, Any], options: dict[str, Any]) -> TParent:
        raise NotImplementedError

    @abstractmethod
    def to_str(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict[int, Any]:
        return {i.label: [i] for i in self.iter_children()}

    def to_array(self) -> NDArray | None:
        """内部データ配列のコピーを返す.

        Returns:
            各サブクラスごとに次のような配列を返す:

            - Nodes : dtype=node_coord_array_dtype の structured array
                      fields=("label","x","y","z"), shape=(N,)
            - Elements : int32 配列, shape=(Ne, 1+num_nodes)
                         先頭列が element label, 以降が node id
            - Nset/Elset : 1次元の int32 配列, shape=(N,)

        NOTE:
            形や dtype はサブクラス実装に依存するが、
            Granpa / Mesher 側は上記の前提で実装している。
        """
        return self.data.copy()


def to_str_if_data_exists(f):
    @wraps(f)
    def wrapper(self: BaseParentComponent, *args, **kwargs):
        if all(i != 0 for i in tuple(self.data.shape)):
            result = f(self, *args, **kwargs)
        else:
            result = ""
        return result

    return wrapper


class Nodes(BaseParentComponent[Node]):
    dtype = node_coord_array_dtype

    @property
    def name(self) -> str:
        if self.options:
            return self.options["nset"]
        return ""

    @to_str_if_data_exists
    def to_str(self) -> str:
        text = f"*NODE, NSET={self.name.upper()}\n"
        df = pd.DataFrame(self.data)
        df["label"] = " " + df["label"].astype(str)
        csv_buffer: StringIO = StringIO()
        df.to_csv(
            csv_buffer,
            index=False,
            header=False,
            lineterminator="\n",
            float_format="%.6E",
        )
        text += csv_buffer.getvalue()
        # for i in self.iter_children():
        # text += f" {i.label}, {i.x:.8f}, {i.y:.8f}, {i.z:8f}\n"
        return text

    def append_array(self, arr: NDArray | list[tuple[float, ...]]):
        if not isinstance(arr[0], tuple):
            arr = [tuple(i) for i in arr]
        super().append_array(arr=arr)
        unique_labels = np.unique(self.data["label"])
        if self.data["label"].size != unique_labels.size:
            raise ValueError(f"節点ラベルが重複しています(重複数：{self.data['label'].size - unique_labels.size})")

    def append_coord_array(self, coord_array: NDArray | list[tuple[float, ...]]):
        if all(i != 0 for i in tuple(self.data.shape)):
            max_label = np.max(self.get_labels())
        else:
            max_label = 0
        arr = [(int(max_label + 1 + i), float(ii[0]), float(ii[1]), float(ii[2])) for i, ii in enumerate(coord_array)]
        self.append_array(arr)

    def make_child(self, data: NDArray | tuple[float, ...]) -> Node:
        return Node(
            nset=self.name,
            label=int(data[0]),
            x=float(data[1]),
            y=float(data[2]),
            z=float(data[3]),
        )


class Elements(BaseParentComponent[Element]):
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name},type={self.type})"

    @property
    def name(self) -> str:
        if self.options:
            return self.options["elset"]
        return ""

    @property
    def type(self) -> str:
        if self.options:
            return self.options["type"]
        return ""

    @to_str_if_data_exists
    def to_str(self) -> str:
        text = f"*ELEMENT, ELSET={self.name.upper()}, TYPE={self.options['type'].upper()}\n"
        df = pd.DataFrame(self.data)
        df[0] = " " + df[0].astype(str)
        csv_buffer: StringIO = StringIO()
        df.to_csv(
            csv_buffer,
            index=False,
            header=False,
            lineterminator="\n",
            float_format="%.6E",
        )
        text += csv_buffer.getvalue()
        return text

    def append_array(self, arr: NDArray | list[tuple[float, ...]]):
        if not isinstance(arr[0], tuple):
            arr = [tuple(i) for i in arr]
        if isinstance(arr, np.ndarray):
            arr = arr.astype(np.int32)
        super().append_array(arr=arr)
        if self.data.ndim == 1:
            raise ValueError(f"array must be 2-dimensional (not {self.data.ndim})")
        unique_labels = np.unique(self.data[:, 0])
        if self.data.shape[0] != unique_labels.size:
            raise ValueError(f"節点ラベルが重複しています(重複数：{self.data.shape[0] - unique_labels.size})")

    def make_child(self, data: NDArray | tuple[float, ...]) -> Element:
        if self.options:
            el_type = self.options["type"]
        else:
            el_type = ""
        return Element(
            elset=self.name,
            type=el_type,
            label=int(data[0]),
            node_id_list=[int(j) for j in data[1:]],
        )


class Nset(BaseParentComponent[Node]):
    @property
    def name(self) -> str:
        if self.options:
            return self.options["nset"]
        return ""

    def make_child(self, data: int) -> Node:
        return Node(nset=self.name, label=data)

    @staticmethod
    def split_into_consecutive_sequences(
        numbers: list[int],
    ) -> tuple[bool, list[list[int]]]:
        """
        指定されたリストの中から連番を抽出し、連番ごとのリストに分割する。
        また、連番が含まれているかどうかのブール値も返す。

        Args:
            numbers (list[int]): 元の整数リスト。

        Returns:
            Tuple[bool, list[list[int]]]: 連番が含まれているかどうかのブール値と、連番ごとのリストを格納したリスト。
        """
        if not numbers:
            return False, []

        numbers = list(set(numbers))
        numbers.sort()
        result = []
        current_sequence = [numbers[0]]
        has_consecutive = False

        for i in range(1, len(numbers)):
            if isinstance(numbers[i - 1], int) and numbers[i] == numbers[i - 1] + 1:
                current_sequence.append(numbers[i])
                has_consecutive = True
            else:
                result.append(current_sequence)
                current_sequence = [numbers[i]]

        result.append(current_sequence)
        return has_consecutive, result

    @staticmethod
    def _to_str(instance: BaseParentComponent, mode: Literal["ELSET", "NSET"]) -> str:
        has_consecutive, consecutive_labels_list = Nset.split_into_consecutive_sequences(instance.get_labels())

        if has_consecutive:
            text = f"*{mode}, {mode}={instance.name.upper()}, GENERATE\n"
            for labels in consecutive_labels_list:
                text += f" {labels[0]}, {labels[-1]}, 1\n"

        else:
            text = f"*{mode}, {mode}={instance.name.upper()}\n"
            all_arr = np.array(instance.data)
            n = 8

            almost_all_arr = all_arr[: int(all_arr.size // n * n)].reshape(-1, n)
            extra_arr = all_arr[almost_all_arr.size :]

            if almost_all_arr.size + extra_arr.size != all_arr.size:
                raise ValueError

            df = pd.DataFrame(almost_all_arr)
            df[0] = " " + df[0].astype(str)
            csv_buffer: StringIO = StringIO()
            df.to_csv(
                csv_buffer,
                index=False,
                header=False,
                lineterminator="\n",
                float_format="%.6E",
            )
            text += csv_buffer.getvalue()

            text += " "
            for i in extra_arr:
                text += f"{i}, "
            text = text[:-2] + "\n"

        return text

    def __iter__(self) -> Iterator[int]:
        for i in self.data:
            yield int(i)

    @staticmethod
    def _iter_labels(instance: Union["Nset", "Elset"]) -> Iterator[int | str]:
        yield from instance

    @staticmethod
    def _sort_labels(instance: Union["Nset", "Elset"]) -> NDArray:
        if instance.data:
            instance.data = np.sort(instance.data)
        return instance.data

    @to_str_if_data_exists
    def to_str(self) -> str:
        return Nset._to_str(instance=self, mode="NSET")

    def iter_labels(self) -> Iterable[int]:
        yield from Nset._iter_labels(instance=self)

    def sort_labels(self) -> NDArray | None:
        return Nset._sort_labels(instance=self)


class Elset(BaseParentComponent[Element]):
    @property
    def name(self) -> str:
        if self.options:
            return self.options["elset"]
        return ""

    def __iter__(self) -> Iterator[int | str]:
        for i in self.data:
            try:
                yield int(i)
            except Exception:
                yield str(i)

    def make_child(self, data: int) -> Element:
        return Element(elset=self.name, label=data)

    @to_str_if_data_exists
    def to_str(self) -> str:
        return Nset._to_str(instance=self, mode="ELSET")

    def iter_labels(self) -> Iterator[int | str]:
        yield from Nset._iter_labels(instance=self)

    def sort_labels(self) -> NDArray:
        return Nset._sort_labels(instance=self)
