# Status 007

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: 検索タグのピル化とpre-push整備

---

## 完了タスク

- [x] SearchBarのタグ入力をピル確定式に変更
  - スペース/Enterで確定、Backspaceで末尾削除
  - 重複タグは大文字小文字無視で抑止
- [x] `/results` のタグ状態を配列で保持し、URLへ反映
- [x] プレビューのタグ入力も新仕様に更新
- [x] pre-pushでSQLite DBファイルを削除するフックを追加
- [x] README差分解消（src/app/README.mdを元に戻し）

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| SearchBar | ✅ タグピル対応 |
| SearchFilter | ✅ 変更済み |

---

## 技術的メモ

- タグURLパラメータはスペース区切りで保存
- pre-pushで `data/mat-db.sqlite` / `data/mat-db.sqlite-wal` / `data/mat-db.sqlite-shm` を削除
