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
        prefixes = sorted({k.split(".")[0] for k in array_keys})
        ac1, ac2 = st.columns(2)
        with ac1:
            ap_prefix = st.selectbox("プレフィックス", prefixes, key="_add_view_ap_prefix")
        with ac2:
            ap_mode = st.selectbox("モード", ["overlay", "single"], key="_add_view_ap_mode")
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
                ap_font_size = st.number_input(
                    "フォントサイズ", value=None, min_value=6, max_value=48, key="_ap_font_size"
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
                            template=get_plotly_template(),
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

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_array_plot_html

        return generate_array_plot_html(provider, dashboard_config, view)


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
) -> None:
    """全条件の配列データを凡例付きで同一グラフに重ね書き"""
    import streamlit as st

    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

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
                title=dict(
                    text=f"{y_key} vs {x_key}（全条件比較）",
                    font=dict(size=24),
                ),
                xaxis=dict(
                    title=dict(
                        text=x_key.split(".")[-1],
                        font=dict(size=20),
                    ),
                    tickfont=dict(size=20),
                ),
                yaxis=dict(
                    title=dict(
                        text=y_key.split(".")[-1],
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
    import streamlit as st

    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

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

        # 軸ラベル・軸数値・凡例のフォントサイズ設定（色はテンプレートに委譲）
        fig.update_layout(
            title=dict(
                text=f"{selected}",
                font=dict(size=24),
            ),
            xaxis=dict(
                title=dict(
                    text=x_key.split(".")[-1],
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
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")
