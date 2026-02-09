# Status 013

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: TODO 1 再開（ユーザー運用/シード統合）

---

## 完了タスク

- [x] エンティティAPIをユーザー認証・スコープ対応
- [x] 検索履歴の保存APIを追加
- [x] /results・/register・/view をログイン必須化
- [x] シード処理で管理者ユーザーと材料データを同時投入

---

## 技術的メモ

- `created_by` をエンティティに反映
- `/api/search-history` で検索履歴の保存/取得
- `/api/entities/seed` で管理者ユーザーの自動作成 + mock挿入
