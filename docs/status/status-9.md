[READMEへ戻る](../../README.md)

# 実装状況 (status-9)

## 概要
- `run` 実行ログに所要時間/ユーザー/ホストなどのメタ情報を追加。
- `services/service` にCLI本体を移し、`main.py` を薄く整理。
- `run` と `storage` の単体テストを追加。

## 変更点
- `RunService` に実行時間・ユーザー・ホスト・script_path を記録し、ログに保存。
- `run` 実行時の出力にモードやメタ情報、propertiesを表示。
- 既存のCLI実装を `services/service/entry.py` に移し、`main.py` から委譲。
- `services/cli` 配下のREADME/初期化ファイルを削除し、CLI導線を整理。
- `run` と `storage` のpytest単体テストを追加。
- README/ロードマップを更新。

## TODO
- `run` 実行ログを `GraphStorage` に反映する設計方針を決める。
- 既存submit機能の `run` へのリファクタリング方針を確定する。
- スクリプト型のproperties抽出ルールを追加拡張する（コメント記法の差分対応など）。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-9.md`です。
- `services/service/entry.py` がCLI本体です。必要に応じて `run` の出力仕様を拡張してください。
- README/roadmap/statusを更新し、引き継ぎ可能な形を維持してください。

## コミット
- feat: refine run command and cli structure
