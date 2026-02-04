[READMEへ戻る](../../README.md)

# 実装状況 (status-7)

## 概要
- `.jj/storage` のYAML/JSON保存を担う `GraphStorage` を追加。
- グラフデータのPydanticモデル（`Node`/`Relation`/`GraphModel`）を整備。
- グラフ保存フォーマットの仕様を `docs/detail.md` と `services/storage/README.md` に明記。

## 変更点
- `types` に `Node`/`Relation`/`GraphModel` を実装し、`GraphModel.empty()` を追加。
- `services/storage` に `GraphStorage` を実装し、`.jj/storage/graph.yaml`/`graph.json` の読み書きを追加。
- `docs/detail.md` に `.jj/storage` の保存フォーマット例を追加。
- `README.md` と `docs/roadmap.md` の記述を更新。

## TODO
- 既存submit機能の `run` へのリファクタリング方針作成。
- `types` のPydanticモデル拡張（Node/Relationのproperties内容、GraphModelのバリデーション詳細）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-7.md`です。
- `.jj/storage/graph.yaml` を起点に、`GraphStorage` と `parse` の接続方法を検討してください。
- README/roadmap/statusを更新し、引き継ぎ可能な形を維持してください。

## コミット
- feat: add graph storage and graph models
