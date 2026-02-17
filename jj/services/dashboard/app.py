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
from typing import TYPE_CHECKING, Any

import streamlit as st
import yaml

if TYPE_CHECKING:
    import pandas as pd

# プロジェクトルートをsys.pathに追加（Streamlitプロセスからのインポート用）
_project_src = str(Path(__file__).resolve().parents[2])
if _project_src not in sys.path:
    sys.path.insert(0, _project_src)

# コネクター自動登録（インポート時に__init_subclass__で登録される）
import contextlib  # noqa: E402

# PageComponent/ViewConfig自動登録（インポート時に__init_subclass__で登録される）
import services.dashboard.components.array_plot  # noqa: E402
import services.dashboard.components.card  # noqa: E402
import services.dashboard.components.gallery  # noqa: E402
import services.dashboard.components.plot  # noqa: E402
import services.dashboard.components.status  # noqa: E402
import services.dashboard.components.table  # noqa: E402
import services.dashboard.connectors.abaqus  # noqa: F401, E402
from jj_types import GraphModel  # noqa: E402
from services.dashboard.components import (  # noqa: E402
    get_page_component,
    get_page_component_by_label,
    get_page_labels,
    get_view_config,
    get_view_type_options,
)
from services.dashboard.connectors import get_connector_pages, render_connector_page  # noqa: E402
from services.dashboard.data_provider import DashboardDataProvider  # noqa: E402
from services.dashboard.html_export import (  # noqa: E402
    _add_group_lines_to_fig,
    _add_ng_regions_to_fig,
    _create_plot_figure,
    generate_saved_views_html,
)
from services.dashboard.query import (  # noqa: E402
    apply_filters,
    apply_saved_view_filters,
    collect_group_keys,
    extract_path_metadata,
    filter_images_by_keys,
    get_graph_mtime,
    is_truthy,
    normalize_group_key,
    saved_view_filters_to_provider_filters,
    select_table_columns,
)
from services.graph import GraphService  # noqa: E402


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
# ビュー永続化（.jj/storage/saved-views.yaml）
# ====================================================================

_SAVED_VIEWS_FILENAME = "saved-views.yaml"


def _saved_views_path(project_root: Path) -> Path:
    """保存済みビューファイルのパスを返す"""
    return project_root / ".jj" / "storage" / _SAVED_VIEWS_FILENAME


