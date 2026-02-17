"""ダッシュボード共有ウィジェット

app.pyとPageComponent双方が使用するStreamlit UIヘルパー関数を提供する。
PageComponentからapp.pyへの逆依存を排除するための共有モジュール。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


def estimate_column_width(col_name: str) -> int:
    """列名の文字幅からAgGrid列幅（px）を推定

    日本語（全角）文字は2文字分、英数字は1文字分として計算。
    1文字あたり約10pxとし、パディング30pxを加算。
    最小幅は80px。

    Args:
        col_name: 列名

    Returns:
        推定列幅（ピクセル）
    """
    char_width = 0
    for ch in col_name:
        if ord(ch) > 0x7F:
            char_width += 2
        else:
            char_width += 1
    return max(80, char_width * 10 + 30)


def try_render_aggrid(df: pd.DataFrame) -> bool:
    """AgGridでDataFrameを表示。失敗時はFalseを返す。

    列幅は列名の文字数に基づいて初期設定する。
    日本語は2文字分、英数字は1文字分として計算し、
    最低限列名が見える幅を確保する。

    Returns:
        True: AgGridで描画成功、False: インポート不可
    """
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return False

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
    )
    # 各列の幅を列名の文字幅に基づいて設定
    for col_name in df.columns:
        width = estimate_column_width(col_name)
        gb.configure_column(col_name, minWidth=width, initialWidth=width)
    gb.configure_selection(
        selection_mode="multiple",
        use_checkbox=True,
    )
    gb.configure_pagination(paginationAutoPageSize=True)
    grid_options = gb.build()

    AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False,
        theme="streamlit",
    )
    return True


# ====================================================================
# 共有フィルタ（session_stateで永続化・ビュー間共有）
# ====================================================================


def init_shared_filters(default_filters: dict[str, Any]) -> None:
    """共有フィルタの初期化（初回のみ）

    Args:
        default_filters: config.dashboard.default-filters
    """
    import streamlit as st

    from services.dashboard.query import is_truthy

    if "_filters_initialized" not in st.session_state:
        st.session_state["_filters_initialized"] = True
        raw_active = default_filters.get("active", False)
        st.session_state.setdefault("_filter_active", is_truthy(raw_active))
        st.session_state.setdefault("_filter_type", "すべて")
        st.session_state.setdefault("_filter_status", "すべて")


def render_shared_filters(rows: list[dict[str, Any]]) -> None:
    """共有フィルタのサイドバーUI描画

    Args:
        rows: フィルタ対象の全行データ
    """
    import streamlit as st

    st.sidebar.markdown("### フィルタ")

    # タイプフィルタ
    types = sorted({r.get("type", "") for r in rows if r.get("type")})
    type_options = ["すべて", *types]
    current_type = st.session_state.get("_filter_type", "すべて")
    type_idx = type_options.index(current_type) if current_type in type_options else 0
    selected_type = st.sidebar.selectbox("タイプフィルタ", type_options, index=type_idx, key="_sb_filter_type")
    st.session_state["_filter_type"] = selected_type

    # ステータスフィルタ
    statuses = sorted({r.get("analysis_status", "unknown") for r in rows if r.get("analysis_status")})
    status_options = ["すべて", *statuses]
    current_status = st.session_state.get("_filter_status", "すべて")
    status_idx = status_options.index(current_status) if current_status in status_options else 0
    selected_status = st.sidebar.selectbox(
        "ステータスフィルタ",
        status_options,
        index=status_idx,
        key="_sb_filter_status",
    )
    st.session_state["_filter_status"] = selected_status

    # activeフィルタ
    active_only = st.sidebar.checkbox(
        "activeのみ",
        value=st.session_state.get("_filter_active", False),
        key="_sb_filter_active",
    )
    st.session_state["_filter_active"] = active_only


def get_active_filters() -> dict[str, Any] | None:
    """現在の共有フィルタ設定をprovider用辞書として取得

    Returns:
        フィルタが有効な場合はdict、全件表示の場合はNone
    """
    import streamlit as st

    filters: dict[str, Any] = {}
    selected_type = st.session_state.get("_filter_type", "すべて")
    selected_status = st.session_state.get("_filter_status", "すべて")
    active_only = st.session_state.get("_filter_active", False)

    if selected_type != "すべて":
        filters["type"] = selected_type
    if selected_status != "すべて":
        filters["analysis_status"] = selected_status
    if active_only:
        filters["active"] = True

    return filters if filters else None


# ====================================================================
# Excelダウンロード
# ====================================================================


def render_excel_download(df: pd.DataFrame, filename_prefix: str = "data") -> None:
    """DataFrameをExcelファイルとしてダウンロードするボタンを表示

    openpyxlが利用可能な場合のみ表示する。

    Args:
        df: ダウンロード対象のDataFrame
        filename_prefix: ファイル名の接頭辞
    """
    try:
        import io

        import openpyxl  # noqa: F401
        import streamlit as st

        buffer = io.BytesIO()
        with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        buffer.seek(0)

        st.download_button(
            label="Excelダウンロード",
            data=buffer,
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ImportError:
        pass


# ====================================================================
# プロットスタイルヘルパー
# ====================================================================


def build_axis_range(
    axis_min: float | None,
    axis_max: float | None,
) -> list[float] | None:
    """軸範囲をplotly用の[min, max]リストに変換

    Args:
        axis_min: 軸最小値（Noneで自動）
        axis_max: 軸最大値（Noneで自動）

    Returns:
        [min, max]リスト。両方Noneの場合はNone（自動範囲）。
    """
    if axis_min is not None or axis_max is not None:
        return [axis_min if axis_min is not None else 0, axis_max if axis_max is not None else 0]
    return None


def build_style_config(
    marker_size: int | None,
    line_width: int | None,
    font_size: int | None,
) -> dict[str, int]:
    """スタイル設定を辞書にまとめる

    Args:
        marker_size: マーカーサイズ（Noneでデフォルト）
        line_width: 線幅（Noneでデフォルト）
        font_size: フォントサイズ（Noneでデフォルト）

    Returns:
        設定値の辞書（値がNoneのキーは除外）
    """
    style: dict[str, int] = {}
    if marker_size is not None:
        style["marker_size"] = int(marker_size)
    if line_width is not None:
        style["line_width"] = int(line_width)
    if font_size is not None:
        style["font_size"] = int(font_size)
    return style


def apply_style_to_fig(fig: Any, style: dict[str, int]) -> None:
    """スタイル設定をplotly Figureに適用

    Args:
        fig: plotly Figure
        style: build_style_configの戻り値
    """
    if not style:
        return
    if "marker_size" in style:
        fig.update_traces(marker=dict(size=style["marker_size"]))
    if "line_width" in style:
        fig.update_traces(line=dict(width=style["line_width"]))
    if "font_size" in style:
        font_sz = style["font_size"]
        # title: 24/20 倍、legend: 16/20 倍
        title_font_sz = round(font_sz * 24 / 20)
        legend_font_sz = round(font_sz * 16 / 20)
        fig.update_layout(
            font=dict(size=font_sz),
            title_font=dict(size=title_font_sz),
            legend=dict(font=dict(size=legend_font_sz)),
            xaxis=dict(
                title_font=dict(size=font_sz),
                tickfont=dict(size=font_sz),
            ),
            yaxis=dict(
                title_font=dict(size=font_sz),
                tickfont=dict(size=font_sz),
            ),
        )
