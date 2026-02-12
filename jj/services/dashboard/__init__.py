"""ダッシュボードデータ供給モジュール

GraphModelからダッシュボード表示用のデータを生成する。
DashboardDataProviderがテーブル/カード/プロット/ステータスの
各ビュー向け汎用データを提供する。
ソフトウェア固有ページ（例: Abaqus物性一覧）は
services/dashboard/connectors/ のコネクターとして実装される。

[READMEへ戻る](../../../README.md)
"""

from services.dashboard.data_provider import DashboardDataProvider

__all__ = ["DashboardDataProvider"]
