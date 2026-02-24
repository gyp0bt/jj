[READMEへ戻る](../../README.md)

# 実装状況 (status-008)

## 概要
- `jj r` の実行ログ保存とトレース収集の初期実装を追加。
- スクリプト型は差分スナップショットから生成ファイル候補を抽出。

## 変更点
- `RunService` を追加し、実行ログを `.j2/storage/run` に保存するようにした。
- `jj r -- <command>` をCLIに追加し、実行結果・ログパス・トレースを表示するようにした。
- 実行ログの保存先/仕様を `docs/detail.md` と `services/run/README.md` に追記。
- READMEとロードマップを更新。

## TODO
- `run` 実行ログを `GraphStorage` へ反映する設計方針を決める。
- 既存submit機能の `run` へのリファクタリング方針を確定する。
- スクリプト型のproperties抽出ルールを追加拡張する（コメント記法の差分対応など）。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-008.md`です。
- `jj r -- <command>` の運用フローを整理し、スクリプト型/ジョブ型の境界を再確認してください。
- README/roadmap/statusを更新し、引き継ぎ可能な形を維持してください。

## コミット
- feat: implement run command logging
