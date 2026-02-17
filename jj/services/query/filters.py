"""汎用フィルタロジック

ノードリストや行データに対するフィルタリング機能を提供する。
type/status/activeの基本フィルタに加え、プロパティ条件式
（props.KEY.OPERATOR=VALUE）による数値比較フィルタを汎用的に扱う。

ダッシュボード（services/dashboard）とREST API（services/api）の
両方から利用される共通フィルタ層。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

# ====================================================================
# truthy判定
# ====================================================================


def is_truthy(value: Any) -> bool:
    """bool/文字列両方に対応したtruthy判定

    YAML経由の値はbool True/Falseだが、GraphService.file_to_node()では
    文字列 "true"/"false" として格納される。両方を正しく扱う。

    Args:
        value: チェック対象の値

    Returns:
        True と見なせる場合 True
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


# ====================================================================
# 基本フィルタ（type / status / active）
# ====================================================================


def apply_filters(
    rows: list[dict[str, Any]],
    type_filter: str | None = None,
    status_filter: str | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """汎用フィルタを適用

    Args:
        rows: フィルタ対象の全行データ
        type_filter: タイプフィルタ（Noneまたは"すべて"で無効）
        status_filter: ステータスフィルタ（Noneまたは"すべて"で無効）
        active_only: Trueの場合activeのみ

    Returns:
        フィルタ適用後の行データ
    """
    filtered = rows
    if type_filter and type_filter != "すべて":
        filtered = [r for r in filtered if r.get("type") == type_filter]
    if status_filter and status_filter != "すべて":
        filtered = [r for r in filtered if r.get("analysis_status") == status_filter]
    if active_only:
        filtered = [r for r in filtered if is_truthy(r.get("active"))]
    return filtered


def apply_saved_view_filters(rows: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    """保存済みビューのフィルタを適用

    Args:
        rows: フィルタ対象の全行データ
        filters: 保存済みフィルタ条件

    Returns:
        フィルタ適用後の行データ
    """
    if not filters:
        return rows

    filtered = rows
    for key, value in filters.items():
        if key == "active":
            if is_truthy(value):
                filtered = [r for r in filtered if is_truthy(r.get("active"))]
            else:
                filtered = [r for r in filtered if not is_truthy(r.get("active"))]
        elif key == "type" and value != "すべて":
            filtered = [r for r in filtered if r.get("type") == value]
        elif key == "analysis_status" and value != "すべて":
            filtered = [r for r in filtered if r.get("analysis_status") == value]
        else:
            filtered = [r for r in filtered if r.get(key) == value]

    return filtered


def saved_view_filters_to_provider_filters(
    filters: dict[str, Any],
) -> dict[str, Any]:
    """保存済みビューのフィルタをDashboardDataProvider.get_*のfilters形式に変換"""
    result: dict[str, Any] = {}
    for key, value in filters.items():
        result[key] = value
    return result


# ====================================================================
# グローバル + ローカルフィルタ結合
# ====================================================================


def merge_filters(
    global_filters: dict[str, Any],
    local_filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """グローバルフィルタとローカルフィルタをマージ

    ローカルフィルタはグローバルフィルタを上書き（AND結合の代わりに
    ローカル優先でマージ）する。ローカルフィルタが空の場合は
    グローバルフィルタのみ返す。

    Args:
        global_filters: グローバルフィルタ条件
        local_filters: ローカルフィルタ条件（オプショナル）

    Returns:
        マージ済みフィルタ条件
    """
    if not local_filters:
        return dict(global_filters) if global_filters else {}
    merged = dict(global_filters) if global_filters else {}
    merged.update(local_filters)
    return merged


def apply_chained_filters(
    rows: list[dict[str, Any]],
    global_filters: dict[str, Any],
    local_filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """グローバル→ローカルの順でフィルタを適用

    グローバルフィルタで絞り込んだ結果に対し、さらにローカルフィルタを
    適用する。ローカルフィルタはオプショナルで、指定しない場合は
    グローバルフィルタのみ適用される。

    Args:
        rows: フィルタ対象の全行データ
        global_filters: グローバルフィルタ条件
        local_filters: ローカルフィルタ条件（オプショナル）

    Returns:
        フィルタ適用後の行データ
    """
    filtered = apply_saved_view_filters(rows, global_filters)
    if local_filters:
        filtered = apply_saved_view_filters(filtered, local_filters)
    return filtered


# ====================================================================
# プロパティ条件式フィルタ（props.KEY.OPERATOR=VALUE）
# ====================================================================

# パターン: props.KEY.OPERATOR（例: props.RF3.gt, props.temperature.le）
PROP_FILTER_PATTERN = re.compile(r"^props\.(.+)\.(eq|ne|gt|ge|lt|le)$")

# 比較オペレータの実装
OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
}


def parse_prop_filters(
    query_params: dict[str, str],
) -> list[tuple[str, str, float]]:
    """クエリパラメータからプロパティフィルターを抽出する

    Args:
        query_params: リクエストのクエリパラメータ辞書

    Returns:
        [(プロパティキー, オペレータ, 比較値), ...] のリスト
    """
    filters: list[tuple[str, str, float]] = []
    for key, value in query_params.items():
        match = PROP_FILTER_PATTERN.match(key)
        if match:
            prop_key = match.group(1)
            operator = match.group(2)
            try:
                num_value = float(value)
                filters.append((prop_key, operator, num_value))
            except (ValueError, TypeError):
                continue
    return filters


def apply_prop_filters(
    items: list[Any],
    filters: list[tuple[str, str, float]],
    prop_getter: Callable[[Any, str], Any] | None = None,
) -> list[Any]:
    """プロパティ比較フィルターを適用する

    items の各要素から prop_getter でプロパティ値を取得し、
    filters の全条件を満たす要素のみ返す。

    Args:
        items: フィルタ対象のリスト
        filters: [(プロパティキー, オペレータ, 比較値), ...]
        prop_getter: (item, key) -> value を返す関数。
                     省略時は item.get(key)（dict想定）。

    Returns:
        フィルタ通過したアイテムリスト
    """
    if not filters:
        return items

    if prop_getter is None:

        def prop_getter(item, key):
            return item.get(key)

    result: list[Any] = []
    for item in items:
        passed = True
        for prop_key, operator, compare_value in filters:
            prop_value = prop_getter(item, prop_key)
            if prop_value is None:
                passed = False
                break
            try:
                num_prop = float(prop_value)
            except (ValueError, TypeError):
                passed = False
                break
            op_func = OPERATORS.get(operator)
            if op_func is None or not op_func(num_prop, compare_value):
                passed = False
                break
        if passed:
            result.append(item)
    return result


# Node.properties 用のヘルパー
def node_prop_getter(node: Any, key: str) -> Any:
    """Node オブジェクトの properties からプロパティ値を取得する

    apply_prop_filters の prop_getter 引数に渡すためのヘルパー関数。

    Args:
        node: Node オブジェクト（properties属性を持つ）
        key: プロパティキー

    Returns:
        プロパティ値。存在しない場合は None。
    """
    return node.properties.get(key)
