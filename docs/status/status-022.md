[READMEへ戻る](../../README.md)

# 実装状況 (status-022)

## 概要

graph機能の作り込み。ファイル関係設定の拡張、アセット関係構築、日付パース機能、path-type-mapの評価順序改善、includes関係構築を実装。

## 実装内容

### 1. FileRelationsConfig の追加 (config/__init__.py)

ファイル関係の拡張子設定をハードコードから設定ファイルに移行。

```python
@dataclass(frozen=True)
class FileRelationsConfig:
    """ファイル関係設定: 入力/結果/アセットファイルの拡張子マッピング"""
    input_extensions: frozenset[str]   # 入力ファイル拡張子
    result_extensions: frozenset[str]  # 結果ファイル拡張子
    asset_extensions: frozenset[str]   # アセットファイル拡張子
```

**設定例 (default-config.yaml)**:
```yaml
file-relations:
  input-extensions:
    - ".inp"
    - ".cas.h5"
  result-extensions:
    - ".odb"
    - ".sta"
  asset-extensions:
    - ".modfem"
    - ".stl"
```

### 2. アセット関係（derived_from）の構築 (services/graph/__init__.py)

同じbasenameを持つ入力ファイルとアセットファイル間に `derived_from` 関係を構築。

```
mesh.inp --[derived_from]--> mesh.modfem
```

### 3. 日付パース機能の強化 (services/parse/file_parse.py)

**新規メソッド**:
- `get_date()`: YYMMDD または YYYYMMDD 形式の日付を抽出
- `get_date_formatted()`: YYYY-MM-DD 形式に変換

```python
parser = FileParse("260205_構造解析_idx1.pptx")
parser.get_date()           # "260205"
parser.get_date_formatted() # "2026-02-05"
```

**特徴**:
- YY > 50 の場合は1900年代として扱う（例: 99 → 1999）
- 日付トークンは tags から自動除外される

### 4. path-type-map の評価順序改善 (config/__init__.py)

より具体的なパターンを先に評価するようにソート。

**具体性の評価基準**:
1. ワイルドカードの少なさ（`**`は2つ分カウント）
2. ディレクトリの深さ
3. パターンの長さ

```python
# 例: 以下の2つのパターンがある場合
"**go_*": {"*.inp": "汎用計算"}      # より汎用的
"**/reports/*": {"*.pptx": "報告書"}  # より具体的 → 先に評価

# reports/260205.pptx は「報告書」にマッチ
```

### 5. includes関係の構築 (services/graph/__init__.py)

Abaqus inpファイルの `*include` ディレクティブを解析して `includes` 関係を構築。

```
go_idx1.inp --[includes]--> material.inp
go_idx1.inp --[includes]--> mesh.inp
```

### 6. テストコードの拡張 (tests/test_graph_feature.py)

11件の新規テストを追加（計38件）:

- **TestDateParsing**: 日付パース機能（YYMMDD/YYYYMMDD、1900年代、tags除外）
- **TestFileRelationsConfig**: 拡張子設定のテスト
- **TestAssetRelations**: derived_from関係のテスト
- **TestPathTypeMapOrdering**: 評価順序のテスト
- **TestIncludesRelations**: includes関係のテスト

## テスト結果

```
38 passed in 0.93s
```

全テストがパス。既存の27件 + 新規11件。

## ファイル構成の変更

```
jj/
├── assets/
│   └── default-config.yaml   (変更: file-relationsセクション追加)
├── config/
│   └── __init__.py           (変更: FileRelationsConfig追加、PathTypeMapConfigソート)
├── services/
│   ├── parse/
│   │   └── file_parse.py     (変更: 日付パース機能追加)
│   └── graph/
│       └── __init__.py       (変更: derived_from/includes関係構築)
├── tests/
│   └── test_graph_feature.py (変更: 11件のテスト追加)
└── docs/
    └── status/
        └── status-022.md     (新規)
```

## 新しい関係タイプ

| 関係ラベル | 説明 | 方向 |
|---|---|---|
| next_version | バージョン系列 | v1 → v2 |
| same_index_group | 同一インデックスグループ | 代表 → メンバー |
| result_of | 計算結果 | 結果ファイル → 入力ファイル |
| derived_from | 派生元 | 入力ファイル → アセットファイル |
| includes | インクルード | インクルード元 → インクルード先 |

## 設定ファイルの拡張

### file-relations セクション

```yaml
file-relations:
  # 入力ファイルとして認識する拡張子
  input-extensions:
    - ".inp"      # Abaqus
    - ".cas.h5"   # Fluent
    - ".k"        # LS-DYNA
    - ".key"      # LS-DYNA
    - ".dat"      # 汎用入力
  # 結果ファイルとして認識する拡張子
  result-extensions:
    - ".odb"      # Abaqus ODB
    - ".sta"      # Abaqus status
    - ".csv"      # 抽出データ
    - ".json"     # 処理済みデータ
  # アセットファイルの拡張子
  asset-extensions:
    - ".modfem"   # 修正済みメッシュ
    - ".stl"      # STLメッシュ
```

## TODO（今後の課題）

- [ ] jj n を jj g に統合
- [ ] includes関係のパフォーマンス最適化（ファイル読み込みのキャッシュ）
- [ ] 日付の検証機能追加（不正な日付の検出）
- [ ] CAEソフト別の拡張子プリセット機能

## 設計上の懸念事項

1. **includes関係のパフォーマンス**: 現在は全inpファイルを読み込んで解析するため、大規模プロジェクトでは遅くなる可能性がある。オプションで無効化できるようにすることを検討
2. **日付形式の拡張**: 現在はYYMMDD/YYYYMMDDのみ対応。YYYY-MM-DD形式への対応も検討

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-021.md](./status-021.md)
**次回**: status-023.md (未作成)
