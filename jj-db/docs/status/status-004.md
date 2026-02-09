# Status 004

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: SQLite永続化の実装

---

## 完了タスク

- [x] better-sqlite3をインストール・ネイティブビルド
- [x] SQLiteスキーマ・接続管理（db.ts）を作成
- [x] リポジトリ層（entity-repository.ts）を実装
- [x] API Routes（CRUD）を実装
  - GET/POST `/api/entities`
  - GET/PUT/DELETE `/api/entities/[id]`
  - POST `/api/entities/seed`（初期データ投入）
- [x] フロントエンド用APIクライアント（entity-api.ts）を作成
- [x] ページをAPI呼び出しに移行
  - results/page.tsx
  - view/page.tsx
  - GenericUploader
- [x] GenericUploaderをDB保存のみに簡素化
- [x] ドキュメント更新（CLAUDE.md, GenericUploader/README.md）

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| Button | ✅ 完成 |
| BackButton | ✅ 完成 |
| EntityCard | ✅ 完成 |
| GenericUploader | ✅ SQLite対応 |

### Pages
| パス | 状態 |
|------|------|
| `/` | ✅ 実装済み |
| `/results` | ✅ SQLite API |
| `/register` | ✅ SQLite API |
| `/view` | ✅ SQLite API |
| `/dev/components` | ✅ 実装済み |

### API Routes
| エンドポイント | メソッド | 状態 |
|----------------|----------|------|
| `/api/entities` | GET/POST | ✅ |
| `/api/entities/[id]` | GET/PUT/DELETE | ✅ |
| `/api/entities/seed` | GET/POST | ✅ |

---

## 次のタスク（優先順）

1. 検索UI改善（並び替え/フィルタUI）
2. エンティティ編集機能
3. エンティティ削除機能（UI）

---

## 技術的メモ

- データベース: `data/mat-db.sqlite`（.gitignore済み）
- WALモード有効
- better-sqlite3はネイティブモジュールのため、初回は`npm run build-release`が必要
- `entity-store.ts`は後方互換性のため残存（deprecated）
