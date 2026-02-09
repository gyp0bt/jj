# Status 019

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: EntityCardにアクション集約

---

## 完了タスク

- [x] favorite/download/copy のロジックをEntityCard内に集約
- [x] /results と /view からアクションロジックを削除

---

## 技術的メモ

- EntityCardで統計取得・お気に入り状態取得・ダウンロード/コピーを実行
- 親クリックを維持しつつアクションは stopPropagation で分離
