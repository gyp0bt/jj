"""サンプルソルバー用ダッシュボードコネクター

DashboardPageConnectorを継承してカスタムページを実装する例。
__init_subclass__により、このモジュールをインポートするだけで
コネクターレジストリに自動登録される。

実装のポイント:
- page_label: サイドバーに表示されるページ名
- connector_key: DashboardConfigのconnectors設定で参照されるキー
- is_available(): グラフデータにこのページが必要なデータがあるか判定
- render(provider, view, dashboard_config): Streamlitで描画（streamlit依存）。
  すべての表示状態は view (SavedViewConfig) 経由で受け取る。
- generate_html(): HTMLエクスポート（streamlit非依存）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.sdk import DashboardPageConnector

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


class ExampleSolverPageConnector(DashboardPageConnector):
    """サンプルソルバー固有ページ

    example_parsed=Trueのノードが存在する場合に
    「Exampleサマリー」ページを提供する。
    """

    page_label = "Exampleサマリー"
    connector_key = "example_solver"

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """exampleパース済みノードが存在するか判定"""
        return any(n.properties.get("example_parsed") for n in provider.graph.nodes)

    def render(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        """Exampleサマリーページをレンダリング"""
        _ = view  # この例ではviewの設定は使わない
        import streamlit as st

        st.header("Exampleサマリー")

        example_nodes = [n for n in provider.graph.nodes if n.properties.get("example_parsed")]

        if not example_nodes:
            st.info("Exampleデータが見つかりません。")
            return

        import pandas as pd

        rows = []
        for n in example_nodes:
            rows.append(
                {
                    "ノード名": n.name,
                    "行数": n.properties.get("example_line_count", 0),
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """ExampleサマリーのHTML断片を生成"""
        import pandas as pd

        example_nodes = [n for n in provider.graph.nodes if n.properties.get("example_parsed")]

        if not example_nodes:
            return "<p>Exampleデータが見つかりません。</p>"

        rows = []
        for n in example_nodes:
            rows.append(
                {
                    "ノード名": n.name,
                    "行数": n.properties.get("example_line_count", 0),
                }
            )

        df = pd.DataFrame(rows)
        return f"<h3>Exampleサマリー</h3>\n{df.to_html(index=False, classes='dataframe')}"
