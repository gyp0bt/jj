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
        from services.dashboard.app import _render_plot_page

        _render_plot_page(provider, dashboard_config)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_saved_plot

        _render_saved_plot(provider, view, dashboard_config)
