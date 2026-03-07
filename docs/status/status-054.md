[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-054: T1 #1 ソートロジック関数化・T2 Config二層分離基盤

- **日付**: 2026-03-07
- **マイルストーン**: v0.3.0 Phase A（T1, T2）
- **ブランチ**: `claude/execute-status-todos-aoOqK`

---

## 概要

status-053のTODOを実行。T1 #1（ソートロジック関数化）とT2（Config二層分離）の基盤を実装:

1. **T1 #1: ソートロジック関数化**: `table.py`のインラインソートロジックを`services/query/sort.py`に`sort_rows_by_index()`として抽出。テスト6件追加。
2. **T2: GraphConfig.default_extensions追加**: `default-config.yaml`の`default-extensions`セクションをGraphConfig経由で取得可能に。
3. **T2: GraphServiceのハードコード削除**: `services/graph/__init__.py`からDEFAULT_EXTENSIONSの直接importを削除し、`config.default_extensions`経由に移行。
4. **T2: jj init最小化**: `init_config_dir()`からextensions.yaml/prefixes.yaml生成を削除。最小限のconfig.yamlテンプレートを生成する方式に変更。

## 変更内容

### 1. T1 #1: ソートロジック関数化

| ファイル | 変更 |
|---------|------|
| `services/query/sort.py` | `sort_rows_by_index(rows, idx_key, ver_key)`関数追加 |
| `services/query/__init__.py` | `sort_rows_by_index`を公開APIに追加 |
| `services/dashboard/query.py` | `sort_rows_by_index`を再エクスポート |
| `services/dashboard/components/table.py` | インラインソートロジックを`sort_rows_by_index()`呼び出しに置換 |
| `tests/test_query.py` | `TestSortRowsByIndex`クラス追加（6テスト） |

### 2. T2: Config二層分離

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | `GraphConfig`に`default_extensions: tuple[str, ...]`属性追加。`from_dict()`でdefault-extensionsセクションを読み込み（未定義時はfile_parse.pyのフォールバック使用） |
| `config/__init__.py` | `init_config_dir()`を最小化: extensions.yaml/prefixes.yaml生成削除、config.yamlテンプレート生成に変更 |
| `services/graph/__init__.py` | `DEFAULT_EXTENSIONS`のimportを削除、`self.config.default_extensions`経由に変更 |
| `services/parse/file_parse.py` | TODOコメントを更新（T2対応済み） |
| `shared/assets/default-config.yaml` | TODOコメントを更新 |
| `tests/config/test_config_loader.py` | `TestInitConfigDir`を二層config方式に更新 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: All files formatted
- **pytest**: 1608 passed, 97 skipped

## v0.3.0 ワークトラック進捗

| トラック | 状態 | 今回の進捗 |
|---------|------|-----------|
| **T1: コードベースTODO解消** | 進行中 | #1（ソートロジック関数化）完了 |
| **T2: Config二層分離** | 進行中 | default_extensions config化・init最小化完了 |
| **T3: M6 Phase 5 MLダッシュボード** | 未着手 | — |
| **T4: Deprecation Warning修正** | 完了 | — |
| **T5: リモートジョブ実行基盤** | 未着手 | — |
| **T6: ダッシュボード高度化** | 進行中 | — |
| **T7: Ollama AI連携** | 未着手 | — |
| **T8: 汎用データ管理** | 未着手 | — |

## TODO

- [ ] T1 #2: list[str]パースのconfig対応+関数化（table.py:150のmsg_errors/dat_errors処理）
- [ ] T1 #5: Abaqus parameter式評価（仕様確認後実装）
- [ ] T1 #6: Abaqus収束情報の収集
- [ ] T2 残作業: jj config migrateコマンド（既存プロジェクトのconfig差分抽出）
- [ ] T2 残作業: legacy config（extensions.yaml/prefixes.yaml）の非推奨化ドキュメント
- [ ] T6-2: AgGridフィルタ共有
- [ ] T6-3: グラフ可視化美化
- [ ] status-052 TODO: Run DAG可視化, Run比較HTMLエクスポート, Runフィルタ保存 → T6と連動

## 確認事項・懸念

- `GraphConfig.from_dict()`にdefault-extensionsが未指定の場合、`services.parse.file_parse.DEFAULT_EXTENSIONS`をフォールバックとして使用。循環import回避のためfrom_dict内でlazy importしている
- legacy config（extensions.yaml, prefixes.yaml）は引き続き動作する。`load_extensions_config`/`load_prefixes_config`のフォールバック機構は維持
- `init_config_dir()`の変更は新規プロジェクトのみに影響。既存プロジェクトの.j2/config/は変更されない

## 開発運用メモ

- **効果的**: T1 #1のような小さなリファクタリングは即時実行可能で、テスト数も単調増加（+6）
- **効果的**: T2の段階的実装（まずdefault_extensions公開→GraphService移行→init最小化）により、各ステップでテストが通ることを確認しながら進められた
