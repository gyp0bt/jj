# spec-roadmap6: jj統合・レポジトリダッシュボード

> [← README.md](../README.md)

---

## 背景

### プロジェクト統合の経緯

mat-db を jj-db にリネームし、jj プロジェクトと統合する。

| プロジェクト | 役割 | 技術 |
|-------------|------|------|
| **jj** (Python CLI) | ローカルプロジェクトのフォルダ/ファイルを解析しグラフデータ化。Obsidian/Neo4j/CSV/JSONにエクスポート | Python, NetworkX, Pydantic, Streamlit |
| **jj-db** (Next.js Web) | jjで構造化したグラフデータをNeo4j経由で参照し、レポジトリダッシュボードとして可視化 | Next.js 15, React 19, TypeScript, Tailwind CSS v4 |

### 統合後のアーキテクチャ

```
ローカルプロジェクト
    │
    ▼
[jj parse] ─── フォルダ/ファイル解析 → グラフ構築
    │
    ▼
[jj export --target neo4j] ─── Neo4jへエクスポート
    │
    ▼
[Neo4j Database] ◄─── グラフデータの永続化層（真実のソース）
    │
    ▼
[jj-db] ─── Neo4j経由でグラフデータを参照・可視化
    │
    ├── レポジトリダッシュボード（新機能）
    ├── 検索・フィルタリング（既存機能を維持）
    └── グラフ/ダイアグラム/テーブル可視化（既存機能を維持）
```

### 設計原則

1. **jjがデータの生成者**: グラフデータの構築・更新はjj CLI側の責務
2. **Neo4jが真実のソース**: jj-dbはNeo4jを読み取り専用（＋メタデータ書き込み）で使用
3. **既存機能の維持**: 検索・可視化ロジックはそのまま。データソースをSQLite→Neo4jに段階的に移行
4. **ダッシュボードの追加**: レポジトリ単位の俯瞰ビューを新たに実装

---

## データモデルの対応関係

### jj → Neo4j → jj-db のマッピング

| jj (Python) | Neo4j | jj-db (TypeScript) |
|-------------|-------|---------------------|
| `Node(id, type, name, format, properties)` | `(:Entity {id, type, name, format, ...props})` | `StringEntity` |
| `Relation(id, label, node1_id, node2_id)` | `-[:LABEL {id}]->` | `Relation` |
| `properties: dict` | ノードプロパティ | `sysProps` + `userProps` |
| `type: str` (file, directory, tag...) | ノードラベル or `type` プロパティ | `sysTags` |

### jj のファイル解析で生成されるノード種別

| jjのtype | jj-dbでの対応 | 説明 |
|----------|-------------|------|
| `project` | `sysTags: ["repository"]` | jj parseの対象プロジェクト |
| `directory` | `sysTags: ["directory"]` | ディレクトリ |
| `file` | formatに応じたsysTags | ファイル（.inp, .csv, .json等） |
| `tag` | `sysTags: ["tag-definition"]` | タグノード |
| `keyword` | `sysTags: ["keyword"]` (新規) | CAEキーワード |

### jj のRelationラベル → jj-db のRelationラベル

| jjのlabel | jj-dbでの対応 | 説明 |
|-----------|-------------|------|
| `child` | `child` | 親子関係（ディレクトリ構造） |
| `contains` | `contains` | 包含関係 |
| `tagged` | `tagged_with` | タグ関係 |
| `similar` | `similar_to` | 類似関係 |
| `depends_on` | `depends_on` (新規) | 依存関係 |

---

## フェーズ構成

### Phase 6-N: Neo4jデータソース接続

> jj側で `jj export --target neo4j` によりエクスポート済みのデータをjj-dbから参照する基盤

| # | 要件 | 概要 | 優先度 |
|---|------|------|--------|
| 6-N-01 | Neo4jドライバー導入 | `neo4j-driver` パッケージの導入、接続設定 | P0 |
| 6-N-02 | 接続設定UI | Neo4j接続情報（URI, user, password）の設定画面 | P0 |
| 6-N-03 | データソース抽象化層 | SQLite/Neo4j両対応のリポジトリパターン。`IEntityRepository` インターフェース | P0 |
| 6-N-04 | Neo4jエンティティリポジトリ | Cypherクエリによるエンティティ CRUD | P0 |
| 6-N-05 | Neo4jリレーションリポジトリ | Cypherクエリによるリレーション管理 | P0 |
| 6-N-06 | データソース切替 | 環境変数/UI設定でSQLite↔Neo4jを切替 | P1 |
| 6-N-07 | Neo4j検索アダプター | 既存の `entity-search.ts` ロジックをNeo4j Cypherに変換 | P1 |

