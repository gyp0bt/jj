"""AIアシスタント ダッシュボードページ (T7-6)

AIサービス（Tips表示・RAG検索・ファイル要約・チャット）を
ダッシュボード上で利用するためのコネクター。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.connectors import DashboardPageConnector

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


def _is_ai_configured() -> bool:
    """AIプロバイダが設定済みかを判定する。"""
    try:
        from config import load_project_config

        config = load_project_config()
        ai_config = config.get("ai", {})
        provider_name = ai_config.get("provider", "")
        return bool(provider_name) and provider_name != "disabled"
    except Exception:
        return False


def _init_provider() -> bool:
    """AIプロバイダを初期化する。成功時True。"""
    from services.ai import get_provider, set_provider

    if get_provider() is not None:
        return True

    try:
        from config import load_project_config
        from services.ai.provider import create_provider_from_config

        config = load_project_config()
        ai_config = config.get("ai", {})
        provider = create_provider_from_config(ai_config)
        if provider is not None:
            set_provider(provider)
            return True
    except Exception:
        pass
    return False


def _load_tips_store() -> Any:
    """TipsStoreをロードして返す。"""
    from pathlib import Path

    from services.ai.tips import TipsStore

    project_root = Path.cwd()
    tips_path = project_root / ".j2" / "storage" / "tips.json"
    store = TipsStore(storage_path=tips_path)
    store.load()
    return store


def _load_rag_index() -> Any:
    """RagIndexをロードして返す。"""
    from pathlib import Path

    from services.ai.rag import RagIndex

    project_root = Path.cwd()
    rag_path = project_root / ".j2" / "storage" / "rag_index.json"
    index = RagIndex(storage_path=rag_path)
    index.load()
    return index


class AIAssistantPageConnector(DashboardPageConnector):
    """AIアシスタントページ

    Tips表示、RAG検索、ファイル要約、チャットを統合したダッシュボードページ。
    """

    page_label = "AIアシスタント"
    connector_key = "ai"

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """AI設定が存在する場合に利用可能"""
        return _is_ai_configured()

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> None:
        """AIアシスタントページを描画"""
        import streamlit as st

        st.header("AIアシスタント")

        # プロバイダ初期化
        if not _init_provider():
            st.warning("AIプロバイダに接続できません。config.yaml の ai セクションを確認してください。")
            return

        from services.ai import get_provider

        ai_provider = get_provider()
        if ai_provider is None:
            st.warning("AIプロバイダが設定されていません。")
            return

        # ステータス表示
        available = ai_provider.available
        status_icon = "🟢" if available else "🔴"
        st.markdown(f"**プロバイダ:** {ai_provider.name} {status_icon} ({'接続中' if available else '未接続'})")

        if not available:
            st.error("AIプロバイダに接続できません。Ollamaが起動しているか確認してください。")
            return

        # タブで機能を分離
        tab_tips, tab_rag, tab_chat = st.tabs(["Tips", "RAG検索", "チャット"])

        with tab_tips:
            self._render_tips_tab()

        with tab_rag:
            self._render_rag_tab()

        with tab_chat:
            self._render_chat_tab()

    def _render_tips_tab(self) -> None:
        """Tipsタブを描画"""
        import streamlit as st

        store = _load_tips_store()
        total = store.size

        st.subheader(f"Tips ({total}件)")

        if total == 0:
            st.info("Tipsがまだありません。CLIで `jj ai tips --extract <file>` を実行して蓄積してください。")
            return

        # 検索
        search_keyword = st.text_input("キーワード検索", key="tips_search", placeholder="検索したいキーワードを入力...")

        if search_keyword:
            tips = store.search(search_keyword)
            st.caption(f"{len(tips)}件ヒット")
        else:
            tips = store.list_all()

        # Tips表示
        if not tips:
            st.info("該当するTipsがありません。")
            return

        # ページネーション
        page_size = 10
        total_pages = max(1, (len(tips) + page_size - 1) // page_size)
        page_num = st.number_input("ページ", min_value=1, max_value=total_pages, value=1, key="tips_page")
        start = (page_num - 1) * page_size
        page_tips = tips[start : start + page_size]

        for tip in page_tips:
            with st.expander(f"**{tip.get('title', '(無題)')}**"):
                st.markdown(tip.get("body", ""))
                tags = tip.get("tags", [])
                if tags:
                    st.caption(f"タグ: {', '.join(tags)}")
                source = tip.get("source", "")
                if source:
                    st.caption(f"ソース: {source}")

    def _render_rag_tab(self) -> None:
        """RAG検索タブを描画"""
        import streamlit as st

        index = _load_rag_index()

        col1, col2 = st.columns(2)
        col1.metric("インデックスエントリ数", index.size)
        col2.metric("インデックス済みファイル数", len(index.indexed_files))

        if index.indexed_files:
            with st.expander("インデックス済みファイル一覧"):
                for f in index.indexed_files:
                    st.text(f)

        st.divider()

        if index.size == 0:
            st.info("RAGインデックスが空です。CLIで `jj ai index <file>` を実行してインデックスを構築してください。")
            return

        # 質問入力
        question = st.text_input("質問を入力", key="rag_question", placeholder="プロジェクトに関する質問...")
        top_k = st.slider("検索件数 (top-k)", min_value=1, max_value=20, value=5, key="rag_topk")

        if st.button("検索", key="rag_search_btn") and question:
            with st.spinner("RAG検索中..."):
                from services.ai.rag import rag_query

                answer = rag_query(question, index, top_k=top_k)
                st.markdown("### 回答")
                st.markdown(answer)

    def _render_chat_tab(self) -> None:
        """チャットタブを描画"""
        import streamlit as st

        st.subheader("AIチャット")

        # チャット履歴管理
        if "ai_chat_history" not in st.session_state:
            st.session_state.ai_chat_history = []

        # 履歴表示
        for msg in st.session_state.ai_chat_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                st.chat_message("user").markdown(content)
            else:
                st.chat_message("assistant").markdown(content)

        # 入力
        user_input = st.chat_input("メッセージを入力...")

        if user_input:
            st.session_state.ai_chat_history.append({"role": "user", "content": user_input})
            st.chat_message("user").markdown(user_input)

            with st.spinner("回答を生成中..."):
                from services.ai import get_provider

                ai_provider = get_provider()
                if ai_provider is not None:
                    messages = list(st.session_state.ai_chat_history)
                    response = ai_provider.chat(messages)
                    st.session_state.ai_chat_history.append({"role": "assistant", "content": response})
                    st.chat_message("assistant").markdown(response)
                else:
                    st.error("AIプロバイダが利用できません。")

        # クリアボタン
        if st.session_state.ai_chat_history and st.button("履歴をクリア", key="clear_chat"):
            st.session_state.ai_chat_history = []
            st.rerun()

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """AIアシスタントのHTML断片を生成"""
        store = _load_tips_store()
        tips = store.list_all()

        if not tips:
            return "<h2>AIアシスタント</h2><p>Tipsはまだありません。</p>"

        rows = []
        for tip in tips[:50]:
            tags_str = ", ".join(tip.get("tags", []))
            rows.append(
                f"<tr><td><b>{tip.get('title', '')}</b></td><td>{tip.get('body', '')}</td><td>{tags_str}</td></tr>"
            )

        return (
            "<h2>AIアシスタント — Tips一覧</h2>"
            '<table border="1" cellpadding="4" cellspacing="0">'
            "<tr><th>タイトル</th><th>内容</th><th>タグ</th></tr>"
            + "".join(rows)
            + f"</table><p>合計: {len(tips)}件</p>"
        )
