[READMEへ戻る](../README.md)

# ロードマップ

## 完了
- `FileParse`/`ObsidianFileParse` の初期実装。
- FileParseの命名規則更新とファイルグループ整理。
- `run` 機能の仕様整理（スクリプト型/ジョブ型の整理）。
- `jj r` の実行ログ保存とスクリプト型の差分トレースの初期実装。
- `run` 実行ログのメタ情報（所要時間/ユーザー/ホスト）拡張とCLIの薄型化。
- `run` と `storage` の単体テスト追加。
- SSH設定/語彙設定の読み込みを `config/` に集約し、`services/ssh` に移行。
- `GraphModel`/`Node`/`Relation` の型定義と `GraphStorage` の初期実装。

## 直近
- モジュール構成の設計整理（services/types/tests/assets/docs/detail）。
- 既存submit機能の `run` へのリファクタリング方針作成。
- アダプター設計（ソフト固有フォーマットを独立実装できる構成）の雛形作成。
- 計算inpの拡張子/フォルダ検出ルールを設定化。

## 中期
- Obsidian向けの出力に加えて、Neo4j向けのエクスポート形式を整理。
- `jj f` のファイル操作（テンプレート、リネーム、送受信）の要件確定。

## 長期
- 複数CAEソフト対応のアダプター群整備（Abaqus, Fluent, Dynaなど）。
- 実行ログ/オプションのトレーサビリティ拡張。
