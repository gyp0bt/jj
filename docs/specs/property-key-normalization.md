[← README.md](../../README.md)

# プロパティキー正規化仕様書

> include継承時のバージョン付きファイル名によるキー膨張問題の対処

---

## 1. 問題

MeshInheritParser のキー競合エスケープ（`{child_name}:{key}`）で、
バージョン付きファイル名からキーが個別化してしまう。

### 例

```
go_idx1.inp
  *INCLUDE, input=mesh_v2.inp    → properties["mesh_v2:v"] = "2"
  *INCLUDE, input=mesh_v3.inp    → properties["mesh_v3:v"] = "3"
```

`mesh_v2:v` と `mesh_v3:v` は本質的に同じプロパティ（メッシュのバージョン）だが、
テーブルでは別カラムとして表示される。goノードが多い場合、
`mesh_v1:v`, `mesh_v2:v`, ... `mesh_vN:v` のN個のカラムが並ぶ。

### 影響

- テーブルのカラム数が膨張
- フィルタ・ソートが困難（同じ意味のカラムが複数）
- ギャラリーのグループ化も同様

## 2. 分析

### キー競合の発生パターン

1. **バージョン違い**: `mesh_v2.inp` / `mesh_v3.inp` → `mesh_v2:v`, `mesh_v3:v`
2. **インデックス違い**: `mesh_idx1.inp` / `mesh_idx2.inp` → `mesh_idx1:t`, `mesh_idx2:t`
3. **正常な競合**: `mesh_fine.inp` / `mesh_coarse.inp` → `mesh_fine:mesh_node_count`, `mesh_coarse:mesh_node_count`

パターン1,2はファイル名のバージョン/インデックス部分だけが異なるため正規化可能。
パターン3は意味のある区別なので正規化すべきではない。

### 既存の正規化

`get_base_key(column)` はコロン以降のベースキー（例: `mesh_v2:v` → `v`）を返すが、
プレフィックス（`mesh_v2`）の正規化はしていない。

## 3. 解決アプローチ

### 3.1 ファイル名の「ベース名」抽出

ファイル名からバージョン・インデックス修飾子を除去した「ベース名」を算出する。

```python
def get_file_base_name(filename: str) -> str:
    """ファイル名からversion/index修飾子を除去してベース名を返す

    Examples:
        "mesh_v2"    → "mesh"
        "mesh_v3"    → "mesh"
        "mesh_idx1"  → "mesh"
        "mesh_idx2"  → "mesh"
        "mesh_fine"  → "mesh_fine"  (バージョンでないので変更しない)

    パターン: _{vN}, _v{N}, _{idxN}, _idx{N} (末尾のみ)
    """
    import re
    # 末尾の _v{数字} または _idx{数字} を除去
    return re.sub(r'_(v\d+|idx\d+)$', '', filename)
```

### 3.2 MeshInheritParser での正規化適用

キー競合時のプレフィックスにベース名を使用する。

**変更前:**
```python
prefixed_key = f"{child.name}:{key}"
```

**変更後:**
```python
base_name = get_file_base_name(child.name)
prefixed_key = f"{base_name}:{key}"
```

### 3.3 同一ベース名の複数includeの値マージ

同じベース名を持つ複数ファイル（`mesh_v2`, `mesh_v3`）から同じキーが来る場合、
**後勝ち（最新バージョン優先）** とする。

```python
# mesh_v2:v = "2", mesh_v3:v = "3" → mesh:v = "3"（v3が後に処理される）
prefixed_key = f"{base_name}:{key}"
# 既に存在していても上書き（後勝ち）
node.properties[prefixed_key] = value
```

### 3.4 結果

```
# 変更前
go_idx1.properties = {
    "v": "1",           # 自身のバージョン
    "mesh_v2:v": "2",   # include元のバージョン
    "mesh_v3:v": "3",   # include元のバージョン
    "mesh_v2:mesh_node_count": 1000,
    "mesh_v3:mesh_node_count": 2000,
}

# 変更後
go_idx1.properties = {
    "v": "1",               # 自身のバージョン
    "mesh:v": "3",          # include元のバージョン（v3が後勝ち）
    "mesh:mesh_node_count": 2000,  # include元のメッシュ数（v3が後勝ち）
}
```

## 4. 代替案

### 4.1 config.yaml でマッピング定義

ユーザーが手動で正規化ルールを定義する。

```yaml
dashboard:
  property-key-aliases:
    "mesh_v*:v": "mesh:v"
    "mesh_v*:mesh_node_count": "mesh:mesh_node_count"
```

**メリット**: ロジックが個別ケースに依存しない
**デメリット**: ユーザー負担が大きい、ファイルが増えるたびに更新が必要

### 4.2 テーブル表示時のみ正規化（表示レイヤー）

グラフデータは変更せず、テーブル表示時にカラムをグルーピングする。

```python
def merge_versioned_columns(df: pd.DataFrame) -> pd.DataFrame:
    """バージョン付きプレフィックスカラムをマージ"""
    # mesh_v2:v, mesh_v3:v → mesh:v (最後の値を使用)
```

**メリット**: データモデルへの影響なし
**デメリット**: ギャラリーやエクスポートにも同じ正規化を適用する必要がある

### 4.3 推奨: 3.2（パーサーレベル）+ 4.1（configフォールバック）

パーサーで自動正規化を行い、自動正規化で対応できないケースはconfigで手動マッピング。

## 5. 影響範囲

| コンポーネント | 影響 |
|--------------|------|
| MeshInheritParser | プレフィックス生成ロジック変更 |
| get_base_key() | 変更不要（コロン以降を返すだけ） |
| sort_columns_by_vocab() | 変更不要 |
| テスト | test_parser_units.py のプレフィックスアサーション更新 |
| 既存データ | 再parseで自動修正（graph.yaml再生成） |

## 6. 実装フェーズ

| Phase | 内容 |
|-------|------|
| K-1 | `get_file_base_name()` 関数追加 + テスト |
| K-2 | MeshInheritParser のプレフィックス生成変更 |
| K-3 | 既存テスト更新 |
| K-4 | （オプション）config property-key-aliases 対応 |

## 7. 懸念事項

- **後方互換性**: 既存のgraph.yamlのプロパティキーが変わるため、再parseが必要
- **意図的な区別**: ユーザーが `mesh_v2:mesh_node_count` と `mesh_v3:mesh_node_count` を
  区別して見たい場合がある → configオプションで正規化ON/OFFを制御
- **ロジックの個別性**: バージョン記法が `_v{N}` 以外のパターン（例: `_rev2`, `_r3`）に
  拡張する可能性 → 正規化パターンをconfigで追加可能にする

```yaml
parse:
  file-base-name-patterns:
    - "_v\\d+$"     # _v2, _v3
    - "_idx\\d+$"   # _idx1, _idx2
    - "_rev\\d+$"   # _rev1, _rev2 (将来追加)
```
