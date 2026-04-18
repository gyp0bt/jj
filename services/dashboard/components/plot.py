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
        vn_key = provider._verbose_name_key
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            px_key = st.selectbox("X軸", keys, key="_add_view_px") if keys else ""
        with pc2:
            py_key = st.selectbox("Y軸", keys, key="_add_view_py", index=min(1, len(keys) - 1)) if keys else ""
        with pc3:
            color_options = ["なし", vn_key, *[k for k in keys if k != vn_key]]
            p_color = st.selectbox("色分け", color_options, index=1, key="_add_view_pcolor")
        with pc4:
            p_chart = st.selectbox(
                "チャート", ["散布図", "棒グラフ", "線図", "コンター", "等高線"], key="_add_view_pchart"
            )
        color_val = p_color if p_color != "なし" else None

        # コンター/等高線用: Z軸・vmin/vmax
        p_z_key: str | None = None
        p_color_range: dict[str, float] = {}
        if p_chart in ("コンター", "等高線"):
            z_options = [k for k in keys if k != px_key and k != py_key]
            if z_options:
                zc1, zc2, zc3 = st.columns(3)
                with zc1:
                    p_z_key = st.selectbox("Z軸（色）", z_options, key="_add_view_pz")
                with zc2:
                    p_vmin = st.number_input("vmin", value=None, key="_add_view_pvmin", format="%g")
                with zc3:
                    p_vmax = st.number_input("vmax", value=None, key="_add_view_pvmax", format="%g")
                if p_vmin is not None:
                    p_color_range["vmin"] = float(p_vmin)
                if p_vmax is not None:
                    p_color_range["vmax"] = float(p_vmax)

        # スタイル設定（オプション）
        with st.expander("スタイル設定", expanded=False):
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                p_marker = st.number_input(
                    "マーカーサイズ", value=None, min_value=1, max_value=50, key="_add_view_p_marker"
                )
            with sc2:
                p_lw = st.number_input("線幅", value=None, min_value=1, max_value=20, key="_add_view_p_lw")
            with sc3:
                p_fs = st.number_input("フォントサイズ", value=None, min_value=6, max_value=48, key="_add_view_p_fs")

        # 軸範囲設定（オプション）
        with st.expander("軸範囲設定", expanded=False):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                p_xmin = st.number_input("X最小", value=None, key="_add_view_p_xmin", format="%g")
            with rc2:
                p_xmax = st.number_input("X最大", value=None, key="_add_view_p_xmax", format="%g")
            with rc3:
                p_ymin = st.number_input("Y最小", value=None, key="_add_view_p_ymin", format="%g")
            with rc4:
                p_ymax = st.number_input("Y最大", value=None, key="_add_view_p_ymax", format="%g")

        from services.dashboard.widgets import build_style_config

        plot_style = build_style_config(p_marker, p_lw, p_fs)

        axis_range: dict[str, float] = {}
        if p_xmin is not None:
            axis_range["x_min"] = float(p_xmin)
        if p_xmax is not None:
            axis_range["x_max"] = float(p_xmax)
        if p_ymin is not None:
            axis_range["y_min"] = float(p_ymin)
        if p_ymax is not None:
            axis_range["y_max"] = float(p_ymax)

        plot_config: dict[str, Any] = {"x": px_key, "y": py_key, "color": color_val, "chart_type": p_chart}
        if p_z_key:
            plot_config["z"] = p_z_key
        if p_color_range:
            plot_config["color_range"] = p_color_range
        if plot_style:
            plot_config["plot_style"] = plot_style
        if axis_range:
            plot_config["axis_range"] = axis_range
        return {"plot": plot_config}


class PlotPage(PageComponent[PlotViewConfig]):
    """プロットビューページコンポーネント"""

    page_key = "plot"
    page_label = "プロット"

    def render(
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

        vocab = kwargs.get("vocab")

        plot_config = view.plot
        x_key = plot_config.get("x")
        y_key = plot_config.get("y")
        color = plot_config.get("color")
        chart_type = plot_config.get("chart_type", "散布図")

        # プロット軸のplaceholder: config未指定時は dashboard_config.plot_x/plot_y、
        # それも無ければプロパティキー先頭2つで補完する
        if not x_key:
            x_key = getattr(dashboard_config, "plot_x", None)
        if not y_key:
            y_key = getattr(dashboard_config, "plot_y", None)
        if not x_key or not y_key:
            keys = provider.get_property_keys()
            if not x_key and keys:
                x_key = keys[0]
            if not y_key and len(keys) > 1:
                y_key = keys[1]
        if not x_key or not y_key:
            st.info("プロットできる数値プロパティがありません。config.dashboard.plot.x / plot.y を設定してください。")
            return

        # グループ結線キーをextra_keysに含める
        group_line_key = getattr(dashboard_config, "group_line_key", None) if dashboard_config else None
        extra_keys: list[str] = []
        if group_line_key:
            extra_keys.append(group_line_key)
        # コンタープロット用Z軸キーもextra_keysに含める
        z_key = plot_config.get("z")
        if z_key:
            extra_keys.append(z_key)

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

            from services.dashboard.html_export import _apply_axis_range, _resolve_plot_style
            from services.dashboard.widgets import apply_style_to_fig

            # plot_style: ビュー設定 > DashboardConfig > デフォルト
            view_plot_style = plot_config.get("plot_style")
            resolved_style = _resolve_plot_style(view_plot_style, dashboard_config)
            color_range = plot_config.get("color_range", {})

            fig = _create_plot_figure(
                px,
                df,
                x_key,
                y_key,
                color,
                chart_type,
                hover_name_col=vn_key,
                z_key=z_key,
                color_range=color_range,
                vocab=vocab,
            )
            # NG領域塗りつぶし
            ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []
            if ng_regions:
                _add_ng_regions_to_fig(fig, ng_regions)
            # グループ結線
            if group_line_key and group_line_key in df.columns:
                _add_group_lines_to_fig(fig, df, x_key, y_key, group_line_key)
            # スタイル設定を適用
            apply_style_to_fig(fig, resolved_style)
            # 軸範囲設定を適用
            axis_range = plot_config.get("axis_range", {})
            if axis_range:
                _apply_axis_range(fig, axis_range)
            st.plotly_chart(fig, width="stretch")
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

        vocab = kwargs.get("vocab")
        return generate_plot_html(provider, view, dashboard_config, vocab=vocab)
