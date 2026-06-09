"""Obsidianプラグイン: Daily Note解析・Obsidianエクスポート

Obsidian固有のパーサー・エクスポーターを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| DailyNoteParser | 95 | Obsidian Daily Noteからのファイル参照・プロパティ・タグ抽出 |

## 登録されるエクスポーター（AbstractExporterサブクラス）

| エクスポーター | format | 説明 |
|---------------|--------|------|
| ObsidianExporter | obsidian | Obsidianマークダウン・Canvas・Vault設定出力 |

## コアモジュール

- plugins.obsidian.parse.daily_parser: DailyNoteParser
- plugins.obsidian.parse.daily: daily note解析ユーティリティ
- plugins.obsidian.export: ObsidianWriter, ObsidianExporter

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import logging

from services.sdk.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_registered = False


def register() -> PluginManifest | None:
    """Obsidianプラグインの全コンポーネントを登録する

    __init_subclass__パターンにより、モジュールをimportするだけで
    各パーサー・エクスポーターがレジストリに自動登録される。
    PluginManifest を返すことで PluginManager がメタデータを管理する。
    """
    global _registered
    if _registered:
        return None
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import plugins.obsidian.parse.daily_parser

    # エクスポーターのインポート（自動登録が発動）
    exporters: list[str] = []
    try:
        import plugins.obsidian.export  # noqa: F401

        exporters.append("plugins.obsidian.export")
    except ImportError:
        logger.debug("Obsidianエクスポーターのロードをスキップ（依存パッケージ不足）")

    logger.debug("Obsidianプラグインを登録完了")

    return PluginManifest(
        name="obsidian",
        version="0.2.1",
        description="Obsidian Daily Note解析・Obsidianエクスポート",
        parsers=[
            "plugins.obsidian.parse.daily_parser",
        ],
        exporters=exporters,
    )


# モジュールインポート時に自動登録
register()
