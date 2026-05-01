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
        """プロットページを対話UIで描画する（旧 render_page 相当）

        軸・色分け・チャート・軸範囲・スタイルをユーザが選択して即時反映する。
        ``view.plot`` で設定された値は選択UIの初期値として尊重する。
        """
        import streamlit as st

        from services.dashboard.html_export import (
            _add_group_lines_to_fig,
            _add_ng_regions_to_fig,
            _create_plot_figure,
        )
        from services.dashboard.widgets import (
            apply_style_to_fig,
            build_axis_range,
            build_style_config,
            get_active_filters,
            render_shared_filters,
        )
        from services.graph.query import apply_saved_view_filters

        vocab = kwargs.get("vocab")

        st.header("プロットビュー")

        # 共有フィルタ
        rows = provider.get_go_table()
        render_shared_filters(rows)
        active_filters = get_active_filters()

        # グローバルカラム設定がある場合はフィルタ済みキーを使用
        all_keys = provider.get_property_keys()
        keys = provider.get_filtered_property_keys()
        if not keys:
            st.info("プロット可能なプロパティがありません。")
            return

        # config駆動デフォルト軸 + viewプリセット復元
        plot_x = getattr(dashboard_config, "plot_x", None)
        plot_y = getattr(dashboard_config, "plot_y", None)
        view_plot = view.plot or {}
        wkey = f"_plot_{view.name}"

        x_default = view_plot.get("x") or st.session_state.get(f"{wkey}_persist_x") or plot_x
        y_default = view_plot.get("y") or st.session_state.get(f"{wkey}_persist_y") or plot_y

        x_default_idx = 0
        if x_default and x_default in keys:
            x_default_idx = keys.index(x_default)

        y_default_idx = min(1, len(keys) - 1)
        if y_default and y_default in keys:
            y_default_idx = keys.index(y_default)

        vn_key = provider._verbose_name_key

        color_options = ["なし", vn_key, *[k for k in keys if k != vn_key]]
        color_default = view_plot.get("color") or st.session_state.get(f"{wkey}_persist_color")
        color_default_idx = 1
        if color_default and color_default in color_options:
            color_default_idx = color_options.index(color_default)

        chart_options = ["散布図", "棒グラフ", "線図", "コンター", "等高線"]
        chart_default = view_plot.get("chart_type") or st.session_state.get(f"{wkey}_persist_chart")
        chart_default_idx = 0
        if chart_default and chart_default in chart_options:
            chart_default_idx = chart_options.index(chart_default)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            x_key = st.selectbox("X軸", keys, index=x_default_idx, key=f"{wkey}_x")
        with col2:
            y_key = st.selectbox("Y軸", keys, index=y_default_idx, key=f"{wkey}_y")
        with col3:
            color_key = st.selectbox("色分け", color_options, index=color_default_idx, key=f"{wkey}_color")
        with col4:
            chart_type = st.selectbox("チャートタイプ", chart_options, index=chart_default_idx, key=f"{wkey}_chart")

        st.session_state[f"{wkey}_persist_x"] = x_key
        st.session_state[f"{wkey}_persist_y"] = y_key
        st.session_state[f"{wkey}_persist_color"] = color_key
        st.session_state[f"{wkey}_persist_chart"] = chart_type

        if not x_key or not y_key:
            return

        # コンター/等高線用
        z_key: str | None = None
        color_range: dict[str, float] = {}
        if chart_type in ("コンター", "等高線"):
            z_options = [k for k in keys if k != x_key and k != y_key]
            if z_options:
                cc1, cc2, cc3 = st.columns(3)
                z_cfg = view_plot.get("z")
                z_default_idx = z_options.index(z_cfg) if z_cfg in z_options else 0
                with cc1:
                    z_key = st.selectbox("Z軸（色）", z_options, index=z_default_idx, key=f"{wkey}_z")
                cfg_cr = view_plot.get("color_range", {}) or {}
                with cc2:
                    vmin = st.number_input(
                        "カラー最小（vmin）",
                        value=cfg_cr.get("vmin"),
                        key=f"{wkey}_vmin",
                        format="%g",
                    )
                with cc3:
                    vmax = st.number_input(
                        "カラー最大（vmax）",
                        value=cfg_cr.get("vmax"),
                        key=f"{wkey}_vmax",
                        format="%g",
                    )
                if vmin is not None:
                    color_range["vmin"] = float(vmin)
                if vmax is not None:
                    color_range["vmax"] = float(vmax)

        # グループ結線設定
        group_line_key = getattr(dashboard_config, "group_line_key", None)
        group_line_options = ["なし"] + [k for k in all_keys if k != x_key and k != y_key]
        gl_default = 0
        if group_line_key and group_line_key in group_line_options:
            gl_default = group_line_options.index(group_line_key)
        col_gl1, _col_gl2 = st.columns(2)
        with col_gl1:
            selected_group_line = st.selectbox(
                "グループ結線キー", group_line_options, index=gl_default, key=f"{wkey}_gl"
            )

        # 軸範囲設定
        cfg_axis = view_plot.get("axis_range", {}) or {}
        with st.expander("軸範囲設定", expanded=False):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                x_min = st.number_input("X最小", value=cfg_axis.get("x_min"), key=f"{wkey}_x_min", format="%g")
            with rc2:
                x_max = st.number_input("X最大", value=cfg_axis.get("x_max"), key=f"{wkey}_x_max", format="%g")
            with rc3:
                y_min = st.number_input("Y最小", value=cfg_axis.get("y_min"), key=f"{wkey}_y_min", format="%g")
            with rc4:
                y_max = st.number_input("Y最大", value=cfg_axis.get("y_max"), key=f"{wkey}_y_max", format="%g")

        # スタイル設定
        cfg_style = view_plot.get("plot_style", {}) or {}
        with st.expander("スタイル設定", expanded=False):
            sc1, sc2, sc3 = st.columns(3)
            psd = dashboard_config.plot_style_defaults
            with sc1:
                plot_marker_size = st.number_input(
                    "マーカーサイズ",
                    value=cfg_style.get("marker_size"),
                    min_value=psd.marker_size_min,
                    max_value=psd.marker_size_max,
                    key=f"{wkey}_marker_size",
                )
            with sc2:
                plot_line_width = st.number_input(
                    "線幅",
                    value=cfg_style.get("line_width"),
                    min_value=psd.line_width_min,
                    max_value=psd.line_width_max,
                    key=f"{wkey}_line_width",
                )
            with sc3:
                plot_font_size = st.number_input(
                    "フォントサイズ",
                    value=cfg_style.get("font_size"),
                    min_value=psd.font_size_min,
                    max_value=psd.font_size_max,
                    key=f"{wkey}_font_size",
                )

        plot_style = build_style_config(plot_marker_size, plot_line_width, plot_font_size)

        color = color_key if color_key != "なし" else None

        gl_key = selected_group_line if selected_group_line != "なし" else None
        extra_keys: list[str] = []
        if gl_key:
            extra_keys.append(gl_key)
        if z_key:
            extra_keys.append(z_key)

        data = provider.get_plot_data(x_key, y_key, color_key=color, extra_keys=extra_keys)

        # view.filters（保存済みフィルタ）と共有フィルタの両方を適用
        if view.filters:
            all_rows = provider.get_go_table()
            filtered_rows = apply_saved_view_filters(all_rows, view.filters)
            filtered_names = {r["name"] for r in filtered_rows}
            data = [d for d in data if d.get("name") in filtered_names]
        if active_filters:
            filtered_rows = provider.get_go_table(filters=active_filters)
            filtered_names = {r["name"] for r in filtered_rows}
            data = [d for d in data if d.get("name") in filtered_names]

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
                z_key=z_key,
                color_range=color_range,
                vocab=vocab,
            )
            # NG領域塗りつぶし
            ng_regions = getattr(dashboard_config, "ng_regions", [])
            if ng_regions:
                _add_ng_regions_to_fig(fig, ng_regions)
            # グループ結線
            if gl_key and gl_key in df.columns:
                _add_group_lines_to_fig(fig, df, x_key, y_key, gl_key)
            # 軸範囲
            x_range = build_axis_range(x_min, x_max)
            y_range = build_axis_range(y_min, y_max)
            if x_range:
                fig.update_xaxes(range=x_range)
            if y_range:
                fig.update_yaxes(range=y_range)
            apply_style_to_fig(fig, plot_style)
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
