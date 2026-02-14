# /register

> [← README.md](../../../README.md)
> [← Pages一覧](../README.md)

## 概要
材料データの登録ページ。テキスト入力とファイル取り込みを行い、SQLiteへ保存する。

## 主要UI
- ファイルドロップ/選択
- 名前、備考入力
- タグ入力（スペース/Enterで確定）
- プロパティ入力（key:value）
- 本文エディタ

## データフロー
- 取り込みデータを `StringEntity` に整形
- `createEntity()` で `/api/entities` にPOST

## 仕様メモ
- タグ入力で `key:value` はプロパティに自動振替
- 保存後はフォームをリセット
