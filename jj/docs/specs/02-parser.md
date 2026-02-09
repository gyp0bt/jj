[READMEへ戻る](../../README.md)

# パーサー層 仕様書

## 1. 概要

本ドメインは2つの層で構成されます。

1. **ファイル名解析層**（`FileParse` / `FileNameParser`）: ファイル名の命名規則からメタ情報を抽出
2. **グラフエンリッチメント層**（`AbstractFileParser` パイプライン）: ProjectGraphにリレーション・プロパティを付与

### 責務範囲

```
services/parse/
├── base.py             # FileNameParser（ファイル名解析）+ AbstractFileParser（グラフパーサー基底）
├── file_parse.py       # FileParse / ObsidianFileParse（レガシー互換）
├── parsers/            # 共通グラフパーサーサブクラス群
│   ├── version_parser.py      # バージョン・グループ関係
│   ├── output_parser.py       # result_of, has_output, derived_from, includes
│   ├── directory_parser.py    # contains, root directory
│   └── enrichment_filter.py   # .sta/.msg/.dat ノード除外
└── connectors/         # ソフト固有パーサーサブクラス群
    ├── abaqus/
    │   ├── inp_parser.py       # material Node化, *PARAMETER抽出
    │   ├── result_parser.py    # .sta/.msg/.dat 解析・プロパティ伝搬
    │   ├── mesh_parser.py      # pymesh メッシュ統計
    │   └── diff_parser.py      # バージョン間差分
    └── obsidian/
        └── daily_parser.py     # daily note 解析
```

---

## 2. ファイル名解析層

### 2.1 命名規則

#### 新形式（推奨）

```
{prefix}_{prop1}_{prop2}_v{version}_idx{index}.{ext}
```

例: `go_ncpu4_mem8_v2_idx1.inp`

#### 旧形式（互換対応）

```
{prefix}_{prop1}_{prop2}.v{version}.{ext}
```

例: `go_sample.v1.inp`

### 2.2 ファイルタイプ判別

| 接頭辞 | FileType | 説明 |
|-------|----------|------|
| `go_` | `go` | 計算実行用の入力ファイル |
| `mesh_` | `mesh` | メッシュファイル |
| `material_` | `material` | 材料定義ファイル |
| `step_` | `step` | ステップ定義ファイル |
| （なし） | `unknown` | 接頭辞なし |

### 2.3 FileNameParser / FileParse インターフェース

| メソッド | 戻り値 | 説明 |
|---------|-------|------|
| `get_index()` | `str` | インデックス番号を取得 |
| `get_version()` | `str` | バージョン番号を取得 |
| `get_props()` | `dict[str, str]` | プロパティ辞書を取得 |
| `get_tags()` | `list[str]` | タグリストを取得 |
| `get_basename()` | `str` | 拡張子を除いたファイル名 |
| `get_file_type()` | `FileType` | ファイルタイプ（接頭辞から判定） |

---

## 3. グラフエンリッチメント層（Phase R）

### 3.1 AbstractFileParser パターン

`AbstractFileParser` のサブクラスを定義すると `__init_subclass__` により自動的にレジストリに登録される。`parse()` 関数で全パーサーが `priority` 順に適用される。

```python
class MyParser(AbstractFileParser):
    priority = 50
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        return graph
```

### 3.2 パーサー実行順序

| priority | パーサー | 責務 |
|----------|---------|------|
| 20 | VersionRelationParser | next_version, same_index_group |
| 30-40 | Result / Asset / Output / Includes | result_of, derived_from, has_output, includes |
| 50 | DirectoryRelationParser | contains |
| 60 | AbaqusInpParser | material Node化 |
| 70 | AbaqusResultParser | .sta/.msg/.dat 解析 |
| 80 | AbaqusMeshParser | pymesh統計 |
| 85-86 | MaterialAssignment / IncludeProperty | プロパティ伝搬 |
| 90 | AbaqusDiffParser | バージョン差分 |
| 95 | DailyNoteParser | daily note |
| 98 | RootDirectory / ElsetParser | root Node, elset Node |
| 99 | EnrichmentOnlyFilter | .sta/.msg/.dat 除外 |

### 3.3 parse() パイプライン

GraphService.parse_project() はファイルスキャン→ノード生成のみを行い、グラフエンリッチメントは `parse()` に委譲する。

---

## 4. 実装状況

- [x] FileParse / FileNameParser
- [x] AbstractFileParser.__init_subclass__ パターン + parse() + priority制御
- [x] 全パーサーサブクラスの抽出（16パーサー）
- [x] ProjectGraph 型定義
- [x] test_asset1 統合テスト（29件パス）
- [ ] レガシーテストの新パイプライン対応

---

## 5. 参考資料

- [parseコネクター仕様書](./07-adapter.md)
- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
