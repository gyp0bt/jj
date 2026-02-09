# spec-roadmap1: ユーザー運用の実現（完了）

> [← README.md](../README.md)

---

## 設計方針

### 目的
CAE業務チーム（10人規模）が材料物性・案件データを安全に登録・閲覧・管理できる認証基盤と基本CRUDを構築する。

### 方針
1. **JWT認証** — ログイン/ログアウト/セッション管理をJWTトークンで実装。Cookieベースのセッション。
2. **ユーザースコープ** — 登録・閲覧・お気に入り・ダウンロード等をユーザー単位で紐付け。
3. **検索履歴** — ユーザーごとに検索クエリを保存し、再利用可能にする。
4. **統計可視化** — お気に入り数・ダウンロード数・Good数をバッジで表示。
5. **EntityType設計** — Material/Project/Tagの3型に限定し、Documentは別オブジェクト。

---

## 実装要件

| # | 要件 | 状態 | 概要 |
|---|------|------|------|
| 1-01 | ユーザー認証基盤 | 完了 | ログイン/ログアウト/セッション管理（JWT） |
| 1-02 | ユーザーごとのデータ登録・閲覧 | 完了 | 認証/権限/スコープ付きCRUD |
| 1-03 | 検索履歴の保存 | 完了 | ユーザー単位でクエリ保存 |
| 1-04 | 検索履歴の再利用 | 完了 | 履歴UIモーダルで過去クエリを選択・再実行 |
| 1-05 | お気に入り/ダウンロード数の可視化 | 完了 | 紐付け＋バッジ表示 |
| 1-06 | Goodの可視化 | 完了 | Good数の紐付け＋バッジ表示 |
| 1-07 | attached_documentsフィールド | 完了 | EntityTypeにドキュメント添付機能追加 |
| 1-08 | EntityType限定 | 完了 | Material/Project/Tagの3型。Documentは別オブジェクト |
| 1-09 | アカウント設定 | 完了 | アイコン色選択、表示名変更、パスワード変更 |

---

## 実装要件 ↔ ファイル対応テーブル

| # | 要件 | 主要ファイル | 補助ファイル |
|---|------|-------------|-------------|
| 1-01 | ユーザー認証基盤 | `src/app/api/auth/login/route.ts`, `src/app/api/auth/logout/route.ts`, `src/app/api/auth/register/route.ts`, `src/app/api/auth/me/route.ts` | `src/contexts/AuthContext.tsx`, `src/lib/auth.ts`, `src/app/login/page.tsx`, `src/components/LoginForm/index.tsx` |
| 1-02 | ユーザーごとのデータ登録・閲覧 | `src/app/api/entities/route.ts`, `src/lib/entity-repository.ts` | `src/lib/entity-api.ts`, `src/app/register/page.tsx` |
| 1-03 | 検索履歴の保存 | `src/app/api/search-history/route.ts`, `src/lib/search-history-repository.ts` | `src/lib/search-history-api.ts` |
| 1-04 | 検索履歴の再利用 | `src/components/SearchHistoryPanel/index.tsx` | `src/app/search/page.tsx` |
| 1-05 | お気に入り/ダウンロード数の可視化 | `src/app/api/entities/[id]/favorite/route.ts`, `src/app/api/entities/[id]/download/route.ts`, `src/app/api/entities/[id]/stats/route.ts` | `src/lib/entity-stats-repository.ts`, `src/lib/entity-stats-api.ts`, `src/components/EntityMetaBadges/index.tsx` |
| 1-06 | Goodの可視化 | `src/lib/entity-stats-repository.ts` | `src/components/EntityMetaBadges/index.tsx`, `src/lib/db.ts`（goodsテーブル） |
| 1-07 | attached_documentsフィールド | `src/lib/types.ts`, `src/lib/document-repository.ts` | `src/lib/db.ts`（entity_documentsテーブル） |
| 1-08 | EntityType限定 | `src/lib/types.ts` | `src/components/SearchBar/index.tsx` |
| 1-09 | アカウント設定 | `src/components/AccountSettingsModal/index.tsx` | `src/components/UserIcon/index.tsx`, `src/components/AccountStatus/index.tsx`, `src/lib/user-api.ts` |
