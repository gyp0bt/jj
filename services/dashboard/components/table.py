"""テーブルビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from services.dashboard.components import PageComponent, ViewConfig
from services.dashboard.data_provider import format_float_value

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class TableViewConfig(ViewConfig):
    """テーブルビュー設定コンポーネント"""

    view_type = "table"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # テーブルビューにはビュータイプ固有の設定はない
        return {}


def render_table_section(
    provider: DashboardDataProvider,
    dashboard_config: DashboardConfig,
    filtered: list[dict[str, Any]],
    total_rows: int,
    vocab: dict[str, str] | None = None,
    *,
    grid_key: str | None = None,
    download_key: str = "go_table",
) -> None:
    """テーブルセクションの描画（OverviewPage等から再利用可能）

    フィルタ済みの行データをDataFrameに変換し、AgGrid/st.dataframeで表示する。

    Args:
        provider: データプロバイダ
        dashboard_config: ダッシュボード設定
        filtered: フィルタ済みの行データ
        total_rows: フィルタ前の総行数
        vocab: vocab辞書（表示名変換用）
        grid_key: AgGridのwidgetキー（Noneでデフォルト）
        download_key: Excelダウンロードのキー
    """
    import streamlit as st

    from services.dashboard.query import select_table_columns
    from services.dashboard.widgets import render_excel_download, try_render_aggrid

    st.caption(f"{len(filtered)} / {total_rows} 件")

    if not filtered:
        st.info("条件に一致するデータがありません。")
        return

    import pandas as pd

    vn_key = provider._verbose_name_key
    idx_key = provider._index_key
    ver_key = provider._version_key

    # related_filesはネストしているので除外。float値は指数表記フォーマット。
    display_rows = []
    for r in filtered:
        row = {k: v for k, v in r.items() if k != "related_files"}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
            elif isinstance(v, float) and not isinstance(v, bool):
                row[k] = format_float_value(v)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)

    # index/version列をint型に変換（可能な場合）
    for int_key in (idx_key, ver_key):
        if int_key in df.columns:
            df[int_key] = pd.to_numeric(df[int_key], errors="coerce").astype("Int64")

    # nameカラムを表示名で置き換え（verbose_nameキーが存在する場合）
    if vn_key in df.columns:
        df["name"] = df[vn_key]
        df = df.drop(vn_key, axis=1)

    remain_cols = []
    for c in df.columns:
        if np.unique(df[c].to_numpy()).shape[0] > 1:
            remain_cols.append(c)
    df = df[remain_cols]

    # config駆動カラム選択（vocab順ソート対応）
    table_columns = getattr(dashboard_config, "table_columns", None)
    exclude_table_columns = getattr(dashboard_config, "exclude_table_columns", None)
    if not table_columns and provider._global_columns:
        table_columns = provider._global_columns
    selected_cols = select_table_columns(
        list(df.columns), table_columns, exclude_table_columns=exclude_table_columns, vocab=vocab or {}
    )
    if selected_cols:
        df = df[[c for c in selected_cols if c in df.columns]]

    # list[str]型カラムの先頭要素のみ表示（config.list_summary_columnsで制御）
    from services.query.transform import summarize_list_columns

    list_summary_cols = getattr(dashboard_config, "list_summary_columns", ["msg_errors", "dat_errors"])
    df = summarize_list_columns(df, list_summary_cols)

    # カラムヘッダーにvocab変換を適用（表示時のみ）
    if vocab:
        from modules.vocab_display import translate_key

        df = df.rename(columns={c: translate_key(c, vocab) for c in df.columns})

    # AgGridを試行、失敗時はst.dataframeにフォールバック
    if not try_render_aggrid(df, grid_key=grid_key):
        st.dataframe(df, width="stretch", hide_index=True)

    # Excelダウンロードボタン
    render_excel_download(df, download_key)


class TablePage(PageComponent[TableViewConfig]):
    """テーブルビューページコンポーネント"""

    page_key = "table"
    page_label = "テーブル"

    def render(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        """テーブルページを対話UIで描画する（旧 render_page 相当）"""
        import streamlit as st

        from services.dashboard.query import apply_filters, apply_saved_view_filters, sort_rows_by_index
        from services.dashboard.widgets import render_shared_filters

        vocab = kwargs.get("vocab") or {}

        st.header("テーブルビュー")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # 共有フィルタ（サイドバー描画 + 適用）
        render_shared_filters(rows)

        # 1) view.filters（保存済みフィルタ）を先に適用
        base_rows = apply_saved_view_filters(rows, view.filters) if view.filters else list(rows)

        # 2) サイドバーの共有フィルタをさらに重ねる
        filtered = apply_filters(
            base_rows,
            type_filter=st.session_state.get("_filter_type", "すべて"),
            status_filter=st.session_state.get("_filter_status", "すべて"),
            active_only=st.session_state.get("_filter_active", False),
            vocab=vocab,
        )

        idx_key = provider._index_key
        ver_key = provider._version_key
        filtered = sort_rows_by_index(filtered, idx_key, ver_key)

        render_table_section(
            provider,
            dashboard_config,
            filtered,
            len(rows),
            vocab=vocab,
            grid_key=f"view_{view.name}",
            download_key=f"view_{view.name}",
        )

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_table_html

        vocab = kwargs.get("vocab")
        return generate_table_html(provider, dashboard_config, view, vocab)
