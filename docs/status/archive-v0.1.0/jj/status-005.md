[READMEへ戻る](../../README.md)

# 実装状況 (status-005)

## 概要
- `docs/.status` を `docs/status` に統合し、運用ドキュメントの参照先を整理。
- `run` サービスの仕様（スクリプト型/ジョブ型、`generated` 関係、properties抽出）を明文化。

## 変更点
- `docs/status/README.md` を新設し、旧 `docs/.status` を統合。
- `docs/detail.md` と `services/run/README.md` に `run` の仕様詳細を追記。
- `docs/roadmap.md` と `README.md` を最新状況に合わせて更新。

## TODO
- `.j2/storage` の保存フォーマット（YAML/JSON）確定と `GraphStorage` 実装。
- 既存submit機能の `run` へのリファクタリング方針作成。
- `types` のPydanticモデル整備（Node/Relation/GraphModel）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-005.md`です。
- Codex/Claudeの交代運用を前提に、READMEとstatusを更新してください。

## コミット
- docs: integrate status notes and specify run service
