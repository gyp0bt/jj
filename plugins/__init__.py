"""jjプラグインSDK

プラグイン開発に必要な基底クラスと関数をre-exportする。

## 基底クラス

- AbstractFileParser: グラフエンリッチメント用パーサー基底クラス
- AbstractExporter: グラフエクスポート用基底クラス
- DashboardPageConnector: ダッシュボードページコネクター基底クラス

## プラグイン構造

```
plugins/
├── base/                   # 基底クラス群
│   ├── parser.py           # AbstractFileParser
│   ├── dashboard.py        # DashboardPageConnector
│   └── exporter.py         # AbstractExporter
├── abaqus/                 # Abaqusプラグイン
│   ├── parse/              # パーサー群
│   ├── dashboard.py        # ダッシュボード
│   └── submit.py           # ジョブ投入
└── obsidian/               # Obsidianプラグイン
    ├── parse/              # パーサー群
    └── export.py           # エクスポーター
```

[READMEへ戻る](../README.md)
"""

from plugins.base import (
    AbstractExporter,
    AbstractFileParser,
    DashboardPageConnector,
    FileGroup,
    FileNameParser,
    FileType,
    clear_exporter_registry,
    clear_parser_registry,
    generate_connector_pages_html,
    generate_connector_saved_view_html,
    get_connector_config_schema,
    get_connector_pages,
    get_connector_view_type_options,
    get_exporter_for_format,
    get_exporter_registry,
    get_parser_registry,
    parse,
    render_connector,
)

__all__ = [
    "AbstractExporter",
    "AbstractFileParser",
    "DashboardPageConnector",
    "FileGroup",
    "FileNameParser",
    "FileType",
    "clear_exporter_registry",
    "clear_parser_registry",
    "generate_connector_pages_html",
    "generate_connector_saved_view_html",
    "get_connector_config_schema",
    "get_connector_pages",
    "get_connector_view_type_options",
    "get_exporter_for_format",
    "get_exporter_registry",
    "get_parser_registry",
    "parse",
    "render_connector",
]
