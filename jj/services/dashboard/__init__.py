"""ダッシュボードデータ供給モジュール

GraphModelからダッシュボード表示用のデータを生成する。
DashboardDataProviderがテーブル/カード/プロット/ステータスの
各ビュー向けデータを提供する。

[READMEへ戻る](../../../README.md)
"""

from services.dashboard.data_provider import DashboardDataProvider

__all__ = ["DashboardDataProvider"]
