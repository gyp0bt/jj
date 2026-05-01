[← status-index.md](status-index.md)

# status-090 — ミニマル化の機能回帰修正・テスト復旧

- **日付**: 2026-05-01
- **ブランチ**: master
- **バージョン**: 0.2.1

---

## 概要

`bb9b5d2 ミニマル化開始` 以降、status-088（軽量化）と status-089（プラグイン構造統合）の作業途中で残されていた以下の問題を解消した：

- 多数のパーサーが `import` から外されたままで、`jj parse` がリレーションを生成しない機能回帰
- 旧パスから新パス（`plugins/`）への移行に伴う後方互換 re-export の取りこぼし
- 削除済みプラグイン（calculix, ml, office等）を参照する旧テストの残存
- 後方互換 re-export 内で参照されていた未存在シンボル
- `MeshInheritParser` 内に誤って混入した `continue` によるロジック欠落

---

## 主要な修正

### 1. パーサー自動登録の復元

`bb9b5d2` 以降、以下の `__init__.py` でパーサー import がコメントアウトされたまま放置されていた：

- `services/parse/parsers/__init__.py`: 13個中12個のコアパーサー（VersionRelationParser等）
- `plugins/abaqus/__init__.py`: 8個中5個のAbaqusパーサー（diff_parser, inp_parser, mesh_parser, mesh_inherit_parser）
- `plugins/obsidian/__init__.py`: DailyNoteParser, ObsidianExporter

→ `__init_subclass__` 自動登録が発火するよう全 import を復元。

#### 効果（examples/work1）

| 指標 | Before | After |
|------|--------|-------|
| 稼働パーサー数 | 4 | 21 |
| ノード数 | 36 | 40 |
| リレーション数 | 0 | 55 |

### 2. `MeshInheritParser` のロジック修正

`plugins/abaqus/parse/mesh_inherit_parser.py:107` に誤って `continue` が混入し、
キー競合時の接頭辞付与処理（`{child_name}:{key}`）が永久に到達不能になっていた。
`continue` を除去して接頭辞ロジックを復活。

### 3. 後方互換 re-export の修復

旧パス → 新パスの re-export で、以下のシンボルが取りこぼされていた：

| 旧パス | 不足していたシンボル |
|--------|---------------------|
| `services.parse.connectors.abaqus.parameter_parser` | `_resolve_param_references` |
| `services.parse.connectors.abaqus.inp_parser` | `parse_keyword_blocks`, `AbaqusElsetParser`, `AbaqusKeywordParser`, `AbaqusMaterialAssignmentParser` |
| `services.parse.connectors.abaqus.inp_parser_base` | （`parse_inp_file` 削除済みの参照を整理） |
| `services.parse.connectors.abaqus.mesh` | `_safe_import_pymesh`, `extract_*` 系（旧名 `MeshQualityAnalyzer` 等の存在しない参照を除去） |
| `services.parse.connectors.abaqus.mesh_parser` | `_parse_inp_worker` |
| `services.parse.connectors.abaqus.result_parser` | `_parse_convergence_info` |
| `services.parse.connectors.abaqus.__init__` | `MaterialPropertyReadComponent`, `_MESH_TOPOLOGY_KEYWORDS`, `_filter_non_mesh_raw_blocks` |
| `services.parse.connectors.obsidian.daily` | `parse_daily_note`, `DailyFileReference`, `_extract_file_path_from_value`, `_strip_obsidian_prefix` |
| `services.parse.base` | `_group_parsers_by_priority`, `_run_parser_group_parallel` |
| `services.export.__init__` | `_exporter_registry`、`services.export.connectors` の自動登録（循環import回避のため遅延 import 関数を採用） |

### 4. 循環import解消

`plugins/obsidian/parse/__init__.py` が `services.export.connectors.obsidian` 経由で
`plugins.obsidian.export` を参照する構造になっていた（旧→新→旧と循環）。
`plugins.obsidian.export` を直接 import するよう変更。

