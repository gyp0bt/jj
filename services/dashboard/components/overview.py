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

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_filters, sort_rows_by_index
        from services.dashboard.widgets import get_active_filters, render_shared_filters

        vocab = kwargs.get("vocab") or {}
        project_root = kwargs.get("project_root")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # 共有フィルタ（サイドバー描画 + 適用）
        render_shared_filters(rows)

        filtered = apply_filters(
            rows,
            type_filter=st.session_state.get("_filter_type", "すべて"),
            status_filter=st.session_state.get("_filter_status", "すべて"),
            active_only=st.session_state.get("_filter_active", False),
            vocab=vocab,
        )

        idx_key = provider._index_key
        ver_key = provider._version_key
        filtered = sort_rows_by_index(filtered, idx_key, ver_key)

        # --- テーブルセクション ---
        st.subheader("テーブル")
        from services.dashboard.components.table import render_table_section

        render_table_section(
            provider,
            dashboard_config,
            filtered,
            len(rows),
            vocab=vocab,
            grid_key="overview_table",
            download_key="overview_table",
        )

        st.divider()

        # --- ギャラリーセクション ---
        if project_root is not None:
            st.subheader("ギャラリー")
            from services.dashboard.components.gallery import render_gallery_section

            active_filters = get_active_filters()
            render_gallery_section(
                provider,
                dashboard_config,
                Path(project_root),
                active_filters=active_filters,
                show_header=False,
                key_prefix="overview",
            )

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_saved_view_filters

        vocab = kwargs.get("vocab") or {}
        project_root = kwargs.get("project_root")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        filtered = apply_saved_view_filters(rows, view.filters)

        # テーブルセクション
        st.subheader("テーブル")
        from services.dashboard.components.table import render_table_section

        render_table_section(
            provider,
            dashboard_config,
            filtered,
            len(rows),
            vocab=vocab,
            grid_key=f"saved_view_{view.name}_table",
            download_key=f"saved_view_{view.name}",
        )

        st.divider()

        # ギャラリーセクション
        if project_root is not None:
            st.subheader("ギャラリー")
            from services.dashboard.components.gallery import render_gallery_section

            render_gallery_section(
                provider,
                dashboard_config,
                Path(project_root),
                show_header=False,
                key_prefix=f"sv_{view.name}",
            )
