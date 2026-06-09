[← README.md](../README.md)

# docs/ — ドキュメントナビゲーション

> **新規セッション開始時**: 本ファイルで全体構造を把握 → roadmap.md で現在地を確認 → 作業開始

---

## 現在地

- **バージョン**: v0.3.0 開発中
- **完了トラック**: T1(TODO解消), T2(Config分離), T3(MLダッシュボード), T4(Deprecation), T5(リモートジョブ), T6(ダッシュボード高度化)
- **進行中トラック**: T7(Ollama AI連携), T8(汎用データ管理), T9(共有フォルダ同期), T10(プラグインコア設計)
- **計画**: [roadmap.md](roadmap.md) を参照

---

## ドキュメント分類

### 計画（Plans）

| ドキュメント | 内容 | 備考 |
|-------------|------|------|
| [roadmap.md](roadmap.md) | v0.3.0 ワークトラック進捗・依存関係 | **最初に読むべき計画書** |
| [specs/midterm-plan-v0.3.md](specs/midterm-plan-v0.3.md) | T1-T10 詳細設計・工数見積 | roadmapの詳細版 |

### 仕様書（Specs） — 機能ドメイン定義

| # | ドメイン | ファイル |
|---|---------|---------|
| 01 | コアデータモデル | [01-core-data-model.md](specs/01-core-data-model.md) |
| 02 | パーサー | [02-parser.md](specs/02-parser.md) |
| 03 | 設定管理 | [03-config.md](specs/03-config.md) |
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
| [ml-task-roadmap.md](specs/ml-task-roadmap.md) | M6: ML対応 |
| [surrogate-model-framework.md](specs/surrogate-model-framework.md) | M6: サロゲートモデル |
| [neo4j-pipeline-design.md](specs/neo4j-pipeline-design.md) | M3: Neo4j統合 |
| [config-classification.md](specs/config-classification.md) | T2: Config分離 |
| [vocab-display-time.md](specs/vocab-display-time.md) | M2: 表示名 |
| [results-directory-restructure.md](specs/results-directory-restructure.md) | M2: results構造 |
| [sync-shared-folder.md](specs/sync-shared-folder.md) | T9: 共有フォルダ同期 |
| [windows-integration.md](specs/windows-integration.md) | W: Office連携 |
| [t8-generic-data-management.md](specs/t8-generic-data-management.md) | T8: 汎用データ管理 |
| [dashboard-improvements.md](specs/dashboard-improvements.md) | T6: ダッシュボード改善 |
| [property-externalization.md](specs/property-externalization.md) | プロパティ外部化 |
| [property-key-normalization.md](specs/property-key-normalization.md) | K: キー正規化 |

### ガイド（Guides） — ユーザー向けマニュアル

> 詳細は [guides/README.md](guides/README.md) を参照

| ドキュメント | 対象 |
|-------------|------|
| [README-jj.md](guides/README-jj.md) | jjコマンドリファレンス |
| [abaqus-usage-guide.md](guides/abaqus-usage-guide.md) | Abaqusリポジトリ向け実践ガイド |
| [ml-usage-guide.md](guides/ml-usage-guide.md) | 機械学習プロジェクト向けガイド |
| [migration-guide.md](guides/migration-guide.md) | バージョン移行ガイド |
| [prefect-integration-guide.md](guides/prefect-integration-guide.md) | Prefectワークフロー連携 |

### アーカイブ

| ドキュメント | 内容 |
|-------------|------|
| [archive/review/review-v0.1.0.md](archive/review/review-v0.1.0.md) | v0.1.0 開発フェーズ総括 |
| [archive/roadmap-v0.1.0.md](archive/roadmap-v0.1.0.md) | v0.1.0 ロードマップ |
| [archive/detail.md](archive/detail.md) | 実装方針・技術詳細（初期設計） |

---

## ディレクトリ構成

```
docs/
├── README.md                  # 本ファイル（ナビゲーション）
├── roadmap.md                 # v0.3.0 ロードマップ（最新計画書）
├── guides/                    # ユーザー向けガイド・マニュアル
│   ├── README.md
│   ├── README-jj.md           # jjコマンドリファレンス
│   ├── abaqus-usage-guide.md
│   ├── ml-usage-guide.md
│   ├── migration-guide.md
│   └── prefect-integration-guide.md
├── specs/                     # 仕様書・設計文書
│   ├── README.md
│   ├── 01〜11-*.md            # ドメイン仕様書
│   ├── midterm-plan-v0.3.md   # 中期計画
│   └── *.md                   # 個別設計文書
└── archive/                   # 旧バージョン文書
    ├── detail.md              # 初期実装方針
    ├── roadmap-v0.1.0.md      # v0.1.0 ロードマップ
    └── review/
        └── review-v0.1.0.md   # v0.1.0 レビュー
```
