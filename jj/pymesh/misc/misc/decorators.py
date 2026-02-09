import time
import types
from functools import wraps
from typing import Any, Callable


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
    """
    関数デコレータ: 関数の実行時間を計測して出力する。

    Args:
        func (Callable): デコレートする関数

    Returns:
        Callable: 実行時間を計測するラップされた関数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 実行前の時間を記録
        result = func(*args, **kwargs)  # 関数実行
        end_time = time.time()  # 実行後の時間を記録
        passed_time = end_time - start_time
        cutoff = getattr(args[0], "timeit_cutoff", 0.1)
        if passed_time >= cutoff:
            print(f"    (timeit) {func.__name__} took {passed_time:.2e} seconds")
        return result

    return wrapper


class TimeitMeta(type):
    """
    メタクラス: すべての関数/メソッドに対してtimeitデコレータを適用
    """

    def __new__(mcs, name, bases, namespace):
        new_ns = {}

        for attr_name, attr_value in namespace.items():
            if isinstance(attr_value, (types.FunctionType, classmethod, staticmethod)):
                original = attr_value

                # method or staticmethod or classmethodの実体取得と再ラップ
                if isinstance(attr_value, classmethod):
                    wrapped = classmethod(timeit(attr_value.__func__))
                elif isinstance(attr_value, staticmethod):
                    wrapped = staticmethod(timeit(attr_value.__func__))
                else:
                    wrapped = timeit(attr_value)

                new_ns[attr_name] = wrapped
            else:
                new_ns[attr_name] = attr_value

        return super().__new__(mcs, name, bases, new_ns)
