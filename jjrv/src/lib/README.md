# lib

> [← README.md](../../README.md)

アプリ共通のユーティリティとデータ層。

---

## Entity Search / Store

- `entity-search.ts`: `StringEntity` の検索ロジック
  - `searchEntities(entities, { nameQuery, tags, propertyKey, propertyValue, domain, sortBy, sortOrder })`
  - 材料名の部分一致、タグ一致、プロパティ数値一致、ドメインフィルタ、並び替えに対応
  - 並び替え: `created`（作成日時）、`updated`（更新日時）、`name`（名前）
  - 並び替え順序: `asc`（昇順）、`desc`（降順）
- `entity-store.ts`: ローカルストレージによる簡易永続化（deprecated）
  - キー: `mat-db.entities`
  - `loadEntities()` / `saveEntities()` / `upsertEntity()` / `findEntityById()`

### 仕様メモ
- ストレージが空の場合は `MOCK_ENTITIES` を読み取り専用の初期値として返す。
- `upsertEntity` は既存IDを更新、未存在なら先頭に追加。
- `entity-store.ts`は後方互換性のため残存（現在はSQLiteを使用）。
