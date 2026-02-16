# pymesh/mesh/mesh_base/decorater.py

"""
Mesher などのクラスのメソッド呼び出し回数を簡易に計測するためのユーティリティ.

本モジュールは開発・プロファイル用途のみを想定しており、
本番運用ではインポートしない / メタクラスを適用しない運用を推奨する。
"""

from __future__ import annotations

import atexit
import functools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

# プロセス内で共有するメソッド呼び出しカウンタ
COUNTER: dict[str, int] = {}

# 出力先。必要に応じてリポジトリルートなどに変更すること
OUTPUT_PATH = Path("C:\\COMMAND\\pymesh\\.method_count.json")


def _wrap_method(name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """メソッドをラップして呼び出し回数をカウントする.

    Args:
        name: メソッド名
        func: 元の関数オブジェクト

    Returns:
        ラップ済みの関数
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        COUNTER[name] = COUNTER.get(name, 0) + 1
        return func(*args, **kwargs)

    return wrapper


class CountMethodsMeta(type):
    """メソッド呼び出し回数をカウントするためのメタクラス.

    public メソッド（先頭が "_" で始まらない callable）のみを対象とする。
    staticmethod / classmethod は現状対象外。
    """

    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ):
        new_namespace: dict[str, Any] = {}
        for attr_name, value in namespace.items():
            # private / 特殊メソッドはスキップ
            if attr_name.startswith("_"):
                new_namespace[attr_name] = value
                continue

            # staticmethod / classmethod はそのまま
            if isinstance(value, (staticmethod, classmethod)):
                new_namespace[attr_name] = value
                continue

            if callable(value):
                new_namespace[attr_name] = _wrap_method(attr_name, value)
            else:
                new_namespace[attr_name] = value

        return super().__new__(mcls, name, bases, new_namespace, **kwargs)


def dump_counts() -> None:
    """COUNTER の内容を JSON に書き出す.

    既存ファイルが存在する場合はメソッド名ごとに加算マージする。
    """
    if not COUNTER:
        return

    if OUTPUT_PATH.exists():
        try:
            with OUTPUT_PATH.open("r", encoding="utf-8") as f:
                prev: dict[str, int] = json.load(f)
        except Exception:
            prev = {}
    else:
        prev = {}

    for k, v in COUNTER.items():
        prev[k] = prev.get(k, 0) + v

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(prev, f, ensure_ascii=False, indent=2)


# プロセス終了時に一度だけダンプ
atexit.register(dump_counts)
