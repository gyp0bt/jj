"""ダッシュボードコネクター基盤（後方互換）

このモジュールはplugins.base.dashboardからre-exportしています。
新規コードでは plugins.base.dashboard を直接importしてください。

[READMEへ戻る](../../../../README.md)
"""

# 後方互換のためのre-export
from plugins.base.dashboard import (
    DashboardPageConnector,
    generate_connector_pages_html,
    generate_connector_saved_view_html,
    get_connector_config_schema,
    get_connector_pages,
    get_connector_view_type_options,
    render_connector,
)

__all__ = [
    "DashboardPageConnector",
    "generate_connector_pages_html",
    "generate_connector_saved_view_html",
    "get_connector_config_schema",
    "get_connector_pages",
    "get_connector_view_type_options",
    "render_connector",
]
