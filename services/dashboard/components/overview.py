"""概要ビューコンポーネント（テーブル+ギャラリー統合レイアウト）

テーブルを上、ギャラリーを下に配置して一覧性を提供する統合ページ。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class OverviewViewConfig(ViewConfig):
    """概要ビュー設定コンポーネント"""

    view_type = "overview"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}


class OverviewPage(PageComponent["OverviewViewConfig"]):
    """テーブル+ギャラリー統合ビュー"""

    page_key = "overview"
    page_label = "概要"

    def render(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.components.gallery import render_gallery_section
        from services.dashboard.components.table import render_table_section
        from services.dashboard.query import apply_saved_view_filters, sort_rows_by_index

        vocab = kwargs.get("vocab") or {}
        project_root = kwargs.get("project_root")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        filtered = apply_saved_view_filters(rows, view.filters) if view.filters else list(rows)
        filtered = sort_rows_by_index(filtered, provider._index_key, provider._version_key)

        st.subheader("テーブル")
        render_table_section(
            provider,
            dashboard_config,
            filtered,
            len(rows),
            vocab=vocab,
            grid_key=f"view_{view.name}_table",
            download_key=f"view_{view.name}",
        )

        st.divider()

        if project_root is not None:
            st.subheader("ギャラリー")
            render_gallery_section(
                provider,
                dashboard_config,
                Path(project_root),
                show_header=False,
                key_prefix=f"view_{view.name}",
            )
