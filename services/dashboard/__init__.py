"""ダッシュボードデータ供給モジュール (jj-dashboard)

GraphModelからダッシュボード表示用のデータを生成する。
DashboardDataProviderがテーブル/カード/プロット/ステータスの
各ビュー向け汎用データを提供する。
ソフトウェア固有ページ（例: Abaqus物性一覧）は
services/dashboard/connectors/ のコネクターとして実装される。

## 分離境界

本モジュールはjjコアから分離可能な設計:
- **必須依存**: jj_types, config（jjコア）
- **UI依存**: streamlit, plotly, streamlit-aggrid（オプショナル）
- **データ層**: DashboardDataProvider（jj_typesのみに依存、UI非依存）
- **UI層**: app.py, widgets.py, html_export.py（Streamlit依存）
- **コネクター**: connectors/（DashboardPageConnector SDK経由）

将来的にjj-dashboardパッケージとして分離する場合:
- DashboardDataProvider + connectors基盤 はjjコアに残す
- app.py / widgets.py / html_export.py をjj-dashboardに移動
- CLI launchers.pyのdashboard起動ロジックもjj-dashboardに移動

[READMEへ戻る](../../../README.md)
"""

from services.dashboard.data_provider import DashboardDataProvider

__all__ = ["DashboardDataProvider"]

# オプショナル依存関係の定義
OPTIONAL_DEPS = {
    "ui": ["streamlit>=1.30.0", "plotly>=5.0.0"],
    "aggrid": ["streamlit-aggrid>=1.0.0"],
    "excel": ["openpyxl>=3.0.0"],
}
