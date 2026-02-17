"""配列プロットビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

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
        from services.dashboard.app import _render_array_plot_page

        _render_array_plot_page(provider, dashboard_config)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_saved_array_plot

        _render_saved_array_plot(provider, dashboard_config, view)