#### 技術詳細: データソース抽象化

```typescript
// src/lib/datasource/types.ts
interface IEntityRepository {
  findAll(filters?: SearchFilters): Promise<StringEntity[]>;
  findById(id: string): Promise<StringEntity | null>;
  create(entity: Omit<StringEntity, 'id' | 'createdAt' | 'updatedAt'>): Promise<StringEntity>;
  update(id: string, patch: Partial<StringEntity>): Promise<StringEntity>;
  delete(id: string): Promise<void>;
  search(query: string, filters?: SearchFilters): Promise<StringEntity[]>;
}

interface IRelationRepository {
  findByEntityId(entityId: string): Promise<Relation[]>;
  findAll(): Promise<Relation[]>;
  create(relation: Omit<Relation, 'id' | 'createdAt'>): Promise<Relation>;
  delete(id: string): Promise<void>;
}

// src/lib/datasource/neo4j-entity-repository.ts
// src/lib/datasource/sqlite-entity-repository.ts
// src/lib/datasource/factory.ts — 環境に応じてインスタンスを返す
```

#### 接続設定

```typescript
// 環境変数
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
DATA_SOURCE=neo4j  // "neo4j" | "sqlite"
```

---

### Phase 6-D: レポジトリダッシュボード

> jj-dbの新たな中核機能。レポジトリ単位でプロジェクトの全体像を俯瞰するダッシュボード

| # | 要件 | 概要 | 優先度 |
|---|------|------|--------|
| 6-D-01 | レポジトリ一覧ページ | ユーザー所有のレポジトリをカード形式で一覧表示 | P0 |
| 6-D-02 | レポジトリ概要ビュー | README表示、基本統計（ファイル数、ディレクトリ数、タグ数）、最終更新日 | P0 |
| 6-D-03 | ファイルブラウザ | GitHub風のファイル/ディレクトリ一覧。パスナビゲーション付き | P0 |
| 6-D-04 | レポジトリグラフ概観 | レポジトリ内のノード/リレーションを力学グラフで可視化（既存EntityGraphの拡張） | P1 |
| 6-D-05 | アクティビティタイムライン | 最近の変更履歴（jj parse による更新をタイムライン表示） | P1 |
| 6-D-06 | ファイル詳細パネル | ファイル選択時にbody内容、プロパティ、関連タグを右パネルに表示 | P1 |
| 6-D-07 | レポジトリ間比較 | 2つのレポジトリのファイル構成・タグ構成を並列比較 | P2 |
| 6-D-08 | ダッシュボード集計ウィジェット | ファイル種別分布（pie chart）、タグクラウド、プロパティ分布 | P2 |

#### UIレイアウト設計

```
/repos (レポジトリ一覧)
┌─────────────────────────────────────────────────┐
│  TopNav [jj-db]  [Search] [Repos]  [User ▼]    │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Repo A   │  │ Repo B   │  │ Repo C   │      │
│  │ 📁 12    │  │ 📁 8     │  │ 📁 25    │      │
│  │ 🏷 5 tags│  │ 🏷 3 tags│  │ 🏷 12 tag│      │
│  │ ⭐ 3     │  │ ⭐ 1     │  │ ⭐ 7     │      │
│  │ 更新 2h前│  │ 更新 1d前│  │ 更新 5m前│      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
└─────────────────────────────────────────────────┘

/repos/[id] (レポジトリ詳細)
┌─────────────────────────────────────────────────┐
│  TopNav [jj-db]  user / Repo A                  │
├──────────────┬──────────────────────────────────┤
│  Code  Graph │  README.md                       │
│  Activity    │  ┌────────────────────────────┐  │
│              │  │ # Project A                │  │
├──────────────┤  │ CAE解析プロジェクト...      │  │
│              │  └────────────────────────────┘  │
│  📁 materials│                                  │
│  📁 docs     │  ── ファイル一覧 ──              │
│  📄 go_steel │  📁 materials/    3 files        │
│  📄 README   │  📁 docs/         2 files        │
│              │  📄 go_steel_v1.inp  2.3KB       │
│              │  📄 README.md        1.1KB       │
└──────────────┴──────────────────────────────────┘
```

