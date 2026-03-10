[← README.md](../../README.md)

# status-072: プロパティ外部化（Property Externalization）

**日付**: 2026-03-10
**ブランチ**: claude/refactor-graph-data-storage-Wsmdj
**作業者**: Claude

## 概要

graph.yaml に直接書き込まれていた重いプロパティ（配列・dict）を、
ノード単位のJSONファイルに分離し、オンデマンドでロードする仕組みを実装。

## 実施内容

### 設計

- 仕様書: `docs/specs/property-externalization.md`
- graph.yaml にはスカラー値のみ保持
- 重いプロパティ（list/dict, 要素数>0）は `.j2/storage/properties/node_{id}.json` に分離
- `_ext_keys` マーカーで外部化されたキーを追跡
- ロード時はデフォルト軽量、`resolve_externalized=True` でフルロード
- `load_node_properties(node_id)` でオンデマンドアクセス

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/graph/storage/__init__.py` | プロパティ外部化ロジック（save/load/on-demand） |
| `services/sdk/cache.py` | CacheProviderプロトコルに `load_node_properties`, `save_node_properties` 追加 |
| `tests/test_storage_service.py` | 9件の新規テスト追加 |
| `tests/test_sdk.py` | MockCacheProvider にプロトコル新メソッド追加 |
| `docs/specs/property-externalization.md` | 仕様書 |

### 新規テスト（9件）

1. `test_save_externalizes_heavy_properties` - save時の外部化動作
2. `test_load_default_lightweight` - デフォルトの軽量ロード
3. `test_load_with_resolve_externalized` - フルロード（resolve=True）
4. `test_load_node_properties_on_demand` - オンデマンドロード
5. `test_save_node_properties_standalone` - 直接保存・読み込み
6. `test_scalar_only_node_no_externalization` - スカラーのみノードは外部化しない
7. `test_empty_list_dict_not_externalized` - 空list/dictは外部化しない
8. `test_orphan_properties_cleaned_up` - 孤立ファイルの自動削除
9. `test_roundtrip_save_load_resolve` - ラウンドトリップの完全性

### テスト結果

- 全1870テスト合格、102スキップ（optional依存による想定内）
- ruff check / ruff format 合格

## 設計上の判断

- **外部化の閾値**: list/dictで要素数>0を外部化対象とした。サイズベースの閾値は
  将来的に調整可能だが、シンプルに型ベースで判定することで予測可能性を確保。
- **後方互換性**: `load()` のデフォルトは軽量ロード。既存コードで重いプロパティに
  アクセスする場合は `resolve_externalized=True` を指定するか、
  `load_node_properties()` でオンデマンド取得。
- **孤立ファイルの自動掃除**: `save()` 時にグラフから消えたノードの外部ファイルを
  自動削除し、ゴミが残らないようにした。

## TODO

- [ ] ダッシュボードやエクスポート等、重いプロパティにアクセスする箇所で
  `resolve_externalized=True` または `load_node_properties()` への移行
- [ ] GraphService.load() のラッパーに resolve_externalized パラメータを伝搬
- [ ] パフォーマンスベンチマーク（大規模プロジェクトでのロード時間比較）

## 懸念事項・次のAIへの引き継ぎ

- `load()` のデフォルトが軽量ロードに変わったため、重いプロパティに依存する
  既存コードがある場合は `resolve_externalized=True` の追加が必要。
  ただし現時点ではパーサーが書き込むだけで、load後に直接参照する箇所は限定的。
- プロパティの外部化判定は型ベース（list/dict）であり、巨大な文字列値等は
  対象外。将来的にサイズベースの閾値を追加する余地あり。
