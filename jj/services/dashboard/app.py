"""Streamlitダッシュボードアプリ本体（汎用ページのみ）

jj dashboardコマンドから起動されるStreamlitアプリ。
GraphModelを読み込み、テーブル/カード/プロット/ステータス/ギャラリー/保存済みビューの
汎用ビューを提供する。ソフトウェア固有ページ（例: Abaqus物性一覧）は
services/dashboard/connectors/ のコネクターとして実装・自動登録される。

AgGridテーブル、画像ギャラリー、graph.yaml変更検知に対応。
config.yaml駆動のカラム選択・フィルタ・プロット軸・ギャラリーグリッド設定対応。
保存済みビュー機能でフィルタ・プロット条件を保存し、config順に一括表示。
activeフィルタはbool/文字列両方に対応（_is_truthy）。
画像パスはプロジェクトルート基準とnotes/daily基準のフォールバック解決に対応。
ギャラリーはgo_propertiesのキーやproperty_keyでグループ表示可能（daily:日付:キー→キー正規化）。
テーブル列・プロット軸・プロパティキー一覧はvocab順（vocab定義順→未定義は文字列昇順）。
float値は桁数が大きい場合に指数表示（小数2桁）。
AgGridは列名文字幅に基づく初期列幅設定。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch
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
from services.graph import GraphService

# コネクター自動登録（インポート時に__init_subclass__で登録される）
import services.dashboard.connectors.abaqus  # noqa: F401


# ====================================================================
# graph.yaml変更検知
# ====================================================================

_GRAPH_EXTENSIONS = ("yaml", "yml", "json")


def _find_graph_path(project_root: Path) -> Path | None:
    """graph.yamlの実パスを検出"""
    storage_dir = project_root / ".jj" / "storage"
    for ext in _GRAPH_EXTENSIONS:
        p = storage_dir / f"graph.{ext}"
        if p.exists():
            return p
    return None


def _get_graph_mtime(project_root: Path) -> float:
    """graph.yamlの更新時刻を取得"""
    graph_path = _find_graph_path(project_root)
    if graph_path is not None:
        return graph_path.stat().st_mtime
    return 0.0


def _check_graph_changed(project_root: Path) -> bool:
    """graph.yamlが前回読み込み時から変更されたか判定

    Returns:
        True: 変更あり（リロード必要）
    """
    current_mtime = _get_graph_mtime(project_root)
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
# カラムフィルタリング（config.yamlのtable-columns対応）
# ====================================================================


def _sort_columns_by_vocab(
    columns: list[str], vocab: dict[str, str]
) -> list[str]:
    """vocab順でカラムをソート

    vocab辞書の値（日本語表記）の出現順を優先し、
    vocabに含まれないカラムは文字列昇順で後に配置する。

    Args:
        columns: ソート対象のカラムリスト
        vocab: vocabマッピング

    Returns:
        vocab順→文字列昇順のリスト
    """
    vocab_order: dict[str, int] = {}
    for idx, v in enumerate(vocab.values()):
        if v not in vocab_order:
            vocab_order[v] = idx
    for idx, k in enumerate(vocab.keys()):
        if k not in vocab_order:
            vocab_order[k] = len(vocab) + idx

    in_vocab = [c for c in columns if c in vocab_order]
    not_in_vocab = [c for c in columns if c not in vocab_order]
    in_vocab.sort(key=lambda c: vocab_order[c])
    not_in_vocab.sort()
    return in_vocab + not_in_vocab


def _select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）
        vocab: vocabマッピング（vocab順ソート用）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    # 固定カラム（常に先頭に表示）
    fixed = ["name", "type", "format"]

    if table_columns is None:
        # table-columns未指定の場合: 固定カラム + vocab順でソート
        remaining = [c for c in all_columns if c not in fixed]
        if vocab:
            remaining = _sort_columns_by_vocab(remaining, vocab)
        result = [c for c in fixed if c in all_columns] + remaining
        return result

    ordered: list[str] = []
    seen: set[str] = set(fixed)

    for pattern in table_columns:
        for col in all_columns:
            if col in seen:
                continue
            if fnmatch.fnmatch(col, pattern) or col == pattern:
                ordered.append(col)
                seen.add(col)

    # 固定カラム（存在するもののみ） + 指定カラム
    result = [c for c in fixed if c in all_columns] + ordered
    return result


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
            "_filter_active", _is_truthy(raw_active)
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
    """bool/文字列両方に対応したtruthy判定

    YAML経由の値はbool True/Falseだが、GraphService.file_to_node()では
    文字列 "true"/"false" として格納される。両方を正しく扱う。

    Args:
        value: チェック対象の値

    Returns:
        True と見なせる場合 True
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


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
    """共有フィルタを適用

    Args:
        rows: フィルタ対象の全行データ

    Returns:
        フィルタ適用後の行データ
    """
    filtered = rows
    selected_type = st.session_state.get("_filter_type", "すべて")
    selected_status = st.session_state.get("_filter_status", "すべて")
    active_only = st.session_state.get("_filter_active", False)

    if selected_type != "すべて":
        filtered = [r for r in filtered if r.get("type") == selected_type]
    if selected_status != "すべて":
        filtered = [
            r for r in filtered if r.get("analysis_status") == selected_status
        ]
    if active_only:
        filtered = [r for r in filtered if _is_truthy(r.get("active"))]

    return filtered


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
        st.session_state["_graph_mtime"] = _get_graph_mtime(project_root)
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
    """プロットにNG領域（矩形/カーブ）を追加

    矩形タイプ: {"type": "rect", "x_min": float, "x_max": float,
                  "y_min": float, "y_max": float, "color": str, "label": str}
    カーブタイプ: {"type": "curve", "points": [[x,y],...],
                   "fill": "above"|"below", "color": str, "label": str}
    """
    import plotly.graph_objects as go

    for region in ng_regions:
        rtype = region.get("type", "rect")
        color = region.get("color", "rgba(255,0,0,0.1)")
        label = region.get("label", "NG")

        if rtype == "curve":
            points = region.get("points", [])
            if not points:
                continue
            x_pts = [p[0] for p in points]
            y_pts = [p[1] for p in points]
            fill_dir = region.get("fill", "above")
            # カーブの境界線
            fig.add_trace(go.Scatter(
                x=x_pts, y=y_pts,
                mode="lines",
                line=dict(color=color.replace("0.1", "0.6") if "rgba" in color else color, dash="dash"),
                name=label,
                showlegend=True,
            ))
            # 塗りつぶし
            if fill_dir == "above":
                fig.add_trace(go.Scatter(
                    x=x_pts, y=y_pts,
                    fill="tonexty" if len(fig.data) > 1 else "tozeroy",
                    fillcolor=color,
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            elif fill_dir == "below":
                fig.add_trace(go.Scatter(
                    x=x_pts, y=y_pts,
                    fill="tozeroy",
                    fillcolor=color,
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip",
                ))
        else:
            # 矩形
            x0 = region.get("x_min")
            x1 = region.get("x_max")
            y0 = region.get("y_min")
            y1 = region.get("y_max")
            fig.add_shape(
                type="rect",
                x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor=color,
                line=dict(width=0),
                layer="below",
            )
            # ラベル（右上に配置）
            if label and x1 is not None and y1 is not None:
                fig.add_annotation(
                    x=x1, y=y1,
                    text=label,
                    showarrow=False,
                    font=dict(size=10, color="red"),
                    xanchor="right",
                    yanchor="bottom",
                )


def _add_group_lines(
    fig: Any,
    df: "pd.DataFrame",
    x_key: str,
    y_key: str,
    group_key: str,
) -> None:
    """同一グループのデータ点を灰色点線で結線

    Args:
        fig: plotly Figure
        df: データフレーム
        x_key: X軸キー
        y_key: Y軸キー
        group_key: グループ化キー
    """
    import plotly.graph_objects as go

    for group_val, group_df in df.groupby(group_key):
        if len(group_df) < 2:
            continue
        sorted_df = group_df.sort_values(x_key)
        fig.add_trace(go.Scatter(
            x=sorted_df[x_key].tolist(),
            y=sorted_df[y_key].tolist(),
            mode="lines",
            line=dict(color="gray", width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))


def _create_plot_figure(
    px: Any,
    df: "pd.DataFrame",
    x_key: str,
    y_key: str,
    color: str | None,
    chart_type: str,
) -> Any:
    """plotlyのFigureオブジェクトを作成"""
    if chart_type == "散布図":
        return px.scatter(
            df,
            x=x_key,
            y=y_key,
            color=color,
            hover_name="name",
            title=f"{y_key} vs {x_key}",
        )
    elif chart_type == "棒グラフ":
        return px.bar(
            df,
            x="name",
            y=y_key,
            color=color,
            title=f"{y_key} by name",
        )
    else:
        return px.line(
            df,
            x=x_key,
            y=y_key,
            color=color,
            hover_name="name",
            title=f"{y_key} vs {x_key}",
            markers=True,
        )


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

    if view_mode == "グリッド比較":
        _render_array_grid(
            provider, dashboard_config, x_key, y_keys, filters=active_filters
        )
    else:
        _render_array_single(provider, x_key, y_keys, filters=active_filters)


def _render_array_grid(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
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
    """グループキーを正規化（daily:日付:キー → キー部分のみ）

    property_keyが "daily:2026-01-15:screenshot" の場合、
    グルーピング用に "screenshot" に正規化する。
    """
    if key.startswith("daily:"):
        parts = key.split(":", 2)
        if len(parts) >= 3:
            return parts[2]
    return key


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
    """画像リストからグループ化に利用できるキーを収集

    Args:
        images: 画像情報のリスト
        source: "output" or "property"

    Returns:
        グループ化に利用可能なキーのリスト
    """
    keys: set[str] = set()
    for img in images:
        props = img.get("go_properties", {})
        for k in props:
            if k not in ("path", "include_properties"):
                keys.add(k)
    result = sorted(keys)
    # propertyソースの場合はproperty_keyでのグルーピングも追加
    if source == "property":
        result = ["property_key"] + result
    return result


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
    """保存済みビュー: config.yamlのsaved-views順に各ビューをまとめて表示"""
    st.header("保存済みビュー")

    saved_views = getattr(dashboard_config, "saved_views", [])
    if not saved_views:
        st.info(
            "保存済みビューがありません。config.yaml の "
            "dashboard.saved-views に定義してください。"
        )
        return

    for idx, view in enumerate(saved_views):
        st.markdown("---")
        st.subheader(f"{view.name}")
        st.caption(f"タイプ: {view.view_type}")

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
    filtered = _apply_saved_view_filters(rows, view.filters)

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
        filtered_rows = _apply_saved_view_filters(all_rows, view.filters)
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
    filtered = _apply_saved_view_filters(rows, view.filters)
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
    filter_dict = _saved_view_filters_to_provider_filters(filters) if filters else None

    if mode == "single":
        # 個別ノード重ね書き（先頭ノードを表示）
        rows = provider.get_go_table()
        if filters:
            rows = _apply_saved_view_filters(rows, filters)
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


def _saved_view_filters_to_provider_filters(
    filters: dict[str, Any],
) -> dict[str, Any]:
    """保存済みビューのフィルタをDashboardDataProvider.get_*のfilters形式に変換"""
    result: dict[str, Any] = {}
    for key, value in filters.items():
        result[key] = value
    return result


def _apply_saved_view_filters(
    rows: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """保存済みビューのフィルタを適用

    Args:
        rows: フィルタ対象の全行データ
        filters: 保存済みフィルタ条件

    Returns:
        フィルタ適用後の行データ
    """
    if not filters:
        return rows

    filtered = rows
    for key, value in filters.items():
        if key == "active":
            if _is_truthy(value):
                filtered = [r for r in filtered if _is_truthy(r.get("active"))]
            else:
                filtered = [
                    r for r in filtered if not _is_truthy(r.get("active"))
                ]
        elif key == "type" and value != "すべて":
            filtered = [r for r in filtered if r.get("type") == value]
        elif key == "analysis_status" and value != "すべて":
            filtered = [
                r for r in filtered if r.get("analysis_status") == value
            ]
        else:
            filtered = [r for r in filtered if r.get(key) == value]

    return filtered


if __name__ == "__main__":
    main()
