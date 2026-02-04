[READMEへ戻る](../README.md)

# ロードマップ

## 完了
- `FileParse`/`ObsidianFileParse` の初期実装。
- FileParseの命名規則更新とファイルグループ整理。
- `run` 機能の仕様整理（スクリプト型/ジョブ型の整理）。

## 直近
- モジュール構成の設計整理（services/types/tests/assets/docs/detail）。
- 既存submit機能の `run` へのリファクタリング方針作成。
- アダプター設計（ソフト固有フォーマットを独立実装できる構成）の雛形作成。
- 計算inpの拡張子/フォルダ検出ルールを設定化。

## 中期
- Obsidian向けの出力に加えて、Neo4j向けのエクスポート形式を整理。
- グラフデータの永続化（Node/RelationのYAMLフォーマット）を確定。
- `jj f` のファイル操作（テンプレート、リネーム、送受信）の要件確定。

## 長期
- 複数CAEソフト対応のアダプター群整備（Abaqus, Fluent, Dynaなど）。
- 実行ログ/オプションのトレーサビリティ拡張。
