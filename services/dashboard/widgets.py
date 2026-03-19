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


def try_render_aggrid(df: pd.DataFrame, *, grid_key: str | None = None) -> bool:
    """AgGridでDataFrameを表示。失敗時はFalseを返す。

    列幅は列名の文字数に基づいて初期設定する。
    日本語は2文字分、英数字は1文字分として計算し、
    最低限列名が見える幅を確保する。

    フィルタ共有がONの場合、AgGridのフィルタ変更イベントをキャプチャして
    session_stateの共有フィルタに格納し、他ビューにも反映する。

    Args:
        df: 表示するDataFrame
        grid_key: AgGridのStreamlitキー（複数AgGrid描画時の衝突回避用）

    Returns:
        True: AgGridで描画成功、False: インポート不可
    """
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return False

    import streamlit as st

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        groupable=True,
        value=True,
        enableRowGroup=True,
        aggFunc="sum",
        editable=True,
    )
    # 各列の幅と適切なフィルタータイプを設定
    for col_name in df.columns:
        width = estimate_column_width(col_name)
        col_config: dict[str, Any] = {"minWidth": width, "initialWidth": width}
        # 数値列にはagNumberColumnFilterを設定
        if df[col_name].dtype in ("int64", "float64", "int32", "float32"):
            col_config["filter"] = "agNumberColumnFilter"
        else:
            col_config["filter"] = "agTextColumnFilter"
        gb.configure_column(col_name, **col_config)
    gb.configure_selection(
        selection_mode="multiple",
        use_checkbox=True,
    )
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()

    grid_options = gb.build()

    # フィルタ共有ON時はフィルタ変更も検知する
    sharing_enabled = st.session_state.get("_filter_sharing_enabled", False)
    update_mode = GridUpdateMode.MODEL_CHANGED if sharing_enabled else GridUpdateMode.SELECTION_CHANGED

    # 共有フィルタがある場合、AgGridにプリセットフィルタを適用
    aggrid_filters = st.session_state.get("_aggrid_shared_filters")
    if sharing_enabled and aggrid_filters:
        grid_options["filterModel"] = aggrid_filters

    response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=update_mode,
        fit_columns_on_grid_load=False,
        theme="streamlit",
        key=grid_key,
    )

    # フィルタ共有ON時: AgGridのフィルタ状態をsession_stateに保存
    if sharing_enabled and hasattr(response, "grid_options_state"):
        filter_model = (response.grid_options_state or {}).get("filterModel")
        if filter_model is not None:
            st.session_state["_aggrid_shared_filters"] = filter_model

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
        st.session_state.setdefault("_filter_sharing_enabled", False)
        st.session_state.setdefault("_aggrid_shared_filters", None)


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

    # AgGridフィルタ共有トグル
    st.sidebar.markdown("---")
    sharing = st.sidebar.checkbox(
        "AgGridフィルタ共有",
        value=st.session_state.get("_filter_sharing_enabled", False),
        key="_sb_filter_sharing",
        help="ONにすると、テーブルのフィルタ変更が他のビューにも反映されます",
    )
    st.session_state["_filter_sharing_enabled"] = sharing

    # 共有フィルタのクリアボタン
    if (
        sharing
        and st.session_state.get("_aggrid_shared_filters")
        and st.sidebar.button("共有フィルタをクリア", key="_sb_clear_aggrid_filters")
    ):
        st.session_state["_aggrid_shared_filters"] = None


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
    """DataFrameを書式付きExcelファイルとしてダウンロードするボタンを表示

    書式付きExcel出力（メイリオフォント・ヘッダー色付き・列幅自動調整）を試行し、
    失敗時はpandas標準のExcel出力にフォールバックする。

    Args:
        df: ダウンロード対象のDataFrame
        filename_prefix: ファイル名の接頭辞
    """
    try:
        import openpyxl  # noqa: F401
        import streamlit as st
    except ImportError:
        return

    # 書式付きExcel出力を試行
    try:
        from services.export.connectors.excel_export import export_table_to_excel_bytes

        excel_bytes = export_table_to_excel_bytes(df)
    except Exception:
        # フォールバック: pandas標準出力
        import io

        buffer = io.BytesIO()
        with __import__("pandas").ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        buffer.seek(0)
        excel_bytes = buffer.getvalue()

    st.download_button(
        label="Excelダウンロード",
        data=excel_bytes,
        file_name=f"{filename_prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def render_pptx_gallery_download(
    image_paths: list[Any],
    title: str = "Gallery",
    cols: int = 3,
    rows: int = 2,
    filename_prefix: str = "gallery",
) -> None:
    """ギャラリー画像をPPTXファイルとしてダウンロードするボタンを表示

    python-pptxが利用可能な場合のみ表示する。

    Args:
        image_paths: 画像ファイルパスのリスト
        title: プレゼンテーションタイトル
        cols: グリッド列数
        rows: グリッド行数
        filename_prefix: ファイル名の接頭辞
    """
    try:
        from pathlib import Path

        import streamlit as st

        from services.export.connectors.pptx_export import export_gallery_to_pptx_bytes

        paths = [Path(p) for p in image_paths]
        existing = [p for p in paths if p.exists()]
        if not existing:
            return

        if st.button("PPTXダウンロード", key=f"pptx_gallery_{filename_prefix}"):
            pptx_bytes = export_gallery_to_pptx_bytes(existing, cols, rows, title)
            st.download_button(
                label="PPTXファイルを保存",
                data=pptx_bytes,
                file_name=f"{filename_prefix}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key=f"pptx_save_{filename_prefix}",
            )
    except ImportError:
        pass


