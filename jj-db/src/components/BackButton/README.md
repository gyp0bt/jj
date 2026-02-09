# BackButton

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
履歴戻り（router.back）または指定URLへの遷移を行う共通ボタン。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | `string` | `"戻る"` | 表示ラベル |
| href | `string` | `undefined` | 指定時はそのURLへ遷移（未指定時は履歴戻り） |

## Variants / States
- `Button` コンポーネントの `secondary` を使用

## Events
- `onClick` 相当の挙動は内部で制御（propsとしては公開しない）

## 備考
- クリック時は `href` があれば `router.push(href)`、なければ `router.back()`。
