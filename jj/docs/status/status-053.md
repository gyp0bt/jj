# status-053

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

AbaqusElsetParserの拡張（elset別element数・材料割り当てのproperty化）、
AbaqusDiffParserのパイプラインレベルテスト追加、
パーサーキャッシュ(DRY)のTODO追加。

## 実装内容

### 1. AbaqusElsetParser拡張（inp_parser.py）

AbaqusElsetParser（priority=98）が生成する`abaqus_elset`ノードに以下のプロパティを追加:

#### element_count
- `mesh_elset_summary`からelset別のelement数を取得してproperty化
- go_*.inp自身 + include先の`mesh_elset_summary`を統合（`merged_elset_summary`）

#### material（材料割り当て）
- `material_elsets`を逆引きして、各elsetに割り当てられた材料名をproperty化
- `material_elsets: {"Steel_S235": ["BODY"]}` → elset "BODY"に `material: "Steel_S235"` を設定

### 2. AbaqusDiffParserパイプラインテスト追加（test_parser_units.py）

diff_abq_blocks()は既にnode/element/nset/elsetのカウント・サイズ・品質を比較対象に含んでいたが、
パイプラインレベルでの検証テストが不足していた。以下5件を追加:

- **test_diff_properties_added_for_version_pair**: 隣接バージョンにdiff_from, diff_summary, diff_detailsが付与される
- **test_diff_contains_node_count_change**: ノード数変更がdiff_detailsに反映される
- **test_diff_contains_element_count_change**: 要素数変更がdiff_detailsに反映される
- **test_diff_contains_nset_elset_changes**: nset/elsetの変更がdiff_detailsに反映される
- **test_no_diff_for_identical_versions**: 同一内容のバージョンではdiffプロパティ非付与

### 3. AbaqusElsetParserテスト追加（test_parser_units.py）

以下7件を追加:

- **test_creates_elset_nodes_from_mesh_elset_summary**: mesh_elset_summaryからelsetノード生成
- **test_elset_has_element_count**: element_countプロパティ付与
- **test_elset_has_material_assignment**: 材料割り当てプロパティ付与
- **test_elset_from_include_child**: include先のmesh_elset_summaryからelement_count取得
- **test_has_elset_relation_created**: has_elsetリレーション生成
- **test_go_node_gets_elsets_property**: go_*.inpにelsetsプロパティ設定
- **test_material_only_elset_no_element_count**: material_elsetsのみの場合はelement_countなし

### 4. パーサーキャッシュTODO追加（roadmap.md）

ロードマップPhase 2-2に以下を追加:
- 個々のパーサーがincludeロジックで何度も同じファイルを読む可能性があるため、parseのキャッシュを実装
- read_inp()結果のABQDataをファイルパスで管理するキャッシュ
- IncludesRelationParser、AbaqusDiffParser、AbaqusMeshParser等が共有キャッシュを参照

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/connectors/abaqus/inp_parser.py` | AbaqusElsetParser: elset別element_count・材料割り当てproperty化 |
| `tests/test_parser_units.py` | AbaqusElsetParser 7件 + AbaqusDiffParser 5件 = 計12件テスト追加 |
| `docs/roadmap.md` | elset/diff完了マーク、パーサーキャッシュTODO追加 |
| `docs/status/status-053.md` | 本ステータスファイル |

## テスト結果

```
test_parser_units.py: 43 passed (新規12件追加、既存31件)
test_parser_pipeline.py: 31 passed
test_abaqus_connector.py: 62 passed
合計: 136 passed
```

## パーサー実行順

| priority | パーサー | 備考 |
|----------|---------|------|
| 20 | VersionRelationParser | |
| 30 | ResultRelationParser | |
| 31 | AssetRelationParser | |
| 32 | OutputRelationParser | |
| 33 | JsonPropertyParser | |
| 40 | IncludesRelationParser | |
| 50 | DirectoryRelationParser | |
| 60 | AbaqusInpParser | |
| 80 | AbaqusMeshParser | requires_full=True |
| 81 | MeshInheritParser | |
| 85 | AbaqusMaterialAssignmentParser | |
| 86 | AbaqusResultRelationParser | |
| 90 | AbaqusDiffParser | requires_full=True, **テスト5件追加** |
| 95 | ObsidianDailyParser | |
| 98 | AbaqusElsetParser / RootDirectoryParser | **拡張: element_count, material property** |
| 99 | EnrichmentOnlyFilter | |
| 100 | VocabFinalizer | |

## 確認事項・TODO

- [x] AbaqusElsetParserにelset別element_count追加 → テスト7件追加で確認済み
- [x] AbaqusElsetParserに材料割り当てproperty追加 → テスト追加で確認済み
- [x] AbaqusDiffParserでnode/nset/element/elsetの差分がプロパティに反映 → テスト5件追加で確認済み
- [ ] volumeなどのelement_qualityを個々のelsetごとに評価しproperty化（pymesh依存、将来対応）
- [ ] パーサーキャッシュの実装（DRY）: read_inp()結果をファイルパスでキャッシュし、複数パーサー間で共有
- [ ] go_inp element/elsetのabaqus_elsetノード化のE2Eテスト（graph.yaml書き出し確認）
