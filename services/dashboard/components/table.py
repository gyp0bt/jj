"""テーブルビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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


class TablePage(PageComponent[TableViewConfig]):
    """テーブルビューページコンポーネント"""

    page_key = "table"
    page_label = "テーブル"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_filters, select_table_columns
        from services.dashboard.widgets import render_excel_download, render_shared_filters, try_render_aggrid

        vocab = kwargs.get("vocab") or {}

        st.header("テーブルビュー")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # 共有フィルタ（サイドバー描画 + 適用）
        render_shared_filters(rows)

        vocab = kwargs.get("vocab")

        filtered = apply_filters(
            rows,
            type_filter=st.session_state.get("_filter_type", "すべて"),
            status_filter=st.session_state.get("_filter_status", "すべて"),
            active_only=st.session_state.get("_filter_active", False),
            vocab=vocab,
        )

        # verbose_nameキー
        vn_key = provider._verbose_name_key
        idx_key = provider._index_key
        ver_key = provider._version_key

        # idx_key と ver_key を int に変換できるか確認し、可能なら idx, ver の順で昇順ソート
        # TODO: queryとかに関数化して外出しする
        def _to_int(val):
            try:
                if isinstance(val, bool):
                    return None
                return int(val)
            except Exception:
                return None

        # どちらか一方でも int に変換できる行があるか判定
        _can_sort = any(
            _to_int(row.get(idx_key)) is not None or _to_int(row.get(ver_key)) is not None for row in filtered
        )

        if _can_sort:
            sentinel = float("inf")

            def _sort_key(row):
                idx_val = _to_int(row.get(idx_key))
                ver_val = _to_int(row.get(ver_key))
                return (
                    idx_val if idx_val is not None else sentinel,
                    ver_val if ver_val is not None else sentinel,
                )

            filtered = sorted(filtered, key=_sort_key)

        st.caption(f"{len(filtered)} / {len(rows)} 件")

        if not filtered:
            st.info("条件に一致するデータがありません。")
            return

        import pandas as pd

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

        # nameカラムを表示名で置き換え（verbose_nameキーが存在する場合）
        if vn_key in df.columns:
            df["name"] = df[vn_key]
            df = df.drop(vn_key, axis=1)

        # config駆動カラム選択（vocab順ソート対応）
        # グローバルカラム設定がある場合はそちらを優先
        table_columns = getattr(dashboard_config, "table_columns", None)
        exclude_table_columns = getattr(dashboard_config, "exclude_table_columns", None)
        if not table_columns and provider._global_columns:
            table_columns = provider._global_columns
        selected_cols = select_table_columns(
            list(df.columns), table_columns, exclude_table_columns=exclude_table_columns, vocab=vocab or {}
        )
        if selected_cols:
            df = df[[c for c in selected_cols if c in df.columns]]

        # Convert JSON columns that may contain NaN values.
        # For each target column, parse the JSON string (if present) and replace it
        # with the first element of the list. If the value is NaN or cannot be parsed,
        # leave it as None (or the original value).
        import json
        import pandas as pd

        # message_errorsとdat_errorsのようなlist[str]型の値がある列はパースして1番目要素のみ表示
        # この対応だけ個別対応なので、将来的にはconfigで対応する。
        # TODO: この処理をconfig対応にしてかつ関数化しておく
        for col in ["msg_errors", "dat_errors"]:
            if col in df.columns:

                def _parse_json(value):
                    # Preserve missing values as None
                    if pd.isna(value):
                        return None
                    # If the value is already a Python object, use it directly
                    if isinstance(value, (list, dict)):
                        data = value
                    else:
                        try:
                            data = value[1:-1].split(",")[0].replace("'", "")
                            # data = json.loads(str(value))
                        except Exception:
                            # If loading fails, keep the original value
                            # print(value)
                            return value
                    return data

                df[col] = df[col].apply(_parse_json)

        # AgGridを試行、失敗時はst.dataframeにフォールバック
        if not try_render_aggrid(df):
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Excelダウンロードボタン
        render_excel_download(df, "go_table")

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_saved_view_filters, select_table_columns
        from services.dashboard.widgets import render_excel_download

        vocab = kwargs.get("vocab") or {}

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # 保存済みフィルタを適用
        filtered = apply_saved_view_filters(rows, view.filters)

        st.caption(f"{len(filtered)} / {len(rows)} 件")
        if not filtered:
            st.info("条件に一致するデータがありません。")
            return

        import pandas as pd

        # verbose_nameキー
        vn_key = provider._verbose_name_key

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

        # nameカラムを表示名で置き換え
        if vn_key in df.columns:
            df["name"] = df[vn_key]
            df = df.drop(vn_key, axis=1)

        # config駆動カラム選択（vocab順ソート対応）
        # グローバルカラム設定がある場合はそちらを優先
        table_columns = getattr(dashboard_config, "table_columns", None)
        if not table_columns and provider._global_columns:
            table_columns = provider._global_columns
        selected_cols = select_table_columns(list(df.columns), table_columns, vocab=vocab or {})
        if selected_cols:
            df = df[[c for c in selected_cols if c in df.columns]]

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Excelダウンロードボタン
        render_excel_download(df, f"saved_view_{view.name}")

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
