[← status-index.md](status-index.md) | [← README.md](../../../README.md)

# status-046: Run-Propertyトレーサビリティ・Vocab表示時適用・Config classification仕様

- **日付**: 2026-03-06
- **マイルストーン**: M7（Run中心スキーマ）/ M2（基盤改善）
- **ブランチ**: `claude/track-feature-implementation-UCgLX`

---

## 概要

status-045の追加TODOを実行し、3つの大きな変更を実施:

1. **Run-Propertyトレーサビリティ**: Run↔Property双方向追跡機能を実装
2. **Vocab表示時適用**: VocabFinalizer廃止、parse時に生キーを保存し表示時のみvocab変換する設計に変更
3. **Config classification仕様書**: ハードコード値のconfig class集約の仕様書を策定

## 変更内容

### 1. Run-Propertyトレーサビリティ

| ファイル | 変更 |
|---------|------|
| `services/run/query.py` | `PropertyTrace`, `RunPropertySummary` データクラス追加。`get_run_properties()`, `get_property_source_runs()`, `get_run_property_summary()`, `find_runs_by_property()` メソッド追加 |
| `tests/test_run_centric_schema.py` | `TestRunPropertyTraceability` テストクラス（10テスト）追加 |
| `docs/specs/run-property-traceability.md` | 仕様書新規作成 |

**機能**:
- `get_run_properties(run)`: Run→Property方向。Runの出力ノードからプロパティ一覧を取得
- `get_property_source_runs(node)`: Property→Run方向。ノードのプロパティの生成元Runを逆引き
- `get_run_property_summary(run)`: Runのプロパティ生成サマリー
- `find_runs_by_property(key, value)`: プロパティキー(+値)からRunを検索

### 2. Vocab表示時適用（大規模リファクタリング）

| ファイル | 変更 |
|---------|------|
| `modules/vocab_display.py` | **新規**: 表示時vocab変換ユーティリティ |
| `services/parse/parsers/vocab_finalizer.py` | apply()を空操作に変更 |
| `services/parse/parsers/display_name_parser.py` | 生キーベースに変更、verbose_nameキーを"verbose_name"固定 |
| `services/parse/parsers/directory_parser.py` | vocab変換除去、生キー(index/version)で格納 |
| `services/graph/__init__.py` | file_to_nodeのvocab変換除去、index/version生キー統一 |
| `services/graph/project_graph.py` | get_node_index/version簡素化（生キーのみ） |
| `services/parse/connectors/abaqus/inp_parser.py` | vocab変換除去 |
| `services/parse/connectors/abaqus/parameter_parser.py` | vocabパラメータ除去 |
| `services/parse/connectors/abaqus/mesh_inherit_parser.py` | vocab除外キー除去 |
| `services/parse/parsers/output_parser.py` | vocab引数の非使用化 |
| `services/dashboard/data_provider.py` | 生キー参照に変更 |
| `services/query/sort.py` | 生キー順序ソートに変更 |
| `services/export/connectors/obsidian/__init__.py` | 生キー正規化に変更 |
| `services/service/info.py` | 生キー検索に変更 |
| `docs/specs/vocab-display-time.md` | 仕様書新規作成 |

**設計変更**:
```
Before: parse時にvocab変換 → graph.yamlに変換済みキーで保存
After:  parse時に生キーで保存 → 表示時のみvocab変換
```

**メリット**:
- graph.yamlが常に生キー（英語キー）で統一
- vocab変更時にre-parseが不要
- 変換前後のキー混在問題の解消
- デバッグ容易性の向上

### 3. Config classification仕様書

`docs/specs/config-classification.md` を新規作成。
40+箇所のハードコード設定値をconfig classに集約する計画を策定。

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 212 files already formatted
- **pytest**: 1531 passed, 92 skipped

## TODO

- [ ] Config classification実装（Phase 1: 設定クラス定義、Phase 2: ハードコード置換）
- [ ] vocab_displayユーティリティのダッシュボードUI統合（テーブルヘッダー等のvocab変換表示）
- [ ] Run-Propertyトレーサビリティ CLI対応（`jj run --show-properties`）
- [ ] M7 Phase 5: Run比較ダッシュボード
- [ ] M7 Phase 6: Neo4j Run Node対応

## 確認事項・懸念

- Vocab表示時適用は大規模変更（20+ファイル、31テスト修正）のため、既存プロジェクトはre-parseが必要
- vocab_display.pyは作成済みだが、ダッシュボードUIでの表示名変換はまだ未統合。テーブルヘッダーは生キー表示になる
- Config classification は仕様書のみ。実装は次statusで対応
