"""Abaqus *PARAMETERパーサー（後方互換）

このモジュールはplugins.abaqus.parse.parameter_parserからre-exportしています。
新規コードでは plugins.abaqus.parse.parameter_parser を直接importしてください。
"""

from plugins.abaqus.parse.parameter_parser import (
    AbaqusParameterParser,
    _resolve_param_references,
)

__all__ = [
    "AbaqusParameterParser",
    "_resolve_param_references",
]
