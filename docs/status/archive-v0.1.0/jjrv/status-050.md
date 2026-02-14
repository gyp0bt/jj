# status-050 (2026-02-05)

> [← README.md](../../README.md) | [status一覧](status-index.md)

---

## 今回の作業内容

### 4-A-03: 検索・フィルター強化

`src/components/SearchBar/index.tsx` を拡張し、以下の機能を実装:

#### 1. 全文検索（FullTextSearchBar）
- body含む全フィールド（名前、ドメイン、タグ、本文、プロパティ）を横断検索
- 空白区切りキーワードによるAND検索
- リアルタイムフィルタリング

#### 2. 高度なフィルター条件（FilterCondition）
- 条件を動的に追加・削除可能
- フィールド選択: すべて / 名前 / ドメイン / タグ / 本文 / プロパティ
- 演算子選択: 含む / 一致 / 前方一致 / 後方一致 / 含まない
- AND/OR ロジック切り替え（2番目以降の条件）

#### 3. 保存フィルター機能
- フィルター条件をlocalStorageに永続化
- 名前付きフィルターとして保存
- 保存フィルターの一覧表示・適用・削除

#### EntityTableへの統合
- `enableFullTextSearch` プロパティを追加
- FullTextSearchBarをテーブル上部に配置
- 既存の列フィルターと併用可能
- 検索結果件数表示に「（全文検索）」ラベル追加

### ロードマップ4の状態更新
- 4-A-01: ✅ 実装済み（テーブル内階層折りたたみ）
- 4-A-02: ✅ 実装済み（プレビュー改善）
- 4-A-03: 🔄 実装中 → ✅ 実装済み

---

## 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/components/SearchBar/index.tsx` | FullTextSearchBar追加、フィルターユーティリティ追加 |
| `src/components/EntityTable/index.tsx` | enableFullTextSearch対応、全文検索統合 |
| `src/components/GenericUploader/index.tsx` | enableFullTextSearch有効化 |
| `docs/spec-roadmap4.md` | 4-A-01, 4-A-02, 4-A-03の状態更新 |

---

## 新規追加された型・関数

### 型
```typescript
type SavedFilter = {
  id: string;
  name: string;
  query: string;
  conditions: FilterCondition[];
  createdAt: string;
};

type FilterCondition = {
  id: string;
  field: "name" | "domain" | "tags" | "body" | "props" | "all";
  operator: "contains" | "equals" | "startsWith" | "endsWith" | "notContains";
  value: string;
  logic: "AND" | "OR";
};
```

### 関数
- `applySearchFilters<T>(items, query, conditions)` - フィルター適用
- `loadSavedFilters()` - localStorageから読み込み
- `saveSavedFilters(filters)` - localStorageに保存

---

## 次のアクション（優先度P1）

- [ ] 4-A-04: インライン編集強化（body直接編集、マルチセル選択編集）
- [ ] 4-A-05: Import/Export整備（CSV/JSON/GraphML形式）
- [ ] 4-A-06: ユーザー設定（列表示設定の永続化）
- [ ] 2-13: hover時type属性表示（ロードマップ2）
- [ ] 3-13: D&D分割/マージ（ロードマップ3）
- [ ] 3-14: import/export整備（ロードマップ3）

---

## 確認事項・懸念

- 全文検索はクライアントサイドで実行されるため、大量データでのパフォーマンス検証が必要
- 保存フィルターはlocalStorageに保存されるため、デバイス間での共有は不可
- 将来的にはサーバーサイド検索（SQLite LIKE / FTS）への移行を検討

---

## 最新コミット（予定）

```
feat(SearchBar): 4-A-03 全文検索・複合フィルター・保存フィルター機能を実装
```
