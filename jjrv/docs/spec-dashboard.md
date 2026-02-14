# spec-dashboard: レポジトリダッシュボード詳細設計

> [← README.md](../README.md)
> 親仕様: [spec-roadmap6](spec-roadmap6.md)

---

## 概要

jj CLIが構造化したプロジェクトグラフデータを、レポジトリ単位で俯瞰するダッシュボード機能。
GitHub/GitLabのレポジトリページをCAEデータ管理に特化させたUI。

---

## 画面構成

### 1. レポジトリ一覧ページ (`/repos`)

#### 機能

- ユーザーが所有/アクセス可能なレポジトリをカード形式で一覧表示
- レポジトリの基本統計（ファイル数、タグ数、最終更新日）をカード内に表示
- レポジトリタイプ（CAE案件, 材料物性, 実験データ等）によるフィルタリング
- 名前による検索

#### カードコンポーネント仕様

```
┌──────────────────────────┐
│ 📦 Repository Name       │  ← レポジトリ名 + アイコン
│ CAE案件                   │  ← レポジトリタイプ (sysProps.repository_type)
│                          │
│ 📁 12 dirs  📄 34 files  │  ← 直下+子孫のディレクトリ/ファイル数
│ 🏷 8 tags                │  ← 関連タグ数
│ ⭐ 5 favorites            │  ← お気に入り数
│                          │
│ 更新: 2026-02-08 14:30   │  ← updatedAt
│ 作成者: user1             │  ← createdBy
└──────────────────────────┘
```

#### データ取得

```typescript
// API: GET /api/repos
// Neo4j Cypher:
MATCH (r:Entity {type: "repository"})
OPTIONAL MATCH (r)-[:CHILD|CONTAINS*]->(child)
RETURN r,
       count(CASE WHEN child.type = "directory" THEN 1 END) as dirCount,
       count(CASE WHEN child.type <> "directory" AND child.type <> "repository" THEN 1 END) as fileCount,
       max(child.updatedAt) as lastChildUpdate
ORDER BY r.updatedAt DESC
```

---

### 2. レポジトリ詳細ページ (`/repos/[id]`)

#### タブ構成

| タブ | 内容 | 対応要件 |
|------|------|---------|
| **Code** | ファイルブラウザ + README | 6-D-02, 6-D-03 |
| **Graph** | レポジトリ内グラフ概観 | 6-D-04 |
| **Activity** | 更新タイムライン | 6-D-05 |
| **Stats** | 統計ダッシュボード | 6-D-08 |

#### 2a. Code タブ（デフォルト）

**上部: レポジトリヘッダ**

```
┌─────────────────────────────────────────────┐
│  📦 user1 / Repo-A         ⭐ Star  📋 Clone │
│  CAE案件 | 更新: 2h前 | 📁 12 | 📄 34       │
├─────────────────────────────────────────────┤
│  [Code] [Graph] [Activity] [Stats]          │
├─────────────────────────────────────────────┤
```

**中部: ファイルブラウザ**

GitHub風のファイル/ディレクトリ一覧テーブル:

```
┌──────────────────────────────────────────┐
│ 📁 materials/          最終更新 2h前      │
│ 📁 docs/               最終更新 1d前      │
│ 📄 go_steel_v1.inp     最終更新 3h前      │
│ 📄 go_aluminum_v2.inp  最終更新 5h前      │
│ 📄 README.md           最終更新 2d前      │
└──────────────────────────────────────────┘
```

- ディレクトリクリックで下位階層に遷移
- パンくずリストでナビゲーション: `Repo-A / materials / thermal /`
- ファイルクリックで既存の詳細ビュー (`/view?id=xxx`) に遷移

**下部: README表示**

- レポジトリ直下のREADME.md（`contains`リレーションで接続されたname="README.md"エンティティ）を検出
- 既存の `BodyRenderer` コンポーネントでMarkdownレンダリング

#### 2b. Graph タブ

