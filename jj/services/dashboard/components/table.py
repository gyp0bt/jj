"""テーブルビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class TableViewConfig(ViewConfig):
    """テーブルビュー設定コンポーネント"""

    view_type = "table"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # テーブルビューにはビュータイプ固有の設定はない
        return {}


class TablePage(PageComponent[TableViewConfig]):
    """テーブルビューページコンポーネント"""

    page_key = "table"
    page_label = "テーブル"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_table_page

        vocab = kwargs.get("vocab") or {}
        _render_table_page(provider, dashboard_config, vocab)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        from services.dashboard.app import _render_saved_table

        vocab = kwargs.get("vocab") or {}
        _render_saved_table(provider, dashboard_config, view, vocab)
