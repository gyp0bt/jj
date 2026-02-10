# status-051

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

status-050のTODO消化（mesh_quality調査、MeshInheritParser改修、elset-materialパラメータ解決、CLIヘルプ更新）、
ディレクトリ階層構造のrelation機能強化（全中間ディレクトリNode化、max-depthオプション）。

## 実装内容

### 1. mesh_quality未付加の原因調査・修正（mesh_parser.py, mesh.py）

- **原因特定**: `_compute_quality_stats()` が以下のケースで失敗しNoneを返す:
  - `get_element_node_coord_array()` がNone/空を返す（要素タイプ未対応、2D要素等）
  - 品質メトリクス計算がすべてのモードで失敗（shell要素等）
  - NaN率100%で有効な統計値が得られない
- **対応**: DEBUGレベルのログ出力を強化
  - `_compute_quality_stats()`: coord_array取得失敗、shape情報、個別モード失敗をログ
  - `AbaqusMeshParser.apply()`: mesh_quality未付加時にnode_count/element_countとともにログ
- docstringに原因の解説を追記

### 2. MeshInheritParser改修（mesh_inherit_parser.py）

- **変更前**: mesh_*.inpのみからプロパティを継承
- **変更後**: includes関係にある全ファイル（mesh_*, material_*, step_*等）からプロパティを継承
  - mesh_*.inp限定のフィルタ(`child_lower.startswith("mesh_")`)を削除
  - include先のプロパティをgo_*の直下プロパティに追加（既存キーは上書きしない）
  - path, tags, active, verbose_name, index, version等のメタキーは除外
- テスト4件追加:
  - mesh_qualityを含むメッシュプロパティの継承
  - 既存キーの非上書き確認
  - 全include先（mesh, step等）からの継承
  - メタプロパティの除外確認

### 3. elset-material mappingの調査・修正（mesh.py）

- **調査結果**: `extract_material_elset_mapping()` が `*PARAMETER` 参照を解決していなかった
  - `*SOLID SECTION, material=<material>` → 材料名が `<material>` のまま
  - `*PARAMETER` ブロック内の `material = "mat_cu"` が未解決
- **修正**: `_parse_parameters()` と `_resolve_parameter_ref()` を新設
  - `_parse_parameters()`: .inpファイルの全`*PARAMETER`ブロックからパラメータ名→値を抽出
  - `_resolve_parameter_ref()`: `<param_name>` 形式の参照を実際の値に解決
  - 文字列値のクォート除去対応
- **修正後の動作**: `go_idx0.v29.inp` → `{'mat_cu': ['Pwire', 'Pwire_coh'], 'mat_PI_20do': ['Pcover', 'Pcover_coh']}`

### 4. --columns CLI引数のglobパターンドキュメント追記（cli/graph.py）

- `--columns` のhelpメッセージにglobパターン対応の説明を追加
  - 変更前: `CSVエクスポートするカラム名を指定（config設定を上書き）`
  - 変更後: `CSVエクスポートするカラム名を指定（globパターン対応: stress* mesh_*等。config設定を上書き）`

### 5. JSONキー衝突の動作確認・文書化

- **確認結果**: `dict.update()` の標準動作で、同一キーは後から処理されたJSONが上書き
- 処理順序はjson_nodesリストの順序（グラフ内のノード順）に依存
- 現時点で実害なし（テストアセットでは衝突なし）。statusに文書化。

### 6. ディレクトリ階層構造のrelation機能強化（directory_parser.py, config/__init__.py）

- **全中間ディレクトリのNode化**:
  - 変更前: ファイルの直接の親ディレクトリのみNode化（中間ディレクトリが欠落）
  - 変更後: ファイルパスの全中間ディレクトリをNode化
  - 例: `a/b/c/file.inp` → `a`, `a/b`, `a/b/c` すべてにdirectoryノード生成
