"""グラフクエリ・フィルタ・ソート・変換 + データ供給層

GraphModel に対する汎用クエリ操作・行整形に加え、go_ ノード向けのデータ供給
（旧 DashboardDataProvider）と vocab/units 表示変換を `GraphQuery` に統合する。
画像ファイル名のパラメータ解析・グルーピングは `images` サブモジュールに置く。
UI（streamlit 等）には依存しない — UI層 services/dashboard が本層を描画する。

公開API:
    クエリ + データ供給クラス:
        GraphQuery (query_nodes / query_relations / nodes_to_rows / apply_view、
                    および get_go_table / get_array_plot_data /
                    get_output_images / get_status_summary 等)

    画像グルーピング (images):
        group_images_by_composite_key, extract_path_metadata,
        build_composite_group_key, filter_images_by_keys, collect_group_keys

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
from services.graph.query.images import (
    build_composite_group_key,
    collect_group_keys,
    extract_path_metadata,
    filter_images_by_keys,
    group_images_by_composite_key,
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
    "build_composite_group_key",
    "collect_group_keys",
    "extract_path_metadata",
    "filter_images_by_keys",
    "filter_latest_version",
    "format_float_value",
    "get_base_key",
    "get_file_base_name",
    "group_images_by_composite_key",
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
