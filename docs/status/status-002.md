[READMEへ戻る](../../README.md)

# 実装状況 (status-002)

## 概要
- モジュール構成の設計を文書化し、services/types/tests/assets/docsのREADMEを追加。
- 実装詳細 `docs/detail.md` を作成し、FileParseやObsidian向け設計を整理。
- README/roadmapを更新し、仕様リンクと直近計画を明確化。

## 変更点
- `services/` 以下の各モジュールREADMEを追加。
- `types/`, `tests/`, `assets/`, `docs/.status/` のREADMEを追加。
- `docs/detail.md` を新規追加。
- `README.md` と `docs/roadmap.md` を更新。

## TODO
- `FileParse`/`ObsidianFileParse` の具体実装。
- `.jj/storage` の保存フォーマット（YAML/JSON）確定と `GraphStorage` 実装。
- `run` サービスのログ/トレース仕様の確定。
- `types` のPydanticモデル整備（Node/Relation/GraphModel）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-002.md`です。
- Codex/Claudeの交代運用を前提に、READMEとstatusを更新してください。

## コミット
- docs: design module structure and document service layout
