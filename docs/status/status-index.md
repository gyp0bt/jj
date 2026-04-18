[← README.md](../../README.md)

# status-index — 実装状況インデックス

---

## アクティブTODO

> 最新statusファイルから引き継がれた未完了TODO。作業開始時はここを確認する。

### ワークトラック（進行中）

- [x] **T5**: リモートジョブ実行基盤 — Phase 5-1〜5-9完了（Prefect統合含む）
- [ ] **T7**: Ollama AI連携 — Phase 7-1〜7-6完了（AIProvider・summarize・diff・RAG・Tips・ダッシュボード）
- [ ] **T8**: 汎用データ管理 — Phase 8-1〜8-2完了（Run Discovery標準化・物理実験プラグイン）
- [ ] **T9**: 共有フォルダ同期 — Phase 9-1〜9-6完了（SharedFolder・GitLab・CLI・API）、Windows実環境テスト待ち
- [ ] **W**: Office連携 — W-1〜W-5実装完了（パーサー・エクスポーター・ダッシュボード）、Windows実環境テスト待ち
- [ ] **T10**: プラグインコア設計 — P-1〜P-8実装完了（PluginManifest・JJApp・マニフェスト対応・EventBus・CapabilityRegistry・CLICommand・APIRoute・get_page_data）、CLI/API統合で段階的移行予定

### プロパティキー正規化

- [x] K-1: `get_file_base_name()` 関数 + テスト
- [x] K-2: MeshInheritParserプレフィックス正規化
- [x] K-3: 既存テスト更新
- [ ] K-4: （オプション）config property-key-aliases

### ダッシュボード改善

- [x] D-1: AgGridフィルタ強化（saved_viewでもAgGrid使用）
- [x] D-2: テーブル/ギャラリーロジック関数抽出
- [x] D-3: OverviewPage実装
- [x] D-4: デフォルト保存ボタン + config書き戻し
- [x] D-5: default-page config対応
- [x] D-6: シングルページ化（enabled-pages config制御）
- [x] D-7: ビュー保存/表示機能の統一化（SavedViewConfig駆動・config.yaml一本化）

### T3 改善候補

- [ ] モデルレジストリ詳細ページ（チェックポイント選択・比較UI）
- [ ] Optuna試行詳細表示（パラメータ重要度、パレートフロント）
- [ ] TensorBoard/MLflow連携パーサー

### M2: マルチソルバー検証（検証環境確保後）

- [ ] Fluent/LS-DYNA/Flow-3D/OpenFOAM/CalculiX プラグイン本実装

---

## ワークトラック進捗

| トラック | 状態 | 完了status |
|---------|------|-----------|
| T1: コードベースTODO解消 | **完了** | [053](status-053.md)-[057](status-057.md) |
| T2: Config二層分離 | **完了** | [054](status-054.md)-[055](status-055.md) |
| T3: MLダッシュボード Phase 5 | **完了** | [062](status-062.md)-[063](status-063.md) |
| T4: Deprecation Warning修正 | **完了** | [053](status-053.md) |
| T5: リモートジョブ実行基盤 | **完了** | [065](status-065.md)-[068](status-068.md) |
| T6: ダッシュボード高度化 | **完了** | [053](status-053.md)-[061](status-061.md) |
| T7: Ollama AI連携 | **進行中** | [069](status-069.md)〜[071](status-071.md) |
| T8: 汎用データ管理 | **進行中** | [071](status-071.md) |
| T9: 共有フォルダ同期 | **進行中** | [076](status-076.md) |
| T10: プラグインコア設計 | **実装中** | [079](status-079.md)〜[082](status-082.md) |

---

## v0.2.0 マイルストーン進捗

| マイルストーン | 状態 | 概要 |
|---------------|------|------|
| M1: 基盤整備 | 完了 | CI/CD, docs, CLAUDE.md |
| M1.5: ドキュメント再構成 | 完了 | roadmap分離, プラグイン雛形 |
| M2: マルチソルバー基盤 | 検証待ち | 雛形作成済み、検証環境確保後に本実装 |
| M3: Neo4j統合 | jj側完了 | エクスポーター完了 |
| M4: 横断ダッシュボード | 凍結 | jjrv分離により凍結 |
| M5: ワークフロー自動化 | →T5 | v0.3.0 T5に発展 |
| M6: ML/最適化タスク | Phase5完了 | パーサー9種+ダッシュボード |
| M7: Run中心スキーマ | Phase6完了 | RunDiscoverer+RunService+比較+Neo4j |

---

## statusファイル一覧

### v0.3.0 (status-053〜)

