# SearchFilter

> [← README.md](../../../README.md) /[← コンポーネント一覧](../README.md)

## 概要

検索結果のフィルタリングと並び替えを行う横長フィルタバー。ドメイン入力/並び替え/ユーザーをまとめて提供。

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| domain | `string` | `""` | 入力中のドメイン |
| availableDomains | `string[]` | `[]` | サジェストに使うドメイン一覧 |
| onDomainChange | `(domain: string) => void` | - | ドメイン変更時のコールバック（必須） |
| sortBy | `"created" \| "updated" \| "name" \| "favoriteCount" \| "downloadCount"` | `"updated"` | 並び替え基準 |
| sortOrder | `"asc" \| "desc"` | `"desc"` | 並び替え順序 |
| onSortChange | `(sortBy: "created" \| "updated" \| "name" \| "favoriteCount" \| "downloadCount", sortOrder: "asc" \| "desc") => void` | - | 並び替え変更時のコールバック（必須） |
| createdBy | `string` | `""` | 登録ユーザーのフィルタ |
| onCreatedByChange | `(userId: string) => void` | - | 登録ユーザー変更時のコールバック |
| favoritedBy | `string` | `""` | お気に入りユーザーのフィルタ |
| onFavoritedByChange | `(userId: string) => void` | - | お気に入りユーザー変更時のコールバック |
| availableUsers | `{ id: string; username: string }[]` | `[]` | ユーザー候補一覧 |
| className | `string` | - | 追加のCSSクラス |

## Variants / States

- **横長バー**: 薄く平たいレイアウト
- **ドメイン入力**: テキスト入力 + サジェスト
- **並び替え**: セレクト + 昇順/降順トグル
- **ユーザー絞り込み**: 登録ユーザー/お気に入りユーザー

## Events

- `onDomainChange`: ドメイン入力が変更されたときに発火
- `onSortChange`: 並び替え設定が変更されたときに発火
- `onCreatedByChange`: 登録ユーザーが変更されたときに発火
- `onFavoritedByChange`: お気に入りユーザーが変更されたときに発火

## 備考

- ドメインは`domain`フィールドから取得
- 並び替えは`createdAt`、`updatedAt`、`name`に対応
- 並び替えにお気に入り数/ダウンロード数を追加
- モバイル対応（レスポンシブデザイン）
