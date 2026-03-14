[← status-index](status-index.md)

# status-022: Neo4j Docker環境構築・IEntityRepository抽象化

- **日付**: 2026-02-18
- **マイルストーン**: M3
- **ブランチ**: claude/setup-neo4j-docker-fDy9r

---

## 概要

status-021のTODO「M3 Phase 2: jjrvのIEntityRepository抽象化着手」を実行。
Docker ComposeによるNeo4j開発環境の統合と、jjrvのデータアクセス層をIEntityRepository/IRelationRepositoryインターフェースで抽象化し、SQLite/Neo4j両バックエンド対応の基盤を構築。

## 実施内容

### 1. Docker Compose統合（プロジェクトルート）

プロジェクトルートにdocker-compose.ymlを新設し、WSL環境でのNeo4j開発環境を一元管理。

- **docker-compose.yml**: Neo4j 5-community、APOC有効、healthcheck付き
- `shared/neo4j/init/` を initスクリプトディレクトリとしてマウント
- ポート: 7474（ブラウザ）、7687（Bolt）

### 2. jjrv環境変数設定

- **jjrv/.env.example**: DATA_SOURCE、NEO4J_URI/USER/PASSWORD、JWT設定のテンプレート
- **.gitignore**: `.env.example`のみ追跡対象に追加

### 3. IEntityRepository / IRelationRepository インターフェース定義

`src/lib/datasource/types.ts` にデータアクセス層の抽象インターフェースを定義。

- **IEntityRepository**: getAllEntities, getEntityById, createEntity, updateEntity, deleteEntity, searchEntities等 14メソッド
- **IRelationRepository**: getAllRelations, getRelationsByEntityId, getRelationGraph等 10メソッド
- **RelatedEntityWithDepth / RelationGraphResult**: N親等グラフ探索の型定義
- **DataSourceType**: `"sqlite" | "neo4j"` リテラル型

### 4. SQLiteリポジトリ実装（既存コードの移植）

既存の`entity-repository.ts`の関数群をクラスベースに移植。

- **sqlite-entity-repository.ts**: SqliteEntityRepository クラス（IEntityRepository実装）
- **sqlite-relation-repository.ts**: SqliteRelationRepository クラス（IRelationRepository実装）
- 既存ロジックの完全移植（rowToEntity, entityToRow, BFS探索等）

### 5. Neo4jリポジトリ実装

neo4j-driver 6.0.1 を導入し、Cypherクエリベースのリポジトリを新規実装。

- **neo4j-driver.ts**: ドライバ管理（シングルトン）、セッション取得、接続検証
- **neo4j-entity-repository.ts**: Neo4jEntityRepository（読み取り専用、書き込みはjj CLI経由）
  - Neo4jノードプロパティ → StringEntity のマッピング（jj_id→id、type→sysTags、properties→sysProps）
  - CONTAINS検索、全ラベル横断クエリ
- **neo4j-relation-repository.ts**: Neo4jRelationRepository（読み取り専用）
  - リレーションシップタイプの小文字変換（NEXT_VERSION → next_version）
  - N親等BFSグラフ探索（Cypherのパス展開）
  - ラベル別・エンティティID別のフィルタリング

### 6. データソース切替ファクトリ

- **factory.ts**: 環境変数 `DATA_SOURCE` で SQLite/Neo4j を切替
  - デフォルト: `sqlite`（後方互換）
  - `neo4j` 指定時: Neo4jリポジトリインスタンスを生成
  - シングルトンパターン + テスト用リセット関数

### 7. ファサード（後方互換レイヤー）

- **entity-repository.ts**: 既存の関数エクスポートを維持しつつ、内部はファクトリ経由で委譲
  - APIルート（5ファイル）の変更不要
  - `RelationGraphResult` / `RelatedEntityWithDepth` 型の再エクスポート

## ファイル構成

```
jjrv/src/lib/datasource/
├── types.ts                          # IEntityRepository, IRelationRepository
├── sqlite-entity-repository.ts       # SQLite実装
├── sqlite-relation-repository.ts     # SQLiteリレーション実装
├── neo4j-driver.ts                   # Neo4j接続管理
├── neo4j-entity-repository.ts        # Neo4j読み取り実装
├── neo4j-relation-repository.ts      # Neo4jリレーション読み取り実装
├── factory.ts                        # データソース切替
└── index.ts                          # 公開API
```

## テスト結果

- tsc --noEmit: **PASSED**（型エラーなし）
- biome check (datasource/ + entity-repository.ts): **PASSED**（9ファイル）
- ビルド: Google Fonts接続不可（ネットワーク制約）のみ、コード起因のエラーなし

## 設計判断

### SQLite/Neo4jの使い分け

| データ種別 | バックエンド | 理由 |
|-----------|-------------|------|
| グラフデータ（jj由来） | Neo4j | jj exportで生成、グラフ探索に最適 |
| ユーザー・認証・統計 | SQLite | jjrv固有、リレーショナルデータ |
| お気に入り・検索履歴 | SQLite | jjrv固有、Neo4j不要 |

### Neo4jリポジトリは読み取り専用

- jjがデータの生成者（jj export --neo4j）
- jjrvはNeo4jを参照専用として使用
- CRUDの書き込み操作はエラーを返す（将来のメタデータ書き込み対応予定）

### ファサードパターンによる後方互換

- `entity-repository.ts` の関数シグネチャを一切変更せず
- APIルート5ファイルの変更不要
- 新規コードは `datasource/` を直接利用推奨

## TODO

- [ ] Neo4j Docker起動・実データでの動作検証（`docker compose up -d` → `jj export --neo4j` → jjrv参照）
- [ ] 接頭辞キーのダッシュボードUI表示名改善（vocab翻訳の適用）
- [ ] 接続設定UI（6-N-02）: Neo4j接続情報の設定画面
- [ ] Neo4j検索アダプター（6-N-07）: Cypher全文検索への拡張
- [ ] 統合テスト: Docker環境でのSQLite↔Neo4j切替テスト
- [ ] jj側 pyproject.toml のneo4j依存バージョン確認・統一

## 確認事項・懸念

- Neo4jドライバのバンドルサイズ: neo4j-driver 6.0.1はサーバーサイドのみ使用のため問題なし
- ID変換: 現状 `jj_id` (int) → `String(jj_id)` で単純変換。プロジェクトスコープの分離は `sysProps.project` で管理
- Google Fontsビルドエラー: オフライン環境では `next/font/local` への切替を検討
