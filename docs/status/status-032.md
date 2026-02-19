[← README.md](../../README.md)

# status-032: メッシュ統計キャッシュ — コンテンツハッシュによるファイル間共有

- **日付**: 2026-02-19
- **マイルストーン**: M2（パフォーマンス改善）
- **ブランチ**: claude/optimize-file-parsing-hhX9f
- **前提**: status-031（パフォーマンス最適化: インデックス・IgnoreConfig・CSVサマリー）

---

## 背景

パラメーターや境界条件のみが異なる.inpファイル群（例: `go_idx1.inp`, `go_idx2.inp`）で、
メッシュ部分（`*NODE`, `*ELEMENT`等）が同一の場合、pymeshによるメッシュ統計計算を
毎回実行するのは無駄。メッシュ統計をコンテンツハッシュでディスクキャッシュし、
同一メッシュの2ファイル目以降はpymesh解析をスキップする。

## 実施内容

### 1. メッシュコンテンツハッシュ計算（`_compute_mesh_content_hash`）

**ファイル**: `jj/services/parse/connectors/abaqus/mesh_parser.py`

- .inpファイルのメッシュ定義部分のみをSHA256ハッシュ化
- **ハッシュ対象**: `*NODE`, `*ELEMENT`, `*ELSET`, `*NSET`セクションの全行
- **ハッシュ除外**: `*PARAMETER`, `*BOUNDARY`, `*STEP`, `*MATERIAL`, `*CLOAD`, `*DLOAD`等
- `*INCLUDE`参照: ファイルパス+mtimeをハッシュに含める（参照先変更時にキャッシュ無効化）
- コメント行（`**`）はハッシュに影響しない
- メッシュ定義がないファイルはNoneを返す（キャッシュ対象外）

### 2. ディスクキャッシュ保存/読み込み

- 既存`GraphStorage.plugin_cache`メカニズムを`"mesh_stats"` namespaceで使用
- キャッシュキー: メッシュコンテンツハッシュ（ファイルパスではなく内容ベース）
- キャッシュ値: `{"stats": {...}, "element_quality": {...}, "topology_groups": [...]}`
- 保存先: `.jj/storage/plugin_cache/mesh_stats/{sha256_hash}.pickle`
- 既存のクリーンアップポリシー（30日/100ファイル上限）がそのまま適用される

### 3. AbaqusMeshParser統合

**処理フロー変更**:

```
従来:
  .inpファイル → is_file_modified? → read_inp → pymesh解析 → プロパティ付与

改善後:
  .inpファイル → is_file_modified?
    → メッシュコンテンツハッシュ計算（軽量テキストスキャン）
    → ディスクキャッシュ参照
      → ヒット: キャッシュからプロパティ付与（pymeshスキップ）
      → ミス: pymesh解析 → プロパティ付与 → ディスクキャッシュ保存
```

**効果**:
- 1000条件×同一メッシュの場合: pymesh解析1回 + 999回キャッシュヒット
- ハッシュ計算はテキストスキャンのみで軽量（pymeshの数百分の1）

---

## テスト結果

- 新規テスト: 16件全通過
  - TestComputeMeshContentHash: 9件（ハッシュ計算の正確性）
  - TestMeshStatsDiskCache: 3件（ディスクキャッシュ動作）
  - TestMeshStatsCacheIntegration: 4件（統合テスト・E2E）
- 既存テスト: 74件通過（影響なし）
- lint: ruff check + ruff format 通過

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `jj/services/parse/connectors/abaqus/mesh_parser.py` | 修正（ハッシュ計算・キャッシュ統合） |
| `jj/tests/test_mesh_stats_cache.py` | 新規（16テスト） |
| `docs/status/status-032.md` | 新規 |
| `docs/status/status-index.md` | 修正 |

---

## 残TODO

- [ ] パーサー並列化の検討（multiprocessing/asyncio、依存関係グラフ構築が前提）
- [ ] chardetエンコーディング検出のUTF-8ファースト最適化
- [ ] INP読み込みの段階的解析（軽量/重量モード分離の拡充）
- [ ] サマリーモード時のダッシュボード表示対応（統計量プロットUI）
