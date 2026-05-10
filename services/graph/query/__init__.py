"""グラフクエリ・フィルタ・ソート・変換層

GraphModel に対する汎用クエリ操作と、行データに対するフィルタ/ソート/
変換ロジックを集約する。services/dashboard と services/api の双方から
利用される。dashboard 固有の表示変換（vocab/units/verbose_name）は
ここには含めない — それらは DashboardDataProvider に残す。

公開API:
    クエリクラス:
        GraphQuery (4 メソッド: query_nodes, query_relations,
                    nodes_to_rows, apply_view)

    フィルタ:
        is_truthy, apply_filters, apply_saved_view_filters,
        saved_view_filters_to_provider_filters,
        merge_filters, apply_chained_filters,
        parse_prop_filters, apply_prop_filters, node_prop_getter,
        PROP_FILTER_PATTERN, OPERATORS

    ソート:
        sort_columns_by_vocab, select_table_columns, sort_rows_by_index,
        get_base_key, get_file_base_name

    変換:
        summarize_list_columns, summarize_list_value

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from services.graph.query.filters import (
    OPERATORS,
    PROP_FILTER_PATTERN,
    apply_chained_filters,
    apply_filters,
    apply_prop_filters,
    apply_saved_view_filters,
    filter_latest_version,
    is_truthy,
    merge_filters,
    node_prop_getter,
    parse_prop_filters,
    saved_view_filters_to_provider_filters,
)
from services.graph.query.graph_query import (
    EXT_KEYS_FIELD,
    GraphQuery,
    format_float_value,
)
from services.graph.query.sort import (
    get_base_key,
    get_file_base_name,
    select_table_columns,
    sort_columns_by_vocab,
    sort_rows_by_index,
)
from services.graph.query.transform import summarize_list_columns, summarize_list_value

__all__ = [
    "EXT_KEYS_FIELD",
    "OPERATORS",
    "PROP_FILTER_PATTERN",
    "GraphQuery",
    "apply_chained_filters",
    "apply_filters",
    "apply_prop_filters",
    "apply_saved_view_filters",
    "filter_latest_version",
    "format_float_value",
    "get_base_key",
    "get_file_base_name",
    "is_truthy",
    "merge_filters",
    "node_prop_getter",
    "parse_prop_filters",
    "saved_view_filters_to_provider_filters",
    "select_table_columns",
    "sort_columns_by_vocab",
    "sort_rows_by_index",
    "summarize_list_columns",
    "summarize_list_value",
]
