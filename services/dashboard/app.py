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
import services.dashboard.components.batch_overview  # noqa: E402
import services.dashboard.components.card  # noqa: E402
import services.dashboard.components.gallery  # noqa: E402
import services.dashboard.components.plot  # noqa: E402
import services.dashboard.components.run_comparison  # noqa: E402
import services.dashboard.components.status  # noqa: E402
import services.dashboard.components.table  # noqa: E402
import services.dashboard.connectors.abaqus  # noqa: E402
import services.dashboard.connectors.ai_assistant  # noqa: E402
import services.dashboard.connectors.job_monitor  # noqa: E402
import services.dashboard.connectors.ml  # noqa: F401, E402
from jj_types import GraphModel  # noqa: E402
from services.dashboard.components import (  # noqa: E402
    PageComponent,
    get_page_component,
    get_page_component_by_label,
    get_page_labels,
    get_view_config,
    get_view_type_options,
    load_dashboard_plugins,
)
from services.dashboard.connectors import (  # noqa: E402
    get_connector_config_schema,
    get_connector_pages,
    get_connector_view_type_options,
    render_connector_page,
    render_connector_saved_view,
)
from services.dashboard.data_provider import DashboardDataProvider  # noqa: E402
from services.dashboard.html_export import generate_saved_views_html  # noqa: E402
from services.dashboard.query import get_graph_mtime, is_truthy  # noqa: E402
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
# ビュー永続化（.j2/storage/saved-views.yaml）
# ====================================================================

_SAVED_VIEWS_FILENAME = "saved-views.yaml"


def _saved_views_path(project_root: Path) -> Path:
    """保存済みビューファイルのパスを返す"""
    return project_root / ".j2" / "storage" / _SAVED_VIEWS_FILENAME


