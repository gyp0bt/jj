"""カードビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class CardViewConfig(ViewConfig):
    """カードビュー設定コンポーネント"""

    view_type = "card"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # カードビューにはビュータイプ固有の設定はない
        return {}


class CardPage(PageComponent[CardViewConfig]):
    """カードビューページコンポーネント"""

    page_key = "card"
    page_label = "カード"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_card_page

        _render_card_page(provider)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_saved_card

        _render_saved_card(provider, view)
