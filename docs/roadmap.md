[← README.md](../README.md)

# jj ロードマップ

---

## v0.3.0 — 統合ワークフロー・AI連携・ダッシュボード高度化

**テーマ**: 「Run中心プラットフォーム → リモートジョブ管理 → AI連携 → 汎用データ管理」

v0.2.0でCAE/MLのRun中心スキーマを確立した。v0.3.0はv0.2.0の残タスク完了と、リモートジョブ実行基盤・ダッシュボード高度化・AI連携を実現する。

> **詳細設計**: [中期計画 v0.3](specs/midterm-plan-v0.3.md) に全8ワークトラック（T1-T8）の詳細設計を記載。

### ワークトラック概要

```
v0.2.0 残タスク                         v0.3.0 新規テーマ
─────────────                         ──────────────
T1: コードベースTODO解消               T5: リモートジョブ実行基盤
T2: Config二層分離                     T6: ダッシュボード高度化
T3: M6 Phase 5 (MLダッシュボード)       T7: Ollama AI連携プラグイン
T4: Deprecation Warning修正            T8: 汎用データ管理への昇華
```

### ワークトラック依存関係

```
T1 (TODO解消) ←── T2 (Config分離)   ← 多くのTODOがconfig移動を要求
T4 (deprecation) ── T6 (Dashboard高度化)
T2 ────────────── T5 (リモートジョブ)
T3 (MLダッシュボード) ─ T8 (汎用データ管理)
                    └── T7 (Ollama AI連携)
```

### ワークトラック進捗

| トラック | 優先度 | 概要 | 工数目安 | 状態 |
|---------|--------|------|---------|------|
| **T1: コードベースTODO解消** | 高 | コード内13件のTODO実装 | 1セッション | 未着手 |
| **T2: Config二層分離** | 高 | default-config + user-configのdeep merge | 2セッション | 未着手 |
| **T3: M6 Phase 5 MLダッシュボード** | 中 | MLOverviewPage, 三層データフロー可視化 | 2セッション | 未着手 |
| **T4: Deprecation Warning修正** | 高 | streamlit/plotly API更新 | 0.5セッション | 未着手 |
| **T5: リモートジョブ実行基盤** | 高 | jj submit/watch/collect + Prefect統合 | 4-5セッション | 未着手 |
| **T6: ダッシュボード高度化** | 中-高 | parseボタン, AgGridフィルタ共有, グラフ可視化 | 4-5セッション | 未着手 |
| **T7: Ollama AI連携** | 中 | AIProviderプロトコル, 要約, RAG, tips | 5-7セッション | 未着手 |
| **T8: 汎用データ管理** | 低-中 | Run中心プラットフォームへの昇華 | 設計2セッション | 未着手 |

### 実施ロードマップ

