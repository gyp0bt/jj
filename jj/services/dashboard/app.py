"""Streamlitダッシュボードアプリ本体（描画層）

jj dashboardコマンドから起動されるStreamlitアプリ。
GraphModelを読み込み、テーブル/カード/プロット/ステータス/ギャラリー/保存済みビューの
汎用ビューを提供する。ソフトウェア固有ページ（例: Abaqus物性一覧）は
services/dashboard/connectors/ のコネクターとして実装・自動登録される。

## 責務分離（status-078）
- **描画層（本ファイル）**: Streamlit UIの構築・ユーザー操作の処理
- **クエリ層（query.py）**: フィルタ・ソート・カラム選択等の純粋ロジック
- **データ供給層（data_provider.py）**: GraphModelからのデータ取得
- **HTMLエクスポート（html_export.py）**: スタンドアロンHTML生成
- **共有ウィジェット（widgets.py）**: AgGrid等のUIヘルパー
- **コネクター（connectors/）**: ソフトウェア固有ページ

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# プロジェクトルートをsys.pathに追加（Streamlitプロセスからのインポート用）
_project_src = str(Path(__file__).resolve().parents[2])
if _project_src not in sys.path:
    sys.path.insert(0, _project_src)

from jj_types import GraphModel
from services.dashboard.data_provider import DashboardDataProvider
from services.dashboard.connectors import get_connector_pages, render_connector_page
from services.dashboard.query import (
    find_graph_path,
    get_graph_mtime,
    is_truthy,
    select_table_columns,
    apply_filters,
    apply_saved_view_filters,
    saved_view_filters_to_provider_filters,
    normalize_group_key,
    collect_group_keys,
)
from services.dashboard.html_export import (
    generate_saved_views_html,
    _create_plot_figure,
    _add_ng_regions_to_fig,
    _add_group_lines_to_fig,
)
from services.graph import GraphService

# コネクター自動登録（インポート時に__init_subclass__で登録される）
import services.dashboard.connectors.abaqus  # noqa: F401


def _check_graph_changed(project_root: Path) -> bool:
    """graph.yamlが前回読み込み時から変更されたか判定

    Returns:
        True: 変更あり（リロード必要）
    """
    current_mtime = get_graph_mtime(project_root)
    prev_mtime = st.session_state.get("_graph_mtime", 0.0)

    if prev_mtime == 0.0:
        # 初回読み込み
        st.session_state["_graph_mtime"] = current_mtime
        return False

    if current_mtime != prev_mtime:
        st.session_state["_graph_mtime"] = current_mtime
        return True

    return False


# ====================================================================
# データ読み込み
# ====================================================================


def _load_graph(project_root: Path) -> GraphModel:
    """GraphModelをロード（キャッシュ対応）"""
    svc = GraphService(project_root=project_root)
    return svc.load()


def _get_project_root() -> Path:
    """プロジェクトルートをセッションまたは環境から取得"""
    if "project_root" not in st.session_state:
        root = os.environ.get("JJ_PROJECT_ROOT", str(Path.cwd()))
        st.session_state["project_root"] = root
    return Path(st.session_state["project_root"])


# ====================================================================
# AgGrid ヘルパー
# ====================================================================


def _try_render_aggrid(df: "pd.DataFrame") -> bool:
    """AgGridでDataFrameを表示（widgets.pyへの委譲ラッパー）"""
    from services.dashboard.widgets import try_render_aggrid
    return try_render_aggrid(df)


def _estimate_column_width(col_name: str) -> int:
    """列名の文字幅からAgGrid列幅を推定（widgets.pyへの委譲ラッパー）"""
    from services.dashboard.widgets import estimate_column_width
    return estimate_column_width(col_name)


# ====================================================================
# カラムフィルタリング（query.pyへの後方互換ラッパー）
# ====================================================================


def _sort_columns_by_vocab(
    columns: list[str], vocab: dict[str, str]
) -> list[str]:
    """query.sort_columns_by_vocabへの委譲ラッパー（後方互換）"""
    from services.dashboard.query import sort_columns_by_vocab
    return sort_columns_by_vocab(columns, vocab)


def _select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """query.select_table_columnsへの委譲ラッパー（後方互換）"""
    return select_table_columns(all_columns, table_columns, vocab=vocab)


# ====================================================================
# 共有フィルタ（session_stateで永続化・ビュー間共有）
# ====================================================================


def _init_shared_filters(default_filters: dict[str, Any]) -> None:
    """共有フィルタの初期化（初回のみ）

    Args:
        default_filters: config.dashboard.default-filters
    """
    if "_filters_initialized" not in st.session_state:
        st.session_state["_filters_initialized"] = True
        # active値はYAML由来のboolまたは文字列"true"の両方に対応
        raw_active = default_filters.get("active", False)
        st.session_state.setdefault(
            "_filter_active", is_truthy(raw_active)
        )
        st.session_state.setdefault("_filter_type", "すべて")
        st.session_state.setdefault("_filter_status", "すべて")


def _render_shared_filters(rows: list[dict[str, Any]]) -> None:
    """共有フィルタのサイドバーUI描画

    Args:
        rows: フィルタ対象の全行データ
    """
    st.sidebar.markdown("### フィルタ")

    # タイプフィルタ
    types = sorted({r.get("type", "") for r in rows if r.get("type")})
    type_options = ["すべて"] + types
    current_type = st.session_state.get("_filter_type", "すべて")
    type_idx = type_options.index(current_type) if current_type in type_options else 0
    selected_type = st.sidebar.selectbox(
        "タイプフィルタ", type_options, index=type_idx, key="_sb_filter_type"
    )
    st.session_state["_filter_type"] = selected_type

    # ステータスフィルタ
    statuses = sorted({
        r.get("analysis_status", "unknown")
        for r in rows
        if r.get("analysis_status")
    })
    status_options = ["すべて"] + statuses
    current_status = st.session_state.get("_filter_status", "すべて")
    status_idx = (
        status_options.index(current_status) if current_status in status_options else 0
    )
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


def _is_truthy(value: Any) -> bool:
    """query.is_truthyへの委譲ラッパー（後方互換）"""
    return is_truthy(value)


def _get_active_filters() -> dict[str, Any] | None:
    """現在の共有フィルタ設定をprovider用辞書として取得

    Returns:
        フィルタが有効な場合はdict、全件表示の場合はNone
    """
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


def _apply_shared_filters(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """共有フィルタを適用（session_stateからフィルタ条件を取得してquery層に委譲）

    Args:
        rows: フィルタ対象の全行データ

    Returns:
        フィルタ適用後の行データ
    """
    selected_type = st.session_state.get("_filter_type", "すべて")
    selected_status = st.session_state.get("_filter_status", "すべて")
    active_only = st.session_state.get("_filter_active", False)

    return apply_filters(
        rows,
        type_filter=selected_type,
        status_filter=selected_status,
        active_only=active_only,
    )


# ====================================================================
# メインエントリポイント
# ====================================================================


def main() -> None:
    """Streamlitアプリのメインエントリポイント"""
    st.set_page_config(
        page_title="jj Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    project_root = _get_project_root()

    # サイドバー: プロジェクト情報
    st.sidebar.title("jj Dashboard")
    st.sidebar.caption(f"Project: {project_root.name}")

    # graph.yaml変更検知
    graph_changed = _check_graph_changed(project_root)
    if graph_changed:
        st.sidebar.success("graph.yaml が更新されました。データを再読み込みしました。")

    # 手動再読み込みボタン
    if st.sidebar.button("再読み込み"):
        st.session_state["_graph_mtime"] = get_graph_mtime(project_root)
        st.rerun()

    # 自動リフレッシュ設定
    auto_refresh = st.sidebar.checkbox("自動リフレッシュ", value=False)
    if auto_refresh:
        refresh_sec = st.sidebar.slider(
            "リフレッシュ間隔（秒）", min_value=3, max_value=60, value=10
        )
        # JavaScriptによる自動リフレッシュ
        st.components.v1.html(
            f"""<script>
            setTimeout(function(){{
                window.parent.document.querySelectorAll(
                    'button[kind="secondary"]'
                ).forEach(function(btn){{
                    if(btn.innerText === '再読み込み') btn.click();
                }});
            }}, {refresh_sec * 1000});
            </script>""",
            height=0,
        )

    st.sidebar.markdown("---")

    # グラフデータ読み込み
    try:
        graph = _load_graph(project_root)
    except Exception as e:
        st.error(f"グラフデータの読み込みに失敗しました: {e}")
        st.info("'jj parse' を実行してグラフデータを生成してください。")
        return

    if not graph.nodes:
        st.warning("グラフデータが空です。'jj parse' を実行してください。")
        return

    # config読み込み
    dashboard_config = None
    try:
        from config import DashboardConfig, GraphConfig

        config = GraphConfig.load(base_dir=project_root)
        vocab = config.vocab
        units = config.export.units
        dashboard_config = config.dashboard
    except Exception:
        vocab = {}
        units = {}

    if dashboard_config is None:
        from config import DashboardConfig

        dashboard_config = DashboardConfig.from_dict({})

    provider = DashboardDataProvider(graph, vocab=vocab, units=units)

    # 共有フィルタ初期化
    _init_shared_filters(dashboard_config.default_filters)

    # ページ選択（コネクターページ + 保存済みビュー動的追加）
    page_options = [
        "テーブル", "カード", "プロット", "配列プロット",
        "ステータス", "ギャラリー",
    ]
    # コネクターが提供するページを動的追加
    connector_pages = get_connector_pages(provider)
    page_options.extend(connector_pages)
    saved_views = getattr(dashboard_config, "saved_views", [])
    if saved_views:
        page_options.append("保存済みビュー")
    page = st.sidebar.radio(
        "ページ",
        page_options,
        index=0,
    )

    # サマリー情報
    status = provider.get_status_summary()
    st.sidebar.markdown("---")
    st.sidebar.metric("総ノード数", len(graph.nodes))
    st.sidebar.metric("総リレーション数", len(graph.relations))
    st.sidebar.metric("go_ ファイル数", status["total"])

    if page == "テーブル":
        _render_table_page(provider, dashboard_config, vocab)
    elif page == "カード":
        _render_card_page(provider)
    elif page == "プロット":
        _render_plot_page(provider, dashboard_config)
    elif page == "配列プロット":
        _render_array_plot_page(provider, dashboard_config)
    elif page == "ステータス":
        _render_status_page(provider)
    elif page == "ギャラリー":
        _render_gallery_page(provider, project_root, dashboard_config)
    elif page == "保存済みビュー":
        _render_saved_views_page(provider, project_root, dashboard_config, vocab)
    elif page in connector_pages:
        render_connector_page(page, provider, dashboard_config)


# ====================================================================
# テーブルビュー（AgGrid対応・config駆動カラム選択）
# ====================================================================


def _render_table_page(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """テーブルビュー: go_ファイルをテーブル表示（AgGrid優先・vocab順カラム）"""
    st.header("テーブルビュー")

    rows = provider.get_go_table()
    if not rows:
        st.info("go_ ファイルが見つかりません。")
        return

    # 共有フィルタ（サイドバー描画 + 適用）
    _render_shared_filters(rows)
    filtered = _apply_shared_filters(rows)

    st.caption(f"{len(filtered)} / {len(rows)} 件")

    if not filtered:
        st.info("条件に一致するデータがありません。")
        return

    import pandas as pd

    # related_filesはネストしているので除外
    display_rows = []
    for r in filtered:
        row = {k: v for k, v in r.items() if k != "related_files"}
        # dictやlistの値は文字列化
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)

    # config駆動カラム選択（vocab順ソート対応）
    table_columns = getattr(dashboard_config, "table_columns", None)
    selected_cols = _select_table_columns(
        list(df.columns), table_columns, vocab=vocab or {}
    )
    if selected_cols:
        df = df[[c for c in selected_cols if c in df.columns]]

    # AgGridを試行、失敗時はst.dataframeにフォールバック
    if not _try_render_aggrid(df):
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Excelダウンロードボタン
    _render_excel_download(df, "go_table")


# ====================================================================
# Excelダウンロード
# ====================================================================


def _render_excel_download(df: "pd.DataFrame", filename_prefix: str = "data") -> None:
    """DataFrameをExcelファイルとしてダウンロードするボタンを表示

    openpyxlが利用可能な場合のみ表示する。

    Args:
        df: ダウンロード対象のDataFrame
        filename_prefix: ファイル名の接頭辞
    """
    try:
        import io
        import openpyxl  # noqa: F401

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
# カードビュー（全プロパティ表示）
# ====================================================================


def _render_card_page(provider: DashboardDataProvider) -> None:
    """カードビュー: ノード詳細をカード表示"""
    st.header("カードビュー")

    rows = provider.get_go_table()
    if not rows:
        st.info("go_ ファイルが見つかりません。")
        return

    names = [r["name"] for r in rows]
    selected = st.selectbox("ノード選択", names)

    if not selected:
        return

    # IDを取得
    node_id = next((r["id"] for r in rows if r["name"] == selected), None)
    if node_id is None:
        return

    card = provider.get_node_card(node_id)
    if card is None:
        st.error("ノード情報を取得できませんでした。")
        return

    # カード表示
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(card["name"])
        st.markdown(f"**タイプ**: {card['type']}")
        st.markdown(f"**フォーマット**: {card['format']}")

    with col2:
        status = card["properties"].get("analysis_status", "unknown")
        status_emoji = {"completed": "✅", "failed": "❌"}.get(status, "❓")
        st.markdown(f"**ステータス**: {status_emoji} {status}")
        if "active" in card["properties"]:
            st.markdown(f"**active**: {card['properties']['active']}")

    # プロパティ
    st.markdown("---")
    st.subheader("プロパティ")

    props = {
        k: v
        for k, v in card["properties"].items()
        if k not in ("path", "include_properties")
    }
    if props:
        import pandas as pd

        props_flat = {}
        for k, v in props.items():
            if isinstance(v, (dict, list)):
                props_flat[k] = str(v)
            else:
                props_flat[k] = v
        df = pd.DataFrame([props_flat]).T
        df.columns = ["値"]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("プロパティがありません。")

    # リレーション
    st.markdown("---")
    st.subheader("リレーション")
    relations = card.get("relations", [])
    if relations:
        for rel in relations:
            direction = "→" if rel["direction"] == "outgoing" else "←"
            st.markdown(
                f"- {direction} **{rel['label']}** → {rel['node_name']} "
                f"({rel['node_type']})"
            )
    else:
        st.info("リレーションがありません。")


# ====================================================================
# プロットビュー（config駆動デフォルト軸・NxMグリッド対応）
# ====================================================================


def _render_plot_page(
    provider: DashboardDataProvider, dashboard_config: Any
) -> None:
    """プロットビュー: プロパティの散布図/棒グラフ"""
    st.header("プロットビュー")

    keys = provider.get_property_keys()
    if not keys:
        st.info("プロット可能なプロパティがありません。")
        return

    # config駆動デフォルト軸
    plot_x = getattr(dashboard_config, "plot_x", None)
    plot_y = getattr(dashboard_config, "plot_y", None)

    x_default_idx = 0
    if plot_x and plot_x in keys:
        x_default_idx = keys.index(plot_x)

    y_default_idx = min(1, len(keys) - 1)
    if plot_y and plot_y in keys:
        y_default_idx = keys.index(plot_y)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        x_key = st.selectbox("X軸", keys, index=x_default_idx)
    with col2:
        y_key = st.selectbox("Y軸", keys, index=y_default_idx)
    with col3:
        color_options = ["なし"] + keys
        color_key = st.selectbox("色分け", color_options, index=0)
    with col4:
        chart_type = st.selectbox("チャートタイプ", ["散布図", "棒グラフ", "線図"])

    if not x_key or not y_key:
        return

    color = color_key if color_key != "なし" else None
    data = provider.get_plot_data(x_key, y_key, color_key=color)

    if not data:
        st.warning(
            f"'{x_key}' と '{y_key}' の両方が数値であるデータが見つかりません。"
        )
        return

    import pandas as pd

    df = pd.DataFrame(data)

    # NxMグリッド表示オプション
    gallery_cols = getattr(dashboard_config, "gallery_columns", 5)
    gallery_rows = getattr(dashboard_config, "gallery_rows", 4)
    grid_mode = st.checkbox("グリッドモード（スクリーンショット用）", value=False)

    # グループ結線設定
    group_line_key = getattr(dashboard_config, "group_line_key", None)
    group_line_options = ["なし"] + [k for k in keys if k != x_key and k != y_key]
    col_gl1, col_gl2 = st.columns(2)
    with col_gl1:
        gl_default = 0
        if group_line_key and group_line_key in group_line_options:
            gl_default = group_line_options.index(group_line_key)
        selected_group_line = st.selectbox(
            "グループ結線キー", group_line_options, index=gl_default
        )

    try:
        import plotly.express as px

        if grid_mode:
            # グリッドモード: 各データ点ごとに個別プロットをNxMグリッド配置
            _render_plot_grid(
                df, x_key, y_key, color, chart_type, gallery_cols, gallery_rows
            )
        else:
            # 通常モード: 1つのプロット
            fig = _create_plot_figure(
                px, df, x_key, y_key, color, chart_type
            )
            # NG領域塗りつぶし
            ng_regions = getattr(dashboard_config, "ng_regions", [])
            if ng_regions:
                _add_ng_regions(fig, ng_regions)
            # グループ結線
            gl_key = selected_group_line if selected_group_line != "なし" else None
            if gl_key and gl_key in df.columns:
                _add_group_lines(fig, df, x_key, y_key, gl_key)
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # plotlyがない場合はStreamlit組み込みチャートを使用
        st.scatter_chart(df, x=x_key, y=y_key)

    st.caption(f"データ点数: {len(data)}")


def _add_ng_regions(fig: Any, ng_regions: list[dict[str, Any]]) -> None:
    """html_export._add_ng_regions_to_figへの委譲ラッパー（後方互換）"""
    _add_ng_regions_to_fig(fig, ng_regions)


def _add_group_lines(
    fig: Any,
    df: "pd.DataFrame",
    x_key: str,
    y_key: str,
    group_key: str,
) -> None:
    """html_export._add_group_lines_to_figへの委譲ラッパー（後方互換）"""
    _add_group_lines_to_fig(fig, df, x_key, y_key, group_key)


# _create_plot_figure はhtml_export.pyからインポート済み


def _render_plot_grid(
    df: "pd.DataFrame",
    x_key: str,
    y_key: str,
    color: str | None,
    chart_type: str,
    cols_per_row: int,
    max_rows: int,
) -> None:
    """プロットをNxMグリッドで表示（スクリーンショット向け）

    色分けキーまたはnameごとに個別プロットを生成しグリッド配置する。
    """
    try:
        import plotly.express as px
    except ImportError:
        st.warning("plotlyが必要です。")
        return

    # 色分けキーでグループ化、なければnameごと
    group_key = color if color else "name"
    if group_key not in df.columns:
        st.plotly_chart(
            _create_plot_figure(px, df, x_key, y_key, color, chart_type),
            use_container_width=True,
        )
        return

    groups = list(df.groupby(group_key))
    max_plots = cols_per_row * max_rows
    groups = groups[:max_plots]

    for row_start in range(0, len(groups), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, (group_name, group_df) in enumerate(
            groups[row_start: row_start + cols_per_row]
        ):
            with cols[col_idx]:
                if chart_type == "散布図":
                    fig = px.scatter(
                        group_df, x=x_key, y=y_key,
                        title=str(group_name),
                        hover_name="name" if "name" in group_df.columns else None,
                    )
                elif chart_type == "棒グラフ":
                    fig = px.bar(
                        group_df, x="name", y=y_key,
                        title=str(group_name),
                    )
                else:
                    fig = px.line(
                        group_df, x=x_key, y=y_key,
                        title=str(group_name),
                        hover_name="name" if "name" in group_df.columns else None,
                        markers=True,
                    )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=300,
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)


# ====================================================================
# 配列プロットビュー（反力プロファイル等の時系列データ）
# ====================================================================


def _render_array_plot_page(
    provider: DashboardDataProvider, dashboard_config: Any
) -> None:
    """配列プロットビュー: GOノードの配列プロパティをラインプロット"""
    st.header("配列プロットビュー")

    array_keys = provider.get_array_property_keys()
    if not array_keys:
        st.info(
            "配列プロパティが見つかりません。"
            "CSVファイルがhas_output関係でGOファイルに紐付いている必要があります。"
        )
        return

    # 共有フィルタ（サイドバー描画 + 適用）
    rows = provider.get_go_table()
    _render_shared_filters(rows)

    # 接頭辞グループの抽出（例: RF, stress）
    prefixes = sorted({k.split(".")[0] for k in array_keys})

    # UI: 接頭辞選択 → X/Y軸選択
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_prefix = st.selectbox("データグループ", prefixes)

    # 選択された接頭辞のキーのみ
    prefix_keys = [k for k in array_keys if k.startswith(selected_prefix + ".")]

    with col2:
        x_key = st.selectbox("X軸", prefix_keys, index=0)
    with col3:
        y_options = [k for k in prefix_keys if k != x_key]
        if not y_options:
            st.warning("Y軸に使用できるキーがありません。")
            return
        y_keys = st.multiselect("Y軸", y_options, default=y_options[:1])

    if not y_keys:
        st.info("Y軸を選択してください。")
        return

    # 表示モード: 個別ノード or グリッド比較
    view_mode = st.radio(
        "表示モード", ["グリッド比較", "個別ノード"], horizontal=True
    )

    # 共有フィルタをprovider用のフィルタ辞書に変換
    active_filters = _get_active_filters()

    # NG領域設定
    ng_regions = getattr(dashboard_config, "ng_regions", [])

    if view_mode == "グリッド比較":
        _render_array_grid(
            provider, dashboard_config, x_key, y_keys,
            filters=active_filters, ng_regions=ng_regions,
        )
    else:
        _render_array_single(
            provider, x_key, y_keys,
            filters=active_filters, ng_regions=ng_regions,
        )


def _render_array_grid(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
) -> None:
    """配列データのグリッド比較表示（indexごとに並べる）"""
    cols_per_row = getattr(dashboard_config, "gallery_columns", 4)

    for y_key in y_keys:
        st.subheader(f"{y_key} vs {x_key}")
        grid_data = provider.get_array_grid_data(x_key, y_key, filters=filters)
        if not grid_data:
            st.info(f"'{x_key}' と '{y_key}' のデータがありません。")
            continue

        # indexでソート
        grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))

        try:
            import plotly.graph_objects as go

            for row_start in range(0, len(grid_data), cols_per_row):
                cols = st.columns(cols_per_row)
                for col_idx, item in enumerate(
                    grid_data[row_start: row_start + cols_per_row]
                ):
                    with cols[col_idx]:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=item["x_values"],
                            y=item["y_values"],
                            mode="lines+markers",
                            name=y_key,
                        ))
                        # NG領域塗りつぶし
                        if ng_regions:
                            _add_ng_regions(fig, ng_regions)
                        idx_str = item.get("index", "")
                        ver_str = item.get("version", "")
                        title = item["name"]
                        if idx_str:
                            title += f" (idx{idx_str}"
                            if ver_str:
                                title += f",v{ver_str}"
                            title += ")"
                        fig.update_layout(
                            title=title,
                            xaxis_title=x_key.split(".")[-1],
                            yaxis_title=y_key.split(".")[-1],
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=300,
                            showlegend=False,
                        )
                        st.plotly_chart(fig, use_container_width=True)

        except ImportError:
            st.warning("plotlyが必要です: pip install plotly")

        st.caption(f"データ数: {len(grid_data)}")


def _render_array_single(
    provider: DashboardDataProvider,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
) -> None:
    """配列データの個別ノード表示（複数Y軸重ね書き）"""
    rows = provider.get_go_table()
    if not rows:
        st.info("go_ファイルが見つかりません。")
        return

    # フィルタ適用
    if filters:
        rows = [r for r in rows if provider._matches_filters(r, filters)]

    # 配列データを持つノードのみ
    names_with_array = []
    for r in rows:
        node_id = r["id"]
        node = provider._node_by_id.get(node_id)
        if node and isinstance(node.properties.get(x_key), list):
            names_with_array.append(r["name"])

    if not names_with_array:
        st.info(f"'{x_key}' データを持つノードがありません。")
        return

    selected = st.selectbox("ノード選択", names_with_array)
    if not selected:
        return

    # 選択ノードのIDを取得
    node_id = next(
        (r["id"] for r in rows if r["name"] == selected),
        None,
    )
    if node_id is None:
        return

    plot_data = provider.get_array_plot_data(node_id, x_key, y_keys)
    if plot_data is None:
        st.warning("配列データの取得に失敗しました。")
        return

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        for s in plot_data["series"]:
            fig.add_trace(go.Scatter(
                x=plot_data["x_values"],
                y=s["values"],
                mode="lines+markers",
                name=s["key"].split(".")[-1],
            ))
        # NG領域塗りつぶし
        if ng_regions:
            _add_ng_regions(fig, ng_regions)
        fig.update_layout(
            title=f"{selected}",
            xaxis_title=x_key.split(".")[-1],
            yaxis_title="値",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")


# ====================================================================
# ステータスモニター
# ====================================================================


def _render_status_page(provider: DashboardDataProvider) -> None:
    """ステータスモニター: 実行ステータス一覧"""
    st.header("ステータスモニター")

    status = provider.get_status_summary()

    # サマリーメトリクス
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("合計", status["total"])
    col2.metric("完了", status["completed"])
    col3.metric("失敗", status["failed"])
    col4.metric("不明", status["unknown"])

    st.markdown("---")

    items = status["items"]
    if not items:
        st.info("go_ ファイルが見つかりません。")
        return

    # ステータス別に分類
    completed_items = [i for i in items if i["analysis_status"] == "completed"]
    failed_items = [i for i in items if i["analysis_status"] == "failed"]
    unknown_items = [
        i for i in items if i["analysis_status"] not in ("completed", "failed")
    ]

    if failed_items:
        st.subheader("❌ 失敗")
        import pandas as pd

        df = pd.DataFrame(failed_items)
        st.dataframe(df, use_container_width=True, hide_index=True)

    if unknown_items:
        st.subheader("❓ 不明 / 実行中")
        import pandas as pd

        df = pd.DataFrame(unknown_items)
        st.dataframe(df, use_container_width=True, hide_index=True)

    if completed_items:
        st.subheader("✅ 完了")
        import pandas as pd

        df = pd.DataFrame(completed_items)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ====================================================================
# 画像ギャラリー（NxMグリッド・プロパティ画像パス対応・キー別一覧）
# ====================================================================


def _render_gallery_page(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """画像ギャラリー: has_output関係 + プロパティ画像パスを表示"""
    st.header("画像ギャラリー")

    # 画像ソース選択
    source_options = ["has_output関係", "プロパティ画像パス"]
    image_source = st.radio(
        "画像ソース", source_options, horizontal=True
    )

    if image_source == "has_output関係":
        _render_gallery_output_images(provider, project_root, dashboard_config)
    else:
        _render_gallery_property_images(provider, project_root, dashboard_config)


def _normalize_group_key(key: str) -> str:
    """query.normalize_group_keyへの委譲ラッパー（後方互換）"""
    return normalize_group_key(key)


def _render_gallery_grouped(
    images: list[dict[str, Any]],
    cols_per_row: int,
    project_root: Path,
    source: str,
    group_key: str,
) -> None:
    """画像をグループ別に表示

    Args:
        images: 画像情報のリスト
        cols_per_row: 1行あたりの列数
        project_root: プロジェクトルート
        source: "output" or "property"
        group_key: グループ化に使用するキー（go_propertiesのキー名 or "property_key"）
    """
    from collections import OrderedDict

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for img in images:
        if group_key == "property_key":
            # property_keyでグルーピング（daily:日付:キー → キー部分のみ）
            raw_key = img.get("property_key", "")
            gk = _normalize_group_key(raw_key)
        else:
            # go_propertiesのキーでグルーピング
            gk = str(img.get("go_properties", {}).get(group_key, "（未設定）"))
        groups.setdefault(gk, []).append(img)

    for group_name, group_images in groups.items():
        st.subheader(f"{group_key}: {group_name}")
        st.caption(f"{len(group_images)} 件")
        _render_image_grid(group_images, cols_per_row, project_root, source=source)


def _render_gallery_output_images(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """has_output関係の画像ギャラリー（NxMグリッド・グループ表示対応）"""
    images = provider.get_output_images()

    if not images:
        st.info(
            "画像出力が見つかりません。has_output関係で画像ファイル"
            "（PNG/GIF/JPG等）が紐付いているgo_ノードがありません。"
        )
        return

    # フィルタ: フォーマット
    formats = sorted({img["image_format"] for img in images})
    selected_format = st.sidebar.selectbox(
        "画像フォーマット", ["すべて"] + formats
    )
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # グループ表示オプション
    group_keys = _collect_group_keys(images, source="output")
    group_by = st.sidebar.selectbox(
        "グループ表示", ["なし"] + group_keys, key="_gallery_output_group"
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(
            images, cols_per_row, project_root, source="output", group_key=group_by
        )
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input(
        "ページ", min_value=1, max_value=total_pages, value=1
    )
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx: start_idx + max_display]

    st.caption(
        f"{len(page_images)} / {total_images} 件 "
        f"（{cols_per_row}列 x {rows_per_page}行、ページ {page_num}/{total_pages}）"
    )

    if not page_images:
        st.info("条件に一致する画像がありません。")
        return

    # NxMグリッドで表示
    _render_image_grid(page_images, cols_per_row, project_root, source="output")


def _render_gallery_property_images(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """プロパティ画像パスのギャラリー（キー別一覧・NxMグリッド・グループ表示対応）"""
    images = provider.get_property_images()

    if not images:
        st.info(
            "プロパティに画像ファイルパスが見つかりません。"
            "Obsidianのdaily noteからプロパティに画像パスを割り当てたノードがありません。"
        )
        return

    # キー別フィルタ
    all_keys = sorted({img["property_key"] for img in images})
    selected_key = st.sidebar.selectbox(
        "プロパティキー", ["すべて"] + all_keys
    )
    if selected_key != "すべて":
        images = [img for img in images if img["property_key"] == selected_key]

    # フォーマットフィルタ
    formats = sorted({img["image_format"] for img in images})
    selected_format = st.sidebar.selectbox(
        "画像フォーマット（プロパティ）", ["すべて"] + formats
    )
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # グループ表示オプション
    group_keys = _collect_group_keys(images, source="property")
    group_by = st.sidebar.selectbox(
        "グループ表示（プロパティ）", ["なし"] + group_keys,
        key="_gallery_property_group",
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(
            images, cols_per_row, project_root, source="property", group_key=group_by
        )
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input(
        "ページ（プロパティ画像）", min_value=1, max_value=total_pages, value=1
    )
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx: start_idx + max_display]

    st.caption(
        f"{len(page_images)} / {total_images} 件 "
        f"（{cols_per_row}列 x {rows_per_page}行、ページ {page_num}/{total_pages}）"
    )

    if not page_images:
        st.info("条件に一致する画像がありません。")
        return

    # NxMグリッドで表示
    _render_image_grid(page_images, cols_per_row, project_root, source="property")


def _collect_group_keys(
    images: list[dict[str, Any]], source: str
) -> list[str]:
    """query.collect_group_keysへの委譲ラッパー（後方互換）"""
    return collect_group_keys(images, source)


def _render_image_grid(
    images: list[dict[str, Any]],
    cols_per_row: int,
    project_root: Path,
    source: str,
) -> None:
    """画像をNxMグリッドで描画

    Args:
        images: 画像情報のリスト
        cols_per_row: 1行あたりの列数
        project_root: プロジェクトルート
        source: "output"（has_output）または "property"（プロパティ画像パス）
    """
    for row_start in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, img_info in enumerate(
            images[row_start: row_start + cols_per_row]
        ):
            with cols[col_idx]:
                # ヘッダー情報
                if source == "output":
                    st.markdown(f"**{img_info['go_node_name']}**")
                    props = img_info["go_properties"]
                    prop_lines = []
                    for key in ("index", "version", "type", "analysis_status"):
                        if key in props:
                            prop_lines.append(f"{key}: {props[key]}")
                    if prop_lines:
                        st.caption(" | ".join(prop_lines))
                    image_path_str = img_info["image_path"]
                    caption = img_info["image_name"]
                else:
                    st.markdown(f"**{img_info['go_node_name']}**")
                    st.caption(f"key: {img_info['property_key']}")
                    image_path_str = img_info["image_path"]
                    caption = f"{img_info['property_key']}: {Path(image_path_str).name}"

                # 画像表示（プロジェクトルート基準、フォールバック: notes/daily基準）
                image_path = project_root / image_path_str
                if not image_path.exists():
                    # notes/daily基準のパスとして再試行
                    fallback = project_root / "notes" / "daily" / image_path_str
                    if fallback.exists():
                        image_path = fallback
                if image_path.exists():
                    st.image(
                        str(image_path),
                        caption=caption,
                        use_container_width=True,
                    )
                else:
                    st.warning(f"画像が見つかりません: {image_path_str}")


# ====================================================================
# 保存済みビュー（config.yamlのsaved-views順に各ビューを表示）
# ====================================================================


def _render_saved_views_page(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """保存済みビュー: config.yamlのsaved-views順に各ビューをまとめて表示

    config.yamlからの静的ビューに加え、session_stateに保存された
    動的ビューも表示する。動的ビューはUI上で追加・編集・削除が可能。
    """
    st.header("保存済みビュー")

    saved_views = list(getattr(dashboard_config, "saved_views", []))

    # session_stateに保存された動的ビューを取得
    if "_dynamic_views" not in st.session_state:
        st.session_state["_dynamic_views"] = []
    dynamic_views: list[dict[str, Any]] = st.session_state["_dynamic_views"]

    # 動的ビューをSavedViewConfigに変換
    from config import SavedViewConfig
    dynamic_view_configs: list[SavedViewConfig] = []
    for dv in dynamic_views:
        try:
            dynamic_view_configs.append(SavedViewConfig.from_dict(dv))
        except (ValueError, KeyError):
            pass

    all_views = saved_views + dynamic_view_configs

    if not all_views:
        st.info(
            "保存済みビューがありません。config.yaml の "
            "dashboard.saved-views に定義するか、下のフォームから追加してください。"
        )

    for idx, view in enumerate(all_views):
        st.markdown("---")
        is_dynamic = idx >= len(saved_views)
        dyn_idx = idx - len(saved_views) if is_dynamic else -1

        # ビューヘッダー（動的ビューは編集・削除ボタン付き）
        if is_dynamic:
            hcol1, hcol2, hcol3 = st.columns([6, 1, 1])
            with hcol1:
                st.subheader(f"{view.name}")
            with hcol2:
                if st.button("編集", key=f"_edit_dv_{dyn_idx}"):
                    st.session_state[f"_editing_dv_{dyn_idx}"] = True
            with hcol3:
                if st.button("削除", key=f"_del_dv_{dyn_idx}"):
                    st.session_state["_dynamic_views"].pop(dyn_idx)
                    st.rerun()
        else:
            st.subheader(f"{view.name}")

        st.caption(f"タイプ: {view.view_type}" + (" (動的)" if is_dynamic else ""))

        # 動的ビュー編集フォーム
        if is_dynamic and st.session_state.get(f"_editing_dv_{dyn_idx}", False):
            _render_view_edit_form(provider, dyn_idx, dynamic_views[dyn_idx])
            continue

        if view.view_type == "table":
            _render_saved_table(provider, dashboard_config, view, vocab)
        elif view.view_type == "plot":
            _render_saved_plot(provider, view, dashboard_config)
        elif view.view_type == "gallery":
            _render_saved_gallery(provider, project_root, dashboard_config, view)
        elif view.view_type == "card":
            _render_saved_card(provider, view)
        elif view.view_type == "status":
            _render_status_page(provider)
        elif view.view_type == "array_plot":
            _render_saved_array_plot(provider, dashboard_config, view)

    # HTMLエクスポート
    st.markdown("---")
    _render_html_export_button(
        provider, project_root, dashboard_config, vocab
    )

    # 新規ビュー追加セクション
    st.markdown("---")
    _render_view_add_form(provider)


def _render_saved_table(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    view: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """保存済みテーブルビューを描画"""
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

    display_rows = []
    for r in filtered:
        row = {k: v for k, v in r.items() if k != "related_files"}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)

    # config駆動カラム選択（vocab順ソート対応）
    table_columns = getattr(dashboard_config, "table_columns", None)
    selected_cols = _select_table_columns(
        list(df.columns), table_columns, vocab=vocab or {}
    )
    if selected_cols:
        df = df[[c for c in selected_cols if c in df.columns]]

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Excelダウンロードボタン
    _render_excel_download(df, f"saved_view_{view.name}")


def _render_saved_plot(
    provider: DashboardDataProvider,
    view: Any,
    dashboard_config: Any = None,
) -> None:
    """保存済みプロットビューを描画"""
    plot_config = view.plot
    x_key = plot_config.get("x")
    y_key = plot_config.get("y")
    color = plot_config.get("color")
    chart_type = plot_config.get("chart_type", "散布図")

    if not x_key or not y_key:
        st.warning("プロット設定にx/yが指定されていません。")
        return

    data = provider.get_plot_data(x_key, y_key, color_key=color)

    # 保存済みフィルタを適用（名前ベースでフィルタ）
    if view.filters:
        all_rows = provider.get_go_table()
        filtered_rows = apply_saved_view_filters(all_rows, view.filters)
        filtered_names = {r["name"] for r in filtered_rows}
        data = [d for d in data if d.get("name") in filtered_names]

    if not data:
        st.warning(
            f"'{x_key}' と '{y_key}' の両方が数値であるデータが見つかりません。"
        )
        return

    import pandas as pd

    df = pd.DataFrame(data)

    try:
        import plotly.express as px

        fig = _create_plot_figure(px, df, x_key, y_key, color, chart_type)
        # NG領域塗りつぶし
        ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []
        if ng_regions:
            _add_ng_regions(fig, ng_regions)
        # グループ結線
        group_line_key = getattr(dashboard_config, "group_line_key", None) if dashboard_config else None
        if group_line_key and group_line_key in df.columns:
            _add_group_lines(fig, df, x_key, y_key, group_line_key)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.scatter_chart(df, x=x_key, y=y_key)

    st.caption(f"データ点数: {len(data)}")


def _render_saved_gallery(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    view: Any,
) -> None:
    """保存済みギャラリービューを描画"""
    gallery_config = view.gallery
    source = gallery_config.get("source", "has_output")
    property_key = gallery_config.get("property_key")
    format_filter = gallery_config.get("format")

    if source == "property":
        images = provider.get_property_images()
        if property_key:
            images = [
                img for img in images if img["property_key"] == property_key
            ]
    else:
        images = provider.get_output_images()

    if format_filter:
        images = [
            img for img in images if img["image_format"] == format_filter
        ]

    if not images:
        st.info("条件に一致する画像がありません。")
        return

    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)
    max_display = cols_per_row * rows_per_page
    images = images[:max_display]

    st.caption(f"{len(images)} 件")
    _render_image_grid(
        images, cols_per_row, project_root,
        source="property" if source == "property" else "output",
    )


def _render_saved_card(
    provider: DashboardDataProvider,
    view: Any,
) -> None:
    """保存済みカードビューを描画"""
    rows = provider.get_go_table()
    if not rows:
        st.info("go_ ファイルが見つかりません。")
        return

    # 保存済みフィルタを適用
    filtered = apply_saved_view_filters(rows, view.filters)
    if not filtered:
        st.info("条件に一致するデータがありません。")
        return

    # 先頭のノードをカード表示
    first_row = filtered[0]
    node_id = first_row.get("id")
    if node_id is None:
        return

    card = provider.get_node_card(node_id)
    if card is None:
        return

    st.markdown(f"**{card['name']}** ({card['type']})")
    props = {
        k: v for k, v in card["properties"].items()
        if k not in ("path", "include_properties")
    }
    if props:
        import pandas as pd

        props_flat = {}
        for k, v in props.items():
            if isinstance(v, (dict, list)):
                props_flat[k] = str(v)
            else:
                props_flat[k] = v
        df = pd.DataFrame([props_flat]).T
        df.columns = ["値"]
        st.dataframe(df, use_container_width=True)


def _render_saved_array_plot(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    view: Any,
) -> None:
    """保存済み配列プロットビューを描画

    array_plot設定: {"prefix": "RF", "x": "RF.time", "y": ["RF.RF3"], "mode": "grid"}
    """
    ap_config = getattr(view, "array_plot", {})
    prefix = ap_config.get("prefix", "")
    x_key = ap_config.get("x", "")
    y_keys = ap_config.get("y", [])
    mode = ap_config.get("mode", "grid")

    if not x_key:
        # 接頭辞から自動決定
        array_keys = provider.get_array_property_keys()
        if prefix:
            prefix_keys = [k for k in array_keys if k.startswith(prefix + ".")]
        else:
            prefix_keys = array_keys
        if not prefix_keys:
            st.info("配列プロパティが見つかりません。")
            return
        x_key = prefix_keys[0]
        if not y_keys:
            y_keys = [k for k in prefix_keys if k != x_key]

    if isinstance(y_keys, str):
        y_keys = [y_keys]

    if not y_keys:
        st.info("Y軸の配列キーが指定されていません。")
        return

    # フィルタ適用
    filters = getattr(view, "filters", {}) or {}
    filter_dict = saved_view_filters_to_provider_filters(filters) if filters else None

    # NG領域設定
    ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []

    if mode == "single":
        # 個別ノード重ね書き（先頭ノードを表示）
        rows = provider.get_go_table()
        if filters:
            rows = apply_saved_view_filters(rows, filters)
        if rows:
            node_id = rows[0]["id"]
            plot_data = provider.get_array_plot_data(node_id, x_key, y_keys)
            if plot_data:
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    for s in plot_data["series"]:
                        fig.add_trace(go.Scatter(
                            x=plot_data["x_values"],
                            y=s["values"],
                            mode="lines+markers",
                            name=s["key"].split(".")[-1],
                        ))
                    # NG領域塗りつぶし
                    if ng_regions:
                        _add_ng_regions(fig, ng_regions)
                    fig.update_layout(
                        title=plot_data["name"],
                        xaxis_title=x_key.split(".")[-1],
                        yaxis_title="値",
                        height=500,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.warning("plotlyが必要です。")
    else:
        # グリッド比較
        for y_key in y_keys:
            grid_data = provider.get_array_grid_data(x_key, y_key, filters=filter_dict)
            if not grid_data:
                continue
            grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))
            cols_per_row = getattr(dashboard_config, "gallery_columns", 4)
            st.markdown(f"**{y_key} vs {x_key}**")
            try:
                import plotly.graph_objects as go
                for row_start in range(0, len(grid_data), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for col_idx, item in enumerate(
                        grid_data[row_start: row_start + cols_per_row]
                    ):
                        with cols[col_idx]:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=item["x_values"],
                                y=item["y_values"],
                                mode="lines+markers",
                                name=y_key,
                            ))
                            # NG領域塗りつぶし
                            if ng_regions:
                                _add_ng_regions(fig, ng_regions)
                            title = item["name"]
                            idx_str = item.get("index", "")
                            if idx_str:
                                title += f" (idx{idx_str})"
                            fig.update_layout(
                                title=title,
                                xaxis_title=x_key.split(".")[-1],
                                yaxis_title=y_key.split(".")[-1],
                                margin=dict(l=20, r=20, t=40, b=20),
                                height=300,
                                showlegend=False,
                            )
                            st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning("plotlyが必要です。")
            st.caption(f"データ数: {len(grid_data)}")


def _render_html_export_button(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """保存済みビューをスタンドアロンHTMLとしてエクスポート

    plotlyのプロットは`fig.to_html(full_html=False)`でインライン化、
    テーブルはpandas `df.to_html()`で変換し、1つのHTMLファイルにまとめる。
    """
    saved_views = list(getattr(dashboard_config, "saved_views", []))

    # 動的ビューも含める
    dynamic_views = st.session_state.get("_dynamic_views", [])
    from config import SavedViewConfig
    for dv in dynamic_views:
        try:
            saved_views.append(SavedViewConfig.from_dict(dv))
        except (ValueError, KeyError):
            pass

    if not saved_views:
        return

    if st.button("HTMLエクスポート", key="_html_export_btn"):
        with st.spinner("HTMLを生成中..."):
            html = generate_saved_views_html(
                provider, project_root, dashboard_config, saved_views, vocab
            )
        st.download_button(
            label="HTMLダウンロード",
            data=html.encode("utf-8"),
            file_name="dashboard_views.html",
            mime="text/html",
            key="_html_download_btn",
        )


def _render_view_add_form(
    provider: DashboardDataProvider,
) -> None:
    """保存済みビューの新規追加フォーム"""
    with st.expander("ビューを追加", expanded=False):
        view_name = st.text_input("ビュー名", key="_add_view_name")
        view_type = st.selectbox(
            "タイプ",
            ["table", "plot", "array_plot", "gallery", "card", "status"],
            key="_add_view_type",
        )

        # フィルタ設定
        st.markdown("**フィルタ（任意）**")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_type = st.text_input("type", key="_add_view_f_type")
        with fc2:
            f_status = st.text_input("analysis_status", key="_add_view_f_status")
        with fc3:
            f_active = st.checkbox("active", key="_add_view_f_active")

        # タイプ固有設定
        plot_config: dict[str, Any] = {}
        array_plot_config: dict[str, Any] = {}
        gallery_config: dict[str, Any] = {}

        if view_type == "plot":
            st.markdown("**プロット設定**")
            keys = provider.get_property_keys()
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                px_key = st.selectbox("X軸", keys, key="_add_view_px") if keys else ""
            with pc2:
                py_key = st.selectbox("Y軸", keys, key="_add_view_py", index=min(1, len(keys) - 1)) if keys else ""
            with pc3:
                p_chart = st.selectbox("チャート", ["散布図", "棒グラフ", "線図"], key="_add_view_pchart")
            plot_config = {"x": px_key, "y": py_key, "chart_type": p_chart}

        elif view_type == "array_plot":
            st.markdown("**配列プロット設定**")
            array_keys = provider.get_array_property_keys()
            if array_keys:
                prefixes = sorted({k.split(".")[0] for k in array_keys})
                ac1, ac2 = st.columns(2)
                with ac1:
                    ap_prefix = st.selectbox("プレフィックス", prefixes, key="_add_view_ap_prefix")
                with ac2:
                    ap_mode = st.selectbox("モード", ["grid", "single"], key="_add_view_ap_mode")
                prefix_keys = [k for k in array_keys if k.startswith(ap_prefix + ".")]
                ap_x = st.selectbox("X軸", prefix_keys, key="_add_view_ap_x") if prefix_keys else ""
                ap_y_options = [k for k in prefix_keys if k != ap_x]
                ap_y = st.multiselect("Y軸", ap_y_options, key="_add_view_ap_y")
                array_plot_config = {
                    "prefix": ap_prefix, "x": ap_x,
                    "y": ap_y, "mode": ap_mode,
                }

        elif view_type == "gallery":
            st.markdown("**ギャラリー設定**")
            gc1, gc2 = st.columns(2)
            with gc1:
                g_source = st.selectbox("ソース", ["has_output", "property"], key="_add_view_gsrc")
            with gc2:
                g_format = st.text_input("フォーマット", key="_add_view_gfmt")
            gallery_config = {"source": g_source}
            if g_format:
                gallery_config["format"] = g_format

        if st.button("追加", key="_add_view_btn"):
            if not view_name:
                st.warning("ビュー名を入力してください。")
            else:
                filters: dict[str, Any] = {}
                if f_type:
                    filters["type"] = f_type
                if f_status:
                    filters["analysis_status"] = f_status
                if f_active:
                    filters["active"] = True

                new_view: dict[str, Any] = {
                    "name": view_name,
                    "type": view_type,
                    "filters": filters,
                    "plot": plot_config,
                    "array_plot": array_plot_config,
                    "gallery": gallery_config,
                }
                st.session_state["_dynamic_views"].append(new_view)
                st.rerun()


def _render_view_edit_form(
    provider: DashboardDataProvider,
    dyn_idx: int,
    view_data: dict[str, Any],
) -> None:
    """動的ビューの編集フォーム"""
    with st.container():
        view_name = st.text_input(
            "ビュー名", value=view_data.get("name", ""),
            key=f"_edit_name_{dyn_idx}",
        )
        view_type = st.selectbox(
            "タイプ",
            ["table", "plot", "array_plot", "gallery", "card", "status"],
            index=["table", "plot", "array_plot", "gallery", "card", "status"].index(
                view_data.get("type", "table")
            ),
            key=f"_edit_type_{dyn_idx}",
        )

        # フィルタ設定
        st.markdown("**フィルタ**")
        existing_filters = view_data.get("filters", {})
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_type = st.text_input(
                "type", value=existing_filters.get("type", ""),
                key=f"_edit_f_type_{dyn_idx}",
            )
        with fc2:
            f_status = st.text_input(
                "analysis_status",
                value=existing_filters.get("analysis_status", ""),
                key=f"_edit_f_status_{dyn_idx}",
            )
        with fc3:
            f_active = st.checkbox(
                "active", value=existing_filters.get("active", False),
                key=f"_edit_f_active_{dyn_idx}",
            )

        ec1, ec2 = st.columns(2)
        with ec1:
            if st.button("保存", key=f"_edit_save_{dyn_idx}"):
                filters: dict[str, Any] = {}
                if f_type:
                    filters["type"] = f_type
                if f_status:
                    filters["analysis_status"] = f_status
                if f_active:
                    filters["active"] = True

                view_data["name"] = view_name
                view_data["type"] = view_type
                view_data["filters"] = filters
                st.session_state["_dynamic_views"][dyn_idx] = view_data
                st.session_state[f"_editing_dv_{dyn_idx}"] = False
                st.rerun()
        with ec2:
            if st.button("キャンセル", key=f"_edit_cancel_{dyn_idx}"):
                st.session_state[f"_editing_dv_{dyn_idx}"] = False
                st.rerun()


# _saved_view_filters_to_provider_filters, _apply_saved_view_filters は
# query.py からトップレベルでインポート済み


if __name__ == "__main__":
    main()
