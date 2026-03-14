[← README.md](../../README.md) | [← status-index](status-index.md)

# status-077 — テストアセット追加 & UI検証フロー整備

**日付**: 2026-03-13
**ブランチ**: claude/test-assets-ui-verification-jPGVa
**作業者**: Claude Code

---

## 概要

Abaqus合成テストアセットを追加し、パーサーのカバレッジギャップを検証。
BEAM SECTION未対応のギャップを発見・修正。ダッシュボードE2Eテストを拡充。

## 実施内容

### 1. Abaqusアドバンストテストアセット追加

**場所**: `shared/tests/test_asset_abaqus_advanced/`

新規合成ファイル:
- `material_advanced.inp` — 7種の材料定義（HYPERELASTIC/NEO HOOKE, MOONEY-RIVLIN, ORTHOTROPIC, KINEMATIC硬化, VISCOELASTIC, ケース違いSteel/STEEL）
- `go_idx1.v1.inp` — SHELL SECTION + FREQUENCY + CLOAD/DLOAD
- `go_idx2.v1.inp` — General Contact + COUPLED TEMPERATURE-DISPLACEMENT + PRESSURE/FILM
- `go_idx3.v1.inp` — BEAM SECTION + BUCKLE解析
- `nested_include/main.inp` + `sub/assembly.inp` — 3段INCLUDEネスト
- `go_idx1.v1.sta/msg/dat` — 成功+カットバック+負の固有値警告+複数ステップ
- `results/go_idx2.v1.sta/msg/dat` — 失敗解析+複数エラー+切り詰め

### 2. パーサーギャップの発見と修正

**発見**: `extract_material_elset_mapping()`が`*BEAM SECTION`に未対応
**修正**: `services/parse/connectors/abaqus/mesh.py` に `*beamsection` パターン追加

### 3. テスト追加

**`tests/test_abaqus_advanced_assets.py`** — 46テスト
- `TestParseMaterialBlocksAdvanced`: 7材料タイプの解析検証
- `TestParseKeywordBlocksAdvanced`: 10キーワードの検出検証
- `TestExtractMaterialElsetMappingAdvanced`: セクション種別の解析
- `TestResultParserAdvanced`: 結果ファイルエッジケース（カットバック、重複排除、複数ステップ）
- `TestMaterialParsingViaInclude`: INCLUDEベースの材料解析
- `TestNestedInclude`: 3段ネストINCLUDE
- `TestAssetFilesExist`: アセットファイル存在確認

**`tests/test_dashboard_e2e.py`** — 12テスト追加（合計39テスト）
- `TestPageComponentRegistry`: PageComponentレジストリ包括テスト
- `TestDashboardConnectorRegistry`: コネクターレジストリ・HTML生成テスト
- `TestHtmlExportIntegrity`: HTMLエクスポート整合性テスト
- `TestDashboardDataProviderAdvanced`: 多様なデータパターンテスト

### 4. テスト結果

- `test_abaqus_advanced_assets.py`: **46 passed**
- `test_dashboard_e2e.py`: **39 passed**
- 既存テスト: 非破壊確認済み

## 修正ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/connectors/abaqus/mesh.py` | BEAM SECTION対応追加 |
| `tests/test_abaqus_advanced_assets.py` | 新規: 46テスト |
| `tests/test_dashboard_e2e.py` | 12テスト追加 |
| `shared/tests/test_asset_abaqus_advanced/` | 新規: 合成テストアセット群 |

## 確認事項・TODO

- [ ] 他ソルバー（LS-DYNA, OpenFOAM, Flow-3D, Fluent, HFSS）のテストアセット追加は次回以降
- [ ] Playwrightスクリーンショット回帰テストは将来課題
- [ ] ユーザーによるAbaqus実出力ファイルの追加が理想（合成ファイルはフォーマットカバレッジのみ）
- [ ] status-index.md M2項目更新: Abaqus合成アセットによるテスト追加開始

## 設計懸念

- `parse_material_blocks()`はINCLUDEを辿らない（単体ファイル解析）。パイプライン全体のINCLUDE解決は`IncludesRelationParser`が担当するため、材料ファイルが独立INPとしてグラフに登録される前提。
- ケース違い材料名（Steel vs STEEL）は`parse_material_blocks()`では別材料、`AbaqusMaterialAssignmentParser`では`.lower()`で同一視。この非対称性は意図的だが注意。
