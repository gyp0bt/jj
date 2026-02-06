import re
from abc import ABCMeta
from collections import defaultdict
from dataclasses import dataclass, field
from typing import (
    Any,
    Generic,
    Iterable,
    Optional,
    Type,
    TypeVar,
)

import numpy as np
from numpy.typing import NDArray

from ..misc.data import cut_dup_numbers, cut_isolated_numbers
from ..typing import *
from .child import BaseChildComponent, Element, Node
from .parent import BaseParentComponent, Elements, Elset, Nodes, Nset

TParent = TypeVar("TParent", bound=BaseParentComponent)
TChild = TypeVar("TChild", bound=BaseChildComponent)


def wildcard_match(pattern: str, text: str) -> bool:
    """'*' を正規表現の '.*' に変換してマッチを判定"""
    # '*' を '.*' に変換、その他は正規表現メタ文字をエスケープ
    regex = ""
    for c in pattern:
        if c == "*":
            regex += ".*"
        else:
            regex += re.escape(c)

    # パターン全体が text 全体にマッチする必要がある場合
    regex = r"^" + regex + r"$"

    return re.match(regex, text) is not None


class BaseGrandpaComponent(Generic[TParent, TChild], metaclass=ABCMeta):
    """Parent群をまとめて管理する基底クラス.

    - self.data は name(str) -> Parent の dict
    - Parent は BaseParentComponent のサブクラス
    """

    def __init__(
        self,
        data: dict[str, TParent],
        parent_class: type[TParent] = BaseParentComponent,
    ):
        self.data = data
        self.parent_class = parent_class

    def __str__(self) -> str:
        text = f"{self.__class__.__name__}("
        if self.data:
            for i in self.data.keys():
                text += f"{i},"
        text += ")"
        return text

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __repr__(self) -> str:
        return str(self)

    def __getitem__(self, key: str) -> TParent:
        return self.data[key]

    def __setitem__(self, key: str, value: TParent):
        self.data[key] = value

    def __len__(self) -> int:
        return len(self.data)

    def clear(self):
        self.data = {}

    def values(self) -> Iterable[TParent]:
        return self.data.values()

    def keys(self) -> Iterable[str]:
        return self.data.keys()

    def items(self) -> Iterable[Any]:
        return self.data.items()

    def iter_children(self, name: Optional[str | list[str]]) -> Iterable[TChild]:
        if name is not None and isinstance(name, str):
            name = [name]

        for parent in self.data.values():
            if name is None or parent.name in name:
                for child in parent.iter_children():
                    yield child

    def get_child(self, label: int) -> TChild:
        for _, parent in self.data.items():
            if label in parent.iter_labels():
                return parent.get_child(label=label)
        raise IndexError(f"{self.__class__.__name__} has no child, label'{label}'")

    def get_children(self, name: Optional[str | list[str]] = None) -> dict[int, TChild]:
        parent_list = self.get_parents_list(name=name)
        children_dict = {}
        for parent in parent_list:
            for child in parent.iter_children():
                children_dict[child.label] = child
        return children_dict

    def get_labels(self, name: Optional[str | list[str]] = None) -> list[int]:
        parent_list = self.get_parents_list(name=name)
        labels = []
        for component in parent_list:
            labels += component.get_labels()
        return labels

    def drop_labels(
        self,
        labels: list[int],
        except_with: bool = False,
    ):
        if not isinstance(labels, list):
            labels = [labels]
        for parent in self.data.values():
            if parent.data.dtype.fields:
                indices = (
                    np.isin(parent.data["label"], labels)
                    if except_with
                    else ~np.isin(parent.data["label"], labels)
                )
                parent.data = parent.data[indices]
            elif parent.data.ndim == 1:
                if except_with:
                    parent.data = np.array(cut_isolated_numbers(parent.data, labels))
                else:
                    parent.data = np.array(cut_dup_numbers(parent.data, labels))
            else:
                indices = (
                    np.isin(parent.data[:, 0], labels)
                    if except_with
                    else ~np.isin(parent.data[:, 0], labels)
                )
                parent.data = parent.data[indices]

    def pop(self, name: Optional[str | list[str]]):
        self.drop_names(name)

    def drop(self, name: Optional[str | list[str]]):
        self.drop_names(name)

    def drop_names(
        self,
        name: Optional[str | list[str]] = None,
        except_name: Optional[str | list[str]] = None,
    ):
        if name is None and except_name is None:
            raise ValueError(f"you must specify at least one of name or except_name")
        elif name is not None and except_name is not None:
            raise ValueError(
                f"you cannot specify name and except_name at once, choice one"
            )
        elif except_name is not None:
            name = [k for k in self.data.keys() if k not in except_name]

        if name is None:
            raise ValueError

        self.data = {k: v for k, v in self.data.items() if k not in name}

    def isin(self, name: str) -> bool:
        return name in self.keys()

    def get_parents_list(
        self,
        name: str | list[str] | None = None,
    ) -> list[TParent]:
        """名前（キー）で parent をフィルタして取得する.

        name が None のときは全 parent を返す。
        name が str/list[str] のときは、現在はワイルドカード
        ('*' を含む glob) に対応したマッチングを行う。

        NOTE:
            ElementsDict では elset,type 形式のキーを使うため、
            そちらで get_parents_list をオーバーライドしている。
        """
        if name is not None and isinstance(name, str):
            name = [name]

        parent_list: list[TParent] = []
        for key, component in self.data.items():
            if name is None:
                parent_list.append(component)
            else:
                if any(wildcard_match(pattern=i, text=key) for i in name):
                    parent_list.append(component)
        return parent_list

    def get_array(
        self,
        name: str | list[str] | None = None,
    ) -> NDArray | NodeCoordArray:
        """parent 配下のデータ配列を縦方向に単純結合する.

        各 parent の to_array() が返す ndarray/structured array を、
        「列数が一致している」という前提で単純に np.append する。
        列数が異なる場合の右側パディング等は行わない。

        ElementsDict のように polymorphism を許容したい場合は、
        サブクラス側で get_array をオーバーライドすること。
        """
        parents_list = self.get_parents_list(name=name)
        arr: NDArray | NodeCoordArray | None = None

        for parent in parents_list:
            parent_array = parent.to_array()
            if arr is None:
                arr = parent_array
            else:
                if not isinstance(parent_array, np.ndarray):
                    raise TypeError(
                        f"to_array() が ndarray を返していません: {type(parent_array)}"
                    )
                arr = np.append(arr, parent_array, axis=0)

        if arr is None:
            raise ValueError("データが存在しません。get_parents_list の結果が空です。")

        return arr

    def copy(self) -> "BaseGrandpaComponent[TParent, TChild]":
        """自分と同じクラスのインスタンスを deep copy して返す."""
        new_data: dict[str, TParent] = {
            k: self.parent_class.from_array(
                arr=v.data.copy(),
                options=dict(v.options),
            )
            for k, v in self.data.items()
        }
        return self.__class__(data=new_data, parent_class=self.parent_class)


