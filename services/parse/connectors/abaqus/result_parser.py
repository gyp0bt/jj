"""Abaqus結果パーサー（後方互換）

このモジュールはplugins.abaqus.parse.result_parserからre-exportしています。
新規コードでは plugins.abaqus.parse.result_parser を直接importしてください。
"""

from plugins.abaqus.parse.result_parser import (
    AbaqusResultParser,
    _parse_convergence_info,
    parse_dat_file,
    parse_msg_file,
    parse_sta_file,
)

__all__ = [
    "AbaqusResultParser",
    "_parse_convergence_info",
    "parse_dat_file",
    "parse_msg_file",
    "parse_sta_file",
]