### 5. 削除プラグイン参照テストの除去/更新

- `tests/test_plugin_integration.py`: `test_calculix_plugin_registers`, `test_ml_plugin_registers` 等を削除、`test_all_plugins_register_without_error` の対象を abaqus/obsidian に絞る
- `tests/test_plugin_manifest_p3.py`: `TestMLManifest`, `TestOfficeManifest` を削除し、`_reset_plugin` の対象モジュールを `plugins.*` に修正
- 削除済みヘルパー関数のテスト除去: `TestAgGridHelper`, `TestEstimateColumnWidth` (test_dashboard.py), `test_view_add_form_present` (test_dashboard_e2e.py)

### 6. テストの import path 修正

`bb9b5d2` の機械的リネームで `inp_parser` → `inp_parser_base` に置換された箇所のうち、
実際は `inp_parser.py` 側に残っているシンボルへの参照を修正：

- `tests/test_abaqus_advanced_assets.py`: `parse_keyword_blocks` の import 経路修正
- `tests/test_parser_units.py`: `AbaqusElsetParser` の import 経路修正
- `tests/test_graph_feature.py`: `AbaqusMaterialAssignmentParser` の import 経路修正

### 7. その他

- `services/graph/query/sort.py`: `select_table_columns()` で `table_columns` 指定時にも固定カラム（name/type/format）が常に含まれるよう動作復元
- `pyproject.toml`: `[tool.ruff]` に `extend-exclude = ["examples"]` を追加（ユーザー作業領域の除外）

---

## 検証結果

### テスト

```
全テスト: 1649 passed, 18 skipped (parser_pipeline以外)
parser_pipeline: 102 passed (3分以上かかる重テスト)
合計: 1751+ passed, 0 failed
```

### lint/format

```bash
ruff check .          # All checks passed!
ruff format --check . # 223 files already formatted
```

### CLI動作確認（examples/work1）

| コマンド | 結果 |
|----------|------|
| `jj parse` | ノード40件・リレーション55件・21パーサー稼働 |
| `jj show` | ノード一覧表示OK |
| `jj info <file>` | プロパティ・リレーション表示OK |
| `jj diff` | INP差分比較OK |
| `jj dashboard` | Streamlitサーバー起動OK（ヘルスチェック ok） |

---

## 変更ファイル

### 修正
- `plugins/__init__.py`, `plugins/base/__init__.py`: `__all__` ソート
- `plugins/abaqus/__init__.py`: 4パーサー import 復元
- `plugins/obsidian/__init__.py`: パーサー・エクスポーター import 復元
- `plugins/obsidian/parse/__init__.py`: 循環import解消
- `plugins/abaqus/parse/mesh_inherit_parser.py`: `continue` バグ修正
- `services/parse/parsers/__init__.py`: 12パーサー import 復元
- `services/graph/query/__init__.py`, `services/graph/query/sort.py`
- `services/export/__init__.py`: 自動登録 + `_exporter_registry` 公開
- `services/parse/connectors/abaqus/`: 各 re-export ファイル（symbol整理）
- `services/parse/connectors/obsidian/daily.py`
- `pyproject.toml`: `extend-exclude = ["examples"]`

### テスト修正
- `tests/test_abaqus_advanced_assets.py`
- `tests/test_dashboard.py`
- `tests/test_dashboard_e2e.py`
- `tests/test_graph_feature.py`
- `tests/test_parser_units.py`
- `tests/test_plugin_integration.py`
- `tests/test_plugin_manifest_p3.py`

---

## TODO

- [ ] 大量の未コミット変更（status-088/089/090 を含む 132 ファイル、29k 行削除）について、機能単位で commit を分割する判断
- [ ] テストの import path をすべて新パス（`plugins.*`）に統一する整理（任意・後方互換 re-export 経由でも全て通る）