---

### Phase 6-S: 検索の拡張（Neo4j活用）

> 既存の検索ロジックをNeo4jのCypherに対応させ、グラフネイティブな検索を実現

| # | 要件 | 概要 | 優先度 |
|---|------|------|--------|
| 6-S-01 | グラフトラバーサル検索 | N親等以内のノードを辿る近傍検索 | P1 |
| 6-S-02 | パス検索 | 2つのノード間の最短パスを発見 | P2 |
| 6-S-03 | 類似ノード推薦 | 共通タグ・プロパティに基づく類似ノードの推薦 | P2 |
| 6-S-04 | Cypherクエリ直接実行 | 上級者向け: 生Cypherクエリの入力・実行 | P2 |

---

### Phase 6-J: jj CLIとの連携強化

> jj CLI側の更新をjj-dbにリアルタイム反映するための仕組み

| # | 要件 | 概要 | 優先度 |
|---|------|------|--------|
| 6-J-01 | Webhook/ポーリング | `jj export` 完了時にjj-dbのキャッシュを無効化 | P2 |
| 6-J-02 | 差分同期 | 前回エクスポートからの差分のみを検出・更新 | P2 |
| 6-J-03 | jj-db→jj フィードバック | jj-db上でのタグ付け・メモをjjのローカルストレージに反映 | P3 |

---

## 実装ロードマップ

### マイルストーン

```
M1: Neo4j接続基盤      (6-N-01 〜 6-N-05)
 │   データソース抽象化層の実装
 │   SQLite/Neo4j両対応
 │
M2: レポジトリ一覧      (6-D-01 〜 6-D-03)
 │   レポジトリカード一覧
 │   ファイルブラウザ
 │   README表示
 │
M3: ダッシュボード充実    (6-D-04 〜 6-D-08)
 │   グラフ概観
 │   アクティビティタイムライン
 │   統計ウィジェット
 │
M4: 検索拡張            (6-S-01 〜 6-S-04)
 │   グラフトラバーサル
 │   Cypherクエリ
 │
M5: jj連携              (6-J-01 〜 6-J-03)
     リアルタイム同期
```

### 推奨実装順序

**第1段階**: M1 (Neo4j接続) → M2 (レポジトリ一覧)
- まずNeo4jへの接続を確立し、既存のSQLiteロジックと並行稼働
- レポジトリ一覧を `/repos` ページとして実装

**第2段階**: M3 (ダッシュボード) + M4 (検索拡張)
- レポジトリ詳細画面の充実
- Neo4jのグラフアルゴリズムを活用した検索の強化

**第3段階**: M5 (jj連携)
- jj CLI との双方向データフロー

---

## 実装ファイル対応（予定）

| # | 要件 | 主要ファイル | 新規/既存 |
|---|------|-------------|-----------|
| 6-N-01 | Neo4jドライバー | `src/lib/datasource/neo4j-driver.ts` | 新規 |
| 6-N-02 | 接続設定UI | `src/app/settings/page.tsx` | 新規 |
| 6-N-03 | データソース抽象化 | `src/lib/datasource/types.ts` | 新規 |
| 6-N-04 | Neo4jエンティティリポジトリ | `src/lib/datasource/neo4j-entity-repository.ts` | 新規 |
| 6-N-05 | Neo4jリレーションリポジトリ | `src/lib/datasource/neo4j-relation-repository.ts` | 新規 |
| 6-N-06 | データソース切替 | `src/lib/datasource/factory.ts` | 新規 |
| 6-N-07 | Neo4j検索アダプター | `src/lib/datasource/neo4j-search.ts` | 新規 |
| 6-D-01 | レポジトリ一覧 | `src/app/repos/page.tsx` | 新規 |
| 6-D-02 | レポジトリ概要 | `src/app/repos/[id]/page.tsx` | 新規 |
| 6-D-03 | ファイルブラウザ | `src/components/FileBrowser/index.tsx` | 新規 |
| 6-D-04 | レポジトリグラフ | `src/components/RepoGraph/index.tsx` | 新規 |
| 6-D-05 | アクティビティタイムライン | `src/components/ActivityTimeline/index.tsx` | 新規 |
| 6-D-06 | ファイル詳細パネル | `src/components/FileDetailPanel/index.tsx` | 新規 |
| 6-D-08 | 集計ウィジェット | `src/components/DashboardWidgets/index.tsx` | 新規 |

