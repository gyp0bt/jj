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
        import streamlit as st

        st.header("カードビュー")

        rows = provider.get_go_table()
        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        # verbose_nameキー（vocab変換後）
        vn_key = provider._verbose_name_key
        # 選択肢: 表示名があればそれを使用
        display_names = [r.get(vn_key, r["name"]) for r in rows]
        selected = st.selectbox("ノード選択", display_names)

        if not selected:
            return

        # IDを取得
        node_id = next((r["id"] for r in rows if r.get(vn_key, r["name"]) == selected), None)
        if node_id is None:
            return

        card = provider.get_node_card(node_id)
        if card is None:
            st.error("ノード情報を取得できませんでした。")
            return

        # カード表示
        col1, col2 = st.columns(2)

        # 表示名を取得
        display_name = card["properties"].get(vn_key) or card["properties"].get("verbose_name") or card["name"]

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

        # プロパティ
        st.markdown("---")
        st.subheader("プロパティ")

        props = {k: v for k, v in card["properties"].items() if k != "path"}
        if props:
            import pandas as pd

            props_flat = {}
            for k, v in props.items():
                if isinstance(v, (dict, list)):
                    props_flat[k] = str(v)
                else:
                    props_flat[k] = v
            df = pd.DataFrame([props_flat]).T
            df.columns = ["値"]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("プロパティがありません。")

        # リレーション
        st.markdown("---")
        st.subheader("リレーション")
        relations = card.get("relations", [])
        if relations:
            for rel in relations:
                direction = "→" if rel["direction"] == "outgoing" else "←"
                st.markdown(f"- {direction} **{rel['label']}** → {rel['node_name']} ({rel['node_type']})")
        else:
            st.info("リレーションがありません。")

    def render_saved_view(
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

        # 保存済みフィルタを適用
        filtered = apply_saved_view_filters(rows, view.filters)
        if not filtered:
            st.info("条件に一致するデータがありません。")
            return

        # 先頭のノードをカード表示
        first_row = filtered[0]
        node_id = first_row.get("id")
        if node_id is None:
            return

        card = provider.get_node_card(node_id)
        if card is None:
            return

        st.markdown(f"**{card['name']}** ({card['type']})")
        props = {k: v for k, v in card["properties"].items() if k != "path"}
        if props:
            import pandas as pd

            props_flat = {}
            for k, v in props.items():
                if isinstance(v, (dict, list)):
                    props_flat[k] = str(v)
                else:
                    props_flat[k] = v
            df = pd.DataFrame([props_flat]).T
            df.columns = ["値"]
            st.dataframe(df, use_container_width=True)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_card_html

        return generate_card_html(provider, view)
