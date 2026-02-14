# ViewSwitcher

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要

検索結果の表示形式（カード/テーブル/グラフ/ダイアグラム）を切り替えるためのコンポーネント。アイコンボタンで直感的に切り替え可能。

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `"card" \| "table" \| "graph" \| "diagram"` | - | 現在選択中のビュー（必須） |
| onChange | `(view: "card" \| "table" \| "graph" \| "diagram") => void` | - | ビュー変更時のコールバック（必須） |
| disabled | `boolean` | `false` | 無効化状態 |
| views | `("card" \| "table" \| "graph" \| "diagram")[]` | - | 表示するビューの並び順（省略時はcard/table/diagram/graph） |

## 型定義

```typescript
type ViewType = "card" | "table" | "graph" | "diagram";

type ViewSwitcherProps = {
  value: ViewType;
  onChange: (view: ViewType) => void;
  disabled?: boolean;
  views?: ViewType[];
};
```

## アイコン

| ビュー | アイコン | ラベル |
|--------|----------|--------|
| card | `LayoutGrid` | カード |
| table | `Table` | テーブル |
| graph | `Network` | グラフ |
| diagram | `GitFork` | ダイアグラム |

※ lucide-react を使用

## States

- **default**: 通常状態
- **selected**: 選択中（背景色ハイライト）
- **hover**: ホバー時（背景色変化）
- **disabled**: 無効化時（opacity低下、クリック不可）

## スタイル

- ボタングループ形式（border-radiusは外側のみ）
- 選択中のボタンは背景色でハイライト
- ダークモード対応
- コンパクトサイズ（アイコンのみ表示、tooltipでラベル）

## 使用例

```tsx
const [view, setView] = useState<ViewType>("card");

<ViewSwitcher value={view} onChange={setView} />
<ViewSwitcher value={view} onChange={setView} views={["card", "table", "diagram"]} />
```

## 備考

- SearchFilterの隣に配置想定
- URLパラメータ `view=card|table|diagram|graph` との連携は親コンポーネントで行う
