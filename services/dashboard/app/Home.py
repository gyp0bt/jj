"""jj ダッシュボード（Streamlit マルチページアプリのエントリ）

`streamlit run services/dashboard/app/Home.py` で起動する。
GraphModel をロードして概要メトリクスを表示し、各ページ（応力–ひずみ曲線、
画像ギャラリー）は ``pages/`` 配下のスクリプトとして提供される。

実行前に ``pip install -e ".[dashboard]"`` でUI依存（streamlit / plotly /
streamlit-aggrid / pandas）をインストールしておくこと。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from jj.services.dashboard.data_provider import DashboardDataProvider
from jj.services.graph import GraphService


@st.cache_resource
def load_provider() -> DashboardDataProvider:
    """カレントディレクトリのプロジェクトグラフからプロバイダを構築（キャッシュ）"""
    svc = GraphService()
    gm = svc.load(resolve_externalized=True)
    return DashboardDataProvider(graph=gm, project_root=Path("./"))


def main() -> None:
    st.set_page_config(
        page_title="jj Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("📊 jj Dashboard")
    st.caption(f"Project: {Path('./').resolve().name}")

    if st.sidebar.button("reload"):
        st.cache_resource.clear()
        st.rerun()

    try:
        provider = load_provider()
    except Exception as e:  # noqa: BLE001 — UI層なので例外を表示して継続
        st.error(f"グラフデータの読み込みに失敗しました: {e}")
        st.info("`jj parse` を実行してグラフデータ（.j2/storage/graph.yaml）を生成してください。")
        return

    if not provider.graph.nodes:
        st.warning("グラフデータが空です。`jj parse` を実行してください。")
        return

    status = provider.get_status_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("総ノード数", len(provider.graph.nodes))
    c2.metric("総リレーション数", len(provider.graph.relations))
    c3.metric("go_ ファイル数", status["total"])
    c4.metric("完了", status["completed"])

    st.markdown(
        "左サイドバーからページを選択してください：\n\n"
        "- **応力–ひずみ曲線** — ABQ inp ケースを絞り込み、配列データを応力–ひずみに換算してプロット\n"
        "- **画像ギャラリー** — 出力画像 / プロパティ画像をパラメータでグルーピング表示"
    )


if __name__ == "__main__":
    main()