@dataclass
class ElementField:
    """要素スカラー場を表現する簡易コンテナ.

    NOTE:
        現状は ElementsDict にぶら下がっているが、
        将来的には Mesher など別コンポーネントへ移動する候補。
    """

    name: str = ""
    field_scalars: dict[int, float] = field(default_factory=dict)


class NodesDict(BaseGrandpaComponent[Nodes, Node]):
    def __init__(self, data: dict[str, Nodes], parent_class: Type[Nodes] = Nodes):
        self.data = data
        self.parent_class = parent_class


class ElementsDict(BaseGrandpaComponent[Elements, Element]):
    parent_class = Elements

    def __init__(
        self, data: dict[str, Elements], parent_class: Type[Elements] = Elements
    ):
        self.data = data
        # 要素場名 -> ElementField
        self.fields: dict[str, ElementField] = defaultdict(ElementField)
        self.parent_class = parent_class

    def get_elset_key_from_elset_and_type(self, elset: str, type: str) -> str:
        return f"{elset},type={type}"

    def get_parent_with_elset(self, elset_name: str, type: str):
        key = self.get_elset_key_from_elset_and_type(elset=elset_name, type=type)
        return self.data[key]

    def drop_names(
        self,
        name: Optional[str | list[str]] = None,
        except_name: Optional[str | list[str]] = None,
    ):
        if name is None and except_name is None:
            raise ValueError(f"you must specify at least one of name or except_name")
        elif name is not None and except_name is not None:
            raise ValueError(
                f"you cannot specify name and except_name at once, choice one"
            )

        if isinstance(name, str):
            name = [name]
        elif except_name is not None:
            if not isinstance(except_name, list):
                except_name = [except_name]
            name = [k for k in self.data.keys() if k not in except_name]

        if name is not None:
            self.data = {
                k: v
                for k, v in self.data.items()
                if all([k.split(",")[0] != i for i in name])
            }

        if name is None:
            raise ValueError("何かおかしい")

    def get_array(
        self,
        name: Optional[str | list[str]] = None,
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray:
        """親オブジェクト群の配列をまとめて取得する.

        各 parent の to_array() が返す ndarray を縦方向に結合する。
        allow_polymorphism=True の場合は、列数が異なる配列同士を
        invalid_node で右側パディングしてから結合する。

        Args:
            name: 親オブジェクトのフィルタ条件（実装依存）。
            allow_polymorphism: True のとき、列数の異なる配列もパディングして結合する。
            invalid_node: パディングに用いる値。

        Returns:
            shape (N, M) の ndarray。N は全 parent の行数の合計、
            M は結合後の最大列数。
        """
        parents_list = self.get_parents_list(name=name)

        arr: Optional[NDArray] = None

        for parent in parents_list:
            parent_array = parent.to_array()

            if not isinstance(parent_array, np.ndarray):
                raise TypeError(
                    f"to_array() が ndarray を返していません: {type(parent_array)}"
                )

            if arr is None:
                # 最初の配列を基準として採用
                arr = parent_array
                continue

            # ここから 2個目以降
            if arr.ndim != parent_array.ndim:
                raise ValueError(
                    f"配列の次元数が一致しません: arr.ndim={arr.ndim}, "
                    f"parent_array.ndim={parent_array.ndim}"
                )

            if arr.ndim != 2:
                # 必要なら 1次元対応など広げてもよいが、メッシュ用途なら2D前提でよいはず
                raise ValueError("get_array は 2次元配列 (行×列) を想定しています。")

            n_cols_arr = arr.shape[1]
            n_cols_new = parent_array.shape[1]

            if n_cols_arr != n_cols_new:
                if not allow_polymorphism:
                    raise ValueError(
                        f"列数が一致しません (allow_polymorphism=False): "
                        f"既存={n_cols_arr}, 新規={n_cols_new}"
                    )

                # 列数を合わせるために右側パディング
                max_cols = max(n_cols_arr, n_cols_new)

                if n_cols_arr < max_cols:
                    pad = np.full(
                        (arr.shape[0], max_cols - n_cols_arr),
                        invalid_node,
                        dtype=arr.dtype,
                    )
                    arr = np.concatenate([arr, pad], axis=1)

                if n_cols_new < max_cols:
                    pad_new = np.full(
                        (parent_array.shape[0], max_cols - n_cols_new),
                        invalid_node,
                        dtype=parent_array.dtype,
                    )
                    parent_array = np.concatenate([parent_array, pad_new], axis=1)

            # ここまで来た時点で列数は一致している
            arr = np.append(arr, parent_array, axis=0)

        if arr is None:
            raise ValueError("データが存在しません。get_parents_list の結果が空です。")

        arr = arr[:, ~(arr == invalid_node).all(axis=0)]

        return arr

    def iter_by_elset(self, elset: str) -> Iterable[tuple[str, Elements]]:
        """elset 名でフィルタして (key, parent) を返す."""
        for key, parent in self.data.items():
            # "gmain,type=C3D8" -> "gmain"
            base_elset = key.split(",")[0]
            if base_elset == elset:
                yield key, parent

    def get_by_elset(self, elset: str) -> list[Elements]:
        """指定 elset 名に属する Elements をすべて返す."""
        return [parent for _, parent in self.iter_by_elset(elset)]

    def get_by_elset_and_type(self, elset: str, etype: str) -> Elements:
        """elset + type で 1 つの Elements を取得する."""
        key = self.get_elset_key_from_elset_and_type(elset=elset, type=etype)
        try:
            return self.data[key]
        except KeyError:
            raise KeyError(f"ElementsDict にキー {key!r} は存在しません。")

    def get_parents_list(
        self,
        name: str | list[str] | None = None,
    ) -> list[Elements]:
        """ElementsDict 用の get_parents_list.

        互換性のため、従来の以下の仕様を維持する:

        - name に "*" や "," を含む場合:
            BaseGrandpaComponent.get_parents_list と同様に、
            キー文字列に対するワイルドカードマッチを行う。
            例: "gmain,*", "gmain,type=C3D8"

        - name が単なる elset 名の場合 (例: "gmain"):
            自動的に "gmain,*" に変換して、同 elset に属する
            全ての Elements を返す。

        将来的には get_by_elset / get_by_elset_and_type の使用を推奨する。
        """
        if name is not None:
            if not isinstance(name, list):
                name = [name]

            new_name: list[str] = []
            for i in name:
                if "*" in i or "," in i:
                    # 既にフルパターンとして扱う
                    new_name.append(i)
                else:
                    # 素の elset 名とみなし、"elset,*" に変換
                    new_name.append(i + ",*")
            name = new_name

        return super().get_parents_list(name=name)


class NsetDict(BaseGrandpaComponent[Nset, Node]):
    def __init__(self, data: dict[str, Nset], parent_class: Type[Nset] = Nset):
        self.data = data
        self.parent_class = parent_class


class ElsetDict(BaseGrandpaComponent[Elset, Element]):
    def __init__(self, data: dict[str, Elset], parent_class: Type[Elset] = Elset):
        self.data = data
        self.parent_class = parent_class
