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

    def render(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_saved_view_filters

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        filtered = apply_saved_view_filters(rows, view.filters) if view.filters else list(rows)
        if not filtered:
            st.info("条件に一致するデータがありません。")
            return

        # view.plot or local_filters に "node" 指定があればそれを採用、無ければ先頭
        vn_key = provider._verbose_name_key
        target_name = view.local_filters.get("node") if view.local_filters else None
        target_row = None
        if target_name:
            target_row = next(
                (r for r in filtered if r.get(vn_key, r["name"]) == target_name or r["name"] == target_name),
                None,
            )
        if target_row is None:
            target_row = filtered[0]

        node_id = target_row.get("id")
        if node_id is None:
            return

        card = provider.get_node_card(node_id)
        if card is None:
            st.error("ノード情報を取得できませんでした。")
            return

        display_name = card["properties"].get(vn_key) or card["properties"].get("verbose_name") or card["name"]

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(display_name)
            st.markdown(f"**タイプ**: {card['type']}")
            st.markdown(f"**フォーマット**: {card['format']}")
        with col2:
            status = card["properties"].get("analysis_status", "unknown")
            status_emoji = {"completed": "✅", "failed": "❌"}.get(status, "❓")
            st.markdown(f"**ステータス**: {status_emoji} {status}")
            if "active" in card["properties"]:
                st.markdown(f"**active**: {card['properties']['active']}")

        props = {k: v for k, v in card["properties"].items() if k != "path"}
        if props:
            import pandas as pd

            props_flat = {k: (str(v) if isinstance(v, (dict, list)) else v) for k, v in props.items()}
            df = pd.DataFrame([props_flat]).T
            df.columns = ["値"]
            st.dataframe(df, width="stretch")

        relations = card.get("relations", [])
        if relations:
            st.markdown("**リレーション**")
            for rel in relations:
                direction = "→" if rel["direction"] == "outgoing" else "←"
                st.markdown(f"- {direction} **{rel['label']}** → {rel['node_name']} ({rel['node_type']})")

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_card_html

        return generate_card_html(provider, view)
