[← status-index.md](status-index.md) | [← README.md](../../../README.md)

# status-043: プロジェクト構造フラット化・jjrv分離反映・M7 Phase 4

- **日付**: 2026-03-04
- **マイルストーン**: M1（基盤整備）、M7（Run中心スキーマ Phase 4）
- **ブランチ**: `claude/update-docs-jjrv-separation-KiW6d`

---

## 概要

jjrvが別リポジトリに分離されたため、`jj/jj/` のネスト構造をフラット化しプロジェクトルートに移動。jjrv関連の参照をドキュメントから除去。併せてM7 Phase 4（RunService統合）を実装。

## 変更内容

### 1. フォルダ階層フラット化

jjrvがあった時代は `jj/` (root) / `jj/jj/` (Python) / `jjrv/` (TypeScript) の3層構造だった。jjrv分離により `jj/jj/` の中身をルートに移動し1層フラット化。

| 変更前 | 変更後 |
|--------|--------|
| `jj/services/` | `services/` |
| `jj/jj_types/` | `jj_types/` |
| `jj/tests/` | `tests/` |
| `jj/modules/` | `modules/` |
| `jj/config/` | `config/` |
| `jj/pyproject.toml` | `pyproject.toml` |
| `jj/docs/specs/` | `docs/specs/` （統合） |
| `jj/docs/detail.md` | `docs/detail.md` |
| `jj/docs/roadmap.md` | `docs/roadmap-v0.1.0.md` |
| `jj/shared/` (Python) | `shared/` （アセットと統合） |

### 2. jjrv参照除去

| ファイル | 変更 |
|---------|------|
| `README.md` | jjrv行削除、単一プロジェクトとして再構成 |
| `CLAUDE.md` | jjrvセクション削除、ディレクトリ構成をフラット化版に更新 |
| `CONTRIBUTING.md` | jjrv関連のテスト/CI記述削除 |
| `docs/roadmap.md` | M4凍結、jjrv仕様書リンク削除、パス修正 |
| `docs/README.md` | jjrv固有ドキュメントセクション削除 |
| `.github/workflows/ci.yml` | jjrv CIジョブ3件削除、`working-directory: jj` 削除 |
| `.gitignore` | jjrv関連24行削除、jj固有パス削除 |
| `docker-compose.yml` | コメントからjjrv削除 |
| `shared/__init__.py` | docstringからjjrv削除 |
| `shared/neo4j_schema.py` | docstring・コメントからjjrv削除 |

### 3. M7 Phase 4: RunService統合

`RunService._update_graph_storage()` を `ProjectGraph.add_run_node()` に移行。

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| Nodeカテゴリ | `type="run"` (generic) | `category=NodeCategory.RUN` |
| リレーション | `generated` | `run_output`, `run_media` |
| run_type | なし | 自動推定（script/ml_training/cae_job） |
| discovery | なし | `"runtime"` |
| run_status | なし | `"completed"` |

## テスト結果

- **ruff check**: All checks passed（メインコード）
- **pytest**: 1353 passed, 96 skipped, 159 failed（既知のoptional依存失敗、移動に起因する新規失敗は0件）
- **Run関連テスト**: 68 passed（run_service: 4件、run_centric_schema: 35件、cae_run_discoverer: 27件、ml_run_discoverer: 24件 → 計90件中68件がコア）

## TODO

- [ ] M7 Phase 5: Run比較ダッシュボード（Run一覧・Run比較・Run DAGビュー）
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] M6 Phase 5: MLダッシュボードコネクター
- [ ] プラグイン分離の検討（Abaqusプラグインの外部パッケージ化）
- [x] 既存159件の既知テスト失敗の修正（optional依存: pandas/plotly/pymesh/sta解析） → status-044で解消
- [x] docs/specs内の旧パス参照（`../jj/docs/specs/` → `specs/`）の一括修正 → status-044で解消

## 確認事項・懸念

- jjrv分離後のNeo4j統合方針: jj側はNeo4jエクスポーターとして維持。将来的にjjrvが必要になる場合は別リポジトリから参照する設計
- フォルダ構造変更後、`pip install -e ".[dev]"` と `pytest` が正常動作することを確認済み
- 既知のテスト失敗159件はoptional依存（pandas, plotly, pymesh, scipy）によるもので、今回の変更とは無関係
