[READMEへ戻る](../../README.md)

# パーサー層 仕様書

## 1. 概要

本ドメインは、プロジェクトフォルダ内のファイルを解析し、グラフデータ化するための基盤機能を提供します。ファイル名の命名規則から情報を抽出し、Nodeとして構造化します。

### 目的

- CAE業務で用いられる独自の命名規則を統一的に解析
- ファイル名からメタ情報（index, version, properties, tags）を抽出
- 拡張子や接頭辞によるファイルタイプの判別
- Obsidian等の外部ツール向けのパス変換

### 責務範囲

- `services/parse/` : 共通パーサー基盤とアダプター
  - `file_parse.py` : FileParse基底クラス
  - `obsidian_file_parse.py` : Obsidian向け拡張

---

## 2. FileParse（共通基盤）

### 2.1 命名規則

#### 新形式（推奨）

```
{prefix}_{prop1}_{prop2}_v{version}_idx{index}.{ext}
```

- **prefix**: ファイルタイプを示す（`go_`, `mesh_`, `material_`, `step_`）
- **prop**: プロパティ（`文字列+数値` or `文字列=数値` の形式）
- **version**: バージョン番号（`v1`, `v2`, ...）
- **index**: インデックス番号（`idx1`, `idx2`, ...）

例:
```
go_ncpu4_mem8_v2_idx1.inp
mesh_elem10000_v1_idx1.cdb
```

#### 旧形式（互換対応）

```
{prefix}_{prop1}_{prop2}.v{version}.{ext}
```

versionが `_v1` ではなく `.v1` で表現される形式も補完対象とする。

例:
```
go_sample.v1.inp
```

### 2.2 プロパティ抽出ルール

#### 採用条件

以下のいずれかに該当する文字列を `properties` として採用:

1. **数値付き形式**: `文字列+数値` (例: `ncpu4`, `mem16`)
2. **代入形式**: `文字列=数値` (例: `time=120`, `step=5`)

それ以外の文字列は **tag** として扱います。

#### 抽出例

| ファイル名 | properties | tags |
|-----------|-----------|------|
| `go_ncpu4_v1_idx1.inp` | `{"ncpu": "4", "ver": "1", "idx": "1"}` | `[]` |
| `go_sample_ncpu8_v2_idx3.inp` | `{"ncpu": "8", "ver": "2", "idx": "3"}` | `["sample"]` |
| `mesh_test_elem5000_v1_idx1.cdb` | `{"elem": "5000", "ver": "1", "idx": "1"}` | `["test"]` |

### 2.3 ファイルタイプ判別

接頭辞によりファイルタイプを分類します。

| 接頭辞 | ファイルタイプ | 説明 |
|-------|-------------|------|
| `go_` | `calculation_input` | 計算実行用の入力ファイル |
| `mesh_` | `mesh` | メッシュファイル |
| `material_` | `material` | 材料定義ファイル |
| `step_` | `step` | ステップ定義ファイル |

接頭辞がない場合は `unknown` として扱います。

### 2.4 拡張子判定

複数ドット拡張子（例: `.cas.h5`, `.tar.gz`）に対応します。

#### 判定ルール

1. 既知の複数ドット拡張子リストに最長一致
2. 該当しない場合は最後のドットから抽出

#### 既知の複数ドット拡張子

```python
MULTI_DOT_EXTENSIONS = [
    ".cas.h5",
    ".dat.h5",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
]
```

### 2.5 FileParseインターフェース

#### メソッド一覧

| メソッド | 戻り値 | 説明 |
|---------|-------|------|
| `get_index()` | `str \| None` | インデックス番号を取得 |
| `get_version()` | `str \| None` | バージョン番号を取得 |
| `get_props()` | `dict[str, str]` | プロパティ辞書を取得 |
| `get_tags()` | `list[str]` | タグリストを取得 |
| `get_basename()` | `str` | 拡張子を除いたファイル名 |
| `get_directory()` | `str` | ファイルのディレクトリパス |
| `get_file_type()` | `str` | ファイルタイプ（接頭辞から判定） |
| `get_file_group()` | `list[Path]` | 同一index+接頭辞のファイルグループ |
| `to_node()` | `Node` | ファイル情報をNodeに変換 |

---

## 3. ObsidianFileParse（Obsidian向け拡張）

### 3.1 パス変換

