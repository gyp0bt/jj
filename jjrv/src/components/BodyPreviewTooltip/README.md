# BodyPreviewTooltip

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要

body テキストのプレビューをコンパクトなツールチップとして表示するコンポーネント。

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| text | `string` | - | 表示する本文テキスト |
| className | `string` | `""` | 追加クラス |
| style | `CSSProperties` | - | インラインスタイル |
| maxChars | `number` | `600` | 最大文字数 |
| visible | `boolean` | - | 表示状態を制御する場合に使用（hover不要） |

## 使用例

```tsx
<BodyPreviewTooltip text={entity.body} className="left-0 top-full mt-2" />
```

## 備考

- `visible` を指定しない場合のみ `group-hover` での表示に対応
- `visible` を指定するとその値で表示を制御
