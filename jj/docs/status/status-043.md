[READMEへ戻る](../../README.md)

# status-043: Phase R4-R6 完了（services構造リファクタリング完了）

**日付**: 2026-02-10

## 概要

Phase R（services構造リファクタリング）のR4-R6を実装完了。ObsidianConnectorをexport層へ移動、graph/__init__.pyの旧メソッド群を削除（2026行→510行）、全テストを新パイプラインに対応。pymeshインポートパスを`modules/pymesh`に修正。テスト443件パス、0失敗、20スキップ。

## 変更内容

### 1. Phase R4: export層の整理

**ObsidianConnectorの移動**:
- `services/parse/connectors/obsidian/__init__.py` → `services/export/connectors/obsidian/__init__.py` にObsidianConnector本体を移動
- 旧パス（`services/parse/connectors/obsidian/__init__.py`）に後方互換re-exportラッパーを配置
- `services/export/connectors/__init__.py` のインポートを新パスに更新
- `services/cli/graph.py` のインポートを新パスに更新

### 2. Phase R5: lib層の整理

確認の結果、credentials, file等のユーティリティは既に `services/lib/` 配下に正しく配置済み。変更不要。

### 3. graph/__init__.py の旧メソッド群の削除

**2026行 → 510行**（75%削減）

**削除したメソッド群**（~25個）:
- `_build_version_and_group_relations`, `_build_result_relations`, `_build_asset_relations`
- `_build_output_relations`, `_build_includes_relations`, `_build_directory_relations`
- `_build_root_directory_node`, `_enrich_*` 系メソッド群
- `_is_material_source_node`, `_build_material_nodes`, `_enrich_material_verbose_name`
- `_enrich_material_assignment_props`, `_build_elset_nodes`

**残存メソッド**（GraphServiceの本来の責務のみ）:
- `scan_files`, `file_to_node`, `parse_project`, `load`, `save`, `parse_and_save`
- `_build_verbose_name`, `_read_inp_parameter_props`, `_safe_relative_path`
- `get_nodes_by_type`, `get_node_by_id`, `get_relations_for_node`, `summary`

**後方互換re-export追加**:
```python
from services.parse.connectors.abaqus.result_parser import (  # noqa: F401
    parse_sta_file, parse_msg_file, parse_dat_file,
)
from services.parse.connectors.abaqus.inp_parser import (  # noqa: F401
    parse_material_blocks,
)
```

### 4. パーサーサブクラスの単体テスト追加

**新規ファイル**: `tests/test_parser_units.py`（18テスト）

| テストクラス | テスト数 | 対象パーサー |
|-------------|---------|-------------|
| `TestVersionRelationParser` | 5 | next_version / same_index_group |
| `TestResultRelationParser` | 2 | result_of |
| `TestAssetRelationParser` | 1 | derived_from |
| `TestOutputRelationParser` | 2 | has_output |
| `TestEnrichmentOnlyFilter` | 2 | .sta/.msg/.dat除外 |
| `TestRootDirectoryParser` | 4 | ルートdirectory Node |
| `TestDirectoryRelationParser` | 1 | contains |
| `TestIncludesRelationParser` | 1 | includes |

### 5. Phase R6: 既存レガシーテストの新パイプライン対応

**インポートパス修正**（`from jj.services...` → `from services...`）:
- `services/cli/graph.py`
- `services/run/__init__.py`
- `tests/test_abaqus_connector.py`, `tests/test_graph_feature.py`
- `tests/test_obsidian_connector.py`, `tests/test_storage_service.py`
- `shared/config.py`
- `services/parse/connectors/abaqus/` 配下

**テスト修正**:
- `test_is_material_source_node_static`: `GraphService` → `AbaqusInpParser` に参照変更
- `test_material_enrich`: `GraphService` → `AbaqusMaterialAssignmentParser` に参照変更、`ProjectGraph`構築に対応
- `test_parse_dat_file_extracts_time` / `test_dat_enriches_inp`: `parse_dat_file`の正規表現修正（`WALLCLOCK TIME` → `WALL\s*CLOCK\s+TIME`）

**config/__init__.py 修正**:
- `get_default_config_path`にフォールバックパス追加（`shared/assets/default-config.yaml`）
- Obsidianコネクタのデフォルトビュー/vocab設定が正しく読み込まれるように修正

### 6. pymeshインポートパス修正

- `services/parse/connectors/abaqus/mesh.py`: `from services.pymesh.*` → `from modules.pymesh.*`
- pymesh/pysshは`modules/`に移動済みであることを反映

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/export/connectors/obsidian/__init__.py` | 新規: ObsidianConnector移動先 |
| `services/parse/connectors/obsidian/__init__.py` | 変更: 後方互換re-exportラッパー化 |
| `services/export/connectors/__init__.py` | 変更: インポートパス更新 |
| `services/graph/__init__.py` | 変更: 旧メソッド削除（2026行→510行） |
| `services/cli/graph.py` | 変更: インポートパス修正 |
| `services/run/__init__.py` | 変更: インポートパス修正 |
| `services/parse/connectors/abaqus/mesh.py` | 変更: pymeshインポートパスをmodules/に修正 |
| `services/parse/connectors/abaqus/result_parser.py` | 変更: parse_dat_file正規表現修正 |
| `config/__init__.py` | 変更: default-config.yamlフォールバックパス追加 |
| `tests/test_parser_units.py` | 新規: パーサー単体テスト18件 |
| `tests/test_graph_feature.py` | 変更: パーサー移動に伴うテスト更新 |
| `tests/test_abaqus_connector.py` | 変更: インポートパス修正 |
| `tests/test_obsidian_connector.py` | 変更: インポートパス修正 |
| `tests/test_storage_service.py` | 変更: インポートパス修正 |
| `shared/config.py` | 変更: インポートパス修正 |

## テスト結果

```
443 passed, 20 skipped in 465.77s
```

- 全443テストパス（0失敗）
- 新規追加: test_parser_units.py 18件
- pymeshインポートテスト: 修正によりスキップ→パスに復帰

## マイルストーン MR 達成

Phase R（services構造リファクタリング）の全フェーズが完了:

| フェーズ | 内容 | ステータス |
|---------|------|-----------|
| R1 | ProjectGraph型の実装 | ✅ (status-042) |
| R2 | AbstractFileParser.__init_subclass__パターン確立 | ✅ (status-042) |
| R3 | graph/__init__.pyの分解（16パーサー） | ✅ (status-042) |
| R4 | export層の整理 | ✅ (本status) |
| R5 | lib層の整理（確認済み） | ✅ (本status) |
| R6 | テスト移行と検証 | ✅ (本status) |

## TODO / 次のステップ

- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤
- [ ] jj-db側のTODO（status-060参照）
