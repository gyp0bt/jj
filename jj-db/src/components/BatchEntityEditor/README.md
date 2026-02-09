# BatchEntityEditor

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
一括アップロードで抽出した候補をまとめて編集・タグ付けするためのエディタ。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | `BatchEditItem[]` | - | 編集対象の候補一覧 |
| onChange | `(items: BatchEditItem[]) => void` | - | 編集内容の変更通知 |
| onApplyTags | `(tags: string[]) => void` | - | 一括タグ付けの適用 |
| onApplyProps | `(props: Record<string, string>) => void` | - | 一括プロパティ適用 |
| className | `string` | `""` | 追加のCSSクラス |

## 型定義
```ts
export type BatchEditItem = {
  id: string;
  name: string;
  body: string;
  sourcePath: string;
  tags: string[];
  props: Record<string, string>;
  selected: boolean;
};
```

## Variants / States
- **list**: 一覧表示（複数選択）
- **bulk**: 一括編集フォーム表示

## Events
- `onChange`: 各項目の編集で発火
- `onApplyTags`: 一括タグの適用
- `onApplyProps`: 一括プロパティの適用

## 備考
- 選択済みの項目にのみ一括操作を適用する
- 個別編集と一括編集の両方を提供
