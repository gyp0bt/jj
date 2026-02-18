[← README.md](../../README.md) | [← roadmap](../roadmap.md)

# M3: Neo4j統合パイプライン設計仕様書

**日付**: 2026-02-18
**マイルストーン**: M3（Neo4j統合パイプライン）
**ステータス**: 設計段階

---

## 概要

jj→Neo4j→jjrv のエンドツーエンドデータパイプラインの設計仕様。
jjで構築したプロジェクトグラフをNeo4jに永続化し、jjrvから横断的にアクセスする。

---

## アーキテクチャ

```
┌──────────────────┐         ┌─────────┐         ┌─────────────────┐
│  jj (Python CLI) │ ──W/R──▶│ Neo4j   │◀──R──── │ jjrv (Next.js)  │
│                  │         │ (共有)   │         │                 │
│ ・parse          │         │         │         │ ・リポジトリ一覧  │
│ ・export --neo4j │         │ 5.x     │         │ ・ノード検索      │
│ ・export --cypher│         │ Bolt    │         │ ・リレーション表示 │
└──────────────────┘         └─────────┘         └─────────────────┘
         │                        ▲                       │
         │                        │                       │
         └── shared/neo4j_schema ─┘── shared/types ───────┘
```

### データフロー

1. `jj parse` → `graph.yaml` にローカル永続化
2. `jj export --target neo4j` → Neo4jにバッチupsert
3. jjrv → Neo4jから読み取り → UI表示

---

## 実装状況

### 完了済み（jj側）

| コンポーネント | ファイル | 状態 |
|---------------|---------|------|
| Neo4jConnector | `services/export/connectors/neo4j.py` | 完了（489行） |
| Neo4jExporter | 同上（priority=30） | 完了 |
| CypherExporter | 同上（priority=31） | 完了 |
| Neo4jConfig | `shared/config.py` | 完了 |
| Neo4jスキーマ定義 | `shared/neo4j_schema.py` | 完了（6ラベル, 14リレーション） |
| データ型定義 | `shared/types.py` | 完了 |
| Dockerセットアップ | `shared/neo4j/docker-compose.yml` | 完了 |
| スキーマ初期化 | `shared/neo4j/init/01-schema.cypher` | 完了 |
| テストスイート | `tests/test_neo4j_connector.py` | 完了（839行, 19クラス） |

### 未着手（jjrv側）

| コンポーネント | 設計文書 | 実装ファイル |
|---------------|---------|-------------|
| Neo4jドライバ導入 | spec-roadmap6.md Phase 6-N-01 | `src/lib/datasource/neo4j-driver.ts` |
| IEntityRepository抽象化 | Phase 6-N-03 | `src/lib/datasource/types.ts` |
| Neo4jエンティティリポジトリ | Phase 6-N-04 | `src/lib/datasource/neo4j-entity-repository.ts` |
| Neo4jリレーションリポジトリ | Phase 6-N-05 | `src/lib/datasource/neo4j-relation-repository.ts` |
| データソース切替ファクトリ | Phase 6-N-06 | `src/lib/datasource/factory.ts` |
| 接続設定UI | Phase 6-N-02 | `src/components/settings/` |

---

## Neo4jスキーマ契約

### ノードラベル

| ラベル | 対応するjjノードtype | 用途 |
|--------|---------------------|------|
| JJFile | go, input, output, asset, version_diff 等 | ファイルノード全般 |
| JJMaterial | abaqus_material | Abaqus物性定義 |
| JJRun | run | 実行ジョブ |
| JJTag | tag | タグ |
| JJDBMaterial | db_material | jjrv材料データベース |
| JJDBTest | db_test | jjrv試験データ |

### 主要リレーション

| リレーション | 意味 |
|-------------|------|
| NEXT_VERSION | バージョン系列 |
| INCLUDES | インクルード関係 |
| HAS_OUTPUT | 入力→出力 |
| RESULT_OF | 結果→入力 |
| USES_MATERIAL | 物性利用 |
| ASSIGNED_TO | elset割り当て |

### メッシュ関連プロパティ（JJFile上）

