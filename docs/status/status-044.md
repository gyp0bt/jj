[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-044: テスト全件通過・フラット化後のパス修正・バグ修正

- **日付**: 2026-03-04
- **マイルストーン**: M1（基盤整備）
- **ブランチ**: `claude/execute-status-todos-lfDl8`

---

## 概要

status-043のTODOを実行。フォルダフラット化（jj/jj/ → jj/）後に残っていたパス参照の不整合を全面修正し、テスト失敗を159件→0件に解消。

## 変更内容

### 1. docs/specs内の旧パス参照修正

| ファイル | 変更 |
|---------|------|
| `docs/specs/run-centric-schema.md` | `../../jj/docs/specs/` → 同ディレクトリ相対パスに修正 |
| `docs/specs/multi-solver.md` | 同上 |
| `docs/specs/ml-task-roadmap.md` | 同上 |
| `docs/review/review-v0.1.0.md` | jjrv関連リンク除去、パス修正 |

### 2. テストアセットパス修正（10ファイル）

フラット化により `.parent.parent.parent / "shared"` が `/home/user/shared` に誤解決されていた問題を修正。

| ファイル | 変数 |
|---------|------|
| `tests/test_parser_pipeline.py` | ASSET_DIR, インライン参照 |
| `tests/test_solver_profile.py` | ASSET_DIR |
| `tests/test_mesh_stats_cache.py` | ASSET_DIR |
| `tests/test_parser_units.py` | ASSET_DIR |
| `tests/test_abaqus_connector.py` | ASSET_DIR |
| `tests/test_performance_optimizations.py` | ASSET_DIR |
| `tests/test_surrogate_framework.py` | ML_ASSET_DIR, SURROGATE_ASSET_DIR |
| `tests/test_ml_parsers.py` | ML_ASSET_DIR |

### 3. default-config.yamlパス解決修正

`config/__init__.py` の `get_default_config_path()` で `shared/assets/` のフォールバックパスが `package_dir.parent / "shared"` (誤) → `package_dir / "shared"` (正) に修正。

### 4. AbaqusResultParser バグ修正

`_enrich_sta_status` / `_enrich_msg_status` / `_enrich_dat_status` で inp_node へのプロパティ集約が `if False:` で無効化されていたバグを復元。`analysis_status`, `sta_errors`, `msg_warnings`, `cpu_time` 等がinpノードに正しく付与されるように。

### 5. AbaqusParameterParser 改善

- 科学表記への変換 (`.3e` フォーマット) を廃止、元の数値表記を保持
- 文字列パラメータ値もサポート（vocab変換が値にも適用可能に）
- `**props` コメント不要で全 `*PARAMETER` ブロックを読み取る設計に統一

### 6. default-config vocab有効化

`ver: バージョン` と `v: バージョン` のコメントアウトを解除。

### 7. optional依存テストのimportorskip追加

| テストクラス | 依存 |
|-------------|------|
| `TestPlotlyDarkModeVisibility` | plotly |
| `TestDashboardPageConnector` (HTML生成テスト) | pandas |
| `TestConnectorSavedViewUnit` | pandas |
| `TestMaterialComparisonCsv` | pandas |
| `TestConnectorSavedViewHtml` | pandas |
| `TestMeshTopologyGroups` | pymesh |
| `TestPymeshWithModules` | pymesh |
| `TestPymeshImport` | pymesh |

### 8. ruffエラー修正

テストアセット・サンプルファイルの未使用変数、SIM401等を修正。

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 210 files already formatted
- **pytest**: 1497 passed, 113 skipped, 0 failed（159件→0件解消）

## TODO

- [ ] M7 Phase 5: Run比較ダッシュボード（Run一覧・Run比較・Run DAGビュー）
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] M6 Phase 5: MLダッシュボードコネクター
- [ ] プラグイン分離の検討（Abaqusプラグインの外部パッケージ化）

## 確認事項・懸念

- `if False:` パターンがAbaqusResultParserの3メソッドすべてに適用されていた。意図的に無効化した可能性もあるが、テストが期待する動作と矛盾するため復元した
- `AbaqusParameterParser` の科学表記変換の廃止は、既存プロジェクトでの表示に影響する可能性あり。元の値を保持する方がデータの忠実性が高い
- テストアセット（evaluate.py等）のMLパーサー検出テストは実ファイル内容と期待値の整合性を確認・修正済み
