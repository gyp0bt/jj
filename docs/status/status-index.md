[← README.md](../../README.md)

# status-index — 実装状況インデックス

---

## アクティブTODO

> 最新statusファイルから引き継がれた未完了TODO。作業開始時はここを確認する。

### ワークトラック（進行中）

- [x] **T5**: リモートジョブ実行基盤 — Phase 5-1〜5-9完了（Prefect統合含む）
- [ ] **T7**: Ollama AI連携 — Phase 7-1〜7-6完了（AIProvider・summarize・diff・RAG・Tips・ダッシュボード）
- [ ] **T8**: 汎用データ管理 — Phase 8-1〜8-2完了（Run Discovery標準化・物理実験プラグイン）

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

### v0.2.0 M7: Run中心スキーマ (status-043〜052)

| # | 日付 | 概要 | ブランチ |
|---|------|------|---------|
| [052](status-052.md) | 03-06 | M7完了: バッチ俯瞰・Run比較・Neo4j対応 | claude/execute-status-todos-h9bRM |
| [051](status-051.md) | 03-06 | 配列プロット凡例vocab変換・バッチ俯瞰Run統合 | claude/execute-status-todos-h9bRM |
| [050](status-050.md) | 03-06 | プロット軸vocab変換・Run --show-properties | claude/execute-status-todos-ifjHD |
| [049](status-049.md) | 03-06 | Activeフィルタ全ページ適用・バッチ俯瞰ページ | claude/batch-run-visualization-iOJAa |
| [048](status-048.md) | 03-06 | Config classification実装・vocab_display UI | claude/execute-status-todos-oFw3W |
| [047](status-047.md) | 03-06 | 配列プロット クロスグループ軸選択 | claude/dashboard-configurable-axes-FLuI3 |
| [046](status-046.md) | 03-06 | Run-Propertyトレーサビリティ・Vocab表示時適用 | claude/track-feature-implementation-UCgLX |
| [045](status-045.md) | 03-04 | Parse-Run統合: jj run後にparse自動実行 | claude/integrate-parse-run-sujin |
| [044](status-044.md) | 03-04 | テスト全件通過: パス修正・importorskip | claude/execute-status-todos-lfDl8 |
| [043](status-043.md) | 03-04 | フォルダフラット化・jjrv分離反映・M7 Phase 4 | claude/update-docs-jjrv-separation-KiW6d |

### v0.2.0 M6: ML/最適化 + パフォーマンス (status-024〜042)

| # | 日付 | 概要 |
|---|------|------|
| [042](status-042.md) | 02-24 | .jj → .j2 リネーム |
| [041](status-041.md) | 02-21 | 等高線モード・サムネイル・ビュー編集 |
| [040](status-040.md) | 02-21 | スタイル永続化・コンタープロット・ギャラリー上限 |
| [039](status-039.md) | 02-20 | HTMLエクスポート: plotスタイル反映・ギャラリー |
| [038](status-038.md) | 02-20 | ダークモード視認性・ベンチマーク・キーワード拡充 |
| [037](status-037.md) | 02-20 | plotlyテーマ横断適用・ProcessPool検証 |
| [036](status-036.md) | 02-19 | ProcessPool並列化・plotlyダークモード |
| [035](status-035.md) | 02-19 | lightweight最適化・ワーカーチューニング |
| [034](status-034.md) | 02-19 | 並列プリフェッチ・lightweight対応・plotly統合 |
| [033](status-033.md) | 02-19 | UTF-8ファースト・段階的INP解析・パーサー並列化 |
| [032](status-032.md) | 02-19 | メッシュ統計キャッシュ |
| [031](status-031.md) | 02-19 | ProjectGraphインデックス・IgnoreConfigプリコンパイル |
| [030](status-030.md) | 02-19 | M7 Phase 2-3: RunDiscoverer |
| [029](status-029.md) | 02-19 | M7 Phase 1: コアモデル拡張 |
| [028](status-028.md) | 02-19 | Phase 4.5: バグ修正・パスマッチング改善 |
| [027](status-027.md) | 02-18 | サロゲートモデルフレームワーク Phase 4 |
| [026](status-026.md) | 02-18 | MLプラグイン Phase 3 |
| [025](status-025.md) | 02-18 | MLプラグイン Phase 2 |
| [024](status-024.md) | 02-18 | ML対応ロードマップ策定 |

### v0.2.0 M1-M3: 基盤・ダッシュボード (status-001〜023)

<details>
<summary>status-001〜023（クリックで展開）</summary>

| # | 日付 | 概要 |
|---|------|------|
| [023](status-023.md) | 02-18 | 接続設定UI・Neo4j検索アダプター |
| [022](status-022.md) | 02-18 | Neo4j Docker環境・IEntityRepository |
| [021](status-021.md) | 02-18 | Neo4jスキーマ反映・接頭辞キー表示 |
| [020](status-020.md) | 02-18 | pymeshリファクタリング |
| [019](status-019.md) | 02-18 | 新構造パーサー・connector_config UI |
| [018](status-018.md) | 02-17 | 設計仕様書・コネクター保存ビュー |
| [017](status-017.md) | 02-17 | ビュー保存/HTMLエクスポート横断対応 |
| [016](status-016.md) | 02-17 | メッシュ品質修正・E2Eテスト |
| [015](status-015.md) | 02-17 | メッシュ品質ダッシュボード分離 |
| [014](status-014.md) | 02-17 | バグ修正4件 |
| [013](status-013.md) | 02-17 | PageComponent描画ロジック移動 |
| [012](status-012.md) | 02-17 | PageComponent[ViewConfig]導入 |
| [011](status-011.md) | 02-17 | 表示名parse時移動・プロットスタイル |
| [010](status-010.md) | 02-17 | verbose_name展開・グループ結線修正 |
| [009](status-009.md) | 02-17 | ライトテーマ・ビュー永続化 |
| [008](status-008.md) | 02-16 | results/メタデータ抽出パーサー |
| [007](status-007.md) | 02-16 | verbose-name-format・vocab表示名 |
| [006](status-006.md) | 02-16 | ダッシュボード表示改善 |
| [005](status-005.md) | 02-15 | SolverProfileConfigテスト34件 |
| [004](status-004.md) | 02-15 | プラグイン雛形6ソルバー |
| [003](status-003.md) | 02-14 | ドキュメント再構成 |
| [002](status-002.md) | 02-14 | CLAUDE.md作成、Getting Started |
| [001](status-001.md) | 02-14 | CI/CD構築、statusアーカイブ |

</details>

---

## 過去バージョン

- [v0.1.0 statusインデックス](status-index-v0.1.0.md) — 151件（jj: 90件、jjrv: 61件・分離済み）
