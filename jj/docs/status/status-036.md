[READMEへ戻る](../../README.md)

# status-036: jjrv統合設計（jj × jjrv × Neo4j）

**日付**: 2026-02-08

## 概要

jjrv（旧mat-db）をNeo4j経由で統合する方針を策定。共有データ型を`shared/`パッケージで管理する設計を文書化した。

## 環境調査結果

| 確認項目 | 結果 |
|---------|------|
| jjrvリポジトリ閲覧（WebFetch） | 可能 |
| jjrvリポジトリのgit clone/push | **不可**（Gitプロキシがjjリポジトリのみ認可） |
| submodule追加 | **不可**（clone不可のため） |

### jjrv技術スタック（WebFetch経由で確認）

| 項目 | 値 |
|------|------|
| フレームワーク | Next.js 15 / React 19 / TypeScript |
| 現行DB | **SQLite (sql.js)** |
| スタイル | Tailwind CSS v4 |
| パッケージ管理 | pnpm |
| コンポーネント | Storybook |
| リンター | Biome |

**重要**: jjrvは現在SQLiteを使用しており、Neo4j統合では**SQLite + Neo4j併用**を推奨。

## 設計判断

### リポジトリ構成

| 選択肢 | 判定 | 理由 |
|--------|------|------|
| submodule分離（理想） | **現時点で不可** | Gitプロキシがjjrvを認可していない |
| 一時的モノレポ | **採用** | 開発効率を確保しつつ、将来の分離を前提に設計 |
| 完全統合（1リポジトリ） | 不採用 | コンテキスト肥大化の懸念 |

### アーキテクチャ

- **通信**: jj ↔ Neo4j ↔ jjrv（直接のコード依存は禁止）
- **共有型**: `shared/` パッケージ（neo4j_schema.py, types.py, config.py）
- **依存方向**: `services/` → `shared/` ← `jjrv/`（shared → services/jjrvは禁止）
- **jjrv側DB**: SQLite維持 + Neo4j追加（併用方式）

### コンテキスト肥大化対策

- ディレクトリ分離（`jjrv/` 独立）
- 独立README
- 共有層を最小化（型定義とスキーマのみ）
- テスト分離
- statusファイルで作業範囲明示

## 新規ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/specs/10-db-integration.md` | jjrv統合設計書（Neo4jスキーマ、ディレクトリ構成、実装フェーズ） |

## 実装フェーズ（DB統合）

| Phase | 内容 | 前提 |
|-------|------|------|
| N1 | 基盤構築（shared/, Neo4j Docker, スキーマ） | なし |
| N2 | jj Neo4jエクスポーター | N1 |
| N3 | jjrv Neo4jクライアント（TypeScript） | N1, jjrvコード入手 |
| N4 | クロスリレーション（材料マッチング、import） | N2, N3 |
| N5 | submodule移行 | jjrvリポジトリへのGitアクセス復旧 |

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `docs/specs/10-db-integration.md` | 新規→更新: jjrv統合設計書（mat-db→jjrvリネーム、技術スタック反映） |
| `docs/status/status-036.md` | 新規→更新: 本ステータス |
| `docs/roadmap.md` | 変更: Phase N追加 |
| `docs/specs/README.md` | 変更: DB統合仕様追加 |
| `README.md` | 変更: ステータスリンク追加 |

## TODO / 次のステップ

- [ ] Phase N1: `shared/`パッケージ実装
- [ ] Phase N1: Neo4j Docker Compose構築
- [ ] Phase N2: `services/connectors/neo4j_connector.py` 実装
- [ ] Phase N2: `jj export --target neo4j` CLI追加
- [ ] jjrvリポジトリへのGitアクセス復旧確認（プロキシ認可問題）
- [ ] jjrvの既存データモデルとの詳細マッピング（SQLite側のスキーマ確認）

## 確認事項・設計上の懸念

- Gitプロキシの認可問題: この環境ではjjリポジトリのみがプロキシ認可されており、jjrvへのclone/pushは不可。パブリック化後も状況変わらず。ユーザー側でプロキシ設定の変更、またはjjrvのコードを手動で`jjrv/`にコピーする必要がある可能性あり
- jjrvの現行DB（SQLite）とNeo4jの併用: 移行ではなく併用を推奨。SQLiteで既存機能維持、Neo4jはjjとの通信専用
- jjrv側のNeo4jクライアントはTypeScript（neo4j-driver npm package）で実装が必要
- Neo4j Community vs Enterprise: 初期はCommunity Editionで十分
- 材料名マッチングのアルゴリズム: 完全一致 → ファジーマッチ → LLMベースの段階的改善を想定
