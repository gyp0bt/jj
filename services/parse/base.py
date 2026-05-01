"""パーサー基盤モジュール（後方互換）

このモジュールはplugins.base.parserからre-exportしています。
新規コードでは plugins.base.parser を直接importしてください。

[READMEへ戻る](../../../README.md)
"""

# 後方互換のためのre-export
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
    _group_parsers_by_priority,
    _parse_prop_token,
    _run_parser_group_parallel,
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
    "AbstractFileParser",
    "FileGroup",
    "FileNameParser",
    "FileType",
    "_group_parsers_by_priority",
    "_parse_prop_token",
    "_run_parser_group_parallel",
    "clear_parser_registry",
    "get_parser_registry",
    "parse",
]
