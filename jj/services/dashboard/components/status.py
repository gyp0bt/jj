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
        self._render_status(provider)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        self._render_status(provider)

    def _render_status(self, provider: DashboardDataProvider) -> None:
        """ステータスモニター: 実行ステータス一覧"""
        import streamlit as st

        st.header("ステータスモニター")

        status = provider.get_status_summary()

        # サマリーメトリクス
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("合計", status["total"])
        col2.metric("完了", status["completed"])
        col3.metric("失敗", status["failed"])
        col4.metric("不明", status["unknown"])

        st.markdown("---")

        items = status["items"]
        if not items:
            st.info("go_ ファイルが見つかりません。")
            return

        # 統計量プロット
        self._render_statistics(status)

        st.markdown("---")

        # ステータス別に分類
        completed_items = [i for i in items if i["analysis_status"] == "completed"]
        failed_items = [i for i in items if i["analysis_status"] == "failed"]
        unknown_items = [i for i in items if i["analysis_status"] not in ("completed", "failed")]

        if failed_items:
            st.subheader("失敗")
            import pandas as pd

            df = pd.DataFrame(failed_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

        if unknown_items:
            st.subheader("不明 / 実行中")
            import pandas as pd

            df = pd.DataFrame(unknown_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

        if completed_items:
            st.subheader("完了")
            import pandas as pd

            df = pd.DataFrame(completed_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

    @staticmethod
    def _render_statistics(status: dict[str, Any]) -> None:
        """統計量プロット: CPU時間分布・警告件数分布"""
        import streamlit as st

        cpu_stats = status.get("cpu_stats", {})
        warning_stats = status.get("warning_stats", {})

        if not cpu_stats and not warning_stats:
            return

        st.subheader("統計量")

        # CPU時間統計
        if cpu_stats and cpu_stats.get("values"):
            import pandas as pd

            col_chart, col_summary = st.columns([2, 1])

            with col_chart:
                st.caption("CPU時間分布")
                df_cpu = pd.DataFrame({"cpu_time": cpu_stats["values"]})
                st.bar_chart(df_cpu["cpu_time"].value_counts().sort_index())

            with col_summary:
                st.caption("CPU時間サマリー")
                st.metric("件数", cpu_stats["count"])
                st.metric("最小", f"{cpu_stats['min']:.1f}")
                st.metric("最大", f"{cpu_stats['max']:.1f}")
                st.metric("平均", f"{cpu_stats['mean']:.1f}")

        # 警告件数統計
        if warning_stats and warning_stats.get("values"):
            import pandas as pd

            col_chart, col_summary = st.columns([2, 1])

            with col_chart:
                st.caption("警告件数分布")
                df_warn = pd.DataFrame({"warnings": warning_stats["values"]})
                st.bar_chart(df_warn["warnings"].value_counts().sort_index())

            with col_summary:
                st.caption("警告サマリー")
                st.metric("解析数", warning_stats["count"])
                st.metric("警告総数", warning_stats["total"])

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_status_html

        return generate_status_html(provider)
