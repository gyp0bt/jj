"""ステータスビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class StatusViewConfig(ViewConfig):
    """ステータスビュー設定コンポーネント"""

    view_type = "status"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # ステータスビューにはビュータイプ固有の設定はない
        return {}


class StatusPage(PageComponent[StatusViewConfig]):
    """ステータスビューページコンポーネント"""

    page_key = "status"
    page_label = "ステータス"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_status_page

        _render_status_page(provider)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_status_page

        _render_status_page(provider)
