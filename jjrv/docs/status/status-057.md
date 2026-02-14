# status-057 (2026-02-06)

> [← README.md](../../README.md) | [status一覧](status-index.md)

---

## 今回の作業内容

### spec-roadmap5: レポジトリ階層制約（破壊的変更）

すべてのノードをレポジトリツリー内に強制配置する階層制約を導入。

#### 設計方針

- **ルートレポジトリ**: システムに唯一のルートレポジトリ（id: `"root"`）を自動作成
- **レポジトリ制約**: レポジトリはレポジトリの下にしか配置不可
- **非レポジトリ制約**: レポジトリ以外のすべてのノードはレポジトリの下にしか配置不可
- **上下の定義**: ルートレポジトリからのRelation距離で定義（近い=上、遠い=下）
- 対象Relation: `child`/`contains`（分類Relation `tagged_with`等は対象外）

#### Phase 1: コアモデル（5-01〜5-04）

- `src/lib/root-repository.ts` — ルートレポジトリの自動生成・管理
- `src/lib/hierarchy-validator.ts` — 階層バリデーション関数群
  - `validateHierarchyRelation()`: 親子関係の整合性チェック
  - `findAncestorRepository()`: 祖先レポジトリ探索
  - `getPathToRoot()`: ルートまでの経路取得
  - `findOrphanEntities()`: 孤児ノード検出
  - 循環参照チェック
- `src/lib/types.ts` — `HIERARCHY_LABELS` / `HierarchyConstraintError` 型追加
- `src/lib/db.ts` — DB初期化時にルートレポジトリを自動作成

#### Phase 2: API層バリデーション（5-05〜5-07）

- `POST /api/relations` — child/containsリレーション作成時に階層制約を検証
  - 親がレポジトリ/ディレクトリであること
  - レポジトリの親はレポジトリのみ
  - ルートレポジトリを子にできない
  - 循環参照の防止
- `DELETE /api/entities/[id]` — ルートレポジトリの削除を禁止
- `POST /api/migration` — 孤立ノードをルートレポジトリ配下に一括配置（管理者のみ）
- `GET /api/migration` — 孤立ノード数の確認（ドライラン）

#### Phase 3: インポートフロー対応（5-08〜5-10）

- `GenericUploader` にインポート先レポジトリ選択UI追加（violetアクセント）
- フォルダD&D時にトップレベルノードを選択レポジトリに自動紐付け
- 単一ファイルモードでもレポジトリ紐付けを実施

#### Phase 4: UI表示

- 検索ページでルートレポジトリ（id: `"root"`）を一覧から非表示

#### Phase 5: マイグレーション（5-14〜5-16）

- `src/lib/migration-hierarchy.ts` — 孤立ノードの自動配置ユーティリティ
- マイグレーションAPI（管理者専用）

---

## 実装ファイル

| ファイル | 変更内容 | 新規/既存 |
|---------|---------|-----------|
| `src/lib/root-repository.ts` | ルートレポジトリ管理 | 新規 |
| `src/lib/hierarchy-validator.ts` | 階層バリデーション関数群 | 新規 |
| `src/lib/migration-hierarchy.ts` | マイグレーションユーティリティ | 新規 |
| `src/lib/types.ts` | HIERARCHY_LABELS, HierarchyConstraintError追加 | 既存 |
| `src/lib/db.ts` | ルートレポジトリ自動作成 | 既存 |
| `src/lib/entity-api.ts` | fetchRepositories()追加 | 既存 |
| `src/app/api/relations/route.ts` | 階層バリデーション追加 | 既存 |
| `src/app/api/entities/[id]/route.ts` | ルートレポジトリ削除防止 | 既存 |
| `src/app/api/migration/route.ts` | マイグレーションAPI | 新規 |
| `src/components/GenericUploader/index.tsx` | レポジトリ選択UI・保存時紐付け | 既存 |
| `src/app/search/page.tsx` | ルートレポジトリを検索結果から除外 | 既存 |
| `docs/spec-roadmap5.md` | ロードマップ5仕様書 | 新規 |

---

## 設計メモ

### バリデーションルール

| 親のsysTags | 子のsysTags | 許可されるRelation label |
|-------------|-------------|------------------------|
| `repository` | `repository` | `child` |
| `repository` | `directory` | `child` |
| `repository` | その他 | `contains` |
| `directory` | `directory` | `child` |
| `directory` | その他 | `contains` |
| その他 | 任意 | `child`/`contains` 不可 |

### ルートレポジトリの扱い

- ID: `"root"`（固定値）
- DB初期化時に自動作成
- 削除不可
- 検索結果に表示されない（フロントエンドでフィルタリング）
- すべてのレポジトリの最上位親

---

## 次のアクション（TODO）

- [ ] 5-11: 検索ページにレポジトリツリーナビゲーション追加
- [ ] 5-12: テーブルビューでルート起点の完全階層パス表示
- [ ] 5-13: 制約違反時のユーザーフレンドリーなエラーメッセージUI
- [ ] 既存データのマイグレーション実行（管理者画面からPOST /api/migration）
- [ ] 4-A+-03: データ/検索条件ベースグラフ操作
- [ ] 4-A+-04: 中クリック移動
- [ ] 4-A+-05: 左クリックエリア選択

---

## 確認事項・懸念

- 既存データに孤立ノードがある場合、`POST /api/migration` で一括修復可能。管理者のみ実行可能
- ルートレポジトリ自動作成はDB初期化時（`getDb()`呼び出し時）に実行。既存DBでは初回アクセス時に作成される
- GenericUploaderのレポジトリ選択はデフォルトでルートレポジトリが選択される
- `root-repository.ts` の `ensureRootRepository()` は `db.ts` の `ensureRootRepo()` と重複あり。`db.ts` 側が実際に使用される（起動時の軽量バージョン）

---

## 最新コミット

```
feat(hierarchy): レポジトリ階層制約を導入（spec-roadmap5）
```
