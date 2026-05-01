"""Abaqus INPパーサー（後方互換）

このモジュールはplugins.abaqus.parse.inp_parserからre-exportしています。
新規コードでは plugins.abaqus.parse.inp_parser を直接importしてください。
"""

from plugins.abaqus.parse.inp_parser import (
    AbaqusElsetParser,
    AbaqusKeywordParser,
    AbaqusMaterialAssignmentParser,
    parse_keyword_blocks,
)

__all__ = [
    "AbaqusElsetParser",
    "AbaqusKeywordParser",
    "AbaqusMaterialAssignmentParser",
    "parse_keyword_blocks",
]