def _load_persistent_views(project_root: Path) -> list[dict[str, Any]]:
    """永続化されたビューをファイルから読み込む

    .jj/storage/saved-views.yaml が存在しない場合は空リストを返す。
    """
    path = _saved_views_path(project_root)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_persistent_views(project_root: Path, views: list[dict[str, Any]]) -> None:
    """ビューをファイルに永続化する

    .jj/storage/saved-views.yaml に書き出す。
    """
    path = _saved_views_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(views, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


# ====================================================================
# AgGrid ヘルパー
# ====================================================================


def _try_render_aggrid(df: pd.DataFrame) -> bool:
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
        st.session_state.setdefault("_filter_active", is_truthy(raw_active))
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
        refresh_sec = st.sidebar.slider("リフレッシュ間隔（秒）", min_value=3, max_value=60, value=10)
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
    verbose_name_format = None
    global_columns: list[str] | None = None
    try:
        from config import DashboardConfig, GraphConfig

        config = GraphConfig.load(base_dir=project_root)
        vocab = config.vocab
        units = config.export.units
        dashboard_config = config.dashboard
        verbose_name_format = config.verbose_name_format
        # export.csv-columnsをグローバル設定として昇格（dashboard + exportで共有）
        global_columns = config.export.csv_columns
    except Exception:
        vocab = {}
        units = {}

    if dashboard_config is None:
        from config import DashboardConfig

        dashboard_config = DashboardConfig.from_dict({})

    provider = DashboardDataProvider(
        graph,
        vocab=vocab,
        units=units,
        verbose_name_format=verbose_name_format,
        global_columns=global_columns,
    )

    # 共有フィルタ初期化
    _init_shared_filters(dashboard_config.default_filters)

    # ページ選択（PageComponentレジストリ + コネクターページ + 保存済みビュー）
    page_options = get_page_labels()
    # コネクターが提供するページを動的追加
    connector_pages = get_connector_pages(provider)
    page_options.extend(connector_pages)
    # 保存済みビューは常に表示（config定義 + 永続化ビュー）
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

    # 共通kwargs（全PageComponentに渡す）
    render_kwargs: dict[str, Any] = {
        "vocab": vocab,
        "project_root": project_root,
    }

    # PageComponentレジストリからディスパッチ
    component = get_page_component_by_label(page)
    if component is not None:
        component.render_page(provider, dashboard_config, **render_kwargs)
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
    filtered = apply_filters(
        rows,
        type_filter=st.session_state.get("_filter_type", "すべて"),
        status_filter=st.session_state.get("_filter_status", "すべて"),
        active_only=st.session_state.get("_filter_active", False),
    )

    st.caption(f"{len(filtered)} / {len(rows)} 件")

    if not filtered:
        st.info("条件に一致するデータがありません。")
        return

    import pandas as pd

    # verbose_nameキー
    vn_key = provider._verbose_name_key

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

    # nameカラムを表示名で置き換え（verbose_nameキーが存在する場合）
    if vn_key in df.columns:
        df["name"] = df[vn_key]

    # config駆動カラム選択（vocab順ソート対応）
    # グローバルカラム設定がある場合はそちらを優先
    table_columns = getattr(dashboard_config, "table_columns", None)
    if not table_columns and provider._global_columns:
        table_columns = provider._global_columns
    selected_cols = select_table_columns(list(df.columns), table_columns, vocab=vocab or {})
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


def _render_excel_download(df: pd.DataFrame, filename_prefix: str = "data") -> None:
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

    # verbose_nameキー（vocab変換後）
    vn_key = provider._verbose_name_key
    # 選択肢: 表示名があればそれを使用
    display_names = [r.get(vn_key, r["name"]) for r in rows]
    selected = st.selectbox("ノード選択", display_names)

    if not selected:
        return

    # IDを取得
    node_id = next((r["id"] for r in rows if r.get(vn_key, r["name"]) == selected), None)
    if node_id is None:
        return

    card = provider.get_node_card(node_id)
    if card is None:
        st.error("ノード情報を取得できませんでした。")
        return

    # カード表示
    col1, col2 = st.columns(2)

    # 表示名を取得
    display_name = card["properties"].get(vn_key) or card["properties"].get("verbose_name") or card["name"]

    with col1:
        st.subheader(display_name)
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

    props = {k: v for k, v in card["properties"].items() if k not in ("path", "include_properties")}
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
            st.markdown(f"- {direction} **{rel['label']}** → {rel['node_name']} ({rel['node_type']})")
    else:
        st.info("リレーションがありません。")


# ====================================================================
# プロットビュー（config駆動デフォルト軸・NxMグリッド対応）
# ====================================================================


def _build_axis_range(
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


def _build_style_config(
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


def _apply_style_to_fig(fig: Any, style: dict[str, int]) -> None:
    """スタイル設定をplotly Figureに適用

    Args:
        fig: plotly Figure
        style: _build_style_configの戻り値
    """
    if not style:
        return
    if "marker_size" in style:
        fig.update_traces(marker=dict(size=style["marker_size"]))
    if "line_width" in style:
        fig.update_traces(line=dict(width=style["line_width"]))
    if "font_size" in style:
        fig.update_layout(
            font=dict(size=style["font_size"]),
            title_font=dict(size=style["font_size"] + 2),
            xaxis=dict(title_font=dict(size=style["font_size"])),
            yaxis=dict(title_font=dict(size=style["font_size"])),
        )


def _render_plot_page(provider: DashboardDataProvider, dashboard_config: Any) -> None:
    """プロットビュー: プロパティの散布図/棒グラフ"""
    st.header("プロットビュー")

    # グローバルカラム設定がある場合はフィルタ済みキーを使用
    all_keys = provider.get_property_keys()
    keys = provider.get_filtered_property_keys()
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

    # verbose_nameキー
    vn_key = provider._verbose_name_key

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        x_key = st.selectbox("X軸", keys, index=x_default_idx)
    with col2:
        y_key = st.selectbox("Y軸", keys, index=y_default_idx)
    with col3:
        # 色分けオプション: デフォルトで表示名を選択
        color_options = ["なし", vn_key, *[k for k in keys if k != vn_key]]
        color_default_idx = 1  # デフォルト: 表示名で色分け
        color_key = st.selectbox("色分け", color_options, index=color_default_idx)
    with col4:
        chart_type = st.selectbox("チャートタイプ", ["散布図", "棒グラフ", "線図"])

    if not x_key or not y_key:
        return

    # グループ結線設定
    group_line_key = getattr(dashboard_config, "group_line_key", None)
    group_line_options = ["なし"] + [k for k in all_keys if k != x_key and k != y_key]
    col_gl1, _col_gl2 = st.columns(2)
    with col_gl1:
        gl_default = 0
        if group_line_key and group_line_key in group_line_options:
            gl_default = group_line_options.index(group_line_key)
        selected_group_line = st.selectbox("グループ結線キー", group_line_options, index=gl_default)

    # 軸範囲設定（number_input）
    with st.expander("軸範囲設定", expanded=False):
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            x_min = st.number_input("X最小", value=None, key="_plot_x_min", format="%g")
        with rc2:
            x_max = st.number_input("X最大", value=None, key="_plot_x_max", format="%g")
        with rc3:
            y_min = st.number_input("Y最小", value=None, key="_plot_y_min", format="%g")
        with rc4:
            y_max = st.number_input("Y最大", value=None, key="_plot_y_max", format="%g")

    # スタイル設定
    with st.expander("スタイル設定", expanded=False):
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            plot_marker_size = st.number_input(
                "マーカーサイズ", value=None, min_value=1, max_value=50, key="_plot_marker_size"
            )
        with sc2:
            plot_line_width = st.number_input("線幅", value=None, min_value=1, max_value=20, key="_plot_line_width")
        with sc3:
            plot_font_size = st.number_input(
                "フォントサイズ", value=None, min_value=6, max_value=48, key="_plot_font_size"
            )

    plot_style = _build_style_config(plot_marker_size, plot_line_width, plot_font_size)

    color = color_key if color_key != "なし" else None

    # グループ結線キーをextra_keysに追加してデータに含める
    gl_key = selected_group_line if selected_group_line != "なし" else None
    extra_keys: list[str] = []
    if gl_key:
        extra_keys.append(gl_key)

    data = provider.get_plot_data(x_key, y_key, color_key=color, extra_keys=extra_keys)

    if not data:
        st.warning(f"'{x_key}' と '{y_key}' の両方が数値であるデータが見つかりません。")
        return

    import pandas as pd

    df = pd.DataFrame(data)

    try:
        import plotly.express as px

        fig = _create_plot_figure(
            px,
            df,
            x_key,
            y_key,
            color,
            chart_type,
            hover_name_col=vn_key,
        )
        # NG領域塗りつぶし
        ng_regions = getattr(dashboard_config, "ng_regions", [])
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)
        # グループ結線
        if gl_key and gl_key in df.columns:
            _add_group_lines_to_fig(fig, df, x_key, y_key, gl_key)
        # 軸範囲設定を適用
        x_range = _build_axis_range(x_min, x_max)
        y_range = _build_axis_range(y_min, y_max)
        if x_range:
            fig.update_xaxes(range=x_range)
        if y_range:
            fig.update_yaxes(range=y_range)
        # スタイル設定を適用
        _apply_style_to_fig(fig, plot_style)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # plotlyがない場合はStreamlit組み込みチャートを使用
        st.scatter_chart(df, x=x_key, y=y_key)

    st.caption(f"データ点数: {len(data)}")


# ====================================================================
# 配列プロットビュー（反力プロファイル等の時系列データ）
# ====================================================================


def _render_array_plot_page(provider: DashboardDataProvider, dashboard_config: Any) -> None:
    """配列プロットビュー: GOノードの配列プロパティをラインプロット"""
    st.header("配列プロットビュー")

    array_keys = provider.get_array_property_keys()
    if not array_keys:
        st.info("配列プロパティが見つかりません。CSVファイルがhas_output関係でGOファイルに紐付いている必要があります。")
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

    # 表示モード: 全条件比較 or 個別ノード
    view_mode = st.radio("表示モード", ["全条件比較", "個別ノード"], horizontal=True)

    # 軸範囲設定（number_input）
    with st.expander("軸範囲設定", expanded=False):
        rc1, rc2, rc3, rc4 = st.columns(4)
        with rc1:
            ax_x_min = st.number_input("X最小", value=None, key="_ap_x_min", format="%g")
        with rc2:
            ax_x_max = st.number_input("X最大", value=None, key="_ap_x_max", format="%g")
        with rc3:
            ax_y_min = st.number_input("Y最小", value=None, key="_ap_y_min", format="%g")
        with rc4:
            ax_y_max = st.number_input("Y最大", value=None, key="_ap_y_max", format="%g")

    # スタイル設定
    with st.expander("スタイル設定", expanded=False):
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            ap_marker_size = st.number_input(
                "マーカーサイズ", value=None, min_value=1, max_value=50, key="_ap_marker_size"
            )
        with sc2:
            ap_line_width = st.number_input("線幅", value=None, min_value=1, max_value=20, key="_ap_line_width")
        with sc3:
            ap_font_size = st.number_input("フォントサイズ", value=None, min_value=6, max_value=48, key="_ap_font_size")

    ap_x_range = _build_axis_range(ax_x_min, ax_x_max)
    ap_y_range = _build_axis_range(ax_y_min, ax_y_max)
    ap_style = _build_style_config(ap_marker_size, ap_line_width, ap_font_size)

    # 共有フィルタをprovider用のフィルタ辞書に変換
    active_filters = _get_active_filters()

    # NG領域設定
    ng_regions = getattr(dashboard_config, "ng_regions", [])

    if view_mode == "全条件比較":
        _render_array_overlay(
            provider,
            x_key,
            y_keys,
            filters=active_filters,
            ng_regions=ng_regions,
            x_range=ap_x_range,
            y_range=ap_y_range,
            style=ap_style,
        )
    else:
        _render_array_single(
            provider,
            x_key,
            y_keys,
            filters=active_filters,
            ng_regions=ng_regions,
            x_range=ap_x_range,
            y_range=ap_y_range,
            style=ap_style,
        )


def _render_array_overlay(
    provider: DashboardDataProvider,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    style: dict[str, int] | None = None,
) -> None:
    """全条件の配列データを凡例付きで同一グラフに重ね書き"""
    for y_key in y_keys:
        st.subheader(f"{y_key} vs {x_key}")
        grid_data = provider.get_array_grid_data(x_key, y_key, filters=filters)
        if not grid_data:
            st.info(f"'{x_key}' と '{y_key}' のデータがありません。")
            continue

        grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            for item in grid_data:
                # display_nameがあれば優先使用
                label = item.get("display_name", item["name"])
                fig.add_trace(
                    go.Scatter(
                        x=item["x_values"],
                        y=item["y_values"],
                        mode="lines+markers",
                        name=label,
                    )
                )
            if ng_regions:
                _add_ng_regions_to_fig(fig, ng_regions)
            fig.update_layout(
                title=f"{y_key} vs {x_key}（全条件比較）",
                xaxis_title=x_key.split(".")[-1],
                yaxis_title=y_key.split(".")[-1],
                height=600,
                showlegend=True,
            )
            if x_range:
                fig.update_xaxes(range=x_range)
            if y_range:
                fig.update_yaxes(range=y_range)
            if style:
                _apply_style_to_fig(fig, style)
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
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    style: dict[str, int] | None = None,
) -> None:
    """配列データの個別ノード表示（複数Y軸重ね書き）"""
    rows = provider.get_go_table()
    if not rows:
        st.info("go_ファイルが見つかりません。")
        return

    # フィルタ適用
    if filters:
        rows = [r for r in rows if provider._matches_filters(r, filters)]

    # verbose_nameキー
    vn_key = provider._verbose_name_key

    # 配列データを持つノードのみ（表示名を使用）
    items_with_array = []
    for r in rows:
        nid = r["id"]
        node = provider._node_by_id.get(nid)
        if node and isinstance(node.properties.get(x_key), list):
            items_with_array.append(
                {
                    "id": nid,
                    "display_name": r.get(vn_key, r["name"]),
                }
            )

    if not items_with_array:
        st.info(f"'{x_key}' データを持つノードがありません。")
        return

    display_names = [item["display_name"] for item in items_with_array]
    selected = st.selectbox("ノード選択", display_names)
    if not selected:
        return

    # 選択ノードのIDを取得
    node_id = next(
        (item["id"] for item in items_with_array if item["display_name"] == selected),
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
            fig.add_trace(
                go.Scatter(
                    x=plot_data["x_values"],
                    y=s["values"],
                    mode="lines+markers",
                    name=s["key"].split(".")[-1],
                )
            )
        # NG領域塗りつぶし
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)
        fig.update_layout(
            title=f"{selected}",
            xaxis_title=x_key.split(".")[-1],
            yaxis_title="値",
            height=500,
        )
        if x_range:
            fig.update_xaxes(range=x_range)
        if y_range:
            fig.update_yaxes(range=y_range)
        if style:
            _apply_style_to_fig(fig, style)
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
    unknown_items = [i for i in items if i["analysis_status"] not in ("completed", "failed")]

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
    image_source = st.radio("画像ソース", source_options, horizontal=True)

    if image_source == "has_output関係":
        _render_gallery_output_images(provider, project_root, dashboard_config)
    else:
        _render_gallery_property_images(provider, project_root, dashboard_config)


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
        group_key: グループ化に使用するキー
            - "property_key": プロパティキーでグルーピング
            - "result_key": 画像パスからresult_keyを抽出してグルーピング
            - その他: go_propertiesのキー名でグルーピング
    """
    from collections import OrderedDict

    if group_key == "result_key":
        # 画像パスからresult_keyとプロパティを抽出してグルーピング
        groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        for img in images:
            path = img.get("image_path", "")
            result_key, _props = extract_path_metadata(path)
            gk = result_key if result_key else "(その他)"
            groups.setdefault(gk, []).append(img)

        for group_name, group_images in groups.items():
            # グループ内の画像からプロパティ情報を表示
            st.subheader(f"result_key: {group_name}")
            # 代表的なプロパティを表示
            sample_path = group_images[0].get("image_path", "")
            _, sample_props = extract_path_metadata(sample_path)
            if sample_props:
                prop_str = ", ".join(f"{k}={v}" for k, v in sorted(sample_props.items()))
                st.caption(f"{len(group_images)} 件 | {prop_str}")
            else:
                st.caption(f"{len(group_images)} 件")
            _render_image_grid(group_images, cols_per_row, project_root, source=source)
        return

    groups_ord: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for img in images:
        if group_key == "property_key":
            # property_keyでグルーピング（daily:日付:キー → キー部分のみ）
            raw_key = img.get("property_key", "")
            gk = normalize_group_key(raw_key)
        else:
            # go_propertiesのキーでグルーピング
            gk = str(img.get("go_properties", {}).get(group_key, "（未設定）"))
        groups_ord.setdefault(gk, []).append(img)

    for group_name, group_images in groups_ord.items():
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
    selected_format = st.sidebar.selectbox("画像フォーマット", ["すべて", *formats])
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # フィルタ: キー名リスト指定（result_keyベース）
    from services.dashboard.query import _extract_result_key_from_path

    available_result_keys = sorted({_extract_result_key_from_path(img.get("image_path", "")) for img in images} - {""})
    if available_result_keys:
        selected_keys = st.sidebar.multiselect(
            "result_keyフィルタ",
            available_result_keys,
            key="_gallery_output_key_filter",
        )
        if selected_keys:
            images = filter_images_by_keys(images, selected_keys, source="output")

    # グループ表示オプション（デフォルト: 最初の利用可能キー）
    group_keys = collect_group_keys(images, source="output")
    group_options = ["なし", *group_keys]
    default_group_idx = 1 if group_keys else 0
    group_by = st.sidebar.selectbox(
        "グループ表示",
        group_options,
        index=default_group_idx,
        key="_gallery_output_group",
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(images, cols_per_row, project_root, source="output", group_key=group_by)
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input("ページ", min_value=1, max_value=total_pages, value=1)
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx : start_idx + max_display]

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

    # キー名リスト指定フィルタ（multiselect、未選択時は全件表示）
    all_keys = sorted({normalize_group_key(img["property_key"]) for img in images})
    selected_keys = st.sidebar.multiselect(
        "プロパティキー",
        all_keys,
        key="_gallery_property_key_filter",
    )
    if selected_keys:
        images = filter_images_by_keys(images, selected_keys, source="property")

    # フォーマットフィルタ
    formats = sorted({img["image_format"] for img in images})
    selected_format = st.sidebar.selectbox("画像フォーマット（プロパティ）", ["すべて", *formats])
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # グループ表示オプション（デフォルト: property_key でグループ化）
    group_keys = collect_group_keys(images, source="property")
    group_options = ["なし", *group_keys]
    # property_keyが利用可能な場合はデフォルトで選択
    default_group_idx = 0
    if "property_key" in group_keys:
        default_group_idx = group_options.index("property_key")
    elif group_keys:
        default_group_idx = 1
    group_by = st.sidebar.selectbox(
        "グループ表示（プロパティ）",
        group_options,
        index=default_group_idx,
        key="_gallery_property_group",
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(images, cols_per_row, project_root, source="property", group_key=group_by)
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input("ページ（プロパティ画像）", min_value=1, max_value=total_pages, value=1)
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx : start_idx + max_display]

    st.caption(
        f"{len(page_images)} / {total_images} 件 "
        f"（{cols_per_row}列 x {rows_per_page}行、ページ {page_num}/{total_pages}）"
    )

    if not page_images:
        st.info("条件に一致する画像がありません。")
        return

    # NxMグリッドで表示
    _render_image_grid(page_images, cols_per_row, project_root, source="property")


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
        for col_idx, img_info in enumerate(images[row_start : row_start + cols_per_row]):
            with cols[col_idx]:
                # ヘッダー情報（表示名を優先使用）
                display_name = img_info.get("display_name", img_info["go_node_name"])
                if source == "output":
                    st.markdown(f"**{display_name}**")
                    image_path_str = img_info["image_path"]
                    caption = img_info["image_name"]
                else:
                    st.markdown(f"**{display_name}**")
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

    config.yamlからの静的ビューに加え、永続化された動的ビューも表示する。
    動的ビューはUI上で追加・編集・削除が可能で、.jj/storage/saved-views.yaml
    にファイル永続化される。
    """
    st.header("保存済みビュー")

    saved_views = list(getattr(dashboard_config, "saved_views", []))

    # 永続化された動的ビューをファイルから読み込み（初回のみ）
    if "_dynamic_views" not in st.session_state:
        st.session_state["_dynamic_views"] = _load_persistent_views(project_root)
    dynamic_views: list[dict[str, Any]] = st.session_state["_dynamic_views"]

    # 動的ビューをSavedViewConfigに変換
    from config import SavedViewConfig

    dynamic_view_configs: list[SavedViewConfig] = []
    for dv in dynamic_views:
        with contextlib.suppress(ValueError, KeyError):
            dynamic_view_configs.append(SavedViewConfig.from_dict(dv))

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
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                    st.rerun()
        else:
            st.subheader(f"{view.name}")

        st.caption(f"タイプ: {view.view_type}" + (" (動的)" if is_dynamic else ""))

        # 動的ビュー編集フォーム
        if is_dynamic and st.session_state.get(f"_editing_dv_{dyn_idx}", False):
            _render_view_edit_form(provider, project_root, dyn_idx, dynamic_views[dyn_idx])
            continue

        # PageComponentレジストリからview_typeでディスパッチ
        saved_component = get_page_component(view.view_type)
        if saved_component is not None:
            saved_component.render_saved_view(
                provider,
                view,
                dashboard_config,
                vocab=vocab,
                project_root=project_root,
            )

    # HTMLエクスポート
    st.markdown("---")
    _render_html_export_button(provider, project_root, dashboard_config, vocab)

    # 新規ビュー追加セクション
    st.markdown("---")
    _render_view_add_form(provider, project_root)


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

    # verbose_nameキー
    vn_key = provider._verbose_name_key

    display_rows = []
    for r in filtered:
        row = {k: v for k, v in r.items() if k != "related_files"}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)

    # nameカラムを表示名で置き換え
    if vn_key in df.columns:
        df["name"] = df[vn_key]

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

    # グループ結線キーをextra_keysに含める
    group_line_key = getattr(dashboard_config, "group_line_key", None) if dashboard_config else None
    extra_keys: list[str] = []
    if group_line_key:
        extra_keys.append(group_line_key)

    # colorが未設定の場合、デフォルトで表示名を使用
    vn_key = provider._verbose_name_key
    if not color:
        color = vn_key

    data = provider.get_plot_data(x_key, y_key, color_key=color, extra_keys=extra_keys)

    # 保存済みフィルタを適用（名前ベースでフィルタ）
    if view.filters:
        all_rows = provider.get_go_table()
        filtered_rows = apply_saved_view_filters(all_rows, view.filters)
        filtered_names = {r["name"] for r in filtered_rows}
        data = [d for d in data if d.get("name") in filtered_names]

    if not data:
        st.warning(f"'{x_key}' と '{y_key}' の両方が数値であるデータが見つかりません。")
        return

    import pandas as pd

    df = pd.DataFrame(data)

    try:
        import plotly.express as px

        fig = _create_plot_figure(px, df, x_key, y_key, color, chart_type, hover_name_col=vn_key)
        # NG領域塗りつぶし
        ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)
        # グループ結線
        if group_line_key and group_line_key in df.columns:
            _add_group_lines_to_fig(fig, df, x_key, y_key, group_line_key)
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
            images = [img for img in images if img["property_key"] == property_key]
    else:
        images = provider.get_output_images()

    if format_filter:
        images = [img for img in images if img["image_format"] == format_filter]

    if not images:
        st.info("条件に一致する画像がありません。")
        return

    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)
    max_display = cols_per_row * rows_per_page
    images = images[:max_display]

    st.caption(f"{len(images)} 件")
    _render_image_grid(
        images,
        cols_per_row,
        project_root,
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
    props = {k: v for k, v in card["properties"].items() if k not in ("path", "include_properties")}
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
    mode = ap_config.get("mode", "overlay")

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
                        fig.add_trace(
                            go.Scatter(
                                x=plot_data["x_values"],
                                y=s["values"],
                                mode="lines+markers",
                                name=s["key"].split(".")[-1],
                            )
                        )
                    # NG領域塗りつぶし
                    if ng_regions:
                        _add_ng_regions_to_fig(fig, ng_regions)
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
        # overlay（後方互換: gridモードもoverlay扱い）
        _render_array_overlay(
            provider,
            x_key,
            y_keys,
            filters=filter_dict,
            ng_regions=ng_regions,
        )


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
        with contextlib.suppress(ValueError, KeyError):
            saved_views.append(SavedViewConfig.from_dict(dv))

    if not saved_views:
        return

    if st.button("HTMLエクスポート", key="_html_export_btn"):
        with st.spinner("HTMLを生成中..."):
            html = generate_saved_views_html(provider, project_root, dashboard_config, saved_views, vocab)
        st.download_button(
            label="HTMLダウンロード",
            data=html.encode("utf-8"),
            file_name="dashboard_views.html",
            mime="text/html",
            key="_html_download_btn",
        )


def _render_view_add_form(
    provider: DashboardDataProvider,
    project_root: Path | None = None,
) -> None:
    """保存済みビューの新規追加フォーム"""
    with st.expander("ビューを追加", expanded=False):
        view_name = st.text_input("ビュー名", key="_add_view_name")
        # ViewConfigレジストリからビュータイプ一覧を取得
        type_options = get_view_type_options()
        view_type = st.selectbox(
            "タイプ",
            type_options,
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

        # ViewConfigレジストリからビュータイプ固有の設定UIを描画
        type_specific_config: dict[str, Any] = {}
        vc = get_view_config(view_type)
        if vc is not None:
            type_specific_config = vc.render_add_form(provider)

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
                    "plot": type_specific_config.get("plot", {}),
                    "array_plot": type_specific_config.get("array_plot", {}),
                    "gallery": type_specific_config.get("gallery", {}),
                }
                st.session_state["_dynamic_views"].append(new_view)
                if project_root is not None:
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                st.rerun()


def _render_view_edit_form(
    provider: DashboardDataProvider,
    project_root: Path | None,
    dyn_idx: int,
    view_data: dict[str, Any],
) -> None:
    """動的ビューの編集フォーム"""
    with st.container():
        view_name = st.text_input(
            "ビュー名",
            value=view_data.get("name", ""),
            key=f"_edit_name_{dyn_idx}",
        )
        view_type = st.selectbox(
            "タイプ",
            ["table", "plot", "array_plot", "gallery", "card", "status"],
            index=["table", "plot", "array_plot", "gallery", "card", "status"].index(view_data.get("type", "table")),
            key=f"_edit_type_{dyn_idx}",
        )

        # フィルタ設定
        st.markdown("**フィルタ**")
        existing_filters = view_data.get("filters", {})
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_type = st.text_input(
                "type",
                value=existing_filters.get("type", ""),
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
                "active",
                value=existing_filters.get("active", False),
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
                if project_root is not None:
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
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
