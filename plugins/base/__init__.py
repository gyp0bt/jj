"""プラグイン基底クラス群

AbstractFileParser, AbstractExporter, DashboardPageConnector等の基底クラスと
レジストリ関数を提供する。

[READMEへ戻る](../../README.md)
"""

from plugins.base.dashboard import (
    DashboardPageConnector,
    generate_connector_pages_html,
    generate_connector_saved_view_html,
    get_connector_config_schema,
    get_connector_pages,
    get_connector_view_type_options,
    render_connector,
)
from plugins.base.exporter import (
    AbstractExporter,
    clear_exporter_registry,
    get_exporter_for_format,
    get_exporter_registry,
)
from plugins.base.parser import (
    DATE_PATTERN,
    DEFAULT_EXTENSIONS,
    FILE_TYPE_PREFIXES,
    IMPLICIT_TYPE_BASENAMES,
    NO_NODE_EXTENSIONS,
    AbstractFileParser,
    FileGroup,
    FileNameParser,
    FileType,
    _parse_prop_token,
    clear_parser_registry,
    get_parser_registry,
    parse,
)

__all__ = [
    "DATE_PATTERN",
    "DEFAULT_EXTENSIONS",
    "FILE_TYPE_PREFIXES",
    "IMPLICIT_TYPE_BASENAMES",
    "NO_NODE_EXTENSIONS",
    "AbstractExporter",
    "AbstractFileParser",
    "DashboardPageConnector",
    "FileGroup",
    "FileNameParser",
    "FileType",
    "_parse_prop_token",
    "clear_exporter_registry",
    "clear_parser_registry",
    "generate_connector_pages_html",
    "generate_connector_saved_view_html",
    "get_connector_config_schema",
    "get_connector_pages",
    "get_connector_view_type_options",
    "get_exporter_for_format",
    "get_exporter_registry",
    "get_parser_registry",
    "parse",
    "render_connector",
]