---

## 既存機能との関係

### 維持する既存機能

| 機能 | 現在の実装 | 統合後 |
|------|-----------|--------|
| 検索（名前/タグ/プロパティ） | `entity-search.ts` + SQLite | Neo4jアダプター経由で同じロジック |
| カードビュー | `EntityCard` | そのまま維持 |
| テーブルビュー | `EntityTable` | そのまま維持 |
| グラフビュー | `EntityGraph` (D3-Force) | そのまま維持 + レポジトリグラフにも流用 |
| ダイアグラムビュー | `EntityDiagram` | そのまま維持 |
| サイドバーツリー | `SidebarTreeNav` | そのまま維持（ダッシュボード内にも配置） |
| 階層制約 | `hierarchy-validator.ts` | Neo4j側のCypher制約に移行 |
| お気に入り/統計 | SQLiteテーブル | jj-db固有データとしてSQLiteに残す |

### 新規ページ

| ルート | 説明 |
|--------|------|
| `/repos` | レポジトリ一覧ダッシュボード |
| `/repos/[id]` | レポジトリ詳細（README + ファイルブラウザ） |
| `/repos/[id]/graph` | レポジトリ内グラフ概観 |
| `/repos/[id]/activity` | アクティビティタイムライン |
| `/settings` | データソース接続設定 |

---

## jj側のデータモデル参考

### jj Node (Python / Pydantic)

```python
class Node(BaseModel):
    id: int
    type: str        # "project", "directory", "file", "tag", "keyword"
    name: str
    format: str      # "abaqus_inp", "csv", "json", etc.
    properties: dict[str, Any]
```

### jj Relation (Python / Pydantic)

```python
class Relation(BaseModel):
    id: int
    label: str       # "child", "contains", "tagged", "similar"
    node1_id: int
    node2_id: int
```

### Neo4jスキーマ（jj export時に生成される想定）

```cypher
// ノード
CREATE (n:Entity {
  id: 1,
  type: "file",
  name: "go_steel_v1.inp",
  format: "abaqus_inp",
  // properties は展開される
  product: "steel",
  version: "v1"
})

// リレーション
CREATE (parent)-[:CHILD {id: 1}]->(child)
CREATE (dir)-[:CONTAINS {id: 2}]->(file)
CREATE (file)-[:TAGGED {id: 3}]->(tag)
```

---

## 技術的考慮事項

### SQLiteとNeo4jの併用

- **グラフデータ**: Neo4j（jjからのエクスポートデータ）
- **アプリケーション固有データ**: SQLite（ユーザー認証、お気に入り、検索履歴、ダウンロード統計）
- **移行期間**: データソース抽象化層により、API層は変更なしで切替可能

### jj-dbのNode ID体系

- jjは `int` ID、jj-dbは `string` ID
- Neo4j経由で受け取る際にstring変換 (`"jj-{id}"` プレフィックス案)
- または jj側でUUID対応を検討

### パフォーマンス

- Neo4jへのクエリはサーバーサイドのAPI Route内で実行
- クライアントサイドのEntityGraph/SidebarTreeNavはAPIレスポンスのJSON配列を受け取る（変更不要）

---

## 関連ドキュメント

- [spec-roadmap4](spec-roadmap4.md): 本番運用・neo4jグラフDB移行計画（本ロードマップの前段）
- [spec-roadmap5](spec-roadmap5.md): レポジトリ階層制約（ダッシュボードの前提となる階層構造）
- [schema-keys](schema-keys.md): sysProps / sysTags 一覧
- [全仕様](全仕様.md): 詳細仕様
