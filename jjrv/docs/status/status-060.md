# status-060: jj統合ロードマップ策定・レポジトリダッシュボード設計

**日付**: 2026-02-08
**前回**: [status-059](status-059.md)
**ブランチ**: `claude/plan-jjrv-integration-ZaYij`

[README](../../README.md)

---

## 概要

mat-db → jjrv へのリネームに伴い、jjプロジェクト（Python CLI）との統合ロードマップを策定。
jjrvはjjが構造化したグラフデータをNeo4j経由で参照し、レポジトリダッシュボードとして可視化する役割を担う。

---

## 完了した作業

### 1. jjプロジェクト概要の調査

jj (gyp0bt/jj) は以下の機能を持つPython CLIツール:

- **フォルダ/ファイル解析**: `jj parse` でローカルプロジェクトをスキャンしグラフデータ化
- **データモデル**: Node(id, type, name, format, properties) + Relation(id, label, node1_id, node2_id)
- **エクスポート**: Obsidian (markdown), Neo4j, CSV/JSON
- **対応ファイル形式**: Abaqus (.inp), Fluent (.cas.h5), LS-DYNA (.k, .key, .dat)
- **技術**: Python, NetworkX, Pydantic, pytest (294+テスト), Streamlit

### 2. 統合ロードマップ策定 (spec-roadmap6.md)

5フェーズの統合計画を策定:

| フェーズ | 内容 | 優先度 |
|---------|------|--------|
| **6-N: Neo4j接続基盤** | データソース抽象化層、SQLite/Neo4j両対応 | P0 |
| **6-D: レポジトリダッシュボード** | レポジトリ一覧/詳細/ファイルブラウザ/グラフ概観 | P0 |
| **6-S: 検索拡張** | グラフトラバーサル検索、Cypher直接実行 | P1-P2 |
| **6-J: jj CLI連携** | Webhook/ポーリング、差分同期 | P2-P3 |

### 3. レポジトリダッシュボード詳細設計 (spec-dashboard.md)

- `/repos` レポジトリ一覧ページ（カード形式）
- `/repos/[id]` レポジトリ詳細ページ（Code/Graph/Activity/Statsタブ）
- 新規コンポーネント: RepoCard, FileBrowser, ActivityTimeline, DashboardWidgets
- 新規API: `/api/repos`, `/api/repos/[id]`, `/api/repos/[id]/tree`, `/api/repos/[id]/stats`

---

## 新規/変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `docs/spec-roadmap6.md` | **新規** | jj統合ロードマップ |
| `docs/spec-dashboard.md` | **新規** | レポジトリダッシュボード詳細設計 |
| `docs/status/status-060.md` | **新規** | 本ステータスファイル |
| `README.md` | 修正 | プロジェクト名変更、新規ドキュメントリンク追加 |

---

## アーキテクチャ決定

### データフロー

```
jj parse → .jj/storage/ → jj export --target neo4j → Neo4j → jjrv
```

### データソース戦略

- **グラフデータ**: Neo4j（jjからのエクスポートデータ、読み取り中心）
- **アプリ固有データ**: SQLite継続（ユーザー認証、お気に入り、検索履歴）
- **抽象化層**: `IEntityRepository` / `IRelationRepository` インターフェースで切替可能

### 既存機能との関係

- 検索・フィルタリング・グラフ可視化のロジックはそのまま維持
- データソースをSQLite → Neo4jに段階的に移行
- レポジトリダッシュボードは新規ページとして追加

---

## 設計上の懸念・確認事項

1. **jj側のNeo4jエクスポート形式**: jjの `jj export --target neo4j` が出力するCypherスキーマの確定が必要。現時点では想定スキーマで設計
2. **ID体系の統一**: jjは `int` ID、jjrvは `string` ID。Neo4j経由での変換ルールを決定する必要あり
3. **リアルタイム性**: jj parseの実行頻度と、jjrv側のキャッシュ戦略の検討が必要
4. **段階的実装**: まずはSQLiteベースでダッシュボードUIを実装し、Neo4j接続は並行して進めるのが現実的

---

## TODO / 次のステップ

- [ ] Phase 6-N-01: Neo4jドライバー導入（`neo4j-driver` パッケージ）
- [ ] Phase 6-N-03: データソース抽象化層 (`IEntityRepository`) の実装
- [ ] Phase 6-D-01: レポジトリ一覧ページ `/repos` の実装（まずSQLiteベース）
- [ ] Phase 6-D-03: FileBrowser コンポーネントの実装
- [ ] jj側: Neo4jエクスポートのCypherスキーマ確定
- [ ] jj側: ID体系のstring対応検討
- [ ] status-index.md の更新
