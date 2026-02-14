# EntityDiagram

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
グループ内の階層構造（group -> subgroup -> entity）をダイアグラムとして可視化するコンポーネント。検索のグループ表示でサブグループ構造を俯瞰する用途。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| groupLabel | `string` | - | グループ名（entityTypeなど） |
| subgroups | `{ label: string; entities: StringEntity[] }[]` | - | サブグループ配列（domainなど） |
| onNodeClick | `(entity: StringEntity) => void` | - | エンティティノードクリック時のコールバック |
| onToggleSelect | `(entityId: string) => void` | - | 選択モード時のトグル操作 |
| selectionMode | `boolean` | `false` | 選択モードの有無 |
| selectedIds | `Set<string>` | - | 選択中のID一覧 |
| width | `number` | - | 幅指定（省略時は親要素に追従） |
| height | `number` | `360` | 高さ指定 |

## 構造
- groupノード → subgroupノード → entityノード の2段リンク
- entityノードはホバーでBodyPreviewTooltipを表示
- 選択中のエンティティはピンク枠で強調

## 備考
- `react-force-graph-2d` を dynamic import で使用
- ラベルの色は `entityType` と `sysTags` を組み合わせて決定
