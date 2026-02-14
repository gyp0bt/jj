# status-054

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

既存テストをshared/tests/test_asset1の実データ対象に大幅に書き換え・追加。
76件の実データテストを追加し、3件の想定外の問題を発見・記録。

## 実装内容

### 1. test_abaqus_connector.py: 実データ版テスト追加（38件）

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| TestReadInpRealMeshTest | 11 | mesh_test.inp (v1/v2/v3) の実パース: ノード数・要素数・nset・elset・材料・バージョン間単調増加 |
| TestReadInpRealLargeMesh | 6 | mesh_shape1_t95.v7.inp (67,942ノード) の大規模メッシュパース |
| TestReadInpRealErrorCases | 3 | material.inp欠如エラー、*FRICTION under *SURFACE INTERACTION エラー |
| TestDiffRealData | 5 | mesh_test v1→v2 (9差分), v2→v3 (1差分) の実差分検出 |
| TestMsgRealData | 4 | go_idx1.v3.msg(8W/2E), go_idx0.v29.msg(6W/0E), go_idx2.v3.msg(8W/0E) |
| TestDatRealData | 2 | go_idx1.v3.dat: cpu_time, wallclock_time, warnings |
| TestStaRealData | 1 | go_idx1.v3.sta: analysis_status (skip if not found) |
| TestMeshSummaryRealData | 3 | mesh_test.inp の要約（座標範囲・サイズ・abq_to_dict） |
| TestParseMaterialBlocksRealData | 3 | mesh_test(1材料), go_idx1(0=material.inp欠如), mesh_shape1(0=メッシュのみ) |

### 2. test_parser_units.py: 実データ版パーサー単体テスト追加（19件）

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| TestVersionRelationParserRealData | 3 | go_idx3 v1→v2, go_idx2 ディレクトリ跨ぎバージョン, same_index_group |
| TestResultRelationParserRealData | 2 | .dat→.inp(3ペア), .msg→.inp(3ペア) の result_of |
| TestAssetRelationParserRealData | 2 | .modfem→.inp derived_from(6ペア), 方向検証 |
| TestIncludesRelationParserRealData | 4 | includes 8件, go_idx1→mesh+step, go_idx0→meshのみ, old/goのディレクトリ跨ぎ |
| TestDirectoryRelationParserRealData | 2 | old/tools/reports/assets/results ディレクトリ作成, old/のcontains≥15 |
| TestJsonPropertyParserRealData | 3 | JSON→go_*.inp伝搬, NaN→None変換, 3ノード全体伝搬 |
| TestEnrichmentOnlyFilterRealData | 3 | dat/msg除去, inp保持, results/JSON除去 |

### 3. test_parser_pipeline.py: 実データ版パイプライン統合テスト追加（19件）

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| TestGoNodeParametersPipeline | 4 | s_coh, K_coh, target_strain, damage_stabilization の具体値検証 |
| TestJsonPropertyPropagationPipeline | 3 | go_idx1(0.5), go_idx0(NaN→None), go_idx2(0.0) の具体値検証 |
| TestIncludesRelationPipeline | 2 | go_idx1→mesh+step, material.inp不在の検証 |
| TestDerivedFromRelationPipeline | 2 | derived_from 6ペア, inp→modfem方向 |
| TestNodeCountsPipeline | 6 | 全体44ノード/61リレーション, go=6, mesh≥22, step=1, directory=6 |
| TestMsgPropagationPipeline | 2 | go_idx1 msg_errors=2, go_idx0 msg_errors=0 |

## 想定外の発見

### 1. material.inp 欠如
- test_asset1に `material.inp` が存在しない
- go_*.inp は全て `*include, input=material.inp` を記述
- `read_inp()` は Warning を出して include スキップするが、後続の `*FRICTION` で crash
- パイプライン(`AbaqusInpParser`)は `parse_material_blocks()` を使うため影響なし

### 2. *FRICTION under *SURFACE INTERACTION のパーサーエラー
- `step_stress_v1.inp` 内の `*surface interaction` ブロック下に `*FRICTION` がある
- パーサーが `*FRICTION` を材料サブキーワードとしてのみ扱うため "current material がありません" エラー
- Abaqus仕様では `*FRICTION` は `*SURFACE INTERACTION` 下にも配置可能
- `read_inp()` のみ影響、パイプラインは `parse_material_blocks()` 経由なので無影響

### 3. VersionRelationParser のフォーマット混合チェーン
- go_idx2.v2.inp → go_idx2.v3.dat → go_idx2.v3.inp → go_idx2.v3.msg のように
  異フォーマット間で next_version チェーンが構築される
- モックテストでは同一フォーマット前提だったため発覚せず
- 同一 (type, index) グループ内で version + format でソートされた結果

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `tests/test_abaqus_connector.py` | 実データテスト38件追加（9クラス） |
| `tests/test_parser_units.py` | 実データテスト19件追加（7クラス） |
| `tests/test_parser_pipeline.py` | 実データテスト19件追加（6クラス） |
| `docs/status/status-054.md` | 本ステータスファイル |

## テスト結果

```
test_parser_units.py: 62 passed (既存43 + 新規19)
test_parser_pipeline.py: 50 passed (既存31 + 新規19)
test_abaqus_connector.py: 100 passed, 1 skipped (既存62 + 新規38)
合計: 211 passed, 1 skipped
```

## 確認事項・TODO

- [x] test_abaqus_connector.py に実データテスト追加 → 38件全PASS
- [x] test_parser_units.py に実データテスト追加 → 19件全PASS
- [x] test_parser_pipeline.py に実データテスト追加 → 19件全PASS
- [x] `*FRICTION` under `*SURFACE INTERACTION` の read_inp() サポート（status-059で修正）
- [ ] material.inp を test_asset1 に追加するか、欠如テストとして維持するか判断
- [ ] VersionRelationParser: 同一version内のフォーマット間 next_version 抑制の検討
- [ ] パーサーキャッシュの実装（DRY、status-053からの継続TODO）
