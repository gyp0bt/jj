# EntityTable

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要

検索結果をテーブル形式で表示するコンポーネント。一覧性が高く、多くのエンティティを効率的に確認できる。

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| entities | `StringEntity[]` | - | 表示するエンティティ配列（必須） |
| onRowClick | `(entity: StringEntity) => void` | - | 行クリック時のコールバック |
| metaById | `Record<string, EntityMeta>` | - | メタ情報のマップ |
| selectedIds | `Set<string>` | - | 選択中のIDセット |
| onToggleSelect | `(entityId: string) => void` | - | 行の選択切替 |
| onToggleSelectAll | `(next: boolean) => void` | - | 全選択切替 |
| selectionMode | `boolean` | `false` | 選択モード（true時は行クリックで選択） |
| favoriteStateMap | `Record<string, boolean>` | - | お気に入り状態のマップ |
| onFavoriteChange | `(entityId: string, next: boolean) => void` | - | お気に入り変更時 |

## 型定義

```typescript
import type { StringEntity } from "@/lib/types";
import type { EntityMeta } from "@/components/EntityMetaBadges";

type EntityTableProps = {
  entities: StringEntity[];
  onRowClick?: (entity: StringEntity) => void;
  metaById?: Record<string, EntityMeta>;
  selectedIds?: Set<string>;
  onToggleSelect?: (entityId: string) => void;
  onToggleSelectAll?: (next: boolean) => void;
  selectionMode?: boolean;
  favoriteStateMap?: Record<string, boolean>;
  onFavoriteChange?: (entityId: string, next: boolean) => void;
};
```

## 列構成

| 列 | フィールド | 幅 | 説明 |
|----|-----------|-----|------|
| 名前 | name | 可変（広め） | メインの識別子 |
| ドメイン | domain | 100px | ドメインバッジ |
| タグ | sysTags + userTags | 可変 | タグをコンパクト表示（最大3個 + ...） |
| 更新日 | updatedAt | 100px | 日付フォーマット |
| メタ | - | 200px | 登録者/お気に入り/ダウンロード |
| アクション | - | 100px | お気に入り・コピー・ダウンロード |

## States

- **default**: 通常状態
- **hover**: 行ホバー時（背景色変化、カーソルpointer）
- **empty**: エンティティがない場合の表示

## スタイル

- コンパクトなテーブルデザイン
- ヘッダー固定（スクロール時も見える）
- ダークモード対応
- レスポンシブ（横スクロール対応）

## 使用例

```tsx
<EntityTable
  entities={entities}
  onRowClick={(e) => router.push(`/view?id=${e.id}`)}
/>
```

## 備考

- EntityCardと同等の情報を表示するが、よりコンパクト
- 行クリックで詳細ページへ遷移する想定
- 選択モード時は行クリックで選択を切り替える
- お気に入り/コピー/ダウンロードは内部で処理
