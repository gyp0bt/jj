# status-049

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

エクスポート機能の大幅強化（CSV単位系・カラム選択）、JSONプロパティ平坦化方式変更、
メッシュプロパティ継承パーサー追加、ダッシュボード要件定義。

## 実装内容

### 1. ExportConfig追加（config/__init__.py）
- `ExportConfig`データクラスを新設
  - `csv-columns`: CSVエクスポート時の出力カラムリスト（指定順を保持）
  - `units`: カラム名→単位マッピング（例: `応力: MPa`）
  - `csv-unit-format`: CSV単位表示形式（`"header"` or `"row"`）
- `GraphConfig`に`export`フィールドとして統合
- default-config.yamlにexportセクション追加

### 2. JSONファイル名vocab置換修正
- **変更前**: JSONキー（ファイル内容の辞書キー）にvocab置換を適用（誤り）
- **変更後**: JSONファイル名のサフィックスに`_`区切りでvocab置換を適用
  - 例: `go_idx0.v29_dat_warning.json` → vocab `dat:データ`, `warning:警告` → `データ_警告`

### 3. JSONプロパティ平坦化方式変更（json_property_parser.py）
- **変更前**: `properties["stress"] = {"center": 0.25, "edge": 1.0}` （ネスト辞書）
- **変更後**: `properties["stress.center"] = 0.25`, `properties["stress.edge"] = 1.0` （"."繋ぎ平坦化）
- JSON内の階層構造は再帰的に"."区切りで平坦化
- `_flatten_json()`関数として公開

### 4. CSVエクスポート強化（info.py）
- **カラム選択**: config `export.csv-columns` で出力カラムを制限
  - `name`, `type`, `format`は常に含まれる（base keys）
  - config指定順にカラムが並ぶ
  - CLI `--columns` でconfig設定を上書き可能
- **単位表示**:
  - `"header"`形式（デフォルト）: `応力[MPa]`, `変位[mm]` のようにヘッダーに単位付加
  - `"row"`形式: 1行目カラム名、2行目単位行
  - CLI `--unit-format` でconfig設定を上書き可能
- CSVの書き込みをDictWriter→csv.writerに変更（単位ヘッダー対応のため）

### 5. MeshInheritParser新規作成（mesh_inherit_parser.py）
- priority=81（IncludesRelationParser(40)、AbaqusMeshParser(80)の後に実行）
- go_*.inpが`*INCLUDE`で参照するmesh_*.inpのプロパティを継承
  - 例: `mesh_t50_v1.inp`のt:50 → go_*.inpにも付与
  - メッシュ統計情報（mesh_node_count等）も継承
- index/version/path/tags/active/verbose_name等のメタプロパティは除外
- vocab変換後のidx/vキーも除外対象

### 6. CLI引数追加（cli/graph.py）
- `--unit-format {header,row}`: CSV単位表示形式の指定
- `--columns col1 col2 ...`: CSVエクスポートカラムの指定（config上書き）

### 7. ダッシュボード要件定義（docs/specs/11-dashboard-requirements.md）
- shared/example/dashboard_example/post.pyを分析
- UIコンポーネント要件（AgGrid、サイドバーフィルタ、Plotly散布図/棒グラフ、画像ギャラリー）
- データフロー設計
- Phase D1-D4実装計画との対応付け
- 依存ライブラリ一覧

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config/__init__.py` | ExportConfig追加、GraphConfigにexportフィールド統合 |
| `services/parse/parsers/json_property_parser.py` | vocab置換_区切り、JSON平坦化方式変更 |
| `services/parse/parsers/mesh_inherit_parser.py` | **新規**: メッシュプロパティ継承パーサー |
| `services/parse/parsers/__init__.py` | MeshInheritParser登録 |
| `services/service/info.py` | CSVカラム選択、単位マッピング、キー順保持 |
| `services/cli/graph.py` | --unit-format, --columns引数追加 |
| `shared/assets/default-config.yaml` | exportセクション追加 |
| `docs/specs/11-dashboard-requirements.md` | **新規**: ダッシュボード要件定義 |
| `tests/test_selection_and_export.py` | 14テスト追加 |

## テスト結果

```
50 passed (test_selection_and_export.py)
14 新規テスト追加:
  - ExportConfig: 4テスト（デフォルト値、csv-columns/units、バリデーション、GraphConfig統合）
  - CSVエクスポート単位: 2テスト（header形式、row形式）
  - CSVエクスポートカラム: 2テスト（config制限、キー順保持）
  - JSONプロパティ平坦化: 4テスト（単純、ネスト、プレフィックスなし、リスト値）
  - MeshInheritParser: 2テスト（登録確認、priority確認）
```

## パーサー実行順（更新）

| priority | パーサー | 備考 |
|----------|---------|------|
| 20 | VersionRelationParser | |
| 30 | ResultRelationParser | |
| 31 | AssetRelationParser | |
| 32 | OutputRelationParser | |
| 33 | JsonPropertyParser | **変更**: "."繋ぎ平坦化、ファイル名vocab置換 |
| 40 | IncludesRelationParser | |
| 50 | DirectoryRelationParser | |
| 60 | AbaqusInpParser | |
| 80 | AbaqusMeshParser | requires_full=True |
| **81** | **MeshInheritParser** | **新規**: meshプロパティ継承 |
| 85 | AbaqusMaterialAssignmentParser | |
| 86 | AbaqusResultRelationParser | |
| 90 | AbaqusDiffParser | |
| 95 | ObsidianDailyParser | |
| 98 | AbaqusElsetParser | |
| 99 | EnrichmentOnlyFilter | |
| 100 | VocabFinalizer | |

## 確認事項・TODO

- [ ] メッシュプロパティ継承の実プロジェクトでの動作検証（includes関係が正しく構築される前提）
- [ ] NG領域定義のconfig化設計（Phase D2以降）
- [ ] カスタム派生メトリクス（余長率、周波数）の計算パイプライン設計
- [ ] CSVエクスポートの部分一致カラム指定（`stress.*`のようなglobパターン）の検討