| Phase | 期間 | 内容 |
|-------|------|------|
| **A: 基盤整理** | Week 1-2 | T4, T2 (Phase 2-1〜2-3), T1 (#3,#4), T6-1 |
| **B: ワークフロー自動化** | Week 3-6 | T5 (submit/watch/collect/job), T1残, T5-9 (Prefect) |
| **C: ダッシュボード高度化** | Week 6-8 | T6-2〜4, T3 (M6 Phase 5), T5-8 (Job Monitor) |
| **D: AI連携** | Week 9-12 | T7-1〜8, T8設計 |

---

## v0.2.0 — マルチプロジェクト横断・ML/最適化統合（完了）

**テーマ**: 「単一プロジェクト → 複数プロジェクト横断 → ML/最適化統合」

v0.1.0が「1つのCAEプロジェクトのグラフ化と可視化」を実現したのに対し、v0.2.0は「複数プロジェクトの横断検索・比較・再利用」「マルチソルバー対応」「機械学習・実験・最適化タスクのデータフローグラフ化」を目指す。

> **jjrv分離について**: jjrv（Next.js Webダッシュボード）はv0.2.0途中で別リポジトリに分離された。M3/M4のjjrv関連タスクは凍結し、jj CLIとStreamlitダッシュボードの開発に集中する。Neo4j統合はjj側のエクスポーターとして維持する。

### v0.2.0 マイルストーン依存関係

```
M1: 基盤整備 ✅
 ├──→ M1.5: ドキュメント再構成 ✅
 ├──→ M3: Neo4j統合パイプライン（jj側完了）
 └──→ M5: ワークフロー自動化 → v0.3.0 T5に発展

M2: マルチソルバー検証（検証環境確保後に実施）

M6: ML/実験/最適化タスク対応
 ├── Phase 1-4: パーサー9種 ✅
 └── Phase 5: ダッシュボード統合 → v0.3.0 T3に引き継ぎ

M7: Run中心スキーマ再設計
 └── Phase 1-6: 全完了 ✅
```

> **M2について**: Fluent/LS-DYNA/Flow-3D/OpenFOAM/CalculiX等の検証環境は常時利用可能ではないため、M1→M3の順に進める。M2は検証環境確保後にプラグインとして個別対応する。ただし、M1.5でコアモジュールの柔軟性を事前に確保しておく。

> **M6について**: 機械学習タスク（PyTorch, scikit-learn）、実験タスク、CAEタスク、およびそれらを横断する最適化タスクのデータフローをグラフ化する。既存のAbstractFileParserプラグインパターンに則り、`services/plugins/ml/`として実装する。M2（マルチソルバー）と並行して進行可能。

---

## M1: 基盤整備 — 完了

| タスク | 成果物 | status |
|--------|--------|--------|
| CI/CD構築 | `.github/workflows/ci.yml` | [001](status/status-001.md) |
| ドキュメント再編 | README.md更新 | [002](status/status-002.md) |
| statusアーカイブ | `docs/status/archive-v0.1.0/` | [001](status/status-001.md) |
| CLAUDE.md / CONTRIBUTING.md | ルート文書 | [002](status/status-002.md) |

---

## M1.5: ドキュメント再構成 — 完了

| タスク | 成果物 | 状態 |
|--------|--------|------|
| ロードマップ分離 | `docs/roadmap.md`（本ファイル） | 完了 |
| CLAUDE.md スリム化 | 技術規約に特化 | 完了 |
| README.md スリム化 | 重複排除 | 完了 |
| status-index.md 作成 | `docs/status/status-index.md` | 完了 |
| マルチソルバー仕様書 | `docs/specs/multi-solver.md` | 完了 |
| コアconfig柔軟性向上 | `SolverProfile` config拡張 | 完了 |
| default-config.yaml | solver-profiles/solver-detectionコメント付き使用例 | 完了 |
| プラグイン雛形作成 | 6ソルバー（LS-DYNA, Flow-3D, OpenFOAM, CalculiX, Fluent, HFSS） | 完了 |

### 関連仕様書
- [マルチソルバー対応仕様書](specs/multi-solver.md) — ソルバー別ファイル構造の差異分析とconfig対応設計

---

## M2: マルチソルバー検証 — 検証環境確保後

プラグイン雛形（スケルトン）はM1.5で作成済み。各ソルバーの検証環境が利用可能になった段階で、本実装とテストアセット作成を行う。

| ソルバー | 対応方式 | 主な課題 | 仕様書 |
|---------|---------|---------|--------|
| Fluent | `services/plugins/fluent/` | .cas.h5/.dat.h5バイナリ、.jouジャーナル解析 | [マルチソルバー仕様書 §Fluent](specs/multi-solver.md#fluent) |
| HFSS | `services/plugins/hfss/` | .aedtバイナリ（部分テキスト）、.aedt.batchinfoログ | [マルチソルバー仕様書 §HFSS](specs/multi-solver.md#hfss) |
| LS-DYNA | `services/plugins/lsdyna/` | .k/.key/.datインプット、フォルダ=1計算 | [マルチソルバー仕様書 §LS-DYNA](specs/multi-solver.md#ls-dyna) |
| Flow-3D | `services/plugins/flow3d/` | 出力種類.ジョブ名形式のファイル名 | [マルチソルバー仕様書 §Flow-3D](specs/multi-solver.md#flow-3d) |
| OpenFOAM | `services/plugins/openfoam/` | ディレクトリ=1計算、タイムステップディレクトリ | [マルチソルバー仕様書 §OpenFOAM](specs/multi-solver.md#openfoam) |
| CalculiX | `services/plugins/calculix/` | .inp互換だがAbaqusサブセット | [マルチソルバー仕様書 §CalculiX](specs/multi-solver.md#calculix) |

### ダッシュボードアーキテクチャ

PageComponent[ViewConfig]パターンによるプラグイン拡張基盤を整備済み。

| タスク | 成果物 | status |
|--------|--------|--------|
| PageComponent[ViewConfig]パターン導入 | 基底クラス + 6ビューコンポーネント | [012](status/status-012.md) |
| 描画ロジックのコンポーネント移動 | app.py 70%削減（1920→569行） | [013](status/status-013.md) |
| HTMLエクスポートのレジストリ統合 | generate_view_html()レジストリベース化 | [013](status/status-013.md) |
| プラグインローダー | jj.dashboard_pages エントリーポイント対応 | [013](status/status-013.md) |
| コネクターページのビュー保存対応 | render_saved_view + ConnectorViewConfig | [017](status/status-017.md) |
| フィルター階層化（グローバル+ローカル） | apply_local_filters + per-page filter chain | [017](status/status-017.md) |

### ダッシュボード横断要件

> **原則**: コネクターページを含む全てのページはビュー保存およびHTMLエクスポート機能を持つこと。フィルターロジックはグローバルフィルターに加えてオプショナルでローカルフィルターを持てること。

---

## M3: Neo4j統合パイプライン — jj側完了

| タスク | 成果物 | 仕様書 |
|--------|--------|--------|
| Neo4jスキーマ確定 | スキーマ文書 | [10-db-integration.md](specs/10-db-integration.md) |
| ID体系統一 | int→string変換ルール | [10-db-integration.md](specs/10-db-integration.md) |
| Neo4jエクスポーター | `services/export/connectors/neo4j_connector.py` | [08-export.md](specs/08-export.md) |

> ~~jjrv Neo4jクライアント・データソース切替~~: jjrv分離により凍結

---

## M5: ワークフロー自動化

| タスク | 成果物 | 仕様書 |
|--------|--------|--------|
| runコマンド ジョブ型 | `jj r --mode=job` | [04-run-command.md](specs/04-run-command.md) |
| fileコマンド基本 | テンプレート生成、リネーム | [06-file-command.md](specs/06-file-command.md) |
| リモート実行統合 | `jj r --remote` | [04-run-command.md](specs/04-run-command.md) |

---

## M6: ML/実験/最適化タスク対応 — Phase 4完了

**位置づけ**: CAEシミュレーションと連携する機械学習タスク、実験管理タスク、最適化ループのデータフローをグラフ構造化し、三層（CAE/ML/最適化）の横断可視化を実現する。

### 対象フレームワーク

| カテゴリ | フレームワーク | ファイル形式 |
|---------|--------------|-------------|
| 深層学習 | PyTorch, PyTorch Lightning | `.pt`, `.pth`, `.ckpt` |
| 古典ML | scikit-learn | `.pkl`, `.joblib` |
| 実験管理 | MLflow, TensorBoard | メトリクスログ、アーティファクト |
| 最適化 | Optuna, BoTorch | `.db`, 試行履歴 |
| データ | pandas, numpy, HDF5 | `.csv`, `.parquet`, `.h5`, `.npy` |

### 三層データフローモデル

```
Layer 3: 最適化タスク ── Objective Function → Search Space → Pareto Front
    │                         │
Layer 2: ML/実験タスク ── Dataset → Training Script → Model Checkpoint
    │                         │
Layer 1: CAEタスク ────── CAE Input → Solver → CAE Result
```

層間リレーション: `extracted_from`（CAE結果→学習データ）、`surrogate_of`（モデル→CAE入力）、`optimizes`（最適化→モデル/CAE入力）

### 実装計画

| Phase | タスク | 成果物 | 状態 |
|-------|--------|--------|------|
| 1 | 基盤設計 | 仕様書、テストアセット設計 | 完了 |
| 2 | コアパーサー | MLScriptParser, MLDatasetParser, MLConfigParser | 完了 |
| 3 | フレームワーク固有 | TorchCheckpointParser, SklearnModelParser, ExperimentRunParser | 完了 |
| 4 | サロゲートモデルフレームワーク | OptimizationRunParser, MLDataFlowParser, SurrogateWorkflowDetector | 完了 |
| 5 | ダッシュボード統合 | MLダッシュボードコネクター, 三層データフロー可視化 | 未着手 |

### 関連仕様書
- [ML対応仕様書](specs/ml-task-roadmap.md) — ドメイン分析、データモデル拡張、パーサー設計、三層データフロー
- [サロゲートモデルフレームワーク仕様書](specs/surrogate-model-framework.md) — CAE-ML-最適化ワークフロー、層間リレーション設計

---

## M7: Run中心スキーマ再設計 — Phase 6完了

**位置づけ**: M6（ML/実験/最適化タスク対応）の知見から、jjの最重要管理対象はRunであることが明確化。全てのデータ（CAEジョブ、スクリプト実行、ML学習、物理実験、parse自体）をRunとして統一的にモデル化し、Run比較を中核機能とする。

### 設計文書
- [Run中心スキーマ再設計仕様書](specs/run-centric-schema.md) — 全体設計、Nodeカテゴリ体系、Run三項関係、比較モデル

### 実装計画

| Phase | タスク | 成果物 | 状態 |
|-------|--------|--------|------|
| 1 | コアモデル拡張 | NodeCategory, Run構造的リレーション, AbstractRunDiscoverer, RunQueryService | 完了 |
| 2 | CAE Run発見 | CaeRunDiscoverer（inp→odbペアからCAE潜在Runを発見） | 完了 |
| 3 | ML Run発見 | MlTrainingRunDiscoverer（script→dataset→modelからML潜在Runを発見） | 完了 |
| 4 | RunService統合 | 実行時RunもRun Nodeとして統一記録、Parse-Run統合 | 完了 |
| 4.5 | バッチ俯瞰Run統合 | Runバッジ表示、Runサマリー、Run詳細expander | 完了 |
| 5 | Run比較ダッシュボード | RunComparisonPage: Run一覧・Run比較・比較グループ探索 | 完了 |
| 6 | Neo4j Run Node対応 | RUN_INPUT/OUTPUT/MEDIAマッピング、categoryプロパティ | 完了 |

---

## 仕様書リンク集

### v0.3.0 仕様書

| # | ドメイン | ファイル | 関連トラック |
|---|---------|---------|-------------|
| MP-01 | 中期計画 | [midterm-plan-v0.3.md](specs/midterm-plan-v0.3.md) | T1-T8 全体 |

### 仕様書（`docs/specs/`）

| # | ドメイン | ファイル | 関連マイルストーン |
|---|---------|---------|-------------------|
| 01 | コアデータモデル | [01-core-data-model.md](specs/01-core-data-model.md) | 基盤 |
| 02 | パーサー | [02-parser.md](specs/02-parser.md) | M1.5, M2 |
| 03 | 設定管理 | [03-config.md](specs/03-config.md) | M1.5, M2 |
| 04 | runコマンド | [04-run-command.md](specs/04-run-command.md) | M5 |
| 05 | noteコマンド | [05-note-command.md](specs/05-note-command.md) | — |
| 06 | fileコマンド | [06-file-command.md](specs/06-file-command.md) | M5 |
| 07 | アダプター | [07-adapter.md](specs/07-adapter.md) | M2 |
| 08 | エクスポート | [08-export.md](specs/08-export.md) | M3 |
| 09 | ダッシュボード | [09-dashboard.md](specs/09-dashboard.md) | M2 |
| 10 | DB統合 | [10-db-integration.md](specs/10-db-integration.md) | M3 |
| 11 | ダッシュボード要件 | [11-dashboard-requirements.md](specs/11-dashboard-requirements.md) | M2 |
| MS-01 | マルチソルバー対応 | [multi-solver.md](specs/multi-solver.md) | M1.5, M2 |
| MS-02 | 解析結果ディレクトリ再構成 | [results-directory-restructure.md](specs/results-directory-restructure.md) | M2 |
| MS-03 | ML/実験/最適化タスク対応 | [ml-task-roadmap.md](specs/ml-task-roadmap.md) | M6 |
| MS-04 | Run中心スキーマ再設計 | [run-centric-schema.md](specs/run-centric-schema.md) | M7 |
| MS-05 | Neo4jパイプライン設計 | [neo4j-pipeline-design.md](specs/neo4j-pipeline-design.md) | M3 |
| MS-06 | サロゲートモデルフレームワーク | [surrogate-model-framework.md](specs/surrogate-model-framework.md) | M6 |

---

## v0.1.0 アーカイブ

v0.1.0のロードマップは [docs/roadmap-v0.1.0.md](roadmap-v0.1.0.md) に保存されている（Phase 0〜P、全マイルストーン完了済み）。

レビューは [docs/review/review-v0.1.0.md](review/review-v0.1.0.md) を参照。
