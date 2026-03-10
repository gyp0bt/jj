[← README.md](../README.md)

# jj ロードマップ

---

## v0.3.0 — 統合ワークフロー・AI連携・ダッシュボード高度化

**テーマ**: 「Run中心プラットフォーム → リモートジョブ管理 → AI連携 → 汎用データ管理」

> **詳細設計**: [中期計画 v0.3](specs/midterm-plan-v0.3.md)

### ワークトラック進捗

| トラック | 状態 | 概要 |
|---------|------|------|
| T1: コードベースTODO解消 | **完了** | #1〜#6,#13完了 |
| T2: Config二層分離 | **完了** | default/user config deep merge・migrate |
| T3: MLダッシュボード | **完了** | MLOverview・MLDataFlow・比較プロット・ビュー保存 |
| T4: Deprecation Warning修正 | **完了** | 全APIモダン版確認済み |
| T5: リモートジョブ実行基盤 | **完了** | Phase 5-1〜5-9完了（Prefect統合含む） |
| T6: ダッシュボード高度化 | **完了** | parseボタン・AgGrid・グラフ可視化・Run DAG |
| T7: Ollama AI連携 | **進行中** | Phase 7-1〜7-3完了（AIProvider・summarize・diff） |
| T8: 汎用データ管理 | **未着手** | Run中心プラットフォームへの昇華 |

### 依存関係

```
完了                                  未着手
──────────────────────────           ──────────────────────────
T1 (TODO) ← T2 (Config) ──────────→ T5 (リモートジョブ)
T4 (deprecation) ← T6 (Dashboard)
T3 (MLダッシュボード) ────────────→ T7 (Ollama AI連携)
                          └───────→ T8 (汎用データ管理)
```

### 未着手トラック詳細

#### T5: リモートジョブ実行基盤（高優先度・4-5セッション）

- `jj submit`: ローカル→リモートへのジョブ送信（SSH + フォルダマッピング）
- `jj watch`: リモートジョブの進捗監視（staファイルモニタリング）
- `jj collect`: 完了ジョブの結果回収
- Prefect統合: ワークフローオーケストレーション
- 前提: T2完了済み（config基盤）

#### T7: Ollama AI連携（中優先度・5-7セッション）

- AIProviderプロトコル（Ollama/OpenAI互換）
- プロジェクト要約生成（parse結果→自然言語）
- RAG: グラフデータに基づく質疑応答
- Tips: 設定最適化の提案

#### T8: 汎用データ管理（低-中優先度・設計2セッション）

- CAEに限定しない汎用Run管理プラットフォームへの昇華
- 設計フェーズから開始

### 実施ロードマップ

| Phase | 内容 |
|-------|------|
| **B: ワークフロー自動化** | T5 (submit/watch/collect/Prefect) |
| **D: AI連携** | T7 (Ollama), T8 (設計) |

---

## v0.2.0 マイルストーン（完了サマリー）

| マイルストーン | 状態 | 主な成果物 |
|---------------|------|-----------|
| M1: 基盤整備 | 完了 | CI/CD, docs構成, CLAUDE.md |
| M1.5: ドキュメント再構成 | 完了 | roadmap分離, プラグイン雛形6種 |
| M2: マルチソルバー基盤 | 検証待ち | SolverProfile, PageComponent, プラグインローダー |
| M3: Neo4j統合 | jj側完了 | Neo4jエクスポーター, IEntityRepository |
| M4: 横断ダッシュボード | 凍結 | jjrv分離により凍結 |
| M5: ワークフロー自動化 | →T5 | v0.3.0 T5に発展 |
| M6: ML/最適化タスク | Phase5完了 | パーサー9種, ダッシュボード2ページ, ML使用マニュアル |
| M7: Run中心スキーマ | Phase6完了 | RunDiscoverer, RunService, Run比較, Neo4j対応 |

> 各マイルストーンの詳細タスク一覧は [status-index.md](status/status-index.md) の個別statusファイルを参照

### 関連仕様書

| 仕様書 | 対象 |
|--------|------|
| [midterm-plan-v0.3.md](specs/midterm-plan-v0.3.md) | T1-T8全体設計 |
| [multi-solver.md](specs/multi-solver.md) | M2 マルチソルバー |
| [ml-task-roadmap.md](specs/ml-task-roadmap.md) | M6 ML対応 |
| [run-centric-schema.md](specs/run-centric-schema.md) | M7 Run中心スキーマ |
| [neo4j-pipeline-design.md](specs/neo4j-pipeline-design.md) | M3 Neo4j統合 |

---

## アーカイブ

- [v0.1.0 ロードマップ](roadmap-v0.1.0.md) — Phase 0〜P 全完了
- [v0.1.0 レビュー](review/review-v0.1.0.md) — 3週間の開発総括
