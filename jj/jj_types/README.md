[READMEへ戻る](../README.md)

# types

データ型定義と Pydantic モデルを配置します。

## 方針
- `Node`, `Relation`, `GraphModel` などグラフデータの型をここで管理。
- バリデーションは Pydantic を利用し、入出力の整合性を担保。

## 主要モデル
- `Node`: `id`, `type`, `name`, `format`, `properties`
- `Relation`: `id`, `label`, `node1_id`, `node2_id`
- `GraphModel`: `nodes`, `relations`
