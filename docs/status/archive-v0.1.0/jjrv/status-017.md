# Status 017

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: EntityCard統一とfavoriteリクエスト修正

---

## 完了タスク

- [x] /results の favorite 取得が連続発火しないよう依存を修正
- [x] EntityCard のアクションボタンで親クリックを停止
- [x] dev/components の EntityCard を実際の挙動に近づけて統一

---

## 技術的メモ

- paged配列の参照変化による再取得を `pagedIdsKey` で抑制
- アクションボタンは `stopPropagation()` でカード遷移を抑止
