[← README.md](../README.md)

# v0.2.0 ロードマップ

**テーマ**: 「単一プロジェクト → 複数プロジェクト横断」

v0.1.0が「1つのCAEプロジェクトのグラフ化と可視化」を実現したのに対し、v0.2.0は「複数プロジェクトの横断検索・比較・再利用」と「マルチソルバー対応」を目指す。

---

## マイルストーン依存関係

```
M1: 基盤整備（完了）
 │
 ├──→ M1.5: ドキュメント再構成（完了）
 │     └── マルチソルバー仕様書作成 + コアconfig柔軟性向上 + プラグイン雛形
 │
 └──→ M3: Neo4j統合パイプライン
       │
       └──→ M4: jjrv横断ダッシュボード
             │
             └──→ M5: ワークフロー自動化

M2: マルチソルバー検証（検証環境確保後に実施）
```

> **M2について**: Fluent/LS-DYNA/Flow-3D/OpenFOAM/CalculiX等の検証環境は常時利用可能ではないため、M1→M3の順に進める。M2は検証環境確保後にプラグインとして個別対応する。ただし、M1.5でコアモジュールの柔軟性を事前に確保しておく。

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

**ビュー保存/HTMLエクスポート**:
- PageComponentは既にrender_saved_view() + generate_html()で対応済み
- DashboardPageConnectorも同等のインターフェースを持ち、SavedViewConfig経由で保存・復元できること
- SavedViewConfigのview_typeに`connector:{page_label}`形式を追加
- HTMLエクスポートは保存済みビュー + コネクタービュー + 全ページを統合出力

**フィルター階層化**:
- **グローバルフィルター**: サイドバーで設定し、全ページ/ビューに適用（type, analysis_status, active）
- **ローカルフィルター**: 各ページ/ビュー固有のフィルタ（SavedViewConfig.filtersに加え、connector固有フィルタ）
- 適用順: グローバルフィルター → ローカルフィルター（AND結合）
- ローカルフィルターはオプショナル（定義しない場合はグローバルフィルターのみ適用）

---

## M3: Neo4j統合パイプライン

| タスク | 成果物 | 仕様書 |
|--------|--------|--------|
| Neo4jスキーマ確定 | スキーマ文書 | [10-db-integration.md](../jj/docs/specs/10-db-integration.md) |
| ID体系統一 | int→string変換ルール | [10-db-integration.md](../jj/docs/specs/10-db-integration.md) |
| jjrv Neo4jクライアント | `src/lib/datasource/neo4j-*.ts` | [jjrv RM6](../jjrv/docs/spec-roadmap6.md) |
| データソース切替 | SQLite↔Neo4j factory | [jjrv RM6](../jjrv/docs/spec-roadmap6.md) |

---

## M4: jjrv横断ダッシュボード

**位置づけ**: jj dashboard（Streamlit）で軽量検証した可視化パターンをjjrvに洗練移植し、レポジトリ・ノード・リレーションの横断視認性を実現する。

| タスク | 成果物 | 仕様書 |
|--------|--------|--------|
| レポジトリ一覧 | `/repos` ページ | [spec-dashboard.md](../jjrv/docs/spec-dashboard.md) |
| Streamlit検証パターン移植 | 配列プロット/物性一覧/ジョブサマリー | [09-dashboard.md](../jj/docs/specs/09-dashboard.md) |
| ノード横断検索 | Cypherクエリ | [10-db-integration.md](../jj/docs/specs/10-db-integration.md) |

---

## M5: ワークフロー自動化

| タスク | 成果物 | 仕様書 |
|--------|--------|--------|
| runコマンド ジョブ型 | `jj r --mode=job` | [04-run-command.md](../jj/docs/specs/04-run-command.md) |
| fileコマンド基本 | テンプレート生成、リネーム | [06-file-command.md](../jj/docs/specs/06-file-command.md) |
| リモート実行統合 | `jj r --remote` | [04-run-command.md](../jj/docs/specs/04-run-command.md) |

---

## 仕様書リンク集

### jj仕様書（`jj/docs/specs/`）

| # | ドメイン | ファイル | 関連マイルストーン |
|---|---------|---------|-------------------|
| 01 | コアデータモデル | [01-core-data-model.md](../jj/docs/specs/01-core-data-model.md) | 基盤 |
| 02 | パーサー | [02-parser.md](../jj/docs/specs/02-parser.md) | M1.5, M2 |
| 03 | 設定管理 | [03-config.md](../jj/docs/specs/03-config.md) | M1.5, M2 |
| 04 | runコマンド | [04-run-command.md](../jj/docs/specs/04-run-command.md) | M5 |
| 05 | noteコマンド | [05-note-command.md](../jj/docs/specs/05-note-command.md) | — |
| 06 | fileコマンド | [06-file-command.md](../jj/docs/specs/06-file-command.md) | M5 |
| 07 | アダプター | [07-adapter.md](../jj/docs/specs/07-adapter.md) | M2 |
| 08 | エクスポート | [08-export.md](../jj/docs/specs/08-export.md) | M3 |
| 09 | ダッシュボード | [09-dashboard.md](../jj/docs/specs/09-dashboard.md) | M4 |
| 10 | DB統合 | [10-db-integration.md](../jj/docs/specs/10-db-integration.md) | M3, M4 |
| 11 | ダッシュボード要件 | [11-dashboard-requirements.md](../jj/docs/specs/11-dashboard-requirements.md) | M4 |

### 新規仕様書（`docs/specs/`）

| # | ドメイン | ファイル | 関連マイルストーン |
|---|---------|---------|-------------------|
| MS-01 | マルチソルバー対応 | [multi-solver.md](specs/multi-solver.md) | M1.5, M2 |

### jjrv仕様書（`jjrv/docs/`）

| # | ドメイン | ファイル | 状態 |
|---|---------|---------|------|
| RM1 | ユーザー運用 | [spec-roadmap1.md](../jjrv/docs/spec-roadmap1.md) | 完了 |
| RM2 | 検索・閲覧 | [spec-roadmap2.md](../jjrv/docs/spec-roadmap2.md) | 実装済み |
| RM3 | 操作性 | [spec-roadmap3.md](../jjrv/docs/spec-roadmap3.md) | 一部実装 |
| RM4 | 本番運用 | [spec-roadmap4.md](../jjrv/docs/spec-roadmap4.md) | 一部実装 |
| RM5 | 階層制約 | [spec-roadmap5.md](../jjrv/docs/spec-roadmap5.md) | 設計済み |
| RM6 | jj統合 | [spec-roadmap6.md](../jjrv/docs/spec-roadmap6.md) | 設計済み |

---

## v0.1.0 アーカイブ

v0.1.0のロードマップは [jj/docs/roadmap.md](../jj/docs/roadmap.md) に保存されている（Phase 0〜P、全マイルストーン完了済み）。

レビューは [docs/review/review-v0.1.0.md](review/review-v0.1.0.md) を参照。
