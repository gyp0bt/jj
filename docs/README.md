[← README.md](../README.md)

# docs/ — ドキュメントナビゲーション

> **新規セッション開始時**: 1. 本ファイルで全体構造を把握 → 2. [status-index](status/status-index.md) で現在地とTODOを確認 → 3. 作業開始

---

## 現在地

- **バージョン**: v0.3.0 開発中
- **完了トラック**: T1(TODO解消), T2(Config分離), T3(MLダッシュボード), T4(Deprecation), T6(ダッシュボード高度化)
- **未着手トラック**: T5(リモートジョブ), T7(Ollama AI連携), T8(汎用データ管理)
- **最新status**: [status-index.md](status/status-index.md) 末尾を参照
- **アクティブTODO**: 最新statusファイルのTODOセクションに記載

---

## ドキュメント分類

### 計画（Plans）

| ドキュメント | 内容 | 備考 |
|-------------|------|------|
| [roadmap.md](roadmap.md) | v0.3.0 ワークトラック進捗・依存関係 | **最初に読むべき計画書** |
| [specs/midterm-plan-v0.3.md](specs/midterm-plan-v0.3.md) | T1-T8 詳細設計・工数見積 | roadmapの詳細版 |

### 仕様書（Specs） — 機能ドメイン定義

| # | ドメイン | ファイル |
|---|---------|---------|
| 01 | コアデータモデル | [01-core-data-model.md](specs/01-core-data-model.md) |
| 02 | パーサー | [02-parser.md](specs/02-parser.md) |
| 03 | 設定管理 | [03-config.md](specs/03-config.md) |
| 04 | runコマンド | [04-run-command.md](specs/04-run-command.md) |
| 05 | noteコマンド | [05-note-command.md](specs/05-note-command.md) |
| 06 | fileコマンド | [06-file-command.md](specs/06-file-command.md) |
| 07 | アダプター | [07-adapter.md](specs/07-adapter.md) |
| 08 | エクスポート | [08-export.md](specs/08-export.md) |
| 09 | ダッシュボード | [09-dashboard.md](specs/09-dashboard.md) |
| 10 | DB統合 | [10-db-integration.md](specs/10-db-integration.md) |
| 11 | ダッシュボード要件 | [11-dashboard-requirements.md](specs/11-dashboard-requirements.md) |

> 詳細は [specs/README.md](specs/README.md) を参照

### 設計文書（Design） — 個別機能の設計判断

| ドキュメント | 関連トラック |
|-------------|-------------|
| [multi-solver.md](specs/multi-solver.md) | M2: マルチソルバー |
| [run-centric-schema.md](specs/run-centric-schema.md) | M7: Run中心スキーマ |
| [ml-task-roadmap.md](specs/ml-task-roadmap.md) | M6: ML対応 |
| [surrogate-model-framework.md](specs/surrogate-model-framework.md) | M6: サロゲートモデル |
| [neo4j-pipeline-design.md](specs/neo4j-pipeline-design.md) | M3: Neo4j統合 |
| [parse-run-integration.md](specs/parse-run-integration.md) | M7: Parse-Run統合 |
| [run-property-traceability.md](specs/run-property-traceability.md) | M7: Runプロパティ |
| [config-classification.md](specs/config-classification.md) | T2: Config分離 |
| [vocab-display-time.md](specs/vocab-display-time.md) | M2: 表示名 |
| [results-directory-restructure.md](specs/results-directory-restructure.md) | M2: results構造 |

### ガイド（Guides） — ユーザー向けマニュアル

| ドキュメント | 対象 |
|-------------|------|
| [abaqus-usage-guide.md](abaqus-usage-guide.md) | Abaqusリポジトリ向け実践ガイド |
| [ml-usage-guide.md](ml-usage-guide.md) | 機械学習プロジェクト向けガイド |
| [migration-guide.md](migration-guide.md) | バージョン移行ガイド |
| [prefect-integration-guide.md](prefect-integration-guide.md) | Prefectワークフロー連携 |
| [README-jj.md](README-jj.md) | jjコマンドリファレンス |

### 実装ログ（Status）

| ドキュメント | 内容 |
|-------------|------|
| [status-index.md](status/status-index.md) | **v0.2.0+ statusインデックス（64件）** |
| [status-index-v0.1.0.md](status/status-index-v0.1.0.md) | v0.1.0 statusアーカイブ（151件） |

### レビュー・アーカイブ

| ドキュメント | 内容 |
|-------------|------|
| [review-v0.1.0.md](review/review-v0.1.0.md) | v0.1.0 開発フェーズ総括 |
| [roadmap-v0.1.0.md](roadmap-v0.1.0.md) | v0.1.0 ロードマップ（アーカイブ） |
| [detail.md](detail.md) | 実装方針・技術詳細（初期設計） |

---

## statusファイル運用ルール

- 粒度: 1 status ≒ 1 PR
- statusの内容はgitコミットメッセージと整合
- 未完了TODOは次のstatusに引き継ぎ
- v0.1.0のstatusは `docs/status/archive-v0.1.0/` にアーカイブ済み
