"""ダッシュボードデータ供給モジュール

GraphModelからダッシュボード表示用のデータを生成する薄い層。
- **データ層**: `DashboardDataProvider`（jj_types/services.graph.query のみに依存、UI非依存）
- **UI層**: `widgets`（streamlit / streamlit-aggrid 依存、遅延import）
- **Streamlitアプリ**: `app/`（`streamlit run` で起動するページ群）

UI依存（streamlit, plotly, streamlit-aggrid, pandas）は optional-dependencies の
`dashboard` グループに分離されており、`DashboardDataProvider` 自体はコア依存のみで動作する。

[READMEへ戻る](../../README.md)
"""

from services.dashboard.data_provider import DashboardDataProvider

__all__ = ["DashboardDataProvider"]
