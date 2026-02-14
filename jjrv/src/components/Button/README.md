# Button

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
汎用ボタンコンポーネント。プロジェクト全体で統一されたスタイルを提供する。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | `"primary" \| "secondary" \| "ghost"` | `"secondary"` | ボタンのスタイルバリアント |
| size | `"sm" \| "md" \| "lg"` | `"md"` | ボタンのサイズ |
| disabled | `boolean` | `false` | 無効状態 |
| children | `ReactNode` | - | ボタンのラベル |
| className | `string` | `""` | 追加のCSSクラス |

## Variants / States
- **primary**: 主要アクション（保存、送信）- 黒背景、白文字
- **secondary**: 副次アクション（キャンセル）- 白背景、黒文字、ボーダー
- **ghost**: 補助アクション（戻る）- 透明背景
- **disabled**: 全バリアント共通で opacity 50%

## Events
- `onClick`: クリック時のコールバック（HTMLButtonElementの標準イベント継承）

## 備考
- `ComponentProps<"button">`を継承し、標準のbutton属性をすべてサポート
- ダークモード対応済み
