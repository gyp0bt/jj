"""外部プラグインのテスト例

プラグインのパーサーとダッシュボードコネクターが
正しくレジストリに登録されることを検証する。
"""

from __future__ import annotations


def test_parser_registered():
    """ExampleSolverParserがパーサーレジストリに登録される"""
    # プラグインをインポート（自動登録される）
    import jj_plugin_example  # noqa: F401

    from services.parse.base import get_parser_registry

    registry = get_parser_registry()
    cls_names = [cls.__name__ for cls in registry]
    assert "ExampleSolverParser" in cls_names


def test_dashboard_connector_registered():
    """ExampleSolverPageConnectorがレジストリに登録される"""
    import jj_plugin_example  # noqa: F401

    from services.dashboard.connectors import DashboardPageConnector

    assert "Exampleサマリー" in DashboardPageConnector._registry


def test_register_is_idempotent():
    """register()は2回呼んでも問題ない"""
    import jj_plugin_example

    jj_plugin_example.register()
    jj_plugin_example.register()
    # エラーが出なければOK
