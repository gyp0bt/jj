"""Streamlitダッシュボードアプリ本体（オーケストレーション層）

jj dashboardコマンドから起動されるStreamlitアプリ。
GraphModelを読み込み、PageComponentレジストリ経由で各ビューをディスパッチする。
各ビューの描画ロジックはservices/dashboard/components/に分離されている。

## 責務分離
- **オーケストレーション層（本ファイル）**: ページ選択・保存済みビュー管理・HTMLエクスポート
- **コンポーネント層（components/）**: 各ビュータイプの描画ロジック
- **クエリ層（query.py）**: フィルタ・ソート・カラム選択等の純粋ロジック
- **データ供給層（data_provider.py）**: GraphModelからのデータ取得
- **HTMLエクスポート（html_export.py）**: スタンドアロンHTML生成
- **共有ウィジェット（widgets.py）**: AgGrid・フィルタ・スタイル等のUIヘルパー
- **コネクター（connectors/）**: ソフトウェア固有ページ

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    pass

# プロジェクトルートをsys.pathに追加（Streamlitプロセスからのインポート用）
_project_src = str(Path(__file__).resolve().parents[2])
if _project_src not in sys.path:
    sys.path.insert(0, _project_src)

# PageComponent/ViewConfig自動登録（インポート時に__init_subclass__で登録される）
import plugins.abaqus.dashboard  # noqa: F401, E402
import services.dashboard.components.array_plot  # noqa: E402
import services.dashboard.components.batch_overview  # noqa: E402
import services.dashboard.components.card  # noqa: E402
import services.dashboard.components.gallery  # noqa: E402
import services.dashboard.components.overview  # noqa: E402
import services.dashboard.components.plot  # noqa: E402
import services.dashboard.components.run_comparison  # noqa: E402
import services.dashboard.components.status  # noqa: E402
import services.dashboard.components.table  # noqa: F401, E402
from config import SavedViewConfig  # noqa: E402
from jj_types import GraphModel  # noqa: E402
from services.dashboard.components import (  # noqa: E402
    get_page_component,
    load_dashboard_plugins,
)
from services.dashboard.connectors import (  # noqa: E402
    get_connector_pages,
    render_connector,
)
from services.dashboard.data_provider import DashboardDataProvider  # noqa: E402
from services.dashboard.state import get_graph_mtime  # noqa: E402
from services.graph import GraphService  # noqa: E402
from services.graph.query.filters import is_truthy  # noqa: E402


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
        # st.session_state.setdefault("_filter_type", "すべて")
        st.session_state.setdefault("_filter_type", "ABQ inp")
        st.session_state.setdefault("_filter_status", "すべて")


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
    return svc.load(resolve_externalized=True)


def _get_project_root() -> Path:
    """プロジェクトルートをセッションまたは環境から取得"""
    if "project_root" not in st.session_state:
        root = os.environ.get("JJ_PROJECT_ROOT", str(Path.cwd()))
        st.session_state["project_root"] = root
    return Path(st.session_state["project_root"])


# ====================================================================
# enabled-pages 永続化（config.yaml に直接保存）
# ====================================================================


def _persist_enabled_pages(project_root: Path, views: list[Any]) -> None:
    """現在のenabled_pagesをconfig.yamlに書き戻す

    views は SavedViewConfig のリスト。config_writer 経由で
    ``dashboard.enabled-pages`` を上書き保存する。
    """
    from services.dashboard.config_writer import save_enabled_pages

    save_enabled_pages(project_root, views)


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

    # エントリーポイント経由のプラグインをロード
    load_dashboard_plugins()

    project_root = _get_project_root()

    # サイドバー: プロジェクト情報
    st.sidebar.title("jj Dashboard")
    st.sidebar.caption(f"Project: {project_root.name}")

    # graph.yaml変更検知
    graph_changed = _check_graph_changed(project_root)
    if graph_changed:
        st.sidebar.success("graph.yaml が更新されました。データを再読み込みしました。")

    # 手動再読み込みボタン
    if st.sidebar.button("reload"):
        st.session_state["_graph_mtime"] = get_graph_mtime(project_root)
        st.rerun()

    # Re-parseボタン: プロジェクトを再解析してグラフを更新
    if st.sidebar.button("reparse"):
        with st.spinner("Parsing..."):
            try:
                from services.graph import GraphService

                gs = GraphService(project_root)
                gs.parse_and_save()
                st.session_state["_graph_mtime"] = get_graph_mtime(project_root)
                # フィルタ初期化をリセットして再読み込み
                st.session_state.pop("_filters_initialized", None)
                st.sidebar.success("Re-parse 完了")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Re-parse 失敗: {e}")

    # Config再読み込みボタン
    if st.sidebar.button("Config再読み込み"):
        # フィルタ初期化をリセットしてconfigを再読み込み
        st.session_state.pop("_filters_initialized", None)
        st.sidebar.success("Config を再読み込みしました")
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
        project_root=project_root,
    )

    # 共有フィルタ初期化
    _init_shared_filters(dashboard_config.default_filters)

    # 利用可能なコネクターページを取得（enabled_pages解決に必要）
    connector_pages = get_connector_pages(provider)

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

    # 共有フィルタのレンダリング済みフラグを実行ごとにリセット
    # （複数ビューが同一実行中にrender_shared_filtersを呼んでも一度だけ描画する）
    st.session_state["_shared_filters_rendered"] = False

    # シングルページレンダリング: enabled_pagesで指定された各ビューを順次描画
    _render_single_page(
        provider,
        project_root,
        dashboard_config,
        render_kwargs,
        connector_pages,
        vocab,
    )


def _render_single_page(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    render_kwargs: dict[str, Any],
    connector_pages: list[str],
    vocab: dict[str, str] | None,
) -> None:
    """enabled_pagesに含まれる各ビューをシングルページ上に順次描画

    各ビューは ``SavedViewConfig`` として設定を持ち、``PageComponent.render`` /
    ``DashboardPageConnector.render`` の単一エントリポイント経由で描画される。
    configに表示オプションがない場合は各コンポーネントの placeholder が表示される。
    """
    enabled: list[SavedViewConfig] = list(getattr(dashboard_config, "enabled_pages", []) or [])

    if not enabled:
        st.info("有効なビューがありません。config の dashboard.enabled-pages で有効化してください。")
    else:
        for idx, view in enumerate(enabled):
            st.markdown("---")
            _render_enabled_view(
                idx,
                view,
                enabled,
                provider,
                dashboard_config,
                render_kwargs,
                connector_pages,
                project_root,
            )


def _render_enabled_view(
    idx: int,
    view: SavedViewConfig,
    enabled: list[SavedViewConfig],
    provider: DashboardDataProvider,
    dashboard_config: Any,
    render_kwargs: dict[str, Any],
    connector_pages: list[str],
    project_root: Path,
) -> None:
    """enabled_pagesの1エントリをSavedViewConfigとして描画

    ヘッダーに編集・削除ボタンを配置し、通常は ``component.render(view, ...)``
    を呼ぶ。編集中の場合は編集フォームを表示する。
    """
    header_suffix = f"（{view.view_type}）" if view.name != view.view_type else ""
    st.header(f"{view.name}{header_suffix}")

    # 描画: connector or PageComponent.render（単一エントリポイント）
    if view.is_connector_view:
        label = view.connector_page_label
        if label in connector_pages:
            render_connector(label, provider, view, dashboard_config)
        else:
            st.caption(f"コネクターページ '{label}' は利用できません。")
        return

    component = get_page_component(view.view_type)
    if component is None:
        st.caption(f"ビュー '{view.view_type}' は未登録です。")
        return

    component.render(provider, view, dashboard_config, **render_kwargs)


if __name__ == "__main__":
    main()
