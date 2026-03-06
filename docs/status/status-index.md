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
| **M3: Neo4j統合パイプライン** | 進行中 | jj側完了、jjrv IEntityRepository抽象化完了、接続設定UI・検索アダプター完了 |
| **M4: 横断ダッシュボード** | 凍結 | jjrv分離により凍結。Streamlitダッシュボードで対応 |
| **M5: ワークフロー自動化** | 未着手 | runジョブ型、fileコマンド基本 |
| **M6: ML/実験/最適化タスク対応** | 進行中 | パーサー9種実装済み（Phase 2-4完了）、サロゲートモデルフレームワーク構築、三層リレーション構築 |
| **M7: Run中心スキーマ再設計** | 進行中 | Phase 1-4.5完了: コアモデル・RunDiscoverer群・RunService統合・Parse-Run統合 |

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
| [015](status-015.md) | 2026-02-17 | M2 | メッシュ品質ダッシュボードを独立ページに分離 | claude/separate-mesh-quality-dashboard-lXtf4 |
| [016](status-016.md) | 2026-02-17 | M2 | status-015 TODO実行: メッシュ品質修正・コネクターHTML統合・E2Eテスト・プラグイン実例 | claude/execute-status-todos-L25fw |
| [017](status-017.md) | 2026-02-17 | M2 | ビュー保存/HTMLエクスポート横断対応・フィルター階層化 | claude/view-save-html-export-zhqFA |
| [018](status-018.md) | 2026-02-17 | M2 | status-017 TODO実行: 設計仕様書・コネクター保存ビュー・ローカルフィルタ拡張・テスト拡充・CI統合 | claude/execute-status-todos-S8s5u |
| [019](status-019.md) | 2026-02-18 | M2/M3 | status-018 TODO実行: 新構造パーサー・connector_config UI・CI統合・プラグイン検証・Neo4j設計 | claude/execute-status-todos-UcI3G |
| [020](status-020.md) | 2026-02-18 | M2/M3 | M3前pymeshリファクタリング: tags削除・element_quality・トポロジー・include廃止・diff形式 | claude/setup-project-docs-PPYi8 |
| [021](status-021.md) | 2026-02-18 | M2/M3 | status-020 TODO実行: Neo4jスキーマ反映・接頭辞キー表示対応・diff_unifiedエクスポート | claude/execute-status-todos-aP2p4 |
| [022](status-022.md) | 2026-02-18 | M3 | Neo4j Docker環境構築・IEntityRepository抽象化・SQLite/Neo4j両対応 | claude/setup-neo4j-docker-fDy9r |
| [023](status-023.md) | 2026-02-18 | M3 | 接続設定UI・Neo4j検索アダプター・統合テスト・表示名改善 | claude/execute-status-todos-AZ5Am |
| [024](status-024.md) | 2026-02-18 | M6 | ML/実験/最適化タスク対応ロードマップ策定・三層データフロー設計 | claude/ml-task-roadmap-uwhPT |
| [025](status-025.md) | 2026-02-18 | M6 | MLプラグイン Phase 2: コアパーサー3種実装・テストアセット・テスト28件 | claude/execute-status-todos-cMpnf |
| [026](status-026.md) | 2026-02-18 | M6 | MLプラグイン Phase 3: パーサー3種追加（checkpoint/model/experiment）・テスト24件 | claude/execute-status-todos-pdDTh |
| [027](status-027.md) | 2026-02-18 | M6 | サロゲートモデルフレームワーク Phase 4: パーサー3種（最適化/データフロー/層間検出）・テスト37件 | claude/surrogate-model-framework-NSm1k |
| [028](status-028.md) | 2026-02-19 | M6 | Phase 4.5: バグ修正・パスマッチング改善・CAE+ML混在E2Eテスト拡充 | claude/surrogate-model-framework-NSm1k |
| [029](status-029.md) | 2026-02-19 | M7 | Run中心スキーマ再設計 Phase 1: コアモデル拡張・仕様書策定・テスト35件 | claude/run-centric-schema-redesign-KanLN |
| [030](status-030.md) | 2026-02-19 | M7 | Run中心スキーマ Phase 2-3: CaeRunDiscoverer・MlTrainingRunDiscoverer・テスト29件 | claude/execute-status-todos-ltUCT |
| [031](status-031.md) | 2026-02-19 | M2 | パフォーマンス最適化: ProjectGraphインデックス・IgnoreConfigプリコンパイル・CSVサマリーモード | claude/optimize-file-parsing-hhX9f |
| [032](status-032.md) | 2026-02-19 | M2 | メッシュ統計キャッシュ: コンテンツハッシュによるファイル間共有 | claude/optimize-file-parsing-hhX9f |
| [033](status-033.md) | 2026-02-19 | M2 | パフォーマンス最適化Phase2: UTF-8ファースト・段階的INP解析・パーサー並列化・統計量UI | claude/execute-status-todos-IRWbE |
| [034](status-034.md) | 2026-02-19 | M2 | パフォーマンス最適化Phase3: 並列プリフェッチ・lightweight対応・plotly統合 | claude/execute-status-todos-pK7Ih |
| [035](status-035.md) | 2026-02-19 | M2 | status-034 TODO実行: lightweight最適化・ワーカーチューニング・plotlyテーマ・ホバー表示 | claude/execute-status-todos-7XXco |
| [036](status-036.md) | 2026-02-19 | M2 | status-035 TODO実行: ProcessPool並列化・plotlyダークモード・diff分離 | claude/execute-status-todos-11ExX |
| [037](status-037.md) | 2026-02-20 | M2 | status-036 TODO実行: plotlyテーマ横断適用・ProcessPool検証・メッシュフィルタ | claude/execute-status-todos-11ExX |
| [038](status-038.md) | 2026-02-20 | M2 | status-037 TODO実行: ダークモード視認性テスト・ベンチマーク・キーワード拡充 | claude/execute-status-todos-BqohF |
| [039](status-039.md) | 2026-02-20 | M2 | HTMLエクスポート: plotスタイル反映・ギャラリー実装 | claude/fix-plot-export-RH76n |
| [040](status-040.md) | 2026-02-21 | M2 | status-039 TODO実行: スタイル永続化・コンタープロット・ギャラリーサイズ上限 | claude/execute-status-todos-Mlumt |
| [041](status-041.md) | 2026-02-21 | M2 | status-040 TODO実行: 等高線モード・サムネイル生成・ビュー編集フォーム | claude/execute-status-todos-2TD9t |
| [042](status-042.md) | 2026-02-24 | M1 | プロジェクトデータディレクトリ .jj → .j2 リネーム | claude/rename-jj-to-j2-QV2ym |
| [043](status-043.md) | 2026-03-04 | M1/M7 | フォルダフラット化・jjrv分離反映・M7 Phase 4 RunService統合 | claude/update-docs-jjrv-separation-KiW6d |
| [044](status-044.md) | 2026-03-04 | M1 | テスト全件通過: パス修正・ResultParser復元・importorskip追加（159→0件） | claude/execute-status-todos-lfDl8 |
| [045](status-045.md) | 2026-03-04 | M7 | Parse-Run統合: jj run後にparse自動実行・--no-parseオプション・pymeshテスト修正 | claude/integrate-parse-run-sujin |
| [046](status-046.md) | 2026-03-06 | M7/M2 | Run-Propertyトレーサビリティ・Vocab表示時適用・Config classification仕様 | claude/track-feature-implementation-UCgLX |
| [047](status-047.md) | 2026-03-06 | M4 | 配列プロット クロスグループ軸選択・configデフォルト設定 | claude/dashboard-configurable-axes-FLuI3 |
| [048](status-048.md) | 2026-03-06 | M2 | Config classification実装・vocab_display UI統合 | claude/execute-status-todos-oFw3W |
| [049](status-049.md) | 2026-03-06 | M7 | Activeフィルタ全ページ適用・バッチ俯瞰ページ追加 | claude/batch-run-visualization-iOJAa |

---

## 過去バージョン

- [v0.1.0 statusインデックス](status-index-v0.1.0.md) — 151件（jj: 90件、jjrv: 61件・分離済み）