| プロパティキー | 型 | 格納形式 | 用途 |
|---------------|-----|----------|------|
| mesh_node_count | int | ネイティブ | ノード数 |
| mesh_element_count | int | ネイティブ | 要素数 |
| mesh_element_quality | str | JSON文字列 | 要素タイプ別品質統計 |
| mesh_topology_groups | str | JSON文字列 | 連結成分グループ |
| mesh_elset_summary | str | JSON文字列 | elset別サマリー |
| mesh_element_types | str | JSON文字列 | 要素タイプ別カウント |

**型変換ルール**: Neo4jはネストされたプロパティ（dict, list[list]）を直接格納できないため、`_sanitize_property_value()`がJSON文字列に変換する。jjrv側ではJSON.parse()で復元する。

### diff関連プロパティ（JJFile上、type=version_diff）

| プロパティキー | 型 | 格納形式 | 用途 |
|---------------|-----|----------|------|
| diff_summary | str | ネイティブ | テーブル形式の差分要約 |
| diff_details | str | ネイティブ | ブロック別詳細差分 |
| diff_unified | str | ネイティブ | unified diff形式（+/-表記） |
| has_diffs | bool | ネイティブ | 差分有無 |

### 一意性制約

```cypher
(n:JJFile) REQUIRE (n.project, n.jj_id) IS UNIQUE
(n:JJMaterial) REQUIRE (n.project, n.jj_id) IS UNIQUE
```

### インデックス

```cypher
// 検索用
(n:JJFile) ON (n.name), (n.type), (n.project)
(n:JJMaterial) ON (n.name), (n.project)
(n:JJRun) ON (n.project)
// メッシュ統計値検索用
(n:JJFile) ON (n.mesh_node_count), (n.mesh_element_count)
```

プロジェクト単位でデータ隔離される。

---

## 実装フェーズ

### Phase 1: パイプライン動作確認（jj側完了確認）

- [x] Neo4jExporter/CypherExporterの動作確認テスト
- [x] docker-compose upでのNeo4j起動確認
- [x] `jj export --target neo4j` のエンドツーエンド検証

### Phase 2: jjrv IEntityRepository抽象化

jjrvの既存SQLiteリポジトリ（`entity-repository.ts`）を
IEntityRepositoryインターフェースで抽象化する。

```typescript
interface IEntityRepository {
  findAll(filters?: SearchFilters): Promise<StringEntity[]>;
  findById(id: string): Promise<StringEntity | null>;
  create(entity: CreateEntityInput): Promise<StringEntity>;
  update(id: string, patch: Partial<StringEntity>): Promise<StringEntity>;
  delete(id: string): Promise<void>;
  search(query: string, filters?: SearchFilters): Promise<StringEntity[]>;
}
```

### Phase 3: Neo4jリポジトリ実装

- Neo4jドライバ（`neo4j-driver`パッケージ）導入
- IEntityRepositoryのNeo4j実装
- Cypherクエリビルダー

### Phase 4: データソース切替

- SQLite↔Neo4jファクトリパターン
- 環境変数/設定UIによる切替
- フォールバック動作

---

## 懸念事項・設計判断

### ID体系の統一

jjはint型ID、Neo4jは`(project, jj_id)`の複合キー。
jjrvではstring型IDを使用。変換ルール:

- jj→Neo4j: `{project}:{jj_id}` 形式で保持
- Neo4j→jjrv: `jj_id`をstring化して使用

### 接続情報の管理

- jj: `.jj/credentials` (暗号化) または `config.yaml`
- jjrv: 環境変数 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- 共通: `bolt://localhost:7687` がデフォルト

### パフォーマンス考慮

- バッチupsert（UNWIND+MERGE）で大量ノードに対応
- jjrvからの読み取りはページネーション必須
- インデックス設定済み（name, type, projectカラム）

---

## 次回TODO

- [ ] Phase 2: jjrvのIEntityRepository抽象化着手
- [ ] Neo4jドライバの選定（neo4j-driver vs neo4j-driver-core）
- [ ] jjrv側のCypher生成パターン検討
- [ ] 統合テスト環境の構築（docker-compose + テストデータ）
