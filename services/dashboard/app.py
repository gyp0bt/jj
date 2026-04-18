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
    import pandas as pd

# プロジェクトルートをsys.pathに追加（Streamlitプロセスからのインポート用）
_project_src = str(Path(__file__).resolve().parents[2])
if _project_src not in sys.path:
    sys.path.insert(0, _project_src)

# PageComponent/ViewConfig自動登録（インポート時に__init_subclass__で登録される）
import services.dashboard.components.array_plot  # noqa: E402
import services.dashboard.components.batch_overview  # noqa: E402
import services.dashboard.components.card  # noqa: E402
import services.dashboard.components.gallery  # noqa: E402
import services.dashboard.components.overview  # noqa: E402
import services.dashboard.components.plot  # noqa: E402
import services.dashboard.components.run_comparison  # noqa: E402
import services.dashboard.components.status  # noqa: E402
import services.dashboard.components.table  # noqa: E402
import services.dashboard.connectors.abaqus  # noqa: E402
import services.dashboard.connectors.ai_assistant  # noqa: E402
import services.dashboard.connectors.job_monitor  # noqa: E402
import services.dashboard.connectors.ml  # noqa: F401, E402
from config import SavedViewConfig  # noqa: E402
from jj_types import GraphModel  # noqa: E402
from services.dashboard.components import (  # noqa: E402
    get_page_component,
    get_view_config,
    get_view_type_options,
    load_dashboard_plugins,
)
from services.dashboard.connectors import (  # noqa: E402
    get_connector_config_schema,
    get_connector_pages,
    get_connector_view_type_options,
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

    # 利用可能なコネクターページを取得（enabled_pages解決に必要）
    connector_pages = get_connector_pages(provider)

    # サマリー情報
    status = provider.get_status_summary()
    st.sidebar.markdown("---")
    st.sidebar.metric("総ノード数", len(graph.nodes))
    st.sidebar.metric("総リレーション数", len(graph.relations))
    st.sidebar.metric("go_ ファイル数", status["total"])

    # デフォルト保存ボタン
    _render_save_defaults_button(project_root)

    # 共通kwargs（全PageComponentに渡す）
    render_kwargs: dict[str, Any] = {
        "vocab": vocab,
        "project_root": project_root,
    }

    # 共有フィルタのレンダリング済みフラグを実行ごとにリセット
    # （複数ページが同一実行中にrender_shared_filtersを呼んでも一度だけ描画する）
    st.session_state["_shared_filters_rendered"] = False

    # シングルページレンダリング: enabled_pagesで指定された各ページを順次描画
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

    各ビューは ``SavedViewConfig`` として設定を持ち、``render_saved_view`` 経由で
    統一的に描画される。configに表示オプションがない場合は各コンポーネントの
    placeholder（警告メッセージまたはデフォルト設定）が表示される。
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

    # ビュー追加フォームとHTMLエクスポート
    st.markdown("---")
    with st.expander("ビューを追加", expanded=False):
        _render_view_add_form(provider, project_root, enabled)
    _render_html_export_button(provider, project_root, dashboard_config, vocab)


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

    ヘッダーに編集・削除ボタンを配置し、通常は ``render_saved_view`` を呼ぶ。
    編集中の場合は編集フォームを表示する。
    """
    editing_key = f"_editing_view_{idx}"
    editing = st.session_state.get(editing_key, False)

    hcol1, hcol2, hcol3 = st.columns([7, 1, 1])
    with hcol1:
        header_suffix = f"（{view.view_type}）" if view.name != view.view_type else ""
        st.header(f"{view.name}{header_suffix}")
    with hcol2:
        if st.button("編集" if not editing else "キャンセル", key=f"_toggle_edit_{idx}"):
            st.session_state[editing_key] = not editing
            st.rerun()
    with hcol3:
        if st.button("削除", key=f"_delete_view_{idx}"):
            del enabled[idx]
            _persist_enabled_pages(project_root, enabled)
            st.rerun()

    if editing:
        _render_view_edit_form(provider, project_root, idx, view, enabled)
        return

    # 描画: connector or PageComponent.render_saved_view
    if view.is_connector_view:
        label = view.connector_page_label
        if label in connector_pages:
            render_connector_saved_view(label, provider, view, dashboard_config)
        else:
            st.caption(f"コネクターページ '{label}' は利用できません。")
        return

    component = get_page_component(view.view_type)
    if component is None:
        st.caption(f"ビュー '{view.view_type}' は未登録です。")
        return

    component.render_saved_view(provider, view, dashboard_config, **render_kwargs)


# ====================================================================
# HTMLエクスポート
# ====================================================================


def _render_html_export_button(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    vocab: dict[str, str] | None = None,
) -> None:
    """enabled-pagesをスタンドアロンHTMLとしてエクスポート"""
    views = list(getattr(dashboard_config, "enabled_pages", []) or [])
    # 後方互換: saved_views もあればマージ
    legacy_saved = list(getattr(dashboard_config, "saved_views", []) or [])
    all_views = views + legacy_saved

    if not all_views:
        return

    if st.button("HTMLエクスポート", key="_html_export_btn"):
        with st.spinner("HTMLを生成中..."):
            html = generate_saved_views_html(provider, project_root, dashboard_config, all_views, vocab)
        st.download_button(
            label="HTMLダウンロード",
            data=html.encode("utf-8"),
            file_name="dashboard_views.html",
            mime="text/html",
            key="_html_download_btn",
        )


def _render_view_add_form(
    provider: DashboardDataProvider,
    project_root: Path,
    enabled: list[SavedViewConfig],
) -> None:
    """新規ビューをenabled_pagesに追加するフォーム

    追加した瞬間にconfig.yamlのdashboard.enabled-pagesへ書き戻す。
    """
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

    filters = _render_global_filter_inputs("_add_view", {})
    local_filters = _render_local_filter_inputs("_add_view", "_add_lf_count", {})

    # ViewConfigレジストリからビュータイプ固有の設定UIを描画
    type_specific_config: dict[str, Any] = {}
    is_connector = view_type.startswith("connector:")
    connector_config_values: dict[str, Any] = {}
    if not is_connector:
        vc = get_view_config(view_type)
        if vc is not None:
            type_specific_config = vc.render_add_form(provider)
    else:
        page_label = view_type[len("connector:") :]
        connector_config_values = _render_connector_config_inputs(page_label, "_add_cc", {})

    if st.button("追加", key="_add_view_btn"):
        if not view_name:
            st.warning("ビュー名を入力してください。")
            return

        final_cc = _normalize_connector_config(connector_config_values)
        from config import SavedViewConfig

        view = SavedViewConfig.from_dict(
            {
                "name": view_name,
                "type": view_type,
                "filters": filters,
                "local_filters": local_filters,
                "plot": type_specific_config.get("plot", {}),
                "array_plot": type_specific_config.get("array_plot", {}),
                "gallery": type_specific_config.get("gallery", {}),
                "connector_config": final_cc,
            }
        )
        enabled.append(view)
        _persist_enabled_pages(project_root, enabled)
        st.session_state["_add_lf_count"] = 1
        st.rerun()


def _render_global_filter_inputs(
    prefix: str,
    existing: dict[str, Any],
) -> dict[str, Any]:
    """グローバルフィルタ入力UI（type/analysis_status/active）"""
    st.markdown("**フィルタ**")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_type = st.text_input("type", value=existing.get("type", ""), key=f"{prefix}_f_type")
    with fc2:
        f_status = st.text_input(
            "analysis_status",
            value=existing.get("analysis_status", ""),
            key=f"{prefix}_f_status",
        )
    with fc3:
        f_active = st.checkbox("active", value=existing.get("active", False), key=f"{prefix}_f_active")
    filters: dict[str, Any] = {}
    if f_type:
        filters["type"] = f_type
    if f_status:
        filters["analysis_status"] = f_status
    if f_active:
        filters["active"] = True
    return filters


def _render_local_filter_inputs(
    prefix: str,
    count_key: str,
    existing: dict[str, Any],
) -> dict[str, Any]:
    """ローカルフィルタ入力UI（複数キー/値ペア）"""
    st.markdown("**ローカルフィルタ**")
    if count_key not in st.session_state:
        st.session_state[count_key] = max(1, len(existing))
    lf_count: int = st.session_state[count_key]
    existing_items = list(existing.items())
    pairs: list[tuple[str, str]] = []
    for lfi in range(lf_count):
        default_key = existing_items[lfi][0] if lfi < len(existing_items) else ""
        default_val = str(existing_items[lfi][1]) if lfi < len(existing_items) else ""
        lfc1, lfc2 = st.columns(2)
        with lfc1:
            lf_key = st.text_input("プロパティキー", value=default_key, key=f"{prefix}_lf_key_{lfi}")
        with lfc2:
            lf_value = st.text_input("値", value=default_val, key=f"{prefix}_lf_value_{lfi}")
        if lf_key and lf_value:
            pairs.append((lf_key, lf_value))
    lf_btn1, lf_btn2 = st.columns(2)
    with lf_btn1:
        if st.button("フィルタ追加", key=f"{prefix}_lf_more"):
            st.session_state[count_key] = lf_count + 1
            st.rerun()
    with lf_btn2:
        if lf_count > 1 and st.button("フィルタ削除", key=f"{prefix}_lf_remove"):
            st.session_state[count_key] = max(1, lf_count - 1)
            st.rerun()
    return dict(pairs)


def _render_connector_config_inputs(
    page_label: str,
    prefix: str,
    existing: dict[str, Any],
) -> dict[str, Any]:
    """コネクターconfig入力UI"""
    schema = get_connector_config_schema(page_label)
    values: dict[str, Any] = {}
    if not schema:
        return values
    st.markdown("**コネクター設定**")
    for field in schema:
        fkey = field["key"]
        flabel = field.get("label", fkey)
        fhelp = field.get("help", "")
        if field.get("type") == "checkbox":
            values[fkey] = st.checkbox(
                flabel,
                value=existing.get(fkey, True),
                key=f"{prefix}_{fkey}",
                help=fhelp,
            )
        else:
            existing_val = existing.get(fkey, "")
            if isinstance(existing_val, list):
                existing_val = ", ".join(str(v) for v in existing_val)
            val = st.text_input(flabel, value=str(existing_val), key=f"{prefix}_{fkey}", help=fhelp)
            if val:
                values[fkey] = val
    return values


def _normalize_connector_config(cc: dict[str, Any]) -> dict[str, Any]:
    """connector_config正規化: compare_materialsはカンマ区切り→list変換"""
    out = dict(cc)
    if "compare_materials" in out and isinstance(out["compare_materials"], str):
        out["compare_materials"] = [m.strip() for m in out["compare_materials"].split(",") if m.strip()]
    return out


def _render_view_edit_form(
    provider: DashboardDataProvider,
    project_root: Path,
    idx: int,
    view: SavedViewConfig,
    enabled: list[SavedViewConfig],
) -> None:
    """enabled_pages[idx]のビューを編集し、保存時にconfig.yamlへ書き戻す

    基本フィールド（name, type, filters, local_filters, connector_config）と
    view_type が ``plot`` の場合のプロット詳細のみを編集可能。
    array_plot/gallery 等の複雑な設定は config.yaml を直接編集する前提。
    """
    prefix = f"_edit_{idx}"
    with st.container():
        view_name = st.text_input("ビュー名", value=view.name, key=f"{prefix}_name")

        base_types = get_view_type_options()
        connector_types = get_connector_view_type_options(provider)
        all_types = base_types + connector_types
        type_index = all_types.index(view.view_type) if view.view_type in all_types else 0
        view_type = st.selectbox("タイプ", all_types, index=type_index, key=f"{prefix}_type")

        filters = _render_global_filter_inputs(prefix, view.filters)
        local_filters = _render_local_filter_inputs(prefix, f"{prefix}_lf_count", view.local_filters)

        edit_plot_config = _render_plot_edit_inputs(provider, prefix, view.plot) if view_type == "plot" else None

        edit_cc_values: dict[str, Any] = {}
        if view_type.startswith("connector:"):
            page_label = view_type[len("connector:") :]
            edit_cc_values = _render_connector_config_inputs(page_label, f"{prefix}_cc", view.connector_config)

        ec1, ec2 = st.columns(2)
        with ec1:
            if st.button("保存", key=f"{prefix}_save"):
                final_cc = _normalize_connector_config(edit_cc_values)
                from config import SavedViewConfig

                plot_payload = edit_plot_config if edit_plot_config is not None else dict(view.plot)
                new_view = SavedViewConfig.from_dict(
                    {
                        "name": view_name,
                        "type": view_type,
                        "filters": filters,
                        "local_filters": local_filters,
                        "plot": plot_payload,
                        "gallery": dict(view.gallery),
                        "array_plot": dict(view.array_plot),
                        "connector_config": final_cc,
                    }
                )
                enabled[idx] = new_view
                _persist_enabled_pages(project_root, enabled)
                st.session_state[f"_editing_view_{idx}"] = False
                st.rerun()
        with ec2:
            if st.button("キャンセル", key=f"{prefix}_cancel"):
                st.session_state[f"_editing_view_{idx}"] = False
                st.rerun()


def _render_plot_edit_inputs(
    provider: DashboardDataProvider,
    prefix: str,
    existing_plot: dict[str, Any],
) -> dict[str, Any]:
    """プロット編集UI（x/y/color/chart_type + コンター設定 + スタイル + 軸範囲）"""
    st.markdown("**プロット設定**")
    keys = provider.get_property_keys()
    vn_key = provider._verbose_name_key

    epc1, epc2, epc3, epc4 = st.columns(4)
    with epc1:
        ex_x = existing_plot.get("x", "")
        x_idx = keys.index(ex_x) if ex_x in keys else 0
        ep_x = st.selectbox("X軸", keys, index=x_idx, key=f"{prefix}_px") if keys else ""
    with epc2:
        ex_y = existing_plot.get("y", "")
        y_idx = keys.index(ex_y) if ex_y in keys else min(1, len(keys) - 1)
        ep_y = st.selectbox("Y軸", keys, index=y_idx, key=f"{prefix}_py") if keys else ""
    with epc3:
        color_options = ["なし", vn_key, *[k for k in keys if k != vn_key]]
        ex_color = existing_plot.get("color") or "なし"
        c_idx = color_options.index(ex_color) if ex_color in color_options else 0
        ep_color = st.selectbox("色分け", color_options, index=c_idx, key=f"{prefix}_pcolor")
    with epc4:
        chart_options = ["散布図", "棒グラフ", "線図", "コンター", "等高線"]
        ex_chart = existing_plot.get("chart_type", "散布図")
        ct_idx = chart_options.index(ex_chart) if ex_chart in chart_options else 0
        ep_chart = st.selectbox("チャート", chart_options, index=ct_idx, key=f"{prefix}_pchart")

    plot_config: dict[str, Any] = {
        "x": ep_x,
        "y": ep_y,
        "color": ep_color if ep_color != "なし" else None,
        "chart_type": ep_chart,
    }

    if ep_chart in ("コンター", "等高線"):
        z_options = [k for k in keys if k != ep_x and k != ep_y]
        if z_options:
            ezc1, ezc2, ezc3 = st.columns(3)
            with ezc1:
                ex_z = existing_plot.get("z", "")
                z_idx = z_options.index(ex_z) if ex_z in z_options else 0
                ep_z = st.selectbox("Z軸（色）", z_options, index=z_idx, key=f"{prefix}_pz")
            ex_cr = existing_plot.get("color_range", {})
            with ezc2:
                ep_vmin = st.number_input("vmin", value=ex_cr.get("vmin"), key=f"{prefix}_pvmin", format="%g")
            with ezc3:
                ep_vmax = st.number_input("vmax", value=ex_cr.get("vmax"), key=f"{prefix}_pvmax", format="%g")
            if ep_z:
                plot_config["z"] = ep_z
            cr: dict[str, float] = {}
            if ep_vmin is not None:
                cr["vmin"] = float(ep_vmin)
            if ep_vmax is not None:
                cr["vmax"] = float(ep_vmax)
            if cr:
                plot_config["color_range"] = cr

    with st.expander("スタイル設定", expanded=False):
        ex_style = existing_plot.get("plot_style", {})
        esc1, esc2, esc3 = st.columns(3)
        with esc1:
            ep_marker = st.number_input(
                "マーカーサイズ",
                value=ex_style.get("marker_size"),
                min_value=1,
                max_value=50,
                key=f"{prefix}_p_marker",
            )
        with esc2:
            ep_lw = st.number_input(
                "線幅",
                value=ex_style.get("line_width"),
                min_value=1,
                max_value=20,
                key=f"{prefix}_p_lw",
            )
        with esc3:
            ep_fs = st.number_input(
                "フォントサイズ",
                value=ex_style.get("font_size"),
                min_value=6,
                max_value=48,
                key=f"{prefix}_p_fs",
            )
        from services.dashboard.widgets import build_style_config

        ep_plot_style = build_style_config(ep_marker, ep_lw, ep_fs)
        if ep_plot_style:
            plot_config["plot_style"] = ep_plot_style

    with st.expander("軸範囲設定", expanded=False):
        ex_range = existing_plot.get("axis_range", {})
        erc1, erc2, erc3, erc4 = st.columns(4)
        with erc1:
            ep_xmin = st.number_input("X最小", value=ex_range.get("x_min"), key=f"{prefix}_p_xmin", format="%g")
        with erc2:
            ep_xmax = st.number_input("X最大", value=ex_range.get("x_max"), key=f"{prefix}_p_xmax", format="%g")
        with erc3:
            ep_ymin = st.number_input("Y最小", value=ex_range.get("y_min"), key=f"{prefix}_p_ymin", format="%g")
        with erc4:
            ep_ymax = st.number_input("Y最大", value=ex_range.get("y_max"), key=f"{prefix}_p_ymax", format="%g")
        axis_range: dict[str, float] = {}
        if ep_xmin is not None:
            axis_range["x_min"] = float(ep_xmin)
        if ep_xmax is not None:
            axis_range["x_max"] = float(ep_xmax)
        if ep_ymin is not None:
            axis_range["y_min"] = float(ep_ymin)
        if ep_ymax is not None:
            axis_range["y_max"] = float(ep_ymax)
        if axis_range:
            plot_config["axis_range"] = axis_range

    return plot_config


def _render_save_defaults_button(project_root: Path) -> None:
    """サイドバーにデフォルト設定保存ボタンを表示

    シングルページ構成ではページ選択はconfig.dashboard.enabled-pagesで直接制御
    するため、ここではギャラリー設定（columns/rows）の書き戻しのみ扱う。
    """
    st.sidebar.markdown("---")
    with st.sidebar.expander("ギャラリー設定を保存"):
        if st.button("現在のギャラリー設定を保存", key="_save_defaults_btn"):
            from services.dashboard.config_writer import (
                collect_current_dashboard_state,
                save_dashboard_defaults,
            )

            items = collect_current_dashboard_state()
            if items:
                config_path = save_dashboard_defaults(project_root, items)
                st.success(f"設定を保存しました: {config_path.name}")
            else:
                st.warning("保存対象の設定が見つかりません。")


if __name__ == "__main__":
    main()
