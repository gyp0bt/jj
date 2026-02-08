[READMEへ戻る](../../README.md)

# status-036: jj-db統合設計（jj × mat-db × Neo4j）

**日付**: 2026-02-08

## 概要

mat-dbをjj-dbに組み込む統合方針を策定。Neo4jを通信中間層とし、共有データ型を`shared/`パッケージで管理する設計を文書化した。

## 環境調査結果

- **mat-dbリポジトリアクセス**: 不可（`repository not authorized` / HTTP 502）
- **判定**: submodule方式は現時点では不可 → 一時的なモノレポ方式を採用
- **移行計画**: アクセス復旧後にsubmodule化

## 設計判断

### リポジトリ構成

| 選択肢 | 判定 | 理由 |
|--------|------|------|
| submodule分離（理想） | **現時点で不可** | mat-dbリポジトリにアクセスできない |
| 一時的モノレポ | **採用** | 開発効率を確保しつつ、将来の分離を前提に設計 |
| 完全統合（1リポジトリ） | 不採用 | コンテキスト肥大化の懸念 |

### アーキテクチャ

- **通信**: jj ↔ Neo4j ↔ mat-db（直接のコード依存は禁止）
- **共有型**: `shared/` パッケージ（neo4j_schema.py, types.py, config.py）
- **依存方向**: `services/` → `shared/` ← `mat_db/`（shared → services/mat_dbは禁止）

### コンテキスト肥大化対策

- ディレクトリ分離（`mat_db/` 独立）
- 独立README
- 共有層を最小化（型定義とスキーマのみ）
- テスト分離
- statusファイルで作業範囲明示

## 新規ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/specs/10-db-integration.md` | jj-db統合設計書（Neo4jスキーマ、ディレクトリ構成、実装フェーズ） |

## 実装フェーズ（DB統合）

| Phase | 内容 | 前提 |
|-------|------|------|
| N1 | 基盤構築（shared/, Neo4j Docker, スキーマ） | なし |
| N2 | jj Neo4jエクスポーター | N1 |
| N3 | mat-db Neo4jクライアント | N1, mat-dbコード入手 |
| N4 | クロスリレーション（材料マッチング、import） | N2, N3 |
| N5 | submodule移行 | mat-dbリポジトリアクセス復旧 |

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `docs/specs/10-db-integration.md` | 新規: jj-db統合設計書 |
| `docs/status/status-036.md` | 新規: 本ステータス |
| `docs/roadmap.md` | 変更: Phase N追加 |
| `docs/specs/README.md` | 変更: DB統合仕様追加 |
| `README.md` | 変更: ステータスリンク追加 |

## TODO / 次のステップ

- [ ] Phase N1: `shared/`パッケージ実装
- [ ] Phase N1: Neo4j Docker Compose構築
- [ ] Phase N2: `services/connectors/neo4j_connector.py` 実装
- [ ] Phase N2: `jj export --target neo4j` CLI追加
- [ ] mat-dbリポジトリアクセスの復旧確認
- [ ] mat-dbの既存データモデルとの詳細マッピング

## 確認事項・設計上の懸念

- mat-dbリポジトリアクセスの復旧時期が不明。復旧するまではモノレポで開発
- mat-dbの既存データモデル（Node/Edge型）の詳細が未確認。mat-dbコード入手後に具体化が必要
- Neo4j Community vs Enterprise: 初期はCommunity Editionで十分
- 材料名マッチングのアルゴリズム: 完全一致 → ファジーマッチ → LLMベースの段階的改善を想定
