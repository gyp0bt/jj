# EntityMetaBadges

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
登録者・お気に入り・利用状況などのメタ情報をGitHub風のアイコンバッジで表示する。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| owner | `{ name: string; avatarUrl?: string }` | - | 登録者情報 |
| favorites | `number` | `0` | お気に入り数 |
| downloads | `number` | `0` | ダウンロード数 |
| favoriteUsers | `{ name: string; avatarUrl?: string }[]` | `[]` | お気に入りしたユーザーのアイコン一覧 |
| usedBy | `{ label: string; href?: string }[]` | `[]` | 使用プロジェクト/案件の表示リスト |
| className | `string` | `""` | 追加のCSSクラス |

## Variants / States
- **default**: アイコン + 数値
- **compact**: ラベル省略

## Events
- なし（表示専用）

## 備考
- 信頼性を「誰が登録したか」「誰がお気に入りにしたか」「どこで使われたか」で即時判断できることを重視
- `usedBy` はラベルのみ/リンクありの両方に対応
- `favoriteUsers` は最大5人までアイコン表示し、超過分は `+x` 表記で省略する
