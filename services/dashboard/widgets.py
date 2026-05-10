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


def try_render_aggrid(
    df: pd.DataFrame,
    *,
    grid_key: str | None = None,
    raw_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """AgGridでDataFrameを表示。失敗時はFalseを返す。

    列幅は列名の文字数に基づいて初期設定する。
    日本語は2文字分、英数字は1文字分として計算し、
    最低限列名が見える幅を確保する。

    フィルタは常に他コンポーネントと共有される。AgGridのフィルタ変更イベントを
    キャプチャして session_state に格納し、``raw_rows`` が与えられた場合は
    フィルタ後のレコード名集合も保持する（plot/array_plot/gallery で利用）。

    Args:
        df: 表示するDataFrame（AgGridに渡す表示用df）
        grid_key: AgGridのStreamlitキー（複数AgGrid描画時の衝突回避用）
        raw_rows: ``df`` の元になった raw 行リスト。``df`` のindexと位置で対応する。
            指定された場合、AgGridのフィルタ通過行の ``name`` 集合を
            ``_table_filtered_names`` に保存し、他ビューに反映する。

    Returns:
        True: AgGridで描画成功、False: インポート不可
    """
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return False

    import streamlit as st

    gb = GridOptionsBuilder.from_dataframe(df)
    # editable=False: editable=True だと response.data が「編集後の全行」になり
    # data_return_mode=FILTERED_AND_SORTED が効かなくなるため。
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        groupable=True,
        value=True,
        enableRowGroup=True,
        aggFunc="sum",
        editable=False,
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

    # 既存のグリッド状態（フィルタ/ソート/列）をinitialStateで復元
    saved_state = st.session_state.get("_aggrid_grid_state")
    if saved_state:
        grid_options["initialState"] = saved_state

    response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme="streamlit",
        key=grid_key,
    )

    # グリッド状態（フィルタ含む）を session_state に保存
    grid_state = getattr(response, "grid_state", None)
    if grid_state:
        st.session_state["_aggrid_grid_state"] = grid_state
        filter_state = grid_state.get("filter") if isinstance(grid_state, dict) else None
        st.session_state["_aggrid_shared_filters"] = filter_state

    # フィルタ後の行ID（=df位置index）から name 集合を抽出して他ビューに共有
    if raw_rows is not None:
        row_ids = getattr(response, "rows_id_after_filter", None)
        if row_ids is None or len(row_ids) >= len(raw_rows):
            # フィルタなし（or全件通過）→ 共有フィルタ未設定扱い
            st.session_state["_table_filtered_names"] = None
        else:
            names: set[str] = set()
            for rid in row_ids:
                try:
                    i = int(rid)
                except (ValueError, TypeError):
                    continue
                if 0 <= i < len(raw_rows):
                    n = raw_rows[i].get("name")
                    if n:
                        names.add(n)
            st.session_state["_table_filtered_names"] = names

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

    from services.graph.query.filters import is_truthy

    if "_filters_initialized" not in st.session_state:
        st.session_state["_filters_initialized"] = True
        raw_active = default_filters.get("active", False)
        st.session_state.setdefault("_filter_active", is_truthy(raw_active))
        st.session_state.setdefault("_filter_type", "すべて")
        st.session_state.setdefault("_filter_status", "すべて")
        # 最新versionのみフィルタ（同一indexの最新versionだけ残す、デフォルトON）
        raw_latest = default_filters.get("latest_version_only", True)
        st.session_state.setdefault("_filter_latest_version", is_truthy(raw_latest))
        # AgGridフィルタ状態（テーブル → 他ビューへ常時共有）
        st.session_state.setdefault("_aggrid_grid_state", None)
        st.session_state.setdefault("_aggrid_shared_filters", None)
        st.session_state.setdefault("_table_filtered_names", None)


