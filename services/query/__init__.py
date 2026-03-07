"""jjレベル汎用クエリ・フィルタ・ソート層

ダッシュボード（services/dashboard）とREST API（services/api）で
共通利用されるフィルタ/ソートロジックを集約する。

API固有だったprops条件式フィルタ（props.KEY.OPERATOR=VALUE）を
汎用関数として提供し、dict行データ・Nodeオブジェクトの両方で
利用可能にする。

公開API:
    フィルタ:
        is_truthy, apply_filters, apply_saved_view_filters,
        saved_view_filters_to_provider_filters,
        parse_prop_filters, apply_prop_filters, node_prop_getter,
        PROP_FILTER_PATTERN, OPERATORS

    ソート:
        sort_columns_by_vocab, select_table_columns, sort_rows_by_index

    変換:
        summarize_list_columns, summarize_list_value

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from services.query.filters import (
    OPERATORS,
    PROP_FILTER_PATTERN,
    apply_filters,
    apply_prop_filters,
    apply_saved_view_filters,
    is_truthy,
    node_prop_getter,
    parse_prop_filters,
    saved_view_filters_to_provider_filters,
)
from services.query.sort import (
    get_base_key,
    select_table_columns,
    sort_columns_by_vocab,
    sort_rows_by_index,
)
from services.query.transform import summarize_list_columns, summarize_list_value

__all__ = [
    "OPERATORS",
    "PROP_FILTER_PATTERN",
    "apply_filters",
    "apply_prop_filters",
    "apply_saved_view_filters",
    "get_base_key",
    "is_truthy",
    "node_prop_getter",
    "parse_prop_filters",
    "saved_view_filters_to_provider_filters",
    "select_table_columns",
    "sort_columns_by_vocab",
    "sort_rows_by_index",
    "summarize_list_columns",
    "summarize_list_value",
]
