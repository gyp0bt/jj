[← README.md](../../README.md)

# status-index — v0.2.0 実装状況インデックス

v0.2.0以降のstatusファイルの索引。各statusは1PR程度の粒度で記録する。

---

## v0.2.0 マイルストーン進捗

| マイルストーン | 状態 | 概要 |
|---------------|------|------|
| **M1: 基盤整備** | 完了 | CI/CD構築、ドキュメント再編、statusアーカイブ、CLAUDE.md/CONTRIBUTING.md |
| **M1.5: ドキュメント再構成** | 完了 | roadmap分離、CLAUDE.md/README.mdスリム化、マルチソルバー仕様書、プラグイン雛形 |
| **M2: マルチソルバー基盤** | 進行中 | プラグイン雛形作成済み、本実装は検証環境確保後に実施 |
| **M3: Neo4j統合パイプライン** | 未着手 | jj→Neo4j→jjrv パイプライン実稼働 |
| **M4: jjrv横断ダッシュボード** | 未着手 | Streamlit検証パターンのjjrv移植、横断視認性 |
| **M5: ワークフロー自動化** | 未着手 | runジョブ型、fileコマンド基本 |

---

## statusファイル一覧

| # | 日付 | マイルストーン | 概要 | ブランチ |
|---|------|---------------|------|---------|
| [001](status-001.md) | 2026-02-14 | M1 | CI/CD構築、statusアーカイブ、共有docs構成確立 | claude/setup-project-docs |
| [002](status-002.md) | 2026-02-14 | M1 | CLAUDE.md作成、Getting Started、CONTRIBUTING.md、旧status削除 | claude/setup-project-docs |
| [003](status-003.md) | 2026-02-14 | M1.5 | ドキュメント再構成: roadmap分離、CLAUDE.md/README.mdスリム化、マルチソルバー仕様書 | claude/docs-reorganization-BRtfN |
| [004](status-004.md) | 2026-02-15 | M1.5/M2 | M1.5完了: プラグイン雛形6ソルバー作成、HFSS/Fluent追加、default-config更新 | claude/add-hfss-fluent-plugins-w2HvU |
| [005](status-005.md) | 2026-02-15 | M2 | SolverProfileConfigテスト34件追加、パーサー5種のソルバープロファイル拡張子マージ対応 | claude/execute-status-todos-DSXAo |
| [006](status-006.md) | 2026-02-16 | M2 | ダッシュボード表示改善: 配列プロット全条件比較モード、ギャラリーデフォルトグループ表示 | claude/fix-dashboard-display-CcLtb |
| [007](status-007.md) | 2026-02-16 | M2 | ダッシュボード表示名改善: verbose-name-format、vocab表示名、pymesh依存グループ | claude/setup-coding-standards-YyPx7 |
| [008](status-008.md) | 2026-02-16 | M2 | results/サブディレクトリのメタデータ抽出パーサー、go_inpへの結果キー割り当て | claude/extract-results-metadata-ILTKn |
| [009](status-009.md) | 2026-02-17 | M2 | ダッシュボード改善: ライトテーマ・ビュー永続化・results除外ロジック | claude/dashboard-views-light-theme-3Dimf |
| [010](status-010.md) | 2026-02-17 | M2 | ダッシュボード改善: verbose_name展開・グループ結線修正・プロット変数制御・グローバルカラム設定 | claude/fix-verbose-names-plot-LM8Nf |
| [011](status-011.md) | 2026-02-17 | M2 | 表示名parse時移動・プロットスタイル制御・ギャラリーresult_keyグルーピング | claude/setup-project-docs-GNDw6 |
| [012](status-012.md) | 2026-02-17 | M2 | PageComponent[ViewConfig]パターン導入・グリッドビュー廃止・ギャラリーキーフィルタ | claude/fix-iteration-logic-REVGc |
| [013](status-013.md) | 2026-02-17 | M2 | PageComponent描画ロジック移動・HTMLエクスポート統合・プラグインローダー | claude/execute-status-todos-GIwd1 |
| [014](status-014.md) | 2026-02-17 | M2 | バグ修正4件: verbose_name・浮動小数点表記・動的ビュー入力・メッシュ継承 | claude/execute-status-todos-CISAk |

---

## 過去バージョン

- [v0.1.0 statusインデックス](status-index-v0.1.0.md) — 151件（jj: 90件、jjrv: 61件）
