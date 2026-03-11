"""配列プロットビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig
from services.dashboard.widgets import get_plotly_template

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class ArrayPlotViewConfig(ViewConfig):
    """配列プロットビュー設定コンポーネント"""

    view_type = "array_plot"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        import streamlit as st

        st.markdown("**配列プロット設定**")
        array_keys = provider.get_array_property_keys()
        if not array_keys:
            return {"array_plot": {}}
        ac1, ac2 = st.columns(2)
        with ac1:
            ap_mode = st.selectbox("モード", ["overlay", "single"], key="_add_view_ap_mode")
        with ac2:
            cross_group = st.checkbox("クロスグループ選択", value=False, key="_add_view_ap_cross")
        if cross_group:
            # 全配列キーから自由にX/Yを選択
            ap_x = st.selectbox("X軸", array_keys, key="_add_view_ap_x") if array_keys else ""
            ap_y_options = [k for k in array_keys if k != ap_x]
            ap_y = st.multiselect("Y軸", ap_y_options, key="_add_view_ap_y")
            ap_prefix = ""
        else:
            # 従来のプレフィックスグループ内選択
            prefixes = sorted({k.split(".")[0] for k in array_keys})
            ap_prefix = st.selectbox("プレフィックス", prefixes, key="_add_view_ap_prefix")
            prefix_keys = [k for k in array_keys if k.startswith(ap_prefix + ".")]
            ap_x = st.selectbox("X軸", prefix_keys, key="_add_view_ap_x") if prefix_keys else ""
            ap_y_options = [k for k in prefix_keys if k != ap_x]
            ap_y = st.multiselect("Y軸", ap_y_options, key="_add_view_ap_y")
        return {
            "array_plot": {
                "prefix": ap_prefix,
                "x": ap_x,
                "y": ap_y,
                "mode": ap_mode,
            }
        }


class ArrayPlotPage(PageComponent[ArrayPlotViewConfig]):
    """配列プロットビューページコンポーネント"""

    page_key = "array_plot"
    page_label = "配列プロット"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.widgets import (
            build_axis_range,
            build_style_config,
            get_active_filters,
            render_shared_filters,
        )

        vocab = kwargs.get("vocab")

        st.header("配列プロットビュー")

        array_keys = provider.get_array_property_keys()
        if not array_keys:
            st.info(
                "配列プロパティが見つかりません。CSVファイルがhas_output関係でGOファイルに紐付いている必要があります。"
            )
            return

        # 共有フィルタ（サイドバー描画 + 適用）
        rows = provider.get_go_table()
        render_shared_filters(rows)

        # configからデフォルト値を取得
        ap_defaults = _get_array_plot_defaults(dashboard_config)

        # 接頭辞グループの抽出（例: RF, stress）
        prefixes = sorted({k.split(".")[0] for k in array_keys})

        # クロスグループ選択モード
        cross_group = st.checkbox("クロスグループ選択（異なるデータグループ間でX/Y選択）", value=False)

        if cross_group:
            # 全配列キーから自由にX/Yを選択
            col_x, col_y = st.columns(2)
            with col_x:
                default_x_idx = _find_key_index(array_keys, ap_defaults.get("x"))
                x_key = st.selectbox("X軸", array_keys, index=default_x_idx)
            with col_y:
                y_options = [k for k in array_keys if k != x_key]
                if not y_options:
                    st.warning("Y軸に使用できるキーがありません。")
                    return
                default_y = _get_default_y_keys(y_options, ap_defaults.get("y"))
                y_keys = st.multiselect("Y軸", y_options, default=default_y)
        else:
            # 従来のプレフィックスグループ内選択
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_prefix = st.selectbox("データグループ", prefixes)

            # 選択された接頭辞のキーのみ
            prefix_keys = [k for k in array_keys if k.startswith(selected_prefix + ".")]

            with col2:
                default_x_idx = _find_key_index(prefix_keys, ap_defaults.get("x"))
                if default_x_idx == 0 and not ap_defaults.get("x"):
                    default_x_idx = len(prefix_keys) - 1
                x_key = st.selectbox("X軸", prefix_keys, index=default_x_idx)
            with col3:
                y_options = [k for k in prefix_keys if k != x_key]
                if not y_options:
                    st.warning("Y軸に使用できるキーがありません。")
                    return
                default_y = _get_default_y_keys(y_options, ap_defaults.get("y"))
                if not default_y and len(y_options) > 2:
                    default_y = [y_options[2]]
                elif not default_y and y_options:
                    default_y = [y_options[0]]
                y_keys = st.multiselect("Y軸", y_options, default=default_y)

        if not y_keys:
            st.info("Y軸を選択してください。")
            return

        # プロパティベース色分けオプション
        color_by_prop = None
        with st.expander("色分け設定", expanded=False):
            # 利用可能なプロパティキーを取得
            sample_rows = provider.get_go_table()
            prop_keys_for_color = set()
            for r in sample_rows:
                for k, v in r.items():
                    if k not in {"id", "name", "path"} and isinstance(v, str):
                        prop_keys_for_color.add(k)
            prop_keys_sorted = sorted(prop_keys_for_color)
            if prop_keys_sorted:
                color_options = ["なし（自動）", *prop_keys_sorted]
                color_by_prop = st.selectbox("プロパティで色分け", color_options, key="_ap_color_by")
                if color_by_prop == "なし（自動）":
                    color_by_prop = None

        # 表示モード: 全条件比較 or 個別ノード
        view_mode = st.radio("表示モード", ["全条件比較", "個別ノード"], horizontal=True)

        # 軸範囲設定（number_input） - configデフォルト対応
        with st.expander("軸範囲設定", expanded=False):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                ax_x_min = st.number_input("X最小", value=ap_defaults.get("x_min"), key="_ap_x_min", format="%g")
            with rc2:
                ax_x_max = st.number_input("X最大", value=ap_defaults.get("x_max"), key="_ap_x_max", format="%g")
            with rc3:
                ax_y_min = st.number_input("Y最小", value=ap_defaults.get("y_min", 0.0), key="_ap_y_min", format="%g")
            with rc4:
                ax_y_max = st.number_input("Y最大", value=ap_defaults.get("y_max", 1.0), key="_ap_y_max", format="%g")

        # スタイル設定
        with st.expander("スタイル設定", expanded=False):
            sc1, sc2, sc3 = st.columns(3)
            psd = dashboard_config.plot_style_defaults
            with sc1:
                ap_marker_size = st.number_input(
                    "マーカーサイズ",
                    value=None,
                    min_value=psd.marker_size_min,
                    max_value=psd.marker_size_max,
                    key="_ap_marker_size",
                )
            with sc2:
                ap_line_width = st.number_input(
                    "線幅",
                    value=None,
                    min_value=psd.line_width_min,
                    max_value=psd.line_width_max,
                    key="_ap_line_width",
                )
            with sc3:
                ap_font_size = st.number_input(
                    "フォントサイズ",
                    value=None,
                    min_value=psd.font_size_min,
                    max_value=psd.font_size_max,
                    key="_ap_font_size",
                )

        ap_x_range = build_axis_range(ax_x_min, ax_x_max)
        ap_y_range = build_axis_range(ax_y_min, ax_y_max)
        ap_style = build_style_config(ap_marker_size, ap_line_width, ap_font_size)

        # 共有フィルタをprovider用のフィルタ辞書に変換
        active_filters = get_active_filters()

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
                vocab=vocab,
                color_by=color_by_prop,
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
                vocab=vocab,
            )

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.html_export import _add_ng_regions_to_fig
        from services.dashboard.query import apply_saved_view_filters, saved_view_filters_to_provider_filters

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

                        from modules.vocab_display import translate_key

                        sv_vocab = kwargs.get("vocab") or {}
                        fig = go.Figure()
                        for s in plot_data["series"]:
                            series_label = translate_key(s["key"].split(".")[-1], sv_vocab)
                            fig.add_trace(
                                go.Scatter(
                                    x=plot_data["x_values"],
                                    y=s["values"],
                                    mode="lines+markers",
                                    name=series_label,
                                )
                            )
                        # NG領域塗りつぶし
                        if ng_regions:
                            _add_ng_regions_to_fig(fig, ng_regions)
                        fig.update_layout(
                            title=plot_data["name"],
                            xaxis_title=translate_key(x_key.split(".")[-1], sv_vocab),
                            yaxis_title="値",
                            height=500,
                            template=get_plotly_template(),
                        )
                        st.plotly_chart(fig, width="stretch")
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
                vocab=kwargs.get("vocab"),
            )

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_array_plot_html

        vocab = kwargs.get("vocab")
        return generate_array_plot_html(provider, dashboard_config, view, vocab=vocab)


# ====================================================================
# 配列プロット内部描画関数
# ====================================================================


def _render_array_overlay(
    provider: DashboardDataProvider,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    style: dict[str, int] | None = None,
    vocab: dict[str, str] | None = None,
    color_by: str | None = None,
) -> None:
    """全条件の配列データを凡例付きで同一グラフに重ね書き"""
    import streamlit as st

    from modules.vocab_display import translate_key
    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

    v = vocab or {}

    for y_key in y_keys:
        x_label = translate_key(x_key, v)
        y_label = translate_key(y_key, v)
        st.subheader(f"{y_label} vs {x_label}")
        grid_data = provider.get_array_grid_data(x_key, y_key, filters=filters)
        if not grid_data:
            st.info(f"'{x_key}' と '{y_key}' のデータがありません。")
            continue

        grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))

        # プロパティベース色分け: 属性値→色のマッピングを構築
        color_map: dict[str, str] | None = None
        if color_by:
            import plotly.express as px

            unique_vals = sorted({str(item.get("properties", {}).get(color_by, "（未設定）")) for item in grid_data})
            palette = px.colors.qualitative.Plotly
            color_map = {val: palette[i % len(palette)] for i, val in enumerate(unique_vals)}

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            for item in grid_data:
                # display_nameがあれば優先使用
                label = item.get("display_name", item["name"])
                trace_kwargs: dict[str, Any] = {
                    "x": item["x_values"],
                    "y": item["y_values"],
                    "mode": "lines+markers",
                    "name": label,
                }
                if color_map and color_by:
                    prop_val = str(item.get("properties", {}).get(color_by, "（未設定）"))
                    trace_kwargs["line"] = {"color": color_map[prop_val]}
                    trace_kwargs["marker"] = {"color": color_map[prop_val]}
                    trace_kwargs["legendgroup"] = prop_val
                fig.add_trace(go.Scatter(**trace_kwargs))
            if ng_regions:
                _add_ng_regions_to_fig(fig, ng_regions)
            fig.update_layout(
                title=dict(
                    text=f"{y_label} vs {x_label}（全条件比較）",
                    font=dict(size=24),
                ),
                xaxis=dict(
                    title=dict(
                        text=translate_key(x_key.split(".")[-1], v),
                        font=dict(size=20),
                    ),
                    tickfont=dict(size=20),
                ),
                yaxis=dict(
                    title=dict(
                        text=translate_key(y_key.split(".")[-1], v),
                        font=dict(size=20),
                    ),
                    tickfont=dict(size=20),
                ),
                legend=dict(font=dict(size=16)),
                height=600,
                showlegend=True,
                template=get_plotly_template(),
            )
            if x_range:
                fig.update_xaxes(range=x_range)
            if y_range:
                fig.update_yaxes(range=y_range)
            if style:
                apply_style_to_fig(fig, style)
            st.plotly_chart(fig, width="stretch")

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
    vocab: dict[str, str] | None = None,
) -> None:
    """配列データの個別ノード表示（複数Y軸重ね書き）"""
    import streamlit as st

    from modules.vocab_display import translate_key
    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

    v = vocab or {}

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
    # 外部化プロパティ（_ext_keys）も考慮
    items_with_array = []
    for r in rows:
        nid = r["id"]
        node = provider._node_by_id.get(nid)
        if node is None:
            continue
        has_inline = isinstance(node.properties.get(x_key), list)
        ext_keys = node.properties.get("_ext_keys")
        has_ext = isinstance(ext_keys, list) and x_key in ext_keys
        if has_inline or has_ext:
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
            series_label = translate_key(s["key"].split(".")[-1], v)
            fig.add_trace(
                go.Scatter(
                    x=plot_data["x_values"],
                    y=s["values"],
                    mode="lines+markers",
                    name=series_label,
                )
            )
        # NG領域塗りつぶし
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)

        # 軸ラベル・軸数値・凡例のフォントサイズ設定（色はテンプレートに委譲）
        fig.update_layout(
            title=dict(
                text=f"{selected}",
                font=dict(size=24),
            ),
            xaxis=dict(
                title=dict(
                    text=translate_key(x_key.split(".")[-1], v),
                    font=dict(size=20),
                ),
                tickfont=dict(size=20),
            ),
            yaxis=dict(
                title=dict(
                    text="値",
                    font=dict(size=20),
                ),
                tickfont=dict(size=20),
            ),
            legend=dict(font=dict(size=16)),
            height=500,
            template=get_plotly_template(),
        )
        if x_range:
            fig.update_xaxes(range=x_range)
        if y_range:
            fig.update_yaxes(range=y_range)
        if style:
            apply_style_to_fig(fig, style)
        st.plotly_chart(fig, width="stretch")
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")


# ====================================================================
# ヘルパー関数
# ====================================================================


def _get_array_plot_defaults(dashboard_config: DashboardConfig) -> dict[str, Any]:
    """DashboardConfigからarray_plotデフォルト設定を取得

    config.yamlの dashboard.array-plot セクションから以下を読み取る:
    - x: デフォルトX軸キー
    - y: デフォルトY軸キー（リスト）
    - x_min, x_max, y_min, y_max: デフォルト軸範囲

    Returns:
        デフォルト設定の辞書
    """
    if not dashboard_config:
        return {}
    ap_config = getattr(dashboard_config, "array_plot_defaults", None)
    if not ap_config or not isinstance(ap_config, dict):
        return {}
    return ap_config


def _find_key_index(keys: list[str], target: str | None) -> int:
    """キーリスト内でtargetのインデックスを返す。見つからなければ0"""
    if not target or not keys:
        return 0
    try:
        return keys.index(target)
    except ValueError:
        return 0


def _get_default_y_keys(y_options: list[str], config_y: str | list[str] | None) -> list[str]:
    """configからデフォルトY軸キーを取得"""
    if not config_y:
        return []
    if isinstance(config_y, str):
        config_y = [config_y]
    return [k for k in config_y if k in y_options]
