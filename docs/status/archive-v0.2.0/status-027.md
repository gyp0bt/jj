[← status-index](status-index.md)

# status-027: サロゲートモデルフレームワーク Phase 4 実装

- **日付**: 2026-02-18
- **マイルストーン**: M6
- **ブランチ**: claude/surrogate-model-framework-NSm1k

---

## 概要

status-026のTODOを実行し、M6（ML/実験/最適化タスク対応）のPhase 4として
サロゲートモデルフレームワークの基盤パーサー3種を実装した。
CAEシミュレーション（Abaqus等）→ MLサロゲートモデル（PyTorch等）→
最適化（Optuna等）の三層データフローをグラフ構造で表現する
フレームワークの骨格が完成した。

## 実施内容

### 1. サロゲートモデルフレームワーク仕様書策定

`docs/specs/surrogate-model-framework.md` を新規作成:

- 対象ワークフロー（Abaqus + PyTorch + Optuna）
- 三層データフローモデル（L1:CAE, L2:ML, L3:最適化）
- 新規パーサー3種の設計仕様
- Neo4jスキーマ拡張（9リレーション + 9ノードタイプ）
- プラグイン分離設計方針
- テスト計画・実装順序

### 2. OptimizationRunParser 実装（priority: 62）

- **Optuna SQLite DB検出**: sqlite3標準ライブラリでスキーマ検証、study_name/n_trials/direction抽出
- **最適化設定ファイル検出**: YAML/JSON内の最適化キーワード（n_trials, objective, search_space等）
- **試行履歴CSV検出**: trial_history, pareto_front等のファイル名パターン
- **最適化スクリプトメタデータ付与**: optimization/ディレクトリ内のoptunaスクリプトにフラグ追加
- ノードタイプ昇格: `optimization_study`, `optimization_config`, `trial_history`
- コア依存のみ（sqlite3, json, re, pathlib）

### 3. MLDataFlowParser 実装（priority: 65）

- **trains_with**: training_script → dataset（同一experiment_id優先、ディレクトリ近接性フォールバック）
- **produces_model**: training_script → model_checkpoint
- **configured_by**: training_script → experiment_config
- **logs_to**: experiment_metrics → model_checkpoint（同一実験ID）
- 重複リレーション防止（既存リレーション考慮のlinkedセット）
- experiment_idインデックスによる効率的マッチング

### 4. SurrogateWorkflowDetector 実装（priority: 70）

- **extracted_from**: dataset → CAE result（CAE結果からデータ抽出）
- **surrogate_of**: model_checkpoint → CAE input（サロゲートモデルがCAEを近似）
- **optimizes**: optimization_study → model_checkpoint（最適化対象）
- **uses_objective**: optimization_study → training_script（目的関数の定義元）
- プロジェクトルート最上位ディレクトリでの共存判定
- レイヤー分類: L1(CAE), L2(ML), L3(Optim)

### 5. Neo4jスキーマ拡張

- 新規リレーションタイプ9種追加（RelType + LABEL_TO_RELTYPE）
  - ML: TRAINS_WITH, PRODUCES_MODEL, CONFIGURED_BY, EVALUATED_ON, LOGS_TO
  - サロゲート: EXTRACTED_FROM, SURROGATE_OF, OPTIMIZES, USES_OBJECTIVE
- 新規ノードタイプマッピング9種追加（TYPE_TO_LABEL）
  - ML: dataset, model_checkpoint, serialized_model, training_script, experiment_config, experiment_metrics
  - 最適化: optimization_study, optimization_config, trial_history

### 6. テストアセット拡充

- `shared/tests/test_asset_ml/optimization/` ディレクトリを新規追加
  - `optuna_study.db`: Optuna SQLite DB（studies/trials/study_directionsテーブル）
  - `optuna_config.yaml`: 最適化設定（study_name, n_trials, search_space等）
  - `trial_history.csv`: 5件の試行履歴
  - `pareto_front.csv`: パレートフロント2件
  - `optimize.py`: Optuna + PyTorchスクリプト

### 7. テスト（新規37件全パス）

| テストクラス | テスト数 | 検証内容 |
|-------------|---------|---------|
| TestOptimizationRunParser | 10 | DB昇格、メタデータ抽出、設定解析、試行履歴、スクリプト |
| TestMLDataFlowParser | 8 | trains_with/produces_model/configured_by/logs_to/重複防止 |
| TestSurrogateWorkflowDetector | 7 | extracted_from/surrogate_of/optimizes/uses_objective/フルワークフロー |
| TestSurrogateFrameworkRegistration | 3 | パーサー登録、優先度順序 |
| TestNeo4jSchemaExtension | 4 | リレーションタイプ/ノードタイプマッピング |
| TestSurrogateFrameworkE2E | 5 | 全パーサー連続実行、整合性検証 |

### 8. プラグイン登録更新

- `services/plugins/ml/__init__.py` に新パーサー3種のimportを追加
- ドキュメントテーブルを9パーサーに更新

## ファイル構成（新規・変更）

```
docs/specs/surrogate-model-framework.md                   # サロゲートモデル仕様書 [NEW]
jj/services/parse/connectors/ml/optimization_parser.py    # OptimizationRunParser [NEW]
jj/services/parse/connectors/ml/dataflow_parser.py        # MLDataFlowParser [NEW]
jj/services/parse/connectors/ml/surrogate_detector.py     # SurrogateWorkflowDetector [NEW]
jj/services/plugins/ml/__init__.py                        # 新パーサー3種のimport追加
jj/shared/neo4j_schema.py                                 # 9リレーション + 9ノードタイプ追加
jj/tests/test_surrogate_framework.py                      # テスト37件 [NEW]
shared/tests/test_asset_ml/optimization/                  # テストアセット [NEW]
docs/status/status-027.md                                 # 本status [NEW]
docs/status/status-index.md                               # status一覧更新
```

## TODO

- [ ] MLダッシュボードコネクター実装（実験比較ビュー・サロゲートモデルビュー）
- [ ] MLDataFlowParserのパスマッチング改善（プロジェクトルートスコープのフォールバック追加）
- [ ] サロゲートモデルE2Eテスト拡充（CAE + ML混在テストアセット作成）
- [ ] SurrogateWorkflowDetectorの精度向上（設定ファイル内の参照パス解析）
- [ ] Phase 5着手: 三層データフローダイアグラム可視化（ダッシュボードページ）
- [ ] status-024 TODO継続: Neo4j Docker E2E検証（WSLローカル環境）
- [ ] status-024 TODO継続: 検索UIでのNeo4j全文検索統合

## 確認事項・懸念

- **MLDataFlowParserのマッチング精度**: test_asset_mlでは`src/train.py`と`data/raw/dataset_v1.csv`が親ディレクトリでも祖父母ディレクトリでもマッチしないため、`trains_with`リレーションが生成されない。プロジェクトルートスコープのフォールバックを追加するか、ディレクトリツリーの深さを考慮したマッチングが必要
- **SurrogateWorkflowDetectorの共存判定**: `_project_root_segment`は最上位ディレクトリの一致で判定。これにより同一プロジェクト内でのCAE-ML連携は検出されるが、ルート直下のファイル（depth=1）はマッチ対象外
- **OptimizationRunParserのsqlite3依存**: Optuna DBの読み込みにsqlite3を使用。大容量DBの場合はパフォーマンスへの影響に注意。テストアセットは5件の試行で軽量
- 既存テスト23件の失敗はpymesh依存（環境固有）で、今回の変更とは無関係
