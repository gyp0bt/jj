# Status 039

> [← README.md](../../README.md)

**日付**: 2026-01-29
**セッション**: ロードマップ1の実装（ユーザー運用の実現）

---

## 完了タスク

### 1. 検索履歴の再利用（履歴UI）

- [x] SearchHistoryPanelコンポーネントを作成
  - 過去の検索履歴をリスト表示
  - 相対時間表示（「5分前」「2時間前」など）
  - フィルター条件の可視化
  - クリックで検索条件を復元
- [x] 検索ページに履歴ボタンを追加
  - 検索バーの右側に履歴アイコンボタン
  - モーダル形式で履歴パネルを表示

### 2. EntityTypeにattached_documentsフィールドを追加

- [x] types.tsにDocument型とAttachedDocument型を追加
  - Document: id, name, relativePath, mimeType, size, description, createdBy, createdAt, updatedAt
  - AttachedDocument: relativePath, documentId
- [x] StringEntityにattachedDocumentsフィールドを追加
- [x] db.tsにdocumentsテーブルとentity_documentsテーブルを追加
  - documentsテーブル: ドキュメントのメタデータ管理
  - entity_documents: エンティティとドキュメントの多対多関係
- [x] document-repository.tsを作成（CRUD操作とエンティティへの紐付け）

### 3. StringEntityのtypeをMaterial, Project, Tagに限定

- [x] EntityType型を "Material" | "Project" | "Tag" | null に変更
- [x] "Document" をEntityTypeから削除（別オブジェクトとして管理）
- [x] SearchBarコンポーネントのEntityType選択オプションを更新

### 4. アカウント設定機能（アイコン、表示名、パスワード変更）

- [x] User型にavatarフィールドを追加
- [x] DBスキーマにavatarカラムを追加（マイグレーション対応）
- [x] user-repositoryのupdateUser関数をavatar対応に更新
- [x] /api/auth/me にPATCHメソッドを追加
  - 表示名変更
  - アバター（アイコン色）変更
  - パスワード変更（現在のパスワード確認必須）
- [x] user-apiにupdateProfile関数とchangePassword関数を追加
- [x] AccountSettingsModalコンポーネントを作成
  - プロフィールタブ: アイコン色選択（18色）、表示名編集
  - パスワードタブ: 現在のパスワード、新しいパスワード、確認入力
- [x] UserIconコンポーネントをavatar（色）対応に更新
  - xlサイズを追加
  - 17色のカラーパレット対応
- [x] AccountStatusにアカウント設定ボタンとモーダルを統合
- [x] AuthContextにrefreshUser関数を追加

---

## 変更ファイル

### 新規作成
- `src/components/SearchHistoryPanel/index.tsx` - 検索履歴パネル
- `src/components/AccountSettingsModal/index.tsx` - アカウント設定モーダル
- `src/lib/document-repository.ts` - ドキュメントCRUD

### 更新
- `src/app/search/page.tsx` - 検索履歴パネル統合
- `src/lib/types.ts` - Document型、AttachedDocument型、User.avatar追加、EntityType変更
- `src/lib/db.ts` - documents/entity_documentsテーブル、avatarカラム追加
- `src/lib/user-repository.ts` - avatar対応
- `src/lib/user-api.ts` - updateProfile, changePassword関数追加
- `src/app/api/auth/me/route.ts` - PATCHメソッド追加
- `src/components/SearchBar/index.tsx` - EntityType選択オプション更新
- `src/components/UserIcon/index.tsx` - avatar色対応、xlサイズ追加
- `src/components/AccountStatus/index.tsx` - 設定ボタン、モーダル統合
- `src/contexts/AuthContext.tsx` - refreshUser関数追加

---

## 次回への引継ぎ

### ロードマップ2（検索・閲覧体験の拡張）
- [ ] グループ化機能をカードビューコンポーネントの一部として統合
- [ ] ダイアグラムビューのグループ化候補プロパティを一覧で確認したり順序を簡便に変更するための設定用ウィンドウコンポーネントを実装
- [ ] ダイアグラムビュー / テーブルビュー / カードビュー / グラフビューの順に見やすいのでswitch順を変更
- [ ] ダイアグラムビュー、グラフビューで表示するユーザー情報がidになっているので表示名に変更
- [ ] テーブルビューの0行目の列が書いてある箇所を押して列のソートができるよう変更。列下に部分一致の空白区切りフィルター機能実装
- [ ] グルーピング設定のローカルストレージ永続化（プリセット保存）
- [ ] グラフビューでもダイアグラムビューの動的グループ化機能を実装

### その他
- [ ] ドラッグ&ドロップ入力の強化（複数ファイル/分割）
- [ ] import/export（CSV/JSON/INP等）の整備

---
