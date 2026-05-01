"""Abaqus INP解析パーサー（後方互換）

このモジュールはplugins.abaqus.parse.inp_parser_baseからre-exportしています。
新規コードでは plugins.abaqus.parse.inp_parser_base を直接importしてください。
"""

from plugins.abaqus.parse.inp_parser_base import (
    AbaqusInpParser,
    parse_material_blocks,
)

__all__ = [
    "AbaqusInpParser",
    "parse_material_blocks",
]
