# TopNav

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
GitHub風の上部ナビゲーションバー。既存のページヘッダーと統合し、アイコン付きで現在地を表示する。パンくずの各項目は遷移リンクとして提供する。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | `{ label: string; href: string }[]` | - | パス表示用のパンくず配列（すべてリンク） |
| title | `string` | `undefined` | ヘッダータイトル（既存ページヘッダー統合） |
| onHomeClick | `() => void` | `undefined` | ホームアイコン押下時のコールバック |
| showAccountStatus | `boolean` | `true` | AccountStatus を表示するか |
| className | `string` | `""` | 追加のCSSクラス |

## Variants / States
- **default**: 通常表示
- **compact**: モバイル幅で折り返し

## Events
- `onHomeClick`: ホームアイコン押下時

## 備考
- `items` は全て遷移リンクとして表示する（現在地もリンク）
- 既存のページヘッダーと統合して配置する
- AccountStatus を同一行に配置する
