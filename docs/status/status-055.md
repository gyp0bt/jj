[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-055: T1 #2 list[str]関数化・T2 Config migrate完了

- **日付**: 2026-03-07
- **マイルストーン**: v0.3.0 Phase A（T1, T2）
- **ブランチ**: `claude/execute-status-todos-pCe1c`

---

## 概要

status-054のTODOを実行。T1 #2（list[str]パースのconfig対応+関数化）とT2残作業（migrateコマンド・legacy非推奨化）を完了:

1. **T1 #2: list[str]パースのconfig対応+関数化**: table.pyのハードコードされたmsg_errors/dat_errors処理を`services/query/transform.py`に`summarize_list_value/summarize_list_columns`として抽出。DashboardConfigに`list_summary_columns`属性を追加しconfig経由で制御可能に。
2. **T2: jj config migrateコマンド**: extensions.yaml/prefixes.yamlのデフォルトとの差分を検出しconfig.yamlに統合するCLIコマンドを実装。`--check`オプションで差分確認のみも可能。
3. **T2: legacy config非推奨化**: `load_extensions_config`/`load_prefixes_config`にDeprecationWarning追加。default-config.yamlに移行ガイドコメント追加。

## 変更内容

### 1. T1 #2: list[str]パースのconfig対応+関数化

| ファイル | 変更 |
|---------|------|
| `services/query/transform.py` | `summarize_list_value()`/`summarize_list_columns()`関数追加 |
| `services/query/__init__.py` | transform関数を公開APIに追加 |
| `services/dashboard/query.py` | `summarize_list_columns`を再エクスポート |
| `services/dashboard/components/table.py` | インライン処理を`summarize_list_columns()`呼び出しに置換。config経由でカラム名取得 |
| `config/__init__.py` | `DashboardConfig`に`list_summary_columns: list[str]`属性追加 |
| `shared/assets/default-config.yaml` | `list-summary-columns`のコメント追加 |
| `tests/test_query.py` | `TestSummarizeListValue`(10件) + `TestSummarizeListColumns`(4件) 追加 |
| `tests/test_dashboard.py` | `TestDashboardConfig`に3テスト追加 |

### 2. T2: jj config migrateコマンド

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | `migrate_legacy_configs()`関数追加 |
| `services/cli/__init__.py` | `config`コマンドをディスパッチに追加 |
| `services/cli/graph.py` | `jj config migrate`サブコマンド追加（`--check`オプション対応） |
| `tests/config/test_config_loader.py` | `TestMigrateLegacyConfigs`クラス追加（7テスト） |

### 3. T2: legacy config非推奨化

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | `load_extensions_config`/`load_prefixes_config`にDeprecationWarning追加 |
| `shared/assets/default-config.yaml` | 非推奨コメントと移行ガイド追加 |
| `tests/config/test_config_loader.py` | DeprecationWarning発行テスト追加 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: All files formatted
- **pytest**: 全テスト通過（pymeshインポートテストは環境依存でスキップ）
- **新規テスト**: +24件

## v0.3.0 ワークトラック進捗

| トラック | 状態 | 今回の進捗 |
|---------|------|-----------|
| **T1: コードベースTODO解消** | 進行中 | #2（list[str]パース関数化+config対応）完了 |
| **T2: Config二層分離** | **完了** | migrateコマンド・legacy非推奨化完了 |
| **T3: M6 Phase 5 MLダッシュボード** | 未着手 | — |
| **T4: Deprecation Warning修正** | 完了 | — |
| **T5: リモートジョブ実行基盤** | 未着手 | — |
| **T6: ダッシュボード高度化** | 進行中 | — |
| **T7: Ollama AI連携** | 未着手 | — |
| **T8: 汎用データ管理** | 未着手 | — |

## TODO

- [ ] T1 #5: Abaqus parameter式評価（仕様確認後実装）
- [ ] T1 #6: Abaqus収束情報の収集
- [ ] T6-2: AgGridフィルタ共有
- [ ] T6-3: グラフ可視化美化
- [ ] status-052 TODO: Run DAG可視化, Run比較HTMLエクスポート, Runフィルタ保存 → T6と連動
- [ ] pymeshインポートテスト失敗の調査（CI環境でのモジュールパス問題）

## 確認事項・懸念

- `jj config migrate`は差分のみをconfig.yamlにマージする設計。既存config.yamlの内容は保持される
- DeprecationWarningはlegacyファイルが存在する場合のみ発行。新規プロジェクトでは出ない
- `list_summary_columns`のデフォルト値は`["msg_errors", "dat_errors"]`。configで空リストを設定すれば無効化可能

## 開発運用メモ

- **効果的**: status-054のTODOを上から順に実行する方式で、作業の優先順位が明確
- **効果的**: T2の段階的完了（config化→migrate→非推奨化）で全体の整合性を保ちながら進められた
