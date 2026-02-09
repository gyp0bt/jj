[READMEへ戻る](../../README.md) | [ロードマップ](../roadmap.md)

# Status 025 - グラフ機能の作り込み（Phase 2 Abaqusコネクター強化）

**日付**: 2026-02-05

---

## 概要

ロードマップを大幅改定し、notes機能を削除、graph機能を最優先化。
Abaqusコネクターのgraph機能をfile/run機能より上位に配置し、
Phase 2として4つの主要グラフ機能を実装した。

---

## 実施内容

### 1. ロードマップ改定
- notes関連の全項目を削除（noteコマンド層、依存関係拡張）
- Phase 2を「グラフ機能の作り込み」として再定義
- Abaqusコネクターのgraph機能をPhase 2最優先に移動
- file/runコマンドをPhase 3（中期）に後退

### 2. 同一ファイルタイプの関連付け（has_output）
- `_build_output_relations()` メソッドを新規追加
- 入力ファイルのbasenameを接頭辞として持つファイルを自動検出
- 例: `go_idx1_w5_t20.inp` → `go_idx1_w5_t20_RF.csv` (has_output)
- 出力ファイルの追加タグ（RF, stress等）はノードのtagsプロパティに保持
- results/ディレクトリ内の出力ファイルも対応

### 3. フォルダベースの関連付け（contains）
- `scan_directories()` メソッドを新規追加
- `_build_directory_relations()` メソッドを新規追加
- 命名規則に合致するディレクトリ（go_idx1_w5_t20/等）をノード化
- ディレクトリ内ファイルをcontains関係でリンク
- 同名入力ファイルとhas_output関係を自動構築
- ディレクトリノードのtype: `go_directory`（ファイルタイプ + _directory）

### 4. material.inpの高度な解析（abaqus_material）
- `parse_material_blocks()` 関数を新規追加（軽量パーサー）
- `_build_material_nodes()` メソッドを新規追加
- *MATERIAL ブロックを解析し、Node(type="abaqus_material") を生成
- 物性プロパティ（elastic, density, plastic, conductivity）を配列データとして保持
- `defined_in` 関係で入力ファイルにリンク
- テストデータ: Steel_S235（elastic/density/plastic/conductivity）、Aluminum_6061（elastic/density）

### 5. 解析結果ファイルの解析（analysis_status）
- `parse_sta_file()` 関数を新規追加
- `_enrich_sta_status()` メソッドを新規追加
- .staファイルから解析結果の成否を判定
  - "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" → `completed`
  - "THE ANALYSIS HAS NOT BEEN COMPLETED" → `failed`
- エラーメッセージ（***ERROR:）と警告（***WARNING:）を抽出
- `analysis_status`, `errors`, `warnings` プロパティとしてノードに付与

---

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `docs/roadmap.md` | notes削除、graph最優先化、Phase再構成 |
| `services/graph/__init__.py` | 4つの新機能を追加（約400行追加） |
| `tests/test_graph_feature.py` | 新機能用テスト20件追加 |
| `tests/fixtures/graph_test1/material.inp` | 物性定義データを追記 |
| `tests/fixtures/graph_test1/go_idx1_w5_t20.inp` | *INCLUDEディレクティブ追加 |
| `tests/fixtures/graph_test1/go_idx1_w5_t20.sta` | 成功staデータ追加 |
| `tests/fixtures/graph_test1/go_idx2.sta` | 失敗staデータ新規作成 |
| `tests/fixtures/graph_test1/go_idx1_w5_t20/` | フォルダテスト用ディレクトリ新規 |

---

## テスト結果

全92テスト通過（既存72 + 新規20）

### 新規テストクラス
- `TestOutputRelations`: has_output関係のテスト（2件）
- `TestDirectoryRelations`: フォルダベース関連付けのテスト（3件）
- `TestMaterialParsing`: material解析のテスト（5件）
- `TestStaAnalysis`: sta解析のテスト（3件）
- `TestParseMaterialBlocks`: parse_material_blocks単体テスト（3件）
- `TestParseStaFile`: parse_sta_file単体テスト（3件）
- `TestGraphSummaryRelationTypes`: サマリーのリレーションタイプ確認（1件）

---

## 新しいリレーションタイプ一覧

| ラベル | 説明 | 例 |
|--------|------|-----|
| `next_version` | バージョン進行 | v1.inp → v2.inp |
| `same_index_group` | 同一index/typeグループ | idx1系ファイルのグループ |
| `result_of` | 解析結果→入力 | .odb → .inp |
| `derived_from` | アセット←入力 | .inp → .modfem |
| `includes` | *INCLUDEディレクティブ | go.inp → material.inp |
| `has_output` | **[NEW]** 接頭辞一致の出力 | .inp → _RF.csv |
| `contains` | **[NEW]** フォルダ←子ファイル | dir/ → dir/file |
| `defined_in` | **[NEW]** 物性定義←入力 | material → .inp |

---

## TODO（次回以降の作業）

- [ ] パーサー層の拡張機能（ファイルグループ、.v1完全対応、パフォーマンス最適化）
- [ ] run(unknown00)のような仮runを介した関連付け
- [ ] config.yamlの拡張（配列スライス、type=iso/aniso定義）
- [ ] .msgファイルの解析（WARNING/ERROR抽出）
- [ ] ドキュメント連携（index.csv/yaml、Obsidian dailyノート）

---

## 確認事項

特になし。
