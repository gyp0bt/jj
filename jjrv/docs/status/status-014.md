# Status 014

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: フィルタUI調整とお気に入り/ダウンロード可視化

---

## 完了タスク

- [x] SearchFilterを薄く平く横長レイアウトに調整
- [x] AccountStatusを全ページヘッダーに統一
- [x] お気に入り/ダウンロードの紐付けと可視化を追加
  - API: favorites/downloads/stats
  - /results と /view でカウント表示

---

## 技術的メモ

- お気に入りはトグル、ダウンロードは記録追加
- 統計取得は `/api/entities/stats` と `/api/entities/[id]/stats` を使用
