"""Obsidian Dailyパーサー（後方互換）

このモジュールはplugins.obsidian.parse.daily_parserからre-exportしています。
新規コードでは plugins.obsidian.parse.daily_parser を直接importしてください。
"""

from plugins.obsidian.parse.daily_parser import DailyNoteParser

__all__ = ["DailyNoteParser"]
