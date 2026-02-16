from abc import ABCMeta

import numpy as np
from numpy.typing import NDArray


def create_custom_meta(subclasses_list: list, name_list: list, require_slots: bool = True):
    """カスタムメタクラスを生成する関数。

    Args:
        * subclasses_list (list): サブクラスが格納されるリスト。
        * require_slots (bool): __slots__の実装を強制するか否か

    Returns:
        Type[ABCMeta]: カスタムメタクラス。
    """

    class CustomMeta(ABCMeta):
        # 新しいサブクラスが作成されるたびに呼び出される
        def __init__(cls, name: str, bases: tuple, namespace: dict):
            # ABCを継承したクラスのみをリストに追加する
            if bases != (object,):
                subclasses_list.append(cls)
                name_list.append(name)

            super().__init__(name, bases, namespace)

            # if require_slots:
            # if "__slots__" not in namespace:
            # raise TypeError(f"{name} は __slots__ を定義する必要があります")
            # if not namespace["__slots__"]:
            # raise ValueError(f"{name} の __slots__ は空であってはなりません")

    return CustomMeta


def cut_dup_numbers(target: list[int] | NDArray, sub: list[int] | NDArray) -> list[int]:
    if not isinstance(target, np.ndarray):
        target = np.array(target)

    if not isinstance(sub, np.ndarray):
        sub = np.array(sub)

    target = np.setdiff1d(target, sub).tolist()
    return target


def cut_isolated_numbers(target: list[int] | NDArray, sub: list[int] | NDArray) -> list[int]:
    """
    target内の要素から、subに含まれない要素を削除する関数。

    Args:
        target (Union[List[int], NDArray]): 処理対象となる整数リストまたは配列
        sub (Union[List[int], NDArray]): 比較対象となる整数リストまたは配列

    Returns:
        List[int]: subに含まれる要素のみを保持したtargetのリスト
    """
    # targetをNumPy配列に変換
    if not isinstance(target, np.ndarray):
        target = np.array(target)

    # subをNumPy配列に変換
    if not isinstance(sub, np.ndarray):
        sub = np.array(sub)

    # target内の要素のうち、subに含まれている要素だけを抽出
    filtered_target = np.intersect1d(target, sub).tolist()

    return filtered_target
