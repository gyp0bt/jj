"""ギャラリービューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class GalleryViewConfig(ViewConfig):
    """ギャラリービュー設定コンポーネント"""

    view_type = "gallery"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        import streamlit as st

        st.markdown("**ギャラリー設定**")
        gc1, gc2 = st.columns(2)
        with gc1:
            g_source = st.selectbox("ソース", ["has_output", "property"], key="_add_view_gsrc")
        with gc2:
            g_format = st.text_input("フォーマット", key="_add_view_gfmt")
        gallery_config: dict[str, Any] = {"source": g_source}
        if g_format:
            gallery_config["format"] = g_format
        return {"gallery": gallery_config}


class GalleryPage(PageComponent[GalleryViewConfig]):
    """ギャラリービューページコンポーネント"""

    page_key = "gallery"
    page_label = "ギャラリー"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from pathlib import Path

        from services.dashboard.app import _render_gallery_page

        project_root = kwargs.get("project_root")
        if project_root is None:
            import streamlit as st

            st.error("project_rootが指定されていません。")
            return
        _render_gallery_page(provider, Path(project_root), dashboard_config)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from pathlib import Path

        from services.dashboard.app import _render_saved_gallery

        project_root = kwargs.get("project_root")
        if project_root is None:
            return
        _render_saved_gallery(provider, Path(project_root), dashboard_config, view)
