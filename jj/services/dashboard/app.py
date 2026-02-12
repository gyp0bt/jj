"""Streamlitダッシュボードアプリ本体

jj dashboardコマンドから起動されるStreamlitアプリ。
GraphModelを読み込み、テーブル/カード/プロット/ステータス/ギャラリーの
5ビューを提供する。AgGridテーブル、画像ギャラリー、graph.yaml変更検知に対応。
config.yaml駆動のカラム選択・フィルタ・プロット軸・ギャラリーグリッド設定対応。

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
from services.graph import GraphService


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
    """AgGridでDataFrameを表示。失敗時はFalseを返す。

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
        fit_columns_on_grid_load=True,
        theme="streamlit",
    )
    return True


# ====================================================================
# カラムフィルタリング（config.yamlのtable-columns対応）
# ====================================================================


def _select_table_columns(
    all_columns: list[str], table_columns: list[str] | None
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    if table_columns is None:
        return all_columns

    # 固定カラム（常に先頭に表示）
    fixed = ["name", "type", "format"]
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
        st.session_state.setdefault(
            "_filter_active", default_filters.get("active", False)
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
        filtered = [r for r in filtered if r.get("active") is True]

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

    # ページ選択
    page = st.sidebar.radio(
        "ページ",
        ["テーブル", "カード", "プロット", "ステータス", "ギャラリー"],
        index=0,
    )

    # サマリー情報
    status = provider.get_status_summary()
    st.sidebar.markdown("---")
    st.sidebar.metric("総ノード数", len(graph.nodes))
    st.sidebar.metric("総リレーション数", len(graph.relations))
    st.sidebar.metric("go_ ファイル数", status["total"])

    if page == "テーブル":
        _render_table_page(provider, dashboard_config)
    elif page == "カード":
        _render_card_page(provider)
    elif page == "プロット":
        _render_plot_page(provider, dashboard_config)
    elif page == "ステータス":
        _render_status_page(provider)
    elif page == "ギャラリー":
        _render_gallery_page(provider, project_root, dashboard_config)


# ====================================================================
# テーブルビュー（AgGrid対応・config駆動カラム選択）
# ====================================================================


def _render_table_page(
    provider: DashboardDataProvider, dashboard_config: Any
) -> None:
    """テーブルビュー: go_ファイルをテーブル表示（AgGrid優先）"""
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

    # config駆動カラム選択
    table_columns = getattr(dashboard_config, "table_columns", None)
    if table_columns:
        selected_cols = _select_table_columns(list(df.columns), table_columns)
        if selected_cols:
            df = df[[c for c in selected_cols if c in df.columns]]

    # AgGridを試行、失敗時はst.dataframeにフォールバック
    if not _try_render_aggrid(df):
        st.dataframe(df, use_container_width=True, hide_index=True)


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
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # plotlyがない場合はStreamlit組み込みチャートを使用
        st.scatter_chart(df, x=x_key, y=y_key)

    st.caption(f"データ点数: {len(data)}")


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


def _render_gallery_output_images(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """has_output関係の画像ギャラリー（NxMグリッド）"""
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

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)
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
    """プロパティ画像パスのギャラリー（キー別一覧・NxMグリッド）"""
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

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)
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

                # 画像表示
                image_path = project_root / image_path_str
                if image_path.exists():
                    st.image(
                        str(image_path),
                        caption=caption,
                        use_container_width=True,
                    )
                else:
                    st.warning(f"画像が見つかりません: {image_path_str}")


if __name__ == "__main__":
    main()
