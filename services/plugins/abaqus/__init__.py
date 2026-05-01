"""Abaqusプラグイン（後方互換）

このモジュールはplugins.abaqusからre-exportしています。
新規コードでは plugins.abaqus を直接importしてください。

[READMEへ戻る](../../../../README.md)
"""

# 後方互換のためのre-export
from plugins.abaqus import register

__all__ = ["register"]