def render_pptx_plot_download(
    figs: list[Any],
    titles: list[str] | None = None,
    filename_prefix: str = "plots",
) -> None:
    """Plotly figureリストをPPTXファイルとしてダウンロードするボタンを表示

    python-pptx + kaleido が利用可能な場合のみ表示する。

    Args:
        figs: plotly.graph_objects.Figure のリスト
        titles: 各スライドのタイトル
        filename_prefix: ファイル名の接頭辞
    """
    try:
        import streamlit as st

        from services.export.connectors.pptx_export import plotly_fig_to_pptx_bytes

        if st.button("PPTXダウンロード", key=f"pptx_plot_{filename_prefix}"):
            try:
                pptx_bytes = plotly_fig_to_pptx_bytes(figs, titles)
                st.download_button(
                    label="PPTXファイルを保存",
                    data=pptx_bytes,
                    file_name=f"{filename_prefix}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    key=f"pptx_plot_save_{filename_prefix}",
                )
            except ValueError as e:
                st.warning(str(e))
    except ImportError:
        pass


def render_array_excel_download(
    array_data: list[dict[str, Any]],
    filename_prefix: str = "array_data",
) -> None:
    """配列データを書式付きExcelファイルとしてダウンロードするボタンを表示

    openpyxlが利用可能な場合のみ表示する。

    Args:
        array_data: [{"name": str, "x": list, "y": list, "props": dict}, ...]
        filename_prefix: ファイル名の接頭辞
    """
    try:
        import streamlit as st

        from services.export.connectors.excel_export import export_array_data_to_excel_bytes

        if st.button("配列Excel", key=f"array_excel_{filename_prefix}"):
            excel_bytes = export_array_data_to_excel_bytes(array_data)
            st.download_button(
                label="Excelファイルを保存",
                data=excel_bytes,
                file_name=f"{filename_prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"array_excel_save_{filename_prefix}",
            )
    except ImportError:
        pass


# ====================================================================
# プロットスタイルヘルパー
# ====================================================================


def get_plotly_template() -> str:
    """Streamlitテーマに連動したplotlyテンプレートを返す

    Streamlitのテーマ設定を検出し、適切なplotlyテンプレートを選択する。
    - ライトテーマ → "plotly_white"
    - ダークテーマ → "plotly_dark"
    - 検出不可 → "plotly_white"（デフォルト）

    Returns:
        plotlyテンプレート名
    """
    try:
        import streamlit as st

        theme_base = st.get_option("theme.base")
        if theme_base == "dark":
            return "plotly_dark"
    except Exception:
        pass
    return "plotly_white"


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
