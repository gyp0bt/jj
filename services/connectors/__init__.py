"""コネクタモジュール: 外部ツールへのエクスポート機能

このモジュールはグラフデータを外部ツール向けにエクスポートする
コネクタを提供します。

- Obsidian: マークダウンファイルとして出力
- Neo4j: （将来実装予定）

[READMEへ戻る](../../../README.md)
"""

from .obsidian import ObsidianConnector, ObsidianConfig

__all__ = ["ObsidianConnector", "ObsidianConfig"]
