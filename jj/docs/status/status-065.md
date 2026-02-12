[READMEへ戻る](../../README.md)

# status-065: エクスポートロジック統一・CLI レジストリディスパッチ・Obsidianプラグイン構成

**日付**: 2026-02-11

## 実施内容

### 1. CLI `_run_export()` レジストリ経由統一化

- `_run_export()` を if/elif チェーン（target別分岐）からレジストリ経由の統一ディスパッチに変更
- 旧来の `_print_export_obsidian()`, `_print_export_data()`, `_print_export_neo4j()`, `_print_export_dashboard_json()` の4関数を廃止
- 新関数 `_build_export_kwargs(target, args)` で形式ごとのCLIオプション→kwargsマッピングを集約
- エクスポーターの `format_cli_result()` メソッドでCLI出力整形を委譲

### 2. AbstractExporter.format_cli_result() メソッド追加

- `AbstractExporter` 基底クラスにデフォルトの `format_cli_result()` を追加
- 各エクスポーター（CsvExporter, JsonExporter, ObsidianExporter, Neo4jExporter, CypherExporter, DashboardJsonExporter）にオーバーライド実装
- CLI出力のフォーマットをエクスポーター自身に委譲する設計

### 3. GraphCommandService.export_unified() メソッド追加

- 全エクスポート形式を統一パイプラインで処理する新メソッド
- CSV/JSON: `_prepare_data_export_kwargs()` で共通選択オプション（-id, -v等）の事前ノード絞り込みを処理
- dashboard-json: config設定（vocab, units）を自動注入
- 既存の `export_by_format()` は後方互換のため残存

### 4. Obsidianサマリーノート（jj-summary.md）生成

- `ObsidianConnector._write_summary_note()` を追加
- プロジェクト概要（タイプ別ノード数、総統計）をテーブル表示
- Dataviewクエリによる全ファイル一覧・タイプ別セクション
- Canvas ファイルへのリンク
- `export_graph()` 実行時に自動生成（ノードがある場合のみ）

### 5. Obsidianプラグイン構成ドキュメント

- `docs/specs/08-export.md` を全面改訂
- セクション6「Obsidian推奨プラグイン構成」を新設
  - 必須プラグイン: Dataview, DB Folder
  - 推奨プラグイン: Templater, Tag Wrangler, Graph Analysis
  - Vault初期セットアップ手順
  - Dataviewクエリ例

### 6. テスト

- 新テスト12件追加:
  - `TestFormatCliResult`: 各エクスポーターのformat_cli_result()テスト（5件）
  - `TestExportUnified`: export_unified()の統一パイプラインテスト（4件）
  - `TestObsidianSummaryNote`: サマリーノート生成テスト（3件）
- 既存テスト修正: `test_export_graph`, `test_props_always_overwritten`（サマリーノート追加に伴う件数変更）
- **結果: 693テストパス、21スキップ**

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| services/export/__init__.py | format_cli_result()メソッド追加 |
| services/export/connectors/csv_json.py | CsvExporter/JsonExporterにformat_cli_result() |
| services/export/connectors/neo4j.py | Neo4jExporter/CypherExporterにformat_cli_result() |
| services/export/connectors/dashboard_json.py | DashboardJsonExporterにformat_cli_result() |
| services/export/connectors/obsidian/__init__.py | ObsidianExporter.format_cli_result(), _write_summary_note() |
| services/service/graph_command.py | export_unified(), _prepare_data_export_kwargs() |
| services/cli/graph.py | _run_export()統一化、_build_export_kwargs()、旧4関数廃止 |
| docs/specs/08-export.md | 全面改訂（プラグイン構成セクション追加） |
| tests/test_parser_units.py | 12テスト追加 |
| tests/test_obsidian_connector.py | 既存テスト修正（サマリーノート対応） |

## アーキテクチャ

### エクスポートパイプライン（統一後）

```
CLI _run_export()
  → _build_export_kwargs(target, args)  ← 形式別kwargs構築
  → service.export_unified(graph, target, **kwargs)
      → get_exporter_for_format(target) → exporter_cls
      → (CSV/JSON) _prepare_data_export_kwargs() → ノード事前選択
      → (dashboard-json) config自動注入
      → exporter.export(graph, **kwargs) → result
  → exporter.format_cli_result(result, project_root) → CLI出力
```

### エクスポーター一覧

| priority | format | クラス | format_cli_result |
|----------|--------|--------|-------------------|
| 10 | csv | CsvExporter | ✅ |
| 11 | json | JsonExporter | ✅ |
| 20 | obsidian | ObsidianExporter | ✅ |
| 30 | neo4j | Neo4jExporter | ✅ |
| 31 | cypher | CypherExporter | ✅ |
| 40 | dashboard-json | DashboardJsonExporter | ✅ |

## TODO / 次回引き継ぎ事項

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] `export_obsidian()`, `export_data()`, `export_neo4j()` 等の旧メソッドは後方互換のため残存。APIユーザーがいなければ将来削除候補。
- [ ] GraphML エクスポーター（仕様書に記載あるが未実装）
