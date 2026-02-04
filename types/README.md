[READMEへ戻る](../README.md)

# types

データ型定義と Pydantic モデルを配置します。

## 方針
- `Node`, `Relation`, `GraphModel` などグラフデータの型をここで管理。
- バリデーションは Pydantic を利用し、入出力の整合性を担保。
