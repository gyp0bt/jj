[READMEへ戻る](../../README.md)

# 実装状況 (status-004)

## 概要
- FileParseの命名規則を更新し、props/tagの判定と旧式version補完を追加。
- ファイルタイプ判定とファイルグループ集計を導入。
- 仕様更新に合わせてREADME/詳細/ロードマップを整理。

## 変更点
- `services/parse/file_parse.py` にFileType/FileGroupを追加し、props/tag抽出と旧式version補完を実装。
- `services/parse/__init__.py` の公開APIにFileType/FileGroupを追加。
- `services/parse/README.md` と `docs/detail.md` に命名規則とグルーピング仕様を追記。
- `README.md` と `docs/roadmap.md` を更新。
- `tests/test_file_parse.py` を追加して新命名規則のテストを追加。

## TODO
- `.jj/storage` の保存フォーマット（YAML/JSON）確定と `GraphStorage` 実装。
- `run` サービスのログ/トレース仕様の確定。
- `types` のPydanticモデル整備（Node/Relation/GraphModel）。
- 既存 `main.py` の段階的分割計画を作成。

## 次の担当者へ
- 最新の実装状況は`docs/status/status-004.md`です。
- Codex/Claudeの交代運用を前提に、READMEとstatusを更新してください。

## コミット
- feat: update FileParse naming rules and file grouping
