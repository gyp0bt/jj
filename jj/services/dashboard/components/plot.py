"""プロットビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class PlotViewConfig(ViewConfig):
    """プロットビュー設定コンポーネント"""

    view_type = "plot"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        import streamlit as st

        st.markdown("**プロット設定**")
        keys = provider.get_property_keys()
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            px_key = st.selectbox("X軸", keys, key="_add_view_px") if keys else ""
        with pc2:
            py_key = st.selectbox("Y軸", keys, key="_add_view_py", index=min(1, len(keys) - 1)) if keys else ""
        with pc3:
            p_chart = st.selectbox("チャート", ["散布図", "棒グラフ", "線図"], key="_add_view_pchart")
        return {"plot": {"x": px_key, "y": py_key, "chart_type": p_chart}}


class PlotPage(PageComponent[PlotViewConfig]):
    """プロットビューページコンポーネント"""

    page_key = "plot"
    page_label = "プロット"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.html_export import (
            _add_group_lines_to_fig,
            _add_ng_regions_to_fig,
            _create_plot_figure,
        )
        from services.dashboard.widgets import apply_style_to_fig, build_axis_range, build_style_config

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

        plot_style = build_style_config(plot_marker_size, plot_line_width, plot_font_size)

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
            x_range = build_axis_range(x_min, x_max)
            y_range = build_axis_range(y_min, y_max)
            if x_range:
                fig.update_xaxes(range=x_range)
            if y_range:
                fig.update_yaxes(range=y_range)
            # スタイル設定を適用
            apply_style_to_fig(fig, plot_style)
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            # plotlyがない場合はStreamlit組み込みチャートを使用
            st.scatter_chart(df, x=x_key, y=y_key)

        st.caption(f"データ点数: {len(data)}")

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.html_export import (
            _add_group_lines_to_fig,
            _add_ng_regions_to_fig,
            _create_plot_figure,
        )
        from services.dashboard.query import apply_saved_view_filters

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

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_plot_html

        return generate_plot_html(provider, view, dashboard_config)
