[← status-index](status-index.md)

# status-026: MLプラグイン Phase 3 パーサー3種実装

- **日付**: 2026-02-18
- **マイルストーン**: M6
- **ブランチ**: claude/execute-status-todos-pdDTh

---

## 概要

status-025のTODOを実行し、M6（ML/実験/最適化タスク対応）のPhase 3として
MLプラグインの追加パーサー3種を実装した。テストアセットの拡充と
24件の新規ユニットテストを含む。

## 実施内容

### 1. TorchCheckpointParser 実装（priority: 58）

- 対象拡張子: .pt, .pth, .ckpt
- ノードタイプ `file` → `model_checkpoint` に昇格
- ファイル名から正規表現でエポック番号を抽出（epoch_10.pt → epoch: 10）
- ファイル名から正規表現でステップ番号を抽出（step_1000.pt → step: 1000）
- best modelフラグの自動判定（ファイル名に"best"を含む場合）
- ファイルサイズ（file_size_bytes）の取得
- コア依存のみ（re, pathlib標準ライブラリ）

### 2. SklearnModelParser 実装（priority: 59）

- 対象拡張子: .pkl, .joblib
- ノードタイプ `file` → `serialized_model` に昇格
- ファイル名からモデル種別を推定（classifier, scaler, pipeline等）
- best/finalモデルフラグの自動判定
- ファイルサイズ（file_size_bytes）の取得
- コア依存のみ（re, pathlib標準ライブラリ）

### 3. ExperimentRunParser 実装（priority: 60）

- 実験ディレクトリパターンの認識: exp_NNN, run_NNN, experiment_NNN, trial_NNN
- パス内の実験ディレクトリからexperiment_idを自動抽出
- metrics.jsonのキーメトリクス抽出（best_val_accuracy, best_epoch等）
- metrics.jsonをtype `experiment_metrics` に昇格
- 同一実験ディレクトリ内の全ファイルにexperiment_id/experiment_dirを付与
- コア依存のみ（json, re, pathlib標準ライブラリ）

### 4. テストアセット拡充

- `shared/tests/test_asset_ml/models/` ディレクトリを新規追加
  - `best_classifier.pkl`: scikit-learn pickleプレースホルダー
  - `scaler.joblib`: joblibプレースホルダー
  - `pipeline.pkl`: scikit-learn pipelineプレースホルダー

### 5. プラグイン登録更新

- `services/plugins/ml/__init__.py` に新パーサー3種のimportを追加
- ドキュメントテーブルを6パーサーに更新

### 6. ソルバープロファイル統合

- `shared/assets/default-config.yaml` にml-pytorch/ml-sklearnプロファイルを使用例として追加
- solver-detectionにML拡張子パターンを使用例として追加

### 7. プラグイン統合テスト更新

- `tests/test_plugin_integration.py` にMLプラグイン登録テスト（test_ml_plugin_registers）を追加
- 全プラグイン登録テストにMLプラグインを追加

### 8. ユニットテスト（52件→61件、新規24件全パス）

| テストクラス | テスト数 | 検証内容 |
|-------------|---------|---------|
| TestTorchCheckpointParser | 8 | .pt/.pth/.ckpt昇格、エポック抽出、bestフラグ、ファイルサイズ |
| TestSklearnModelParser | 8 | .pkl/.joblib昇格、モデル種別推定、bestフラグ、ファイルサイズ |
| TestExperimentRunParser | 8 | 実験ID検出、メトリクス抽出、run_パターン、複数ファイル |

## ファイル構成（新規・変更）

```
jj/services/parse/connectors/ml/checkpoint_parser.py    # TorchCheckpointParser [NEW]
jj/services/parse/connectors/ml/model_parser.py          # SklearnModelParser [NEW]
jj/services/parse/connectors/ml/experiment_parser.py     # ExperimentRunParser [NEW]
jj/services/plugins/ml/__init__.py                       # 新パーサー3種のimport追加
jj/tests/test_ml_parsers.py                              # テスト24件追加（28→52件）
jj/tests/test_plugin_integration.py                      # MLプラグイン統合テスト追加
shared/assets/default-config.yaml                        # ml-pytorch/ml-sklearnプロファイル追加
shared/tests/test_asset_ml/models/                       # テストアセット [NEW]
docs/status/status-026.md                                # 本status [NEW]
docs/status/status-index.md                              # status一覧更新
```

## TODO

- [ ] Phase 4着手: OptimizationRunParser実装（Optuna study構造認識）
- [ ] Phase 4着手: MLDataFlowParser実装（スクリプト→データセット→モデル間のリレーション自動構築）
- [ ] MLダッシュボードコネクター実装（実験比較ビュー）
- [ ] MLパーサーのE2E統合テスト（test_asset_ml全体をパースしてグラフ検証）
- [ ] status-024 TODO継続: Neo4j Docker E2E検証（WSLローカル環境）
- [ ] status-024 TODO継続: 検索UIでのNeo4j全文検索統合

## 確認事項・懸念

- TorchCheckpointParser/SklearnModelParserのファイルサイズ取得は実ファイルが存在する場合のみ動作。テスト用プレースホルダーファイルは実際のモデルファイルとはサイズが異なる
- ExperimentRunParserのメトリクス抽出は EXTRACTABLE_METRICS に定義されたキーのみ対象。プロジェクト固有のメトリクスキーは設定による拡張が必要になる可能性あり
- SklearnModelParserのモデル種別推定はファイル名ベースのヒューリスティクスであり、実際のモデル内容は検査していない（pickle/joblibの読み込みはセキュリティリスクがあるため意図的に避けている）
