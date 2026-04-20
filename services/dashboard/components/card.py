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
        """カードページを対話UIで描画する（旧 render_page 相当）"""
        import streamlit as st

        from services.dashboard.query import apply_saved_view_filters
        from services.dashboard.widgets import get_active_filters, render_shared_filters

        st.header("カードビュー")

        all_rows = provider.get_go_table()
        if not all_rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # 共有フィルタ（サイドバー描画）
        render_shared_filters(all_rows)
        active_filters = get_active_filters()

        # 1) サイドバーフィルタはprovider側で効かせる
        rows = provider.get_go_table(filters=active_filters) if active_filters else all_rows
        # 2) view.filters（保存済み）をさらに重ねる
        filtered = apply_saved_view_filters(rows, view.filters) if view.filters else list(rows)

        if not filtered:
            st.info("条件に一致するデータがありません。")
            return

        vn_key = provider._verbose_name_key
        display_names = [r.get(vn_key, r["name"]) for r in filtered]

        # view.local_filters["node"] を初期値に採用
        default_node = view.local_filters.get("node") if view.local_filters else None
        default_idx = 0
        if default_node and default_node in display_names:
            default_idx = display_names.index(default_node)

        selected = st.selectbox(
            "ノード選択",
            display_names,
            index=default_idx,
            key=f"_card_node_{view.name}",
        )
        if not selected:
            return

        node_id = next((r["id"] for r in filtered if r.get(vn_key, r["name"]) == selected), None)
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

        st.markdown("---")
        st.subheader("プロパティ")
        props = {k: v for k, v in card["properties"].items() if k != "path"}
        if props:
            import pandas as pd

            props_flat = {k: (str(v) if isinstance(v, (dict, list)) else v) for k, v in props.items()}
            df = pd.DataFrame([props_flat]).T
            df.columns = ["値"]
            st.dataframe(df, width="stretch")
        else:
            st.info("プロパティがありません。")

        st.markdown("---")
        st.subheader("リレーション")
        relations = card.get("relations", [])
        if relations:
            for rel in relations:
                direction = "→" if rel["direction"] == "outgoing" else "←"
                st.markdown(f"- {direction} **{rel['label']}** → {rel['node_name']} ({rel['node_type']})")
        else:
            st.info("リレーションがありません。")

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_card_html

        return generate_card_html(provider, view)
