"""テーブル表示用データ変換ユーティリティ

list[str]型カラムの要約表示など、テーブル表示前のデータ変換を提供する。
"""

from __future__ import annotations

from typing import Any


def summarize_list_value(value: Any) -> Any:
    """list[str]型の値から先頭要素を抽出して要約表示用に変換する。

    - None/NaN → None
    - list → 先頭要素（空リストは None）
    - 文字列 → リスト風文字列をパースして先頭要素を抽出
    - その他 → そのまま返す

    Args:
        value: 変換対象の値

    Returns:
        要約表示用の値
    """
    # NaN判定（pandasなしで動くようにする）
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass

    # pandas NAも考慮
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except (ImportError, TypeError, ValueError):
        pass

    if isinstance(value, list):
        return value[0] if value else None

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            stripped = value[1:-1].split(",")[0].replace("'", "").strip()
            return stripped if stripped else None
        except Exception:
            return value

    return value


def summarize_list_columns(
    df: Any,
    columns: list[str],
) -> Any:
    """DataFrame内の指定カラムにsummarize_list_valueを適用する。

    Args:
        df: pandas DataFrame
        columns: 変換対象のカラム名リスト

    Returns:
        変換後のDataFrame（元のDataFrameは変更されない）
    """
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].apply(summarize_list_value)
    return df
