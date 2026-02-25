[READMEへ戻る](../../README.md)

# services/storage

`.j2/storage` に保存するグラフデータの入出力を担当します。

## 役割
- 解析済みグラフデータの永続化（YAML/JSONなどのテキスト形式を想定）。
- `services/parse` が生成したグラフを読み書きするAPIを提供。
- 既存データから必要な情報を抽出するユーティリティを持つ。

## 主要インターフェース案
- `GraphStorage`
  - `load(project_root: Path) -> GraphModel`
  - `save(project_root: Path, graph: GraphModel) -> None`
  - 既定で `.j2/storage/graph.yaml` を読み書きする。
  - `graph.json` を使う場合は拡張子を指定する。

## 保存フォーマット
- `GraphModel` の直列化結果を `.j2/storage/graph.yaml` に保存する。
- トップレベルは `nodes` と `relations` の2つ。

## 注意点
- `.j2/storage` 配下のファイルレイアウトは `docs/detail.md` の仕様を参照。
