[READMEへ戻る](../../README.md)

# 実装状況 (status-006)

## 概要
- `pyssh` を `services/ssh` に移動し、SSH送受信ユーティリティをサービス配下へ整理。
- `.jj/config` の `vocab.yaml` と `.pyssh.yaml` をまとめて読む `config/` ローダーを追加。

## 変更点
- `config/` に `VocabConfig`/`SSHConfig`/`AppConfig` を追加し、設定読み込みを集約。
- `main.py` と `services/ssh` が新しい `config/` を参照するように変更。
- `pyssh` の配置を `services/ssh` に移動し、ドキュメントの記述を更新。

## TODO
- `.jj/storage` の保存フォーマット（YAML/JSON）確定と `GraphStorage` 実装。
- 既存submit機能の `run` へのリファクタリング方針作成。
- `types` のPydanticモデル整備（Node/Relation/GraphModel）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-006.md`です。
- Codex/Claudeの交代運用を前提に、READMEとstatusを更新してください。

## コミット
- refactor: move ssh service and centralize config loading
