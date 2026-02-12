"""Streamlitダッシュボードアプリ本体

jj dashboardコマンドから起動されるStreamlitアプリ。
GraphModelを読み込み、テーブル/カード/プロット/ステータス/ギャラリーの
5ビューを提供する。AgGridテーブル、画像ギャラリー、graph.yaml変更検知に対応。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
    try:
        from config import GraphConfig

        config = GraphConfig.load(base_dir=project_root)
        vocab = config.vocab
        units = config.export.units
    except Exception:
        vocab = {}
        units = {}

    provider = DashboardDataProvider(graph, vocab=vocab, units=units)

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
        _render_table_page(provider)
    elif page == "カード":
        _render_card_page(provider)
    elif page == "プロット":
        _render_plot_page(provider)
    elif page == "ステータス":
        _render_status_page(provider)
    elif page == "ギャラリー":
        _render_gallery_page(provider, project_root)


# ====================================================================
# テーブルビュー（AgGrid対応）
# ====================================================================


def _render_table_page(provider: DashboardDataProvider) -> None:
    """テーブルビュー: go_ファイルをテーブル表示（AgGrid優先）"""
    st.header("テーブルビュー")

    # フィルタ
    rows = provider.get_go_table()
    if not rows:
        st.info("go_ ファイルが見つかりません。")
        return

    # サイドバーフィルタ
    types = sorted({r.get("type", "") for r in rows if r.get("type")})
    selected_type = st.sidebar.selectbox("タイプフィルタ", ["すべて"] + types)

    statuses = sorted({
        r.get("analysis_status", "unknown")
        for r in rows
        if r.get("analysis_status")
    })
    selected_status = st.sidebar.selectbox(
        "ステータスフィルタ", ["すべて"] + statuses
    )

    active_only = st.sidebar.checkbox("activeのみ", value=False)

    # フィルタ適用
    filtered = rows
    if selected_type != "すべて":
        filtered = [r for r in filtered if r.get("type") == selected_type]
    if selected_status != "すべて":
        filtered = [
            r for r in filtered if r.get("analysis_status") == selected_status
        ]
    if active_only:
        filtered = [r for r in filtered if r.get("active") is True]

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

    # AgGridを試行、失敗時はst.dataframeにフォールバック
    if not _try_render_aggrid(df):
        st.dataframe(df, use_container_width=True, hide_index=True)


# ====================================================================
# カードビュー
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
# プロットビュー
# ====================================================================


def _render_plot_page(provider: DashboardDataProvider) -> None:
    """プロットビュー: プロパティの散布図/棒グラフ"""
    st.header("プロットビュー")

    keys = provider.get_property_keys()
    if not keys:
        st.info("プロット可能なプロパティがありません。")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        x_key = st.selectbox("X軸", keys, index=0)
    with col2:
        y_idx = min(1, len(keys) - 1)
        y_key = st.selectbox("Y軸", keys, index=y_idx)
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

    try:
        import plotly.express as px

        if chart_type == "散布図":
            fig = px.scatter(
                df,
                x=x_key,
                y=y_key,
                color=color,
                hover_name="name",
                title=f"{y_key} vs {x_key}",
            )
        elif chart_type == "棒グラフ":
            fig = px.bar(
                df,
                x="name",
                y=y_key,
                color=color,
                title=f"{y_key} by name",
            )
        else:
            fig = px.line(
                df,
                x=x_key,
                y=y_key,
                color=color,
                hover_name="name",
                title=f"{y_key} vs {x_key}",
                markers=True,
            )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # plotlyがない場合はStreamlit組み込みチャートを使用
        st.scatter_chart(df, x=x_key, y=y_key)

    st.caption(f"データ点数: {len(data)}")


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
# 画像ギャラリー
# ====================================================================


def _render_gallery_page(
    provider: DashboardDataProvider, project_root: Path
) -> None:
    """画像ギャラリー: has_output関係の画像を表示"""
    st.header("画像ギャラリー")

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

    # 最大表示数
    max_display = st.sidebar.number_input(
        "最大表示数", min_value=1, max_value=200, value=50
    )
    images = images[:max_display]

    st.caption(f"{len(images)} 件の画像")

    if not images:
        st.info("条件に一致する画像がありません。")
        return

    # 5列グリッドで表示
    cols_per_row = 5
    for row_start in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, img_info in enumerate(
            images[row_start : row_start + cols_per_row]
        ):
            with cols[col_idx]:
                # パラメータ情報
                st.markdown(f"**{img_info['go_node_name']}**")

                # 主要プロパティをコンパクト表示
                props = img_info["go_properties"]
                prop_lines = []
                for key in ("index", "version", "type", "analysis_status"):
                    if key in props:
                        prop_lines.append(f"{key}: {props[key]}")
                if prop_lines:
                    st.caption(" | ".join(prop_lines))

                # 画像表示
                image_path = project_root / img_info["image_path"]
                if image_path.exists():
                    st.image(
                        str(image_path),
                        caption=img_info["image_name"],
                        use_container_width=True,
                    )
                else:
                    st.warning(
                        f"画像が見つかりません: {img_info['image_path']}"
                    )


if __name__ == "__main__":
    main()
