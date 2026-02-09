# Status 005

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: 検索コンポーネントの拡充

---

## 完了タスク

- [x] SearchBarコンポーネントの実装
  - 検索キーワード入力バー
  - リアルタイム検索対応
  - クリアボタン付き
- [x] SearchFilterコンポーネントの実装
  - タグ選択（複数選択可能）
  - ドメインフィルタ（ドロップダウン）
  - 並び替え機能（作成日時、更新日時、名前、昇順/降順）
  - 折りたたみ可能なパネル
- [x] entity-search.tsに並び替え・ドメインフィルタ機能を追加
- [x] results/page.tsxを新しいコンポーネントで更新
  - SearchBarとSearchFilterを統合
  - URLパラメータで検索状態を保持
  - 利用可能なタグとドメインを自動取得
- [x] dev/componentsにプレビュー追加
- [x] ドキュメント更新（components/README.md, 各コンポーネント仕様書）

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| Button | ✅ 完成 |
| BackButton | ✅ 完成 |
| EntityCard | ✅ 完成 |
| GenericUploader | ✅ SQLite対応 |
| SearchBar | ✅ 完成 |
| SearchFilter | ✅ 完成 |

### Pages
| パス | 状態 |
|------|------|
| `/` | ✅ 実装済み |
| `/results` | ✅ 検索UI拡充済み |
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

1. エンティティ編集機能
2. エンティティ削除機能（UI）
3. 検索履歴機能（オプション）

---

## 技術的メモ

- 検索機能: キーワード、タグ、ドメイン、並び替えに対応
- URLパラメータ: `q`（キーワード）、`tags`（カンマ区切り）、`domain`、`sortBy`、`sortOrder`で状態保持
- 並び替え: `created`（作成日時）、`updated`（更新日時）、`name`（名前）に対応
- 検索ロジック: `entity-search.ts`に集約