def _load_persistent_views(project_root: Path) -> list[dict[str, Any]]:
    """永続化されたビューをファイルから読み込む

    .j2/storage/saved-views.yaml が存在しない場合は空リストを返す。
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

    .j2/storage/saved-views.yaml に書き出す。
    """
    path = _saved_views_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(views, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


# ====================================================================
# AgGrid ヘルパー（後方互換ラッパー）
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
# 共有フィルタ初期化
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
    if st.sidebar.button("再読み込み"):
        st.session_state["_graph_mtime"] = get_graph_mtime(project_root)
        st.rerun()

    # Re-parseボタン: プロジェクトを再解析してグラフを更新
    if st.sidebar.button("Re-parse"):
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

    # ページ選択（PageComponentレジストリ + コネクターページ + 保存済みビュー）
    page_options = get_page_labels()
    # コネクターが提供するページを動的追加
    connector_pages = get_connector_pages(provider)
    page_options.extend(connector_pages)
    # 保存済みビューは常に表示（config定義 + 永続化ビュー）
    page_options.append("保存済みビュー")

    # プリセットからの自動遷移: session_stateにページラベルが設定されていれば優先
    preset_label = st.session_state.pop("_preset_page_label", None)
    default_page_idx = 0
    if preset_label and preset_label in page_options:
        default_page_idx = page_options.index(preset_label)

    page = st.sidebar.radio(
        "ページ",
        page_options,
        index=default_page_idx,
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
        # 各ビューページにビュー保存ボタンを追加
        _render_quick_save_button(provider, project_root, component.page_key)
    elif page == "保存済みビュー":
        _render_saved_views_page(provider, project_root, dashboard_config, vocab)
    elif page in connector_pages:
        render_connector_page(page, provider, dashboard_config)


# ====================================================================
# 保存済みビュー プリセット機能
# ====================================================================


def _apply_preset_and_navigate(view: Any) -> None:
    """保存済みビューの設定をsession_stateにロードし、通常ページに遷移する

    ビューの設定値（フィルタ、プロット軸、ギャラリー設定等）を
    各ページコンポーネントが参照するsession_stateキーにセットした上で、
    対応するページに自動遷移する。

    Args:
        view: SavedViewConfig
    """
    # ビュー設定をプリセットとしてsession_stateに保存
    st.session_state["_preset_view"] = {
        "name": view.name,
        "view_type": view.view_type,
        "filters": view.filters,
        "local_filters": view.local_filters,
        "plot": view.plot,
        "gallery": view.gallery,
        "array_plot": view.array_plot,
        "connector_config": view.connector_config,
    }

    # 共有フィルタをビューのフィルタで上書き
    filters = view.filters
    if filters.get("type"):
        st.session_state["_filter_type"] = filters["type"]
    if filters.get("analysis_status"):
        st.session_state["_filter_status"] = filters["analysis_status"]
    if filters.get("active"):
        st.session_state["_filter_active"] = True

    # ギャラリー設定のプリセット
    gallery = view.gallery
    if gallery.get("source"):
        source_map = {"has_output": 0, "property": 1}
        st.session_state["_gallery_source_idx"] = source_map.get(gallery["source"], 0)

    # プロット設定のプリセット
    plot = view.plot
    if plot.get("x"):
        st.session_state["_preset_plot_x"] = plot["x"]
    if plot.get("y"):
        st.session_state["_preset_plot_y"] = plot["y"]
    if plot.get("color"):
        st.session_state["_preset_plot_color"] = plot["color"]
    if plot.get("chart_type"):
        st.session_state["_preset_plot_chart"] = plot["chart_type"]

    # 対応ページへ遷移（radioボタンのインデックスを設定）
    page_key = view.view_type
    if view.is_connector_view:
        # コネクタービューは直接遷移不可（保存済みビューページに留まる）
        return

    # ページラベルを取得して遷移
    for cls in PageComponent._registry.values():
        if cls.page_key == page_key:
            st.session_state["_preset_page_label"] = cls.page_label
            break

    st.rerun()


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
    動的ビューはUI上で追加・編集・削除が可能で、.j2/storage/saved-views.yaml
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

        # ビューヘッダー（動的ビューは編集・削除ボタン付き、全ビューにプリセットボタン）
        if is_dynamic:
            hcol1, hcol2, hcol3, hcol4 = st.columns([5, 1, 1, 1])
            with hcol1:
                st.subheader(f"{view.name}")
            with hcol2:
                if st.button("開く", key=f"_open_preset_{idx}", help="通常ページとして設定をロード"):
                    _apply_preset_and_navigate(view)
            with hcol3:
                if st.button("編集", key=f"_edit_dv_{dyn_idx}"):
                    st.session_state[f"_editing_dv_{dyn_idx}"] = True
            with hcol4:
                if st.button("削除", key=f"_del_dv_{dyn_idx}"):
                    st.session_state["_dynamic_views"].pop(dyn_idx)
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                    st.rerun()
        else:
            hcol1, hcol2 = st.columns([7, 1])
            with hcol1:
                st.subheader(f"{view.name}")
            with hcol2:
                if st.button("開く", key=f"_open_preset_{idx}", help="通常ページとして設定をロード"):
                    _apply_preset_and_navigate(view)

        st.caption(f"タイプ: {view.view_type}" + (" (動的)" if is_dynamic else ""))

        # 動的ビュー編集フォーム
        if is_dynamic and st.session_state.get(f"_editing_dv_{dyn_idx}", False):
            _render_view_edit_form(provider, project_root, dyn_idx, dynamic_views[dyn_idx])
            continue

        # PageComponentレジストリまたはコネクターレジストリからview_typeでディスパッチ
        if view.is_connector_view:
            # コネクタービュー: connector:{page_label}
            render_connector_saved_view(
                view.connector_page_label,
                provider,
                view,
                dashboard_config,
            )
        else:
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


def _render_html_export_button(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """保存済みビューをスタンドアロンHTMLとしてエクスポート"""
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


def _render_quick_save_button(
    provider: DashboardDataProvider,
    project_root: Path,
    view_type: str,
) -> None:
    """各ビューページ下部にビュー保存ボタンを表示

    現在のページタイプと名前を入力して、動的ビューとして保存する。
    """
    st.markdown("---")
    with st.expander("このビューを保存", expanded=False):
        save_name = st.text_input("ビュー名", key="_quick_save_name")
        if st.button("ビューとして保存", key="_quick_save_btn"):
            if not save_name:
                st.warning("ビュー名を入力してください。")
            else:
                new_view: dict[str, Any] = {
                    "name": save_name,
                    "type": view_type,
                    "filters": {},
                    "local_filters": {},
                    "plot": {},
                    "array_plot": {},
                    "gallery": {},
                    "connector_config": {},
                }
                if "_dynamic_views" not in st.session_state:
                    st.session_state["_dynamic_views"] = _load_persistent_views(project_root)
                st.session_state["_dynamic_views"].append(new_view)
                _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                st.success(f"ビュー '{save_name}' を保存しました。")


def _render_view_add_form(
    provider: DashboardDataProvider,
    project_root: Path | None = None,
) -> None:
    """保存済みビューの新規追加フォーム"""
    with st.expander("ビューを追加", expanded=False):
        view_name = st.text_input("ビュー名", key="_add_view_name")
        # ViewConfigレジストリ + コネクタービュータイプの一覧
        type_options = get_view_type_options()
        connector_type_options = get_connector_view_type_options(provider)
        all_type_options = type_options + connector_type_options
        view_type = st.selectbox(
            "タイプ",
            all_type_options,
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

        # ローカルフィルタ設定（複数キー/値ペア対応）
        st.markdown("**ローカルフィルタ（任意・ページ固有）**")
        if "_add_lf_count" not in st.session_state:
            st.session_state["_add_lf_count"] = 1
        lf_count: int = st.session_state["_add_lf_count"]
        lf_pairs: list[tuple[str, str]] = []
        for lfi in range(lf_count):
            lfc1, lfc2 = st.columns(2)
            with lfc1:
                lf_key = st.text_input("プロパティキー", key=f"_add_view_lf_key_{lfi}")
            with lfc2:
                lf_value = st.text_input("値", key=f"_add_view_lf_value_{lfi}")
            if lf_key and lf_value:
                lf_pairs.append((lf_key, lf_value))
        lf_btn1, lf_btn2 = st.columns(2)
        with lf_btn1:
            if st.button("フィルタ追加", key="_add_lf_more"):
                st.session_state["_add_lf_count"] = lf_count + 1
                st.rerun()
        with lf_btn2:
            if lf_count > 1 and st.button("フィルタ削除", key="_remove_lf"):
                st.session_state["_add_lf_count"] = max(1, lf_count - 1)
                st.rerun()

        # ViewConfigレジストリからビュータイプ固有の設定UIを描画
        type_specific_config: dict[str, Any] = {}
        is_connector = view_type.startswith("connector:")
        connector_config_values: dict[str, Any] = {}
        if not is_connector:
            vc = get_view_config(view_type)
            if vc is not None:
                type_specific_config = vc.render_add_form(provider)
        else:
            # コネクターの場合: connector_config入力UIを表示
            page_label = view_type[len("connector:") :]
            schema = get_connector_config_schema(page_label)
            if schema:
                st.markdown("**コネクター設定**")
                for field in schema:
                    fkey = field["key"]
                    flabel = field.get("label", fkey)
                    fhelp = field.get("help", "")
                    if field.get("type") == "checkbox":
                        connector_config_values[fkey] = st.checkbox(
                            flabel, value=True, key=f"_add_cc_{fkey}", help=fhelp
                        )
                    else:
                        val = st.text_input(flabel, key=f"_add_cc_{fkey}", help=fhelp)
                        if val:
                            connector_config_values[fkey] = val

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

                local_filters: dict[str, Any] = {}
                for lf_k, lf_v in lf_pairs:
                    local_filters[lf_k] = lf_v

                # connector_config: compare_materialsはカンマ区切りをリストに変換
                final_cc = dict(connector_config_values)
                if "compare_materials" in final_cc and isinstance(final_cc["compare_materials"], str):
                    final_cc["compare_materials"] = [
                        m.strip() for m in final_cc["compare_materials"].split(",") if m.strip()
                    ]

                new_view: dict[str, Any] = {
                    "name": view_name,
                    "type": view_type,
                    "filters": filters,
                    "local_filters": local_filters,
                    "plot": type_specific_config.get("plot", {}),
                    "array_plot": type_specific_config.get("array_plot", {}),
                    "gallery": type_specific_config.get("gallery", {}),
                    "connector_config": final_cc,
                }
                st.session_state["_dynamic_views"].append(new_view)
                if project_root is not None:
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                # フィルタカウントをリセット
                st.session_state["_add_lf_count"] = 1
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

        # タイプ選択（コネクタータイプも含む）
        base_types = ["table", "plot", "array_plot", "gallery", "card", "status"]
        connector_types = get_connector_view_type_options(provider)
        all_types = base_types + connector_types
        current_type = view_data.get("type", "table")
        type_index = all_types.index(current_type) if current_type in all_types else 0
        view_type = st.selectbox(
            "タイプ",
            all_types,
            index=type_index,
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

        # ローカルフィルタ設定（複数ペア対応）
        st.markdown("**ローカルフィルタ**")
        existing_local_filters = view_data.get("local_filters", {})
        lf_count_key = f"_edit_lf_count_{dyn_idx}"
        if lf_count_key not in st.session_state:
            st.session_state[lf_count_key] = max(1, len(existing_local_filters))
        edit_lf_count: int = st.session_state[lf_count_key]
        existing_lf_items = list(existing_local_filters.items())
        edit_lf_pairs: list[tuple[str, str]] = []
        for lfi in range(edit_lf_count):
            default_key = existing_lf_items[lfi][0] if lfi < len(existing_lf_items) else ""
            default_val = str(existing_lf_items[lfi][1]) if lfi < len(existing_lf_items) else ""
            lfc1, lfc2 = st.columns(2)
            with lfc1:
                elk = st.text_input(
                    "プロパティキー",
                    value=default_key,
                    key=f"_edit_lf_key_{dyn_idx}_{lfi}",
                )
            with lfc2:
                elv = st.text_input(
                    "値",
                    value=default_val,
                    key=f"_edit_lf_val_{dyn_idx}_{lfi}",
                )
            if elk and elv:
                edit_lf_pairs.append((elk, elv))
        elf_btn1, elf_btn2 = st.columns(2)
        with elf_btn1:
            if st.button("フィルタ追加", key=f"_edit_lf_more_{dyn_idx}"):
                st.session_state[lf_count_key] = edit_lf_count + 1
                st.rerun()
        with elf_btn2:
            if edit_lf_count > 1 and st.button("フィルタ削除", key=f"_edit_lf_remove_{dyn_idx}"):
                st.session_state[lf_count_key] = max(1, edit_lf_count - 1)
                st.rerun()

        # プロット設定の編集UI
        edit_plot_config: dict[str, Any] = {}
        if view_type == "plot":
            st.markdown("**プロット設定**")
            existing_plot = view_data.get("plot", {})
            keys = provider.get_property_keys()
            vn_key = provider._verbose_name_key

            epc1, epc2, epc3, epc4 = st.columns(4)
            with epc1:
                ex_x = existing_plot.get("x", "")
                x_idx = keys.index(ex_x) if ex_x in keys else 0
                ep_x = st.selectbox("X軸", keys, index=x_idx, key=f"_edit_px_{dyn_idx}") if keys else ""
            with epc2:
                ex_y = existing_plot.get("y", "")
                y_idx = keys.index(ex_y) if ex_y in keys else min(1, len(keys) - 1)
                ep_y = st.selectbox("Y軸", keys, index=y_idx, key=f"_edit_py_{dyn_idx}") if keys else ""
            with epc3:
                color_options = ["なし", vn_key, *[k for k in keys if k != vn_key]]
                ex_color = existing_plot.get("color") or "なし"
                c_idx = color_options.index(ex_color) if ex_color in color_options else 0
                ep_color = st.selectbox("色分け", color_options, index=c_idx, key=f"_edit_pcolor_{dyn_idx}")
            with epc4:
                chart_options = ["散布図", "棒グラフ", "線図", "コンター", "等高線"]
                ex_chart = existing_plot.get("chart_type", "散布図")
                ct_idx = chart_options.index(ex_chart) if ex_chart in chart_options else 0
                ep_chart = st.selectbox("チャート", chart_options, index=ct_idx, key=f"_edit_pchart_{dyn_idx}")

            edit_plot_config = {
                "x": ep_x,
                "y": ep_y,
                "color": ep_color if ep_color != "なし" else None,
                "chart_type": ep_chart,
            }

            # コンター/等高線用: Z軸・カラーバー範囲
            if ep_chart in ("コンター", "等高線"):
                z_options = [k for k in keys if k != ep_x and k != ep_y]
                if z_options:
                    ezc1, ezc2, ezc3 = st.columns(3)
                    with ezc1:
                        ex_z = existing_plot.get("z", "")
                        z_idx = z_options.index(ex_z) if ex_z in z_options else 0
                        ep_z = st.selectbox("Z軸（色）", z_options, index=z_idx, key=f"_edit_pz_{dyn_idx}")
                    ex_cr = existing_plot.get("color_range", {})
                    with ezc2:
                        ep_vmin = st.number_input(
                            "vmin",
                            value=ex_cr.get("vmin"),
                            key=f"_edit_pvmin_{dyn_idx}",
                            format="%g",
                        )
                    with ezc3:
                        ep_vmax = st.number_input(
                            "vmax",
                            value=ex_cr.get("vmax"),
                            key=f"_edit_pvmax_{dyn_idx}",
                            format="%g",
                        )
                    if ep_z:
                        edit_plot_config["z"] = ep_z
                    ep_cr: dict[str, float] = {}
                    if ep_vmin is not None:
                        ep_cr["vmin"] = float(ep_vmin)
                    if ep_vmax is not None:
                        ep_cr["vmax"] = float(ep_vmax)
                    if ep_cr:
                        edit_plot_config["color_range"] = ep_cr

            # スタイル設定
            with st.expander("スタイル設定", expanded=False):
                ex_style = existing_plot.get("plot_style", {})
                esc1, esc2, esc3 = st.columns(3)
                with esc1:
                    ep_marker = st.number_input(
                        "マーカーサイズ",
                        value=ex_style.get("marker_size"),
                        min_value=1,
                        max_value=50,
                        key=f"_edit_p_marker_{dyn_idx}",
                    )
                with esc2:
                    ep_lw = st.number_input(
                        "線幅",
                        value=ex_style.get("line_width"),
                        min_value=1,
                        max_value=20,
                        key=f"_edit_p_lw_{dyn_idx}",
                    )
                with esc3:
                    ep_fs = st.number_input(
                        "フォントサイズ",
                        value=ex_style.get("font_size"),
                        min_value=6,
                        max_value=48,
                        key=f"_edit_p_fs_{dyn_idx}",
                    )
                from services.dashboard.widgets import build_style_config

                ep_plot_style = build_style_config(ep_marker, ep_lw, ep_fs)
                if ep_plot_style:
                    edit_plot_config["plot_style"] = ep_plot_style

            # 軸範囲設定
            with st.expander("軸範囲設定", expanded=False):
                ex_range = existing_plot.get("axis_range", {})
                erc1, erc2, erc3, erc4 = st.columns(4)
                with erc1:
                    ep_xmin = st.number_input(
                        "X最小", value=ex_range.get("x_min"), key=f"_edit_p_xmin_{dyn_idx}", format="%g"
                    )
                with erc2:
                    ep_xmax = st.number_input(
                        "X最大", value=ex_range.get("x_max"), key=f"_edit_p_xmax_{dyn_idx}", format="%g"
                    )
                with erc3:
                    ep_ymin = st.number_input(
                        "Y最小", value=ex_range.get("y_min"), key=f"_edit_p_ymin_{dyn_idx}", format="%g"
                    )
                with erc4:
                    ep_ymax = st.number_input(
                        "Y最大", value=ex_range.get("y_max"), key=f"_edit_p_ymax_{dyn_idx}", format="%g"
                    )
                ep_axis_range: dict[str, float] = {}
                if ep_xmin is not None:
                    ep_axis_range["x_min"] = float(ep_xmin)
                if ep_xmax is not None:
                    ep_axis_range["x_max"] = float(ep_xmax)
                if ep_ymin is not None:
                    ep_axis_range["y_min"] = float(ep_ymin)
                if ep_ymax is not None:
                    ep_axis_range["y_max"] = float(ep_ymax)
                if ep_axis_range:
                    edit_plot_config["axis_range"] = ep_axis_range

        # コネクター設定の編集UI
        edit_cc_values: dict[str, Any] = {}
        is_connector_edit = view_type.startswith("connector:")
        if is_connector_edit:
            page_label = view_type[len("connector:") :]
            schema = get_connector_config_schema(page_label)
            if schema:
                st.markdown("**コネクター設定**")
                existing_cc = view_data.get("connector_config", {})
                for field in schema:
                    fkey = field["key"]
                    flabel = field.get("label", fkey)
                    fhelp = field.get("help", "")
                    if field.get("type") == "checkbox":
                        edit_cc_values[fkey] = st.checkbox(
                            flabel,
                            value=existing_cc.get(fkey, True),
                            key=f"_edit_cc_{fkey}_{dyn_idx}",
                            help=fhelp,
                        )
                    else:
                        # compare_materialsなどリスト値はカンマ区切りで表示
                        existing_val = existing_cc.get(fkey, "")
                        if isinstance(existing_val, list):
                            existing_val = ", ".join(str(v) for v in existing_val)
                        val = st.text_input(
                            flabel,
                            value=str(existing_val),
                            key=f"_edit_cc_{fkey}_{dyn_idx}",
                            help=fhelp,
                        )
                        if val:
                            edit_cc_values[fkey] = val

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

                local_filters: dict[str, Any] = {}
                for lf_k, lf_v in edit_lf_pairs:
                    local_filters[lf_k] = lf_v

                # connector_config: compare_materialsはカンマ区切りをリストに変換
                final_edit_cc = dict(edit_cc_values)
                if "compare_materials" in final_edit_cc and isinstance(final_edit_cc["compare_materials"], str):
                    final_edit_cc["compare_materials"] = [
                        m.strip() for m in final_edit_cc["compare_materials"].split(",") if m.strip()
                    ]

                view_data["name"] = view_name
                view_data["type"] = view_type
                view_data["filters"] = filters
                view_data["local_filters"] = local_filters
                if edit_plot_config:
                    view_data["plot"] = edit_plot_config
                view_data["connector_config"] = final_edit_cc
                st.session_state["_dynamic_views"][dyn_idx] = view_data
                if project_root is not None:
                    _save_persistent_views(project_root, st.session_state["_dynamic_views"])
                st.session_state[f"_editing_dv_{dyn_idx}"] = False
                st.rerun()
        with ec2:
            if st.button("キャンセル", key=f"_edit_cancel_{dyn_idx}"):
                st.session_state[f"_editing_dv_{dyn_idx}"] = False
                st.rerun()


if __name__ == "__main__":
    main()