- 既存の `EntityGraph` コンポーネントを再利用
- レポジトリ配下のノード/リレーションのみをフィルタして表示
- ノードの色分け:
  - repository: 紫 (#8b5cf6)
  - directory: 黄 (#eab308)
  - file (abaqus_inp): 青 (#3b82f6)
  - file (csv): 緑 (#22c55e)
  - tag: オレンジ (#f97316)

#### 2c. Activity タブ

```
┌──────────────────────────────────────────┐
│  ● 2026-02-08 14:30                      │
│    go_steel_v3.inp が追加されました       │
│                                          │
│  ● 2026-02-08 10:15                      │
│    materials/ に thermal/ が追加          │
│                                          │
│  ● 2026-02-07 16:00                      │
│    README.md が更新されました             │
└──────────────────────────────────────────┘
```

- `createdAt` / `updatedAt` の変更をタイムライン表示
- jj側で更新履歴を保持している場合はそれも統合

#### 2d. Stats タブ

**集計ウィジェット**:

| ウィジェット | 表示内容 | チャート種別 |
|-------------|---------|------------|
| ファイル種別分布 | format別のファイル数 | ドーナツチャート |
| タグクラウド | 頻出タグのワードクラウド | タグクラウド |
| プロパティ分布 | 特定sysProps値の分布 | 棒グラフ |
| 階層深度 | ルートからの深度別ノード数 | ヒストグラム |

---

## 新規コンポーネント

### RepoCard

```typescript
// src/components/RepoCard/index.tsx
type RepoCardProps = {
  repo: StringEntity;
  stats: {
    dirCount: number;
    fileCount: number;
    tagCount: number;
    favoriteCount: number;
    lastUpdate: string;
  };
  onClick: (id: string) => void;
};
```

### FileBrowser

```typescript
// src/components/FileBrowser/index.tsx
type FileBrowserProps = {
  repoId: string;
  currentPath: string[];  // ["materials", "thermal"]
  entries: FileBrowserEntry[];
  onNavigate: (path: string[]) => void;
  onFileClick: (entityId: string) => void;
};

type FileBrowserEntry = {
  id: string;
  name: string;
  type: "directory" | "file";
  format?: string;
  updatedAt: string;
  size?: string;
};
```

### ActivityTimeline

```typescript
// src/components/ActivityTimeline/index.tsx
type ActivityTimelineProps = {
  activities: Activity[];
};

type Activity = {
  id: string;
  type: "create" | "update" | "delete";
  entityName: string;
  entityType: string;
  timestamp: string;
  description?: string;
};
```

### DashboardWidgets

```typescript
// src/components/DashboardWidgets/index.tsx
type DashboardWidgetsProps = {
  entities: StringEntity[];
  relations: Relation[];
};
```

---

## API設計

### 新規エンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|---------|------|
| `/api/repos` | GET | レポジトリ一覧 + 統計 |
| `/api/repos/[id]` | GET | レポジトリ詳細 + README |
| `/api/repos/[id]/tree` | GET | ファイルツリー（指定パス配下） |
| `/api/repos/[id]/stats` | GET | レポジトリ統計 |
| `/api/repos/[id]/activity` | GET | アクティビティログ |

### クエリパラメータ例

```
GET /api/repos?type=CAE案件&sort=updatedAt&order=desc
GET /api/repos/[id]/tree?path=materials/thermal
GET /api/repos/[id]/activity?limit=20&offset=0
```

---

## 既存機能との統合ポイント

### SidebarTreeNav との連携

- レポジトリ詳細ページにも SidebarTreeNav を配置可能
- ツリーのルートを当該レポジトリに限定して表示

### 検索ページとの相互遷移

- 検索結果からレポジトリ詳細へのリンク
- レポジトリ詳細からのスコープ付き検索（レポジトリ内検索）

### EntityGraph の再利用

- レポジトリグラフは EntityGraph に `scopeEntityId` prop を追加して実装
- 指定エンティティの子孫ノードのみをグラフ表示

---

## 段階的実装計画

### Step 1: レポジトリ一覧（SQLiteベース）

現在のSQLiteデータソースで `/repos` ページを実装。
既存の `entity-repository.ts` を使って repository sysTags のエンティティを取得。

### Step 2: ファイルブラウザ

FileBrowser コンポーネントを実装。
既存のリレーション API を使って子ノードを取得。

### Step 3: Neo4j接続

データソース抽象化層を構築し、Neo4jからのデータ取得に切り替え。

### Step 4: 統計・アクティビティ

集計ウィジェットとアクティビティタイムラインを追加。

---

## 関連ドキュメント

- [spec-roadmap6](spec-roadmap6.md): jj統合ロードマップ（親仕様）
- [spec-roadmap5](spec-roadmap5.md): レポジトリ階層制約
- [spec-roadmap4](spec-roadmap4.md): Neo4j移行計画
