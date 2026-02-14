[READMEへ戻る](../../README.md)

# status-088: Abaqus固有ロジック分離・CacheProvider汎用化・requirements.txt廃止

**日付**: 2026-02-14
**担当**: Claude Code

---

## 概要

CacheProvider・GraphStorage・GraphService・parse層からAbaqus固有ロジックを分離し、プラグインアーキテクチャの汎用性を確保。
`requirements.txt` を廃止し `pyproject.toml` を依存管理の唯一の正とする。

## 変更内容

### 1. requirements.txt 廃止

- `jj/requirements.txt` を削除
- `pyproject.toml` の `[project.dependencies]` + `[project.optional-dependencies]` が唯一の依存管理源

### 2. CacheProvider プロトコル汎用化 (`services/sdk/cache.py`)

| Before | After |
|--------|-------|
| `load_abq_data(project_root, file_path, expected_mtime)` | `load_plugin_data(project_root, namespace, file_path, expected_mtime)` |
| `save_abq_data(project_root, file_path, abq_data, mtime)` | `save_plugin_data(project_root, namespace, file_path, data, mtime)` |

- `namespace` パラメータにより任意のプラグインがキャッシュを利用可能に
- Abaqusプラグインは `namespace="abaqus"` を使用

### 3. GraphStorage 汎用 plugin_cache (`services/graph/storage/__init__.py`)

| Before | After |
|--------|-------|
| `_ABQ_CACHE_DIRNAME = "abq_cache"` | `_PLUGIN_CACHE_DIRNAME = "plugin_cache"` |
| `abq_cache/` 直下にpickle保存 | `plugin_cache/{namespace}/` にpickle保存 |
| `clear_abq_cache(project_root)` | `clear_plugin_cache(project_root, namespace=None)` |
| `cleanup_abq_cache(project_root, ...)` | `cleanup_plugin_cache(project_root, namespace=None, ...)` |

- pickle内部キー: `"abq_data"` → `"data"`
- `namespace=None` で全名前空間を一括クリア

### 4. ProjectGraph キャッシュAPI汎用化 (`services/graph/project_graph.py`)

| Before | After |
|--------|-------|
| `get_cached_abq_data(file_path)` | `get_cached_plugin_data(namespace, file_path)` |
| `set_cached_abq_data(file_path, abq_data)` | `set_cached_plugin_data(namespace, file_path, data)` |

- 内部キー: `"{namespace}:{file_path}"` 形式

### 5. GraphService からAbaqus固有ロジック除去 (`services/graph/__init__.py`)

- `_read_inp_parameter_props()` メソッド（57行）を削除
  - → `AbaqusParameterParser`（priority=15）として再実装
- `file_to_node()` 内の `_read_inp_parameter_props` 呼び出しを除去
- `cleanup_abq_cache` → `cleanup_plugin_cache` に変更

### 6. parse/__init__.py からAbaqus固有エクスポート除去

削除したエクスポート:
- `ABQData`, `BlockDiff`, `diff_abq_blocks`, `format_diff_blocks_markdown`, `format_diff_summary_table`, `generate_diff_props`, `read_inp`
- これらは `services.parse.connectors.abaqus` から直接importすること

### 7. 新規ファイル: AbaqusParameterParser (`services/parse/connectors/abaqus/parameter_parser.py`)

- `AbstractFileParser` サブクラス、priority=15
- `.inp` ファイルの `*PARAMETER/**props` ブロックからkey=valueプロパティを抽出
- vocabによるキー・値の翻訳を適用
- GraphService._read_inp_parameter_propsの完全な置き換え

### 8. MeshInheritParser をAbaqusプラグインに移動

- 実体: `services/parse/connectors/abaqus/mesh_inherit_parser.py` (新規)
- 旧パス: `services/parse/parsers/mesh_inherit_parser.py` → 後方互換re-export stub
- `services/parse/parsers/__init__.py` からimport・__all__を除去

### 9. submit.py をAbaqusプラグインに移動

- 実体: `services/plugins/abaqus/submit.py` (新規, 571行)
- 旧パス: `services/service/submit.py` → 後方互換re-export stub

### 10. Abaqusプラグイン register() 更新 (`services/plugins/abaqus/__init__.py`)

新規登録パーサー:
- `AbaqusParameterParser` (priority=15) — `*PARAMETER/**props` 抽出
- `MeshInheritParser` (priority=81) — メッシュ継承関係

### 11. config docstring更新 (`config/__init__.py`)

- `cache_max_age_days`: "ABQDataキャッシュ" → "プラグインキャッシュ"
- `cache_max_count`: 同上

## Abaqusプラグイン パーサー一覧（status-088時点）

| Priority | クラス | 役割 |
|----------|--------|------|
| 15 | AbaqusParameterParser | `*PARAMETER/**props`ブロック抽出 |
| 20 | AbaqusMeshParser | メッシュ品質解析（pymesh依存） |
| 25 | AbaqusDiffParser | INPブロック差分解析 |
| 81 | MeshInheritParser | メッシュ継承関係 |

## 変更ファイル一覧

### 削除
- `jj/requirements.txt`

### 新規
- `services/parse/connectors/abaqus/parameter_parser.py`
- `services/parse/connectors/abaqus/mesh_inherit_parser.py`
- `services/plugins/abaqus/submit.py`

### 変更
- `config/__init__.py` — docstring更新
- `services/sdk/cache.py` — CacheProviderプロトコル汎用化
- `services/graph/storage/__init__.py` — plugin_cache実装
- `services/graph/project_graph.py` — キャッシュAPI汎用化
- `services/graph/__init__.py` — Abaqus固有ロジック除去
- `services/parse/__init__.py` — Abaqusエクスポート除去
- `services/parse/parsers/__init__.py` — MeshInherit除去
- `services/parse/parsers/mesh_inherit_parser.py` — re-export stub化
- `services/parse/connectors/abaqus/mesh_parser.py` — plugin_data API使用
- `services/parse/connectors/abaqus/diff_parser.py` — plugin_data API使用
- `services/plugins/abaqus/__init__.py` — register()更新
- `services/service/submit.py` — re-export stub化

### テスト更新
- `tests/test_sdk.py` — プロトコルメソッド名・mock更新
- `tests/test_parser_units.py` — キャッシュAPI・ディレクトリパス更新
- `tests/test_graph_feature.py` — AbaqusParameterParser経由テストに変更

## テスト結果

- **1003テスト通過**、59スキップ
- 残存失敗8件（全て既存・今回の変更とは無関係）:
  - TestParseMaterialCurveColumns (4件): `_parse_material_curve_columns` 未定義
  - TestMaterialComparisonCsv (1件): pandas未インストール
  - TestPymeshImport (1件): pymeshインポート失敗
  - TestPymeshWithModules (2件): pandas未インストール

## 後方互換性

- `services/service/submit.py` → re-export stub（既存importは動作）
- `services/parse/parsers/mesh_inherit_parser.py` → re-export stub（同上）
- `services.parse` パッケージからのAbaqus型import（ABQData等）は **非互換** → `services.parse.connectors.abaqus` から直接importに変更が必要

## TODO

- `services/service/submit.py` re-export stubは将来的に削除検討（全importパスの移行後）
- `services/parse/parsers/mesh_inherit_parser.py` re-export stubも同様
- 新プラグイン追加時は `namespace` を指定してplugin_cacheを利用可能
- `_parse_material_curve_columns` 未定義の問題は別途対応が必要
