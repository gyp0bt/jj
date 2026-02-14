# SearchBar

> [← README.md](../../../README.md) /[← コンポーネント一覧](../README.md)

## 概要

キーワード・タグ・タイプを入力する検索バーコンポーネント。部分一致・スペース区切りタグ・タイプ選択の入力をまとめて提供。

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| nameQuery | `string` | - | キーワードの検索文字列（必須） |
| onNameQueryChange | `(value: string) => void` | - | キーワード変更時のコールバック（必須） |
| tags | `string[]` | - | タグのピル一覧（必須） |
| onTagsChange | `(tags: string[]) => void` | - | タグ変更時のコールバック（必須） |
| entityType | `EntityType \| ""` | - | タイプ選択（必須） |
| onEntityTypeChange | `(value: EntityType \| "") => void` | - | タイプ変更時のコールバック（必須） |
| className | `string` | - | 追加のCSSクラス |

## Variants / States

- **デフォルト**: 3入力（キーワード / タグ / タイプ）
- **フォーカス**: フォーカス時のスタイル

## Events

- `onNameQueryChange`: キーワードが変更されたときに発火
- `onTagsChange`: タグが追加/削除されたときに発火
- `onEntityTypeChange`: タイプが変更されたときに発火

## 備考

- タグは入力中にスペース/Enterで確定し、ピルとして表示される
- キーワードは部分一致、タグは完全一致を想定
- Enterキーで検索実行する場合は親コンポーネントで処理
- リアルタイム検索に対応（各onChangeで即座に反映）
