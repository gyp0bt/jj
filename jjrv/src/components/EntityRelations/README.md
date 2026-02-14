# EntityRelations

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
StringEntity間の関連（related/tag）と付属情報（外部リンク・共有パス・案件名）を一覧表示する。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| relations | `RelationItem[]` | - | 関連情報の表示リスト |
| className | `string` | `""` | 追加のCSSクラス |

## 型定義
```ts
export type RelationItem = {
  id: string;
  type: "tag" | "related";
  label: string;
  href?: string;
  meta?: string;
};
```

## Variants / States
- **default**: リスト表示
- **empty**: 関連情報がない場合

## Events
- なし（表示専用）

## 備考
- `type` は StringEntity の `type` と一致させる
- `href` がある場合はリンク表示