def render_shared_filters(rows: list[dict[str, Any]]) -> None:
    """共有フィルタのサイドバーUI描画

    シングルページ構成では複数のページコンポーネントが同一実行中に
    本関数を呼び出すため、2回目以降はウィジェットキー重複を避けるため
    スキップする（サイドバーには1回のみ描画）。

    Args:
        rows: フィルタ対象の全行データ
    """
    import streamlit as st

    if st.session_state.get("_shared_filters_rendered", False):
        return
    st.session_state["_shared_filters_rendered"] = True

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

    # 同一indexの最新versionのみフィルタ
    latest_version_only = st.sidebar.checkbox(
        "同一indexの最新versionのみ",
        value=st.session_state.get("_filter_latest_version", True),
        key="_sb_filter_latest_version",
        help="indexごとに最新versionの行のみ残す（idxが無い行は常に残る）",
    )
    st.session_state["_filter_latest_version"] = latest_version_only

    # AgGridフィルタ（テーブル）の共有クリアボタン
    # ※ AgGridフィルタは常時 他コンポーネントと共有される
    if st.session_state.get("_aggrid_shared_filters") or st.session_state.get("_table_filtered_names"):
        st.sidebar.markdown("---")
        if st.sidebar.button("テーブルフィルタをクリア", key="_sb_clear_aggrid_filters"):
            st.session_state["_aggrid_grid_state"] = None
            st.session_state["_aggrid_shared_filters"] = None
            st.session_state["_table_filtered_names"] = None


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
    # 最新versionフィルタは provider 用辞書には載せない（apply_filters 経由で別途処理）
    # ※ provider.get_go_table の filter は単純な等値マッチのみ対応のため

    return filters if filters else None


def persist_view_changes(
    new_view: Any,
    dashboard_config: Any,
    project_root: Any,
) -> None:
    """SavedViewConfig の変更を config.yaml に保存（save-on-edit）

    ``dashboard_config.enabled_pages`` から (name, view_type) で該当エントリを探し、
    ``new_view`` で置き換えて ``save_enabled_pages`` で書き戻す。
    現在値が同じなら no-op。
    呼び出し元は変更検出を済ませてから呼ぶ想定（dictシリアライズ比較推奨）。
    """
    if project_root is None:
        return
    from pathlib import Path

    from services.dashboard.config_writer import save_enabled_pages

    enabled = list(getattr(dashboard_config, "enabled_pages", []) or [])
    updated: list[Any] = []
    found = False
    for v in enabled:
        if v.name == new_view.name and v.view_type == new_view.view_type:
            updated.append(new_view)
            found = True
        else:
            updated.append(v)
    if not found:
        return
    save_enabled_pages(Path(project_root), updated)


def maybe_persist_view(
    new_view: Any,
    old_view: Any,
    dashboard_config: Any,
    project_root: Any,
) -> bool:
    """save-on-edit ヘルパ：dictシリアライズ比較で変更があれば保存する"""
    from config import saved_view_to_dict

    try:
        if saved_view_to_dict(new_view) == saved_view_to_dict(old_view):
            return False
    except Exception:
        return False
    persist_view_changes(new_view, dashboard_config, project_root)
    return True


def get_active_filtered_names(provider: Any) -> set[str] | None:
    """共有フィルタ + 最新versionフィルタ + テーブルAgGridフィルタ適用後の名前集合

    plot/array_plot/gallery など、テーブル以外のビュー向けに、テーブルで
    実行された AgGrid フィルタの結果を反映した name 集合を返す。
    フィルタが何も効いていない場合は None（= 全件OK扱い）。
    """
    import streamlit as st

    from services.graph.query import filter_latest_version

    filters = get_active_filters()
    latest_only = st.session_state.get("_filter_latest_version", True)
    table_names = st.session_state.get("_table_filtered_names")

    if not filters and not latest_only and table_names is None:
        return None

    rows = provider.get_go_table(filters=filters)
    if latest_only:
        rows = filter_latest_version(rows)
    names = {r["name"] for r in rows}
    if table_names is not None:
        names &= table_names
    return names


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
