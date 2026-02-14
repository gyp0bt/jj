# status-058: GitHub形式レポジトリ構造の実装

**日付**: 2026-02-06
**前回**: [status-057](status-057.md)
**ブランチ**: `claude/implement-repo-structure-fyLiX`

[README](../../README.md)

---

## 概要

GitHub同様のレポジトリ階層構造を実装。
`root > ユーザー名前空間 > レポジトリ > ディレクトリ/ファイル` の構造を導入し、
フォルダD&D時のレポジトリ自動化とREADME.mdレンダリングを実現した。

---

## 実装内容

### 1. ユーザー名前空間（user_namespace）

- **新規sysTag**: `user_namespace` — ユーザーごとの名前空間を表す
- **定数追加** (`src/lib/constants.ts`):
  - `USER_NAMESPACE_TAG = "user_namespace"`
  - `REPOSITORY_TYPES` — レポジトリタイプの候補一覧（CAE案件、材料物性、解析モデル、実験データ、ドキュメント、その他）
  - `RepositoryType` — 型定義
- **管理モジュール** (`src/lib/user-namespace.ts`):
  - `getUserNamespaceId(username)` — `user:username` 形式でID生成
  - `ensureUserNamespace(userId, username, displayName)` — 名前空間をDBに作成しrootの子に登録
  - `findUserNamespaceByUserId(userId)` — ユーザーIDから名前空間を検索
- **自動作成**:
  - ユーザー登録時（`/api/auth/register`）に自動作成
  - seed時（`/api/auth/seed`）にadminの名前空間を自動作成

### 2. 階層バリデータ拡張 (`src/lib/hierarchy-validator.ts`)

- `isUserNamespace()`, `isUserNamespaceFromTags()` 関数追加
- 新ルール:
  - ユーザー名前空間の親はルートレポジトリのみ
  - ユーザー名前空間の下にはレポジトリのみ配置可能
  - レポジトリの親はレポジトリまたはユーザー名前空間
- `findAncestorRepository()` がuser_namespaceも祖先として認識

### 3. GenericUploader更新 (`src/components/GenericUploader/index.tsx`)

- **フォルダD&D時のレポジトリ化**:
  - トップレベルフォルダを `repository` sysTagで作成（従来は `directory`）
  - サブフォルダは従来通り `directory`
  - `sysProps.repository_type` にレポジトリタイプを設定
- **レポジトリタイプ選択UI**:
  - フォルダモード時に緑色のセレクタを表示
  - `REPOSITORY_TYPES` から選択
- **インポート先デフォルト**:
  - `fetchMyNamespace()` でログインユーザーの名前空間を自動検出
  - デフォルトのインポート先をユーザー名前空間に設定
- **インポート先一覧にuser_namespaceを含める**:
  - `fetchRepositoriesAndNamespaces()` 関数を追加
  - セレクタでユーザー名前空間も選択可能

### 4. Viewページ: README.mdレンダリング (`src/app/view/page.tsx`)

- レポジトリ/ディレクトリ/ユーザー名前空間の詳細ビューで:
  - 直下の子エンティティから `README.md` を検索
  - 見つかればMarkdownRendererでレンダリング表示
- レポジトリバッジ表示:
  - レポジトリ（紫）、ユーザー名前空間（藍）、レポジトリタイプ（緑）のバッジ
- レポジトリ/ディレクトリの場合はコンテンツカラムを非表示

### 5. 検索結果フィルタ (`src/app/search/page.tsx`)

- ユーザー名前空間（`user_namespace`）をルートレポジトリ同様に検索結果から除外

### 6. APIレイヤー (`src/lib/entity-api.ts`)

- `fetchRepositoriesAndNamespaces()` — レポジトリ+ユーザー名前空間の一覧取得
- `fetchMyNamespace()` — ログインユーザーの名前空間を取得

---

## 階層構造まとめ

```
root (repository)
├── user:admin (user_namespace)
│   ├── CAE解析2026 (repository, type=CAE案件)
│   │   ├── src/ (directory)
│   │   │   ├── model.inp
│   │   │   └── material.csv
│   │   └── README.md
│   └── 材料DB (repository, type=材料物性)
│       └── ...
├── user:tanaka (user_namespace)
│   └── 実験結果 (repository, type=実験データ)
│       └── ...
```

---

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/lib/constants.ts` | 修正 | USER_NAMESPACE_TAG, REPOSITORY_TYPES, RepositoryType追加 |
| `src/lib/user-namespace.ts` | **新規** | ユーザー名前空間管理モジュール |
| `src/lib/hierarchy-validator.ts` | 修正 | user_namespace対応ルール追加 |
| `src/lib/entity-api.ts` | 修正 | fetchRepositoriesAndNamespaces, fetchMyNamespace追加 |
| `src/components/GenericUploader/index.tsx` | 修正 | フォルダ→レポジトリ化、type選択UI、デフォルトNS |
| `src/app/view/page.tsx` | 修正 | README.mdレンダリング、レポジトリバッジ |
| `src/app/search/page.tsx` | 修正 | user_namespace非表示 |
| `src/app/api/auth/register/route.ts` | 修正 | ユーザー登録時にNS自動作成 |
| `src/app/api/auth/seed/route.ts` | 修正 | seed時にadmin NS自動作成 |

---

## TODO / 次のステップ

- [ ] 既存ユーザーへのuser_namespaceマイグレーション（既にデータがある場合）
- [ ] レポジトリ一覧ページ（ユーザーページでのレポジトリ一覧表示）
- [ ] レポジトリ作成UIの専用フォーム（GenericUploader以外から）
- [ ] レポジトリタイプのカスタム追加機能
- [x] 5-11: レポジトリツリーナビゲーション（検索ページサイドバー） → [status-059](status-059.md)
- [ ] 5-12: 階層パス全表示（テーブルビュー）
- [ ] 5-13: 制約違反のユーザーフレンドリーエラーメッセージ
