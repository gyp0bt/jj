[← README.md](../README.md)

# jj ロードマップ

---

## v0.3.0 — 統合ワークフロー・AI連携・プラグインアーキテクチャ

**テーマ**: 「Run中心プラットフォーム → リモートジョブ管理 → AI連携 → プラグイン完全分離」

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
| T7: Ollama AI連携 | **Phase 7-6完了** | AIProvider・summarize・diff・RAG・Tips・ダッシュボード |
| T8: 汎用データ管理 | **Phase 8-2完了** | Run Discovery標準化・物理実験プラグイン |
| T9: 共有フォルダ同期 | **Phase 9-6完了** | SharedFolder・GitLab・CLI・API、Windows実環境テスト待ち |
| T10: プラグインコア設計 | **P-8完了** | PluginManifest・JJApp・EventBus・CapabilityRegistry・CLI/API拡張 |
| W: Office連携 | **W-5完了** | PPTX/XLSXパーサー・エクスポーター・ダッシュボード、Windows実環境テスト待ち |

### 依存関係

```
完了                                  進行中
──────────────────────────           ──────────────────────────
T1 (TODO) ← T2 (Config) ──────────→ T5 (リモートジョブ) ✓
T4 (deprecation) ← T6 (Dashboard)
T3 (MLダッシュボード) ────────────→ T7 (Ollama AI連携)
                          └───────→ T8 (汎用データ管理)
                                     T9 (共有フォルダ同期)
                                     T10 (プラグインコア設計)
```

### 残タスク詳細

#### T7: Ollama AI連携（フル統合テスト・マニュアル作成待ち）

- Phase 7-1〜7-6実装完了（AIProvider・summarize・diff・RAG・Tips・ダッシュボード）
- 残: フル統合テスト・マニュアル作成

#### T8: 汎用データ管理（設計フェーズ以降の実装）

- Phase 8-1〜8-2完了（Run Discovery標準化・物理実験プラグイン）
- 残: 設計フェーズ以降の実装

#### T9: 共有フォルダ同期（Windows実環境テスト待ち）

- Phase 9-1〜9-6完了（SharedFolder・GitLab連携・CLI・API）
- 残: Windows実環境テスト

#### T10: プラグインコア設計（CLI/API統合で段階的移行予定）

- P-1〜P-8実装完了
- 残: 既存CLI統合、Abaqus CLICommand実装、FastAPI APIアダプター、get_page_data()各サブクラス実装

### 実施ロードマップ

| Phase | 内容 | 状態 |
|-------|------|------|
| **A: 基盤整備** | T1, T2, T4 | 完了 |
| **B: ワークフロー自動化** | T5 (submit/watch/collect/Prefect) | 完了 |
| **C: ダッシュボード高度化** | T3, T6 | 完了 |
| **D: AI連携・拡張** | T7, T8, T9, T10, W | 進行中 |

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
| [midterm-plan-v0.3.md](specs/midterm-plan-v0.3.md) | T1-T10全体設計 |
| [plugin-core-design.md](specs/plugin-core-design.md) | T10 プラグインコア設計 |
| [sync-shared-folder.md](specs/sync-shared-folder.md) | T9 共有フォルダ同期 |
| [multi-solver.md](specs/multi-solver.md) | M2 マルチソルバー |
| [ml-task-roadmap.md](specs/ml-task-roadmap.md) | M6 ML対応 |
| [run-centric-schema.md](specs/run-centric-schema.md) | M7 Run中心スキーマ |
| [neo4j-pipeline-design.md](specs/neo4j-pipeline-design.md) | M3 Neo4j統合 |

---

## アーカイブ

- [v0.1.0 ロードマップ](archive/roadmap-v0.1.0.md) — Phase 0〜P 全完了
- [v0.1.0 レビュー](archive/review/review-v0.1.0.md) — 3週間の開発総括
