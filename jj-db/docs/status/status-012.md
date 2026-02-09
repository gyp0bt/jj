# Status 012

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: TODO 1 再開（ユーザー運用の基盤）

---

## 完了タスク

- [x] エンティティAPIを認証必須に変更
- [x] ユーザーIDで材料データをスコープ
- [x] 検索履歴の保存APIを追加
- [x] /results, /register, /view をログイン必須に統一

---

## 技術的メモ

- `created_by` をエンティティに紐づけ
- 検索履歴は `/api/search-history` で保存/取得
