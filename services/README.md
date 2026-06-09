[READMEへ戻る](../README.md)

# services

`jj` CLI の本体ロジック。各サブパッケージは責務を一つに絞り、依存方向は
`cli → service → graph/parse/export/...` の一方向に保つ。

## 構成

| パッケージ | 責務 |
|-----------|------|
| `cli/` | CLIエントリポイント（`jj = services.cli:main`）。argparse解析と出力整形のみ。ロジックは持たず `service/` に委譲する。サブコマンドは `cli/commands.py` の `COMMANDS` レジストリ（`name → add_args → handler` の1表）で宣言的に定義し、`cli/__init__.py` の `build_parser`/`dispatch` はこの表だけを見る |
| `service/` | CLIコマンドのビジネスロジック。`GraphCommandService`（init/parse/show/export/info/diff/credential/config）と `InfoService` |
| `graph/` | `GraphService`（`.j2/storage/` への保存・読込）と `ProjectGraph`（パイプライン用グラフ型）、`query/`（`GraphQuery` データ供給層） |
| `parse/` | パーサーパイプライン共通基盤と組み込みパーサー（`parsers/`）。プラグインパーサーは `plugins/*/parse/` に分散 |
| `export/` | エクスポーター共通基盤（`AbstractExporter`）と組み込みコネクター |
| `dashboard/` | Streamlit UI（`widgets.py` + `app/`）。データ層は `graph/query/` に統合済み |
| `lib/` | 薄いユーティリティ（`selection`, `credentials`） |
| `sdk/` | プラグインSDK（cache, plugin manifest/registry, entry_points 検出） |

## 依存ルール

- `cli` は `service` 以外からロジックをimportしない。CLI層でロジックを実装しない。
- `parse` / `graph` / `export` は互いの責務を重複させず、横断的な連携は `service` 経由で行う。

## CLIコマンド → service 対応

| コマンド | CLIハンドラ（`cli/graph.py`） | service |
|---------|------------------------------|---------|
| `jj init` | `_run_init` | `GraphCommandService.init_config` |
| `jj parse` | `_run_parse` | `GraphCommandService.parse` + `GraphService` |
| `jj show` | `_run_show` | `GraphCommandService.show` |
| `jj export` | `_run_export` | `GraphCommandService.export_unified` / `export_by_format` |
| `jj info` | `_run_info` | `GraphCommandService.info`（内部で `InfoService`） |
| `jj diff` | `_run_diff` | `GraphCommandService.diff` |
| `jj credential` | `_run_credential` | `GraphCommandService.credential_*` |
| `jj config migrate` | `_run_config_migrate` | `config.migrate_legacy_configs` |
