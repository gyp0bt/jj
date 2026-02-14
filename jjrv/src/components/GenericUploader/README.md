# GenericUploader

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
汎用の取り込みフォーム。ファイル読み込み・タグ/プロパティ入力・本文編集に対応し、SQLite DBに保存。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| - | - | - | なし（内部状態で完結） |

## Variants / States
- なし

## Events
- 保存ボタン押下時に `/api/entities` (POST) を呼び出してSQLite DBに保存
- 保存成功後はフォームをリセット

## 備考
- フォルダ/複数ファイルのドロップに対応。`.inp` から material ブロックを抽出して単一ボディに統合。
- フォルダドロップ時は表示名にフォルダ名を設定し、material 名とキーワードをタグに自動追加。
- ファイルドロップ/選択で本文を読み込み、`name` が空のときはファイル名を適用。
- `tag` 入力で `key:value` 形式なら自動でプロパティに振替。
- データは `data/mat-db.sqlite` に永続化される。