Obsidianの `[[wikilink]]` 形式に対応するため、プロジェクト内の実パスとObsidian用のパスを相互変換します。

### 3.2 ObsidianMapインターフェース

#### メソッド一覧

| メソッド | 戻り値 | 説明 |
|---------|-------|------|
| `get_frontmatter_path()` | `str` | Obsidian用の相対パス |
| `get_base_path()` | `str` | プロジェクト内の実パス |
| `to_frontmatter_path()` | `str` | 実パスをObsidian用パスに変換 |

### 3.3 Frontmatter生成

Obsidianのノート先頭に挿入するFrontmatterを自動生成します。

#### 生成例

```markdown
---
file: go_ncpu4_v1_idx1.inp
type: calculation_input
format: inp
idx: "1"
ver: "1"
ncpu: "4"
tags:
  - cae
  - abaqus
---
```

---

## 4. ファイルグループ機能

### 4.1 目的

同一の計算条件で生成された複数ファイルをグループ化します。

### 4.2 グループ化条件

- 同一の `index` を持つ
- 同一の接頭辞（`go_`, `mesh_` など）を持つ

### 4.3 グループ化例

以下のファイル群がある場合:

```
go_ncpu4_v1_idx1.inp
mesh_elem5000_v1_idx1.cdb
material_steel_v1_idx1.mat
go_ncpu8_v1_idx2.inp
```

- グループ1（idx1）: `go_ncpu4_v1_idx1.inp`, `mesh_elem5000_v1_idx1.cdb`, `material_steel_v1_idx1.mat`
- グループ2（idx2）: `go_ncpu8_v1_idx2.inp`

---

## 5. バイナリ対応

### 5.1 方針

ファイルがバイナリかテキストかは開くまで分からないため、常に `errors="ignore"` で読み込みを行います。

### 5.2 実装例

```python
def read_file_safe(path: Path) -> str:
    """バイナリファイルでもエラーを出さずに読み込む"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
```

---

## 6. 実装計画

### Phase 1: 基本パーサー実装（完了）

- [x] `FileParse` 基底クラスの実装
- [x] 命名規則の解析（index, version, props, tags）
- [x] 拡張子判定（複数ドット対応）
- [x] ファイルタイプ判別

### Phase 2: Obsidian対応（完了）

- [x] `ObsidianFileParse` の実装
- [x] パス変換機能
- [x] Frontmatter生成

### Phase 3: 拡張機能（直近）

- [ ] ファイルグループ機能の実装
- [ ] 旧形式（`.v1`）の完全対応
- [ ] バイナリファイルの判定と対応方針の明確化
- [ ] パフォーマンス最適化（大量ファイル対応）

### Phase 4: アダプター化（中期）

- [ ] ソフト固有のパーサーをアダプターとして分離
- [ ] Abaqus, Fluent, Dyna等のアダプター実装
- [ ] アダプター自動選択機構

---

## 7. 設計上の注意事項

### 7.1 拡張性

- 新しい接頭辞やファイルタイプは設定ファイルで追加可能にする
- アダプターパターンでソフト固有の解析ロジックを分離

### 7.2 パフォーマンス

- 大量ファイル（10,000件以上）を想定し、並列処理やキャッシュを検討
- ファイル読込は必要最小限に留める

### 7.3 エラーハンドリング

- 不正なファイル名でも例外を出さず、`unknown` として扱う
- ログで警告を出力し、ユーザーに気づかせる

---

## 8. テスト方針

### 単体テスト（pytest）

- `tests/services/test_file_parse.py` : FileParse各メソッドのテスト
- `tests/services/test_obsidian_parse.py` : ObsidianFileParse各メソッドのテスト

### テストケース例

- 新形式・旧形式の命名規則解析
- 複数ドット拡張子の正しい抽出
- プロパティとタグの分類
- ファイルグループ化の正確性
- バイナリファイルの読込エラー回避

---

## 9. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| コアデータモデル層 | ← パーサー層 | ファイル情報をNodeに変換 |
| 設定管理層 | ← パーサー層 | 拡張子マッピングや接頭辞定義を設定から取得 |
| noteコマンド層 | → パーサー層 | プロジェクト全体のファイルを解析 |
| アダプター層 | → パーサー層 | ソフト固有の解析ロジックを提供 |

---

## 10. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