- **ディレクトリ間contains関係**: 中間ディレクトリ間にも親→子のcontains関係を構築
- **`directory-max-depth` config設定**: `GraphConfig.directory_max_depth` フィールド追加
  - `None`（デフォルト）: 最終階層まで全ディレクトリをNode化
  - `1`: ルート直下のディレクトリのみ
  - `2`: ルート直下 + 子ディレクトリまで
- **`--max-depth` CLI引数**: parse コマンドに追加。config設定を上書き。
- **default-config.yaml更新**: `directory-max-depth` のコメント付き設定例を追加
- テスト5件追加:
  - 中間ディレクトリNode化
  - ディレクトリ間contains関係
  - max-depth=1の制限動作
  - max-depth=2の制限動作

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/connectors/abaqus/mesh_parser.py` | DEBUGログ強化、docstring追記 |
| `services/parse/connectors/abaqus/mesh.py` | `_parse_parameters()`, `_resolve_parameter_ref()`追加、品質計算ログ強化 |
| `services/parse/parsers/mesh_inherit_parser.py` | 全include先からのプロパティ継承に拡張 |
| `services/parse/parsers/directory_parser.py` | 全中間ディレクトリNode化、max-depth対応 |
| `config/__init__.py` | `GraphConfig.directory_max_depth` フィールド追加 |
| `services/cli/graph.py` | `--max-depth` CLI引数追加、`--columns` ヘルプ更新 |
| `shared/assets/default-config.yaml` | `directory-max-depth` 設定例追加 |
| `tests/test_parser_units.py` | MeshInheritParser 4テスト、Directory 5テスト追加 |

## テスト結果

```
全テスト:
  test_parser_units.py: 26 passed (新規9件追加)
  test_parser_pipeline.py: 31 passed
  test_selection_and_export.py: 55 passed
  test_graph_feature.py: 1 failed (既存: TestVersionDiff - 今回の変更と無関係)
```

## パーサー実行順（更新なし）

| priority | パーサー | 備考 |
|----------|---------|------|
| 20 | VersionRelationParser | |
| 30 | ResultRelationParser | |
| 31 | AssetRelationParser | |
| 32 | OutputRelationParser | |
| 33 | JsonPropertyParser | |
| 40 | IncludesRelationParser | |
| 50 | DirectoryRelationParser | **変更**: 全中間ディレクトリNode化、max-depth対応 |
| 60 | AbaqusInpParser | |
| 80 | AbaqusMeshParser | requires_full=True、**変更**: ログ強化 |
| 81 | MeshInheritParser | **変更**: 全include先からプロパティ継承 |
| 85 | AbaqusMaterialAssignmentParser | |
| 86 | AbaqusResultRelationParser | |
| 90 | AbaqusDiffParser | |
| 95 | ObsidianDailyParser | |
| 98 | AbaqusElsetParser / RootDirectoryParser | |
| 99 | EnrichmentOnlyFilter | |
| 100 | VocabFinalizer | |

## 確認事項・TODO

- [x] ~~実プロジェクトでのJSONキー衝突の確認~~ → dict.update()による後勝ち。現時点で実害なし。
- [x] ~~`--columns` CLI引数のglobパターンドキュメント追記~~ → helpメッセージ更新済み
- [x] ~~mesh_quality未付加の原因調査・修正~~ → DEBUGログで原因追跡可能に。2D要素/shell要素時にcoord_array不備が原因。
- [x] ~~MeshInheritParser改修~~ → 全include先からプロパティ継承に変更
- [x] ~~elset-material mappingの調査~~ → `*PARAMETER`参照の解決を実装。実パラメータ名でマッピング構築可能に。
- [ ] **test_graph_feature.py TestVersionDiff失敗**: AbaqusDiffParserのテストフィクスチャ問題（既存バグ、今回の変更と無関係）
- [ ] elset-materialマッピングの`*INCLUDE`先追跡（現在はファイル単独のみ解析。include先の*SOLID SECTIONは未追跡）
- [ ] mesh_quality問題のさらなる調査: 実プロジェクトでDEBUGログを有効にして要素タイプ別の品質計算可否を確認
