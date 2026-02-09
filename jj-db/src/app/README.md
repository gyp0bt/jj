# Pages (App Router)

> [← README.md](../../README.md)

Next.js 15 App Routerによるページ構成。

---

## ルーティング一覧

| パス | ファイル | 説明 | 状態 |
|------|----------|------|------|
| `/` | `page.tsx` | ダッシュボード | ✅ 実装済み |
| `/search` | `search/page.tsx` | 検索結果一覧 | ✅ SQLite API |
| `/register` | `register/page.tsx` | エンティティ登録 | ✅ 実装済み |
| `/view` | `view/page.tsx` | 詳細表示 | ✅ SQLite API |
| `/dev/components` | `dev/components/page.tsx` | コンポーネントプレビュー | ✅ 実装済み |

---

## ページ別README

- [/search](./search/README.md)
- [/register](./register/README.md)
- [/view](./view/README.md)
- [/dev/components](./dev/components/README.md)

---

## 既存コード（domain/base/）

`src/components/` へ移行済み。

---

## TODO

### リファクタリング
- [x] MOCKデータを `src/lib/mock-data.ts` に分離
- [x] search/page.tsx と view/page.tsx のMOCKデータ重複を解消
- [x] domain/base/ のコンポーネントを src/components/ に移行

### 新機能
- [x] データ永続化（SQLite）
- [x] 検索機能の実装
