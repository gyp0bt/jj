[READMEへ戻る](../../README.md)

# services/storage

`.jj/storage` に保存するグラフデータの入出力を担当します。

## 役割
- 解析済みグラフデータの永続化（YAML/JSONなどのテキスト形式を想定）。
- `services/parse` が生成したグラフを読み書きするAPIを提供。
- 既存データから必要な情報を抽出するユーティリティを持つ。

## 主要インターフェース案
- `GraphStorage`
  - `load(project_root: Path) -> GraphModel`
  - `save(project_root: Path, graph: GraphModel) -> None`
  - `load_nodes(...)`, `load_relations(...)` など用途別APIも検討。

## 注意点
- `.jj/storage` 配下のファイルレイアウトは `docs/detail.md` の仕様を参照。
