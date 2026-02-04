[READMEへ戻る](../../README.md)

# 実装状況 (status-3)

## 概要
- `services/parse` に FileParse と ObsidianFileParse/ObsidianMap を追加。
- README とロードマップを更新し、完了項目を反映。

## 変更点
- `services/parse/file_parse.py` に共通パーサーとObsidian向けマッピングを実装。
- `services/parse/__init__.py` で公開APIを追加。
- `README.md` のディレクトリ説明にFileParse実装を追記。
- `docs/roadmap.md` に完了項目を追加。

## TODO
- `.jj/storage` の保存フォーマット（YAML/JSON）確定と `GraphStorage` 実装。
- `run` サービスのログ/トレース仕様の確定。
- `types` のPydanticモデル整備（Node/Relation/GraphModel）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-3.md`です。
- Codex/Claudeの交代運用を前提に、READMEとstatusを更新してください。

## コミット
- feat: add FileParse and ObsidianFileParse scaffolding
