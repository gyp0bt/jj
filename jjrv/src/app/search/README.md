# /search

> [← README.md](../../../README.md)
> [← Pages一覧](../README.md)

## 概要
検索結果一覧ページ。材料名・タグ・プロパティ・ドメイン・作成者などで絞り込み、カード/テーブル/グラフ/グループ/ダイアグラムで表示する。

## 主要UI
- 検索バー: 材料名 / タグ / プロパティ値
- フィルタ: ドメイン、作成者、いいね、件数、並び替え、entityType
- 表示切替: カード/テーブル/ダイアグラム/グラフ、グループ表示トグル
- グループ表示: entityType -> ドメイン（サブグループ）で階層化
- ダイアグラム表示: グループ内階層（type -> domain -> entity）を可視化
- ページネーション: 非グループ時のみ

## データフロー
- `fetchEntities()` で全件取得
- `searchEntities()` でフロント側フィルタリング
- URLパラメータに検索状態を保存
- 条件がある場合は検索履歴を保存

## URLパラメータ
- `name`: 材料名（部分一致）
- `tags`: スペース区切りタグ（完全一致）
- `propKey`: プロパティキー
- `propValue`: プロパティ数値
- `domain`: ドメイン
- `sortBy`: `updated` / `created` / `name` / `favoriteCount` / `downloadCount`
- `sortOrder`: `asc` / `desc`
- `view`: `card` / `table` / `diagram` / `graph`（groupByType=false時のみ）
- `limit`: 1ページの表示件数
- `createdBy`: 作成者ID
- `favoritedBy`: お気に入りしたユーザーID
- `entityType`: `Material` / `Tag` / `Template` / `Document`
- `groupByType`: `true` の場合、entityTypeでグループ化

## 仕様メモ
- グループ表示時は entityType -> domain でサブグループ化
- ダイアグラムビューは検索結果をドメインで束ねた階層構造を可視化
- 結果0件は「検索結果がありません」
- 読み込み中は「読み込み中...」を表示
