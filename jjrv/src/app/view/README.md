# /view

> [← README.md](../../../README.md)
> [← Pages一覧](../README.md)

## 概要
材料データの詳細表示ページ。EntityCardと本文プレビューを表示する。

## 主要UI
- EntityCard
- 本文プレビュー

## データフロー
- `id` があれば `fetchEntityById()` で取得
- `id` がなければ先頭エンティティを表示

## URLパラメータ
- `id`: エンティティID

## 仕様メモ
- 読み込み中は「読み込み中...」を表示
- 取得失敗時は「エンティティが見つかりませんでした」
