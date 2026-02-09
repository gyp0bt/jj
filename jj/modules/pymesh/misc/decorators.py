import time

import sys
import types
from functools import wraps
from typing import Callable, TypeVar, Any, cast, Type

F = TypeVar("F", bound=Callable[..., Any])


def timeit_methods(cutoff: float = 0.1) -> Any:
    """
    クラスデコレータ: 全メソッドの実行時間を計測して出力する。

    Args:
        cls (Any): デコレートするクラス

    Returns:
        Any: ラップされたクラス
    """

    def wrapper(cls: Any) -> Any:
        # クラスの全ての属性をチェック
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value):  # 関数かどうかを確認
                setattr(cls, attr_name, timeit(attr_value, cutoff=cutoff))
        return cls

    return wrapper


def timeit(func: Callable) -> Callable:
    """計測用ラッパ（簡略版）"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        import time

        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.perf_counter()
            self = args[0] if args else None
            cutoff = getattr(self, "timeit_cutoff", 0.0)
            passed = end - start
            if passed >= cutoff:
                print(f"    (timeit) {func.__qualname__} took {passed:.2e} s")

    return wrapper


class TimeitMeta(type):
    """クラスに生えているメソッド（継承分も含む）を全部 timeit でラップするメタクラス"""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> Type[Any]:
        # まず普通にクラスを作る
        cls = super().__new__(mcs, name, bases, namespace)

        # すでにラップ済みかどうかのマーカー
        MARK_ATTR = "__timeit_wrapped__"

        # cls から見えるメソッドを一通り舐める
        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue  # dunder は放置（必要なら調整）

            # すでに cls 固有として namespace に入っていればそちら優先
            attr = getattr(cls, attr_name)

            # 二重ラップ防止
            if getattr(attr, MARK_ATTR, False):
                continue

            # classmethod/staticmethod/function を判別
            # ※注意: getattr すると descriptor がバインドされるので __dict__ を見る方が安全
            orig = None
            owner_dict = None

            for base in cls.__mro__:
                if attr_name in base.__dict__:
                    owner_dict = base.__dict__
                    orig = owner_dict[attr_name]
                    break

            if orig is None:
                continue

            # staticmethod / classmethod / function 判定
            if isinstance(orig, classmethod):
                func_obj = orig.__func__
                wrapped_func = timeit(func_obj)
                setattr(wrapped_func, MARK_ATTR, True)
                wrapped = classmethod(wrapped_func)
            elif isinstance(orig, staticmethod):
                func_obj = orig.__func__
                wrapped_func = timeit(func_obj)
                setattr(wrapped_func, MARK_ATTR, True)
                wrapped = staticmethod(wrapped_func)
            elif isinstance(orig, types.FunctionType):
                wrapped = timeit(orig)
                setattr(wrapped, MARK_ATTR, True)
            else:
                continue  # プロパティなどは無視

            # サブクラス側に上書き（基底クラス自体は汚さない）
            setattr(cls, attr_name, wrapped)

        return cls
