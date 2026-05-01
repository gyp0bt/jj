"""Abaqus差分パーサー（後方互換）

このモジュールはplugins.abaqus.parse.diff_parserからre-exportしています。
新規コードでは plugins.abaqus.parse.diff_parser を直接importしてください。
"""

from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

__all__ = ["AbaqusDiffParser"]
