[← status-index](status-index.md)

# status-024: ML/実験/最適化タスク対応ロードマップ策定

- **日付**: 2026-02-18
- **マイルストーン**: M6
- **ブランチ**: claude/ml-task-roadmap-uwhPT

---

## 概要

機械学習タスク（PyTorch, scikit-learn）、実験タスク、CAEタスク、およびそれらを横断する最適化タスクのデータフローをグラフ化するための仕様書を策定し、ロードマップにM6マイルストーンとして追加した。

## 実施内容

### 1. ML対応仕様書の作成

`docs/specs/ml-task-roadmap.md` を新規作成。以下の内容を網羅:

- **ドメイン分析**: MLプロジェクトの典型的ディレクトリ構造、CAE-ML連携プロジェクトの構造
- **データモデル拡張**: 10種の新規ノードタイプ（dataset, model_checkpoint, training_script, experiment_config, experiment_run, metric_log, optimization_study, optimization_trial, feature_set, prediction_output）、13種の新規リレーションラベル
- **三層データフローモデル**: Layer 1（CAE）、Layer 2（ML/実験）、Layer 3（最適化）の層間データフロー設計
- **パーサー設計**: MLプラグイン構成（10パーサー）、既存AbstractFileParserパターンの踏襲
- **ソルバープロファイル拡張**: ml-pytorch、ml-sklearn、optimizationプロファイルの定義
- **依存管理**: optional-dependencies（ml, sklearn, optuna, ml-all）、コア層への依存禁止原則
- **ダッシュボード拡張**: MLOverview、ModelRegistry、OptimizationView、DataFlowDiagram
- **実装計画**: 5フェーズ構成
- **設計上の懸念**: スコープ管理、ファイル解析コスト、CAE共存、モデルファイル安全性

### 2. ロードマップ更新

- `docs/roadmap.md` にM6マイルストーンを追加
- テーマを「ML/最適化統合」を含むよう更新
- マイルストーン依存関係図にM6ツリーを追加
- 仕様書リンク集にMS-03（ML対応仕様書）を追加
- M6の概要説明（M2と並行進行可能であること）を記載

### 3. status-index.md更新

- マイルストーン進捗テーブルにM6行を追加

### 4. status-023 TODO確認

status-023のTODO 4件を確認:
- Neo4j Docker E2E検証 → Docker環境制約で実行不可（WSLローカル必要）→ 継続
- SQLite↔Neo4j切替E2E → 同上 → 継続
- 検索UIでのNeo4j全文検索統合 → jjrvフロントエンド実装が必要 → 継続
- M4横断ダッシュボード着手 → 将来マイルストーン → 継続

## ファイル構成（新規・変更）

```
docs/specs/ml-task-roadmap.md          # ML対応仕様書 [NEW]
docs/roadmap.md                         # M6マイルストーン追加
docs/status/status-index.md             # M6行追加
docs/status/status-024.md               # 本status [NEW]
```

## TODO

- [ ] Phase 2着手: MLScriptParser実装（Pythonスクリプトのimport静的解析）
- [ ] MLプロジェクト用テストアセット作成（`shared/tests/test_asset_ml/`）
- [ ] pyproject.tomlにml/sklearn/optuna optional-dependencies追加
- [ ] pyproject.tomlにMLプラグインentry-points追加
- [ ] services/plugins/ml/ プラグイン雛形作成
- [ ] status-023 TODO継続: Neo4j Docker E2E検証（WSLローカル環境）
- [ ] status-023 TODO継続: 検索UIでのNeo4j全文検索統合

## 確認事項・懸念

- M6はM2（マルチソルバー検証）と並行進行可能だが、両方ともプラグインローダー（`jj.plugins`エントリーポイント）を使用するため、ローダーの信頼性をまず確認すべき
- MLプロジェクトのファイル構造はCAEプロジェクトとは大きく異なる（Pythonスクリプト中心、ディレクトリ構造が多様）。既存のFileNameParser命名規則（`go_`, `mesh_`等）との干渉を避けるため、ML検出はimport解析に依存する設計とした
- `.pt`/`.pkl`ファイルのデシリアライズはセキュリティリスクがあるため、`requires_full=True`フラグで制御する方針
- 三層データフローモデルは概念設計段階。実装時にリレーション粒度の調整が必要になる可能性あり
