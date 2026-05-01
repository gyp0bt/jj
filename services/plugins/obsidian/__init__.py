"""Obsidianプラグイン（後方互換）

このモジュールはplugins.obsidianからre-exportしています。
新規コードでは plugins.obsidian を直接importしてください。

[READMEへ戻る](../../../../README.md)
"""

# 後方互換のためのre-export
from plugins.obsidian import register

__all__ = ["register"]
