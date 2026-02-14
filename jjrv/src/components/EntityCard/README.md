# EntityCard

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
エンティティ一覧/詳細で使うカード表示コンポーネント。お気に入り/ダウンロード/コピーの操作とカウント表示を内包。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| entity | `StringEntity` | - | 表示対象エンティティ |
| onEdit | `(e: StringEntity) => void` | `undefined` | 編集押下時のコールバック |
| enableActions | `boolean` | `true` | お気に入り/コピー/ダウンロード操作の表示切替 |
| className | `string` | `""` | 追加のCSSクラス |
| onClick | `() => void` | `undefined` | カード全体クリック時のコールバック |
| clickLabel | `string` | `entity.name` | クリック用ボタンのaria-label |
| meta | `React.ReactNode` | `undefined` | カード内のメタ情報表示エリア |
| selected | `boolean` | `false` | 選択状態（枠線/左ラインを強調） |
| favoriteState | `boolean` | `undefined` | お気に入り状態（指定時はAPI取得を省略） |
| onFavoriteChange | `(next: boolean) => void` | `undefined` | お気に入り変更時のコールバック |

## Variants / States
- なし（タグ/アクセントは `sysTags` に応じて自動決定）

## Events
- 編集ボタン押下時に `onEdit` を発火
- お気に入り/コピー/ダウンロードは内部で処理

## 備考
- サマリーは `remark` または本文から自動生成
- `sysTags` からアクセント色とバッジを自動判定
- コピー後にカード右上ボタンの下に青系トーストで `copied!` を表示