| # | 日付 | 概要 | ブランチ |
|---|------|------|---------|
| [085](status-085.md) | 04-18 | ビュー保存/表示機能の統一化（SavedViewConfig駆動・config.yaml一本化） | claude/dashboard-single-page-YMTol |
| [084](status-084.md) | 04-18 | ダッシュボードのシングルページ化（enabled-pages config制御） | claude/dashboard-single-page-YMTol |
| [083](status-083.md) | 03-14 | docsリファクタリング（ディレクトリ構造整理） | claude/refactor-docs-organization-jNIVP |
| [082](status-082.md) | 03-14 | T10 P-6/P-7/P-8 CLI拡張・API拡張・JJApp統合 | claude/execute-status-todos-9OcUU |
| [081](status-081.md) | 03-14 | T10 P-3/P-4/P-5 マニフェスト対応・EventBus・CapabilityRegistry | claude/execute-status-todos-9VMW5 |
| [080](status-080.md) | 03-14 | T10 P-1/P-2 PluginManifest・JJApp実装 | claude/execute-status-todos-YZtpS |
| [079](status-079.md) | 03-14 | T10 プラグインコア設計仕様書策定 | claude/plugin-core-design-NZnTr |
| [078](status-078.md) | 03-14 | PPTX/XLSX連携プラグイン実装（W-1〜W-5） | claude/pptx-xlsx-integration-PQbpD |
| [077](status-077.md) | 03-13 | テストアセット追加・UI検証フロー整備（Abaqus） | claude/test-assets-ui-verification-jPGVa |
| [076](status-076.md) | 03-13 | T9 Windows共有フォルダ同期 + GitLab連携 | claude/windows-folder-sync-SOkr8 |
| [075](status-075.md) | 03-13 | プロパティキー正規化(K-1〜K-3)・ダッシュボード改善(D-1〜D-5) | claude/execute-status-todos-W5eUH |
| [074](status-074.md) | 03-11 | composite_target_keys外部化・resolve_externalized伝搬 | claude/execute-status-todos-7YJMZ |
| [073](status-073.md) | 03-11 | Streamlit非推奨API修正・ギャラリー改善（idx整数ソート） | claude/setup-project-docs-KtzaJ |
| [072](status-072.md) | 03-10 | プロパティ外部化（graph.yaml軽量化） | claude/refactor-graph-data-storage-Wsmdj |
| [071](status-071.md) | 03-10 | T7-6 AIアシスタントパネル / T8 汎用データ管理基盤 | claude/execute-status-todos-2xvZf |
| [070](status-070.md) | 03-10 | T7-4/7-5 RAG検索・Tips抽出 | claude/execute-status-todos-eL76K |
| [069](status-069.md) | 03-10 | T7-1/7-2/7-3 AI連携基盤（AIProvider・summarize・diff） | claude/execute-status-todos-O8t4T |
| [068](status-068.md) | 03-10 | T5-9 Prefect統合・ダッシュボード改善・単位トークン | claude/integrate-prefect-muffj |
| [065](status-065.md) | 03-09 | T5基盤: JobState/Storage/FolderMapping/CLI | claude/execute-status-todos-l1Idi |
| [064](status-064.md) | 03-09 | ドキュメント構造整理（コンテキスト肥大化対策） | claude/execute-status-todos-6wBmM |
| [063](status-063.md) | 03-09 | T3改善: メトリクス比較プロット・ビュー保存連携 | claude/execute-status-todos-6wBmM |
| [062](status-062.md) | 03-09 | T3完了: MLダッシュボード Phase 5・ML使用マニュアル | claude/t3-tasks-ml-manual-HDXK8 |
| [061](status-061.md) | 03-09 | status-060 TODO: CLI・ダッシュボード改善8件 | claude/execute-status-todos-6R9QI |
| [060](status-060.md) | 03-09 | Migration Guide・Abaqus使用マニュアル | claude/execute-status-todos-LGHaP |
| [059](status-059.md) | 03-09 | Run DAG可視化（agraph/graphviz） | claude/execute-status-todos-LGHaP |
| [058](status-058.md) | 03-08 | CI YAML構文エラー修正 | claude/execute-status-todos-R96yx |
| [057](status-057.md) | 03-07 | CI修正・T6-4完了確認・T6全完了 | claude/execute-status-todos-WMTsa |
| [056](status-056.md) | 03-07 | T1完了(#5,#6)・T6-2,3実装 | claude/execute-status-todos-dwEdz |
| [055](status-055.md) | 03-07 | T1#2 list[str]関数化・T2 Config migrate完了 | claude/execute-status-todos-pCe1c |
| [054](status-054.md) | 03-07 | T1#1ソートロジック・T2 Config二層分離基盤 | claude/execute-status-todos-aoOqK |
| [053](status-053.md) | 03-07 | 中期計画v0.3統合・T1(#3,#4)・T4完了・T6-1 | claude/integrate-midterm-plan-j9Zm2 |

### v0.2.0 アーカイブ (status-001〜052)

> v0.2.0のstatus（001〜052）は [archive-v0.2.0/](archive-v0.2.0/) に移動済み。
> 各ファイルへのリンクは `archive-v0.2.0/status-{NNN}.md` を参照。

---

## 過去バージョン

- [v0.1.0 statusインデックス](archive-v0.1.0/status-index-v0.1.0.md) — 151件（jj: 90件、jjrv: 61件・分離済み）
