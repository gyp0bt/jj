# Status 003

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: 既存変更整理・format対応・永続化/検索

---

## 完了タスク

- [x] 既存変更を整理して複数コミットに分割
- [x] Biomeの全体フォーマット適用＆lint通過
- [x] ローカルストレージによる永続化を追加
- [x] 検索ロジックを共通化し、results/viewをストレージ参照に移行
- [x] libドキュメント追加

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| Button | ✅ 完成 |
| BackButton | ✅ 完成 |
| EntityCard | ✅ 完成 |
| GenericUploader | ✅ 完成 |

### Pages
| パス | 状態 |
|------|------|
| `/` | ✅ 実装済み |
| `/results` | ✅ ローカルストレージ（初期MOCK） |
| `/register` | ✅ 実装済み |
| `/view` | ✅ ローカルストレージ（初期MOCK） |
| `/dev/components` | ✅ 実装済み |

---

## 次のタスク（優先順）

1. 検索UI改善（並び替え/フィルタUI）
2. データ永続化の拡張（FS Access/APIへの統合）

---

## 技術的メモ

- `entity-store.ts` で `localStorage` を簡易永続化（キー: `mat-db.entities`）。
- `entity-search.ts` に検索ロジックを分離。
- `GenericUploader` は保存時に `upsertEntity` を実行してストレージ更新。
