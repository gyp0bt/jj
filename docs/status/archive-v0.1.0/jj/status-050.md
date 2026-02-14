# status-050

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

JSONプロパティ読み取り形式の変更（ファイル名サフィックスプレフィックス除去）、
CSVカラム指定・単位マッピングへのglobパターン対応。

## 実装内容

### 1. JSONプロパティキー形式変更（json_property_parser.py）

- **変更前**: ファイル名サフィックスをプレフィックスとして使用
  - `go_idx0.v29_stress.json` → `properties["stress.center"] = 0.25`
  - 形式: `filename_suffix.key:value` / `filename_suffix.key.key:value`
- **変更後**: JSON内のキーをそのまま使用（ファイル名サフィックスなし）
  - `go_idx0.v29_stress.json` → `properties["center"] = 0.25`
  - 形式: `key:value`（階層1つ）/ `key.key:value`（階層2つ）
- vocab置換によるサフィックス変換処理を削除（不要に）
- `_flatten_json()`のprefix引数を空文字列で呼び出し

### 2. CSVカラム指定のglobパターン対応（info.py）

- `export.csv-columns` でglobパターンが使用可能に
  - 例: `stress*` → `stress.center`, `stress.edge` 等にマッチ
  - 例: `mesh_*` → `mesh_node_count`, `mesh_element_count` 等にマッチ
- パターン指定順にカラムが並ぶ（同一パターン内は発見順）
- base keys（`name`, `type`, `format`）は常に先頭に含まれる
- CLI `--columns` 引数でもglobパターン使用可能

### 3. 単位マッピングのglobパターン対応（info.py）

- `export.units` でglobパターンが使用可能に
  - 例: `"stress*": "MPa"` → `stress.center[MPa]`, `stress.edge[MPa]`
- 完全一致が優先される（完全一致がない場合のみglobマッチ）
- `_match_unit()` ヘルパー関数を新設
- header形式・row形式の両方で対応

### 4. default-config.yaml更新

- exportセクションのコメントにglobパターンの説明を追加

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/parsers/json_property_parser.py` | プレフィックスなしでJSON平坦化、docstring更新 |
| `services/service/info.py` | CSVカラム・単位のglobパターン対応、`_match_unit()`追加 |
| `shared/assets/default-config.yaml` | exportコメントにglob説明追加 |
| `tests/test_selection_and_export.py` | globパターンテスト5件追加 |
| `tests/test_parser_pipeline.py` | JSON伝搬テストをkey:value形式に更新 |

## テスト結果

```
86 passed (test_selection_and_export.py + test_parser_pipeline.py)
新規テスト5件:
  - CSVカラムglobパターン: 2テスト（パターンマッチ、順序保持）
  - CSV単位globパターン: 3テスト（header形式、row形式、完全一致優先）
既存テスト修正1件:
  - test_json_properties_propagated_despite_results_filter: "stress" → "0(center)" に変更
```

## 確認事項・TODO

- [ ] 実プロジェクトでのJSONキー衝突の確認（複数JSONファイルが同一キーを持つ場合の上書き動作）
- [ ] `--columns` CLI引数のglobパターンドキュメント追記（ヘルプメッセージ等）
- [ ] **mesh_quality未付加の原因調査・修正**: mesh_*.inpでmesh_qualityが付加されるものとされないものがある。includeエラーではなく法則性不明。メッシュ数が少ないものが読まれている傾向がある可能性。AbaqusMeshParser周辺を調査しfix。
- [ ] **MeshInheritParser改修: include先プロパティの直下追加**: 現在go_*.inpがincludeしているmesh/material等のファイルからpropertyを読んでinclude_propertiesに一部だけ入れている。これをgo_が持っていないキー全てをinclude_propertiesではなく直下に追加するように変更。テスト要件として「meshをincludeしているgo_*.inpにmesh_qualityを含む属性が付加されること」を追加。
- [ ] **elset-material mappingの調査**: elsetとmaterial定義のmappingを取ったと報告を受けているが、graphには出ておらずコードのどこで実装されているか不明。調査して、存在して問題なければ報告、問題があればfixして報告。
