[← status-index](status-index.md)

# status-025: MLプラグイン Phase 2 コアパーサー実装

- **日付**: 2026-02-18
- **マイルストーン**: M6
- **ブランチ**: claude/execute-status-todos-cMpnf

---

## 概要

status-024のTODOを実行し、M6（ML/実験/最適化タスク対応）のPhase 2として
MLプラグインの基盤インフラとコアパーサー3種を実装した。テストアセットと
28件のユニットテストを含む。

## 実施内容

### 1. pyproject.toml 更新

- `ml`, `sklearn`, `optuna`, `ml-all` の4つのoptional-dependenciesグループを追加
- `all` グループに `ml-all` を追加
- entry-points `jj.plugins` に `ml = "services.plugins.ml:register"` を追加

### 2. MLプラグイン雛形作成

- `services/plugins/ml/__init__.py`: register()関数、3パーサーのimport
- `services/parse/connectors/ml/__init__.py`: パッケージ初期化
- 既存プラグイン（Fluent, Abaqus等）と同じパターンに準拠

### 3. テストアセット作成 (`shared/tests/test_asset_ml/`)

典型的なMLプロジェクト構造を再現:

```
shared/tests/test_asset_ml/
├── configs/                  # 実験設定ファイル
│   ├── train_config.yaml     # 学習設定（PyTorch）
│   ├── model_config.yaml     # モデルアーキテクチャ
│   └── sweep_config.yaml     # ハイパーパラメータ探索
├── data/                     # データセット
│   ├── raw/dataset_v1.csv    # 生データ（CSV）
│   └── processed/            # 前処理済み（train/val/test.npy）
├── src/                      # ソースコード
│   ├── train.py              # PyTorch学習スクリプト
│   ├── evaluate.py           # 評価スクリプト（torch + sklearn）
│   ├── preprocess.py         # 前処理（pandas/numpy、MLフレームワークなし）
│   ├── model.py              # モデル定義（PyTorch）
│   ├── optimizer.py          # Optuna最適化スクリプト
│   ├── sklearn_train.py      # scikit-learn学習スクリプト
│   └── utils.py              # ユーティリティ（ML importなし）
├── experiments/              # 実験結果
│   ├── exp_001/              # 実験1（metrics.json, config.yaml, checkpoints/）
│   └── exp_002/              # 実験2
├── outputs/predictions.csv   # 推論結果
└── optuna_studies/           # 最適化スタディ用ディレクトリ
```

### 4. MLDatasetParser 実装（priority: 55）

- 対象拡張子: csv, parquet, h5, hdf5, npy, npz
- ノードタイプ `file` → `dataset` に昇格
- ファイル名からsplit情報を推定（train/val/test）
- CSVファイルのヘッダー行解析（カラム名、行数、列数）

### 5. MLConfigParser 実装（priority: 56）

- 対象拡張子: yaml, yml, json
- YAML/JSONファイルを読み込み、ML関連キーワードを2階層まで探索
- 検出キーワード: learning_rate, epochs, batch_size, optimizer, n_trials等
- ノードタイプ `file` → `experiment_config` に昇格
- 主要パラメータの値を抽出しプロパティに付与

### 6. MLScriptParser 実装（priority: 57）

- AST（抽象構文木）解析でimport文を抽出
- フレームワーク検出: torch→pytorch, sklearn→scikit-learn, optuna→optuna等
- ファイル名ヒューリスティクス: train→training, evaluate→evaluation等
- training系スクリプトは `training_script` タイプに昇格
- コア依存（ast標準ライブラリ）のみで動作

### 7. ユニットテスト（28件全パス）

| テストクラス | テスト数 | 検証内容 |
|-------------|---------|---------|
| TestMLDatasetParser | 7 | CSV/npy/parquet/h5昇格、split検出、メタデータ抽出 |
| TestMLConfigParser | 7 | YAML/JSON解析、キーワード検出、パラメータ抽出 |
| TestMLScriptParser | 11 | import解析、フレームワーク検出、ロール推定、型昇格 |
| TestMLPluginRegistration | 3 | プラグイン登録、冪等性、優先度検証 |

## ファイル構成（新規・変更）

```
jj/pyproject.toml                                    # ml/sklearn/optuna依存追加、entry-points追加
jj/services/plugins/ml/__init__.py                   # MLプラグイン [NEW]
jj/services/parse/connectors/ml/__init__.py          # パーサーパッケージ [NEW]
jj/services/parse/connectors/ml/dataset_parser.py    # MLDatasetParser [NEW]
jj/services/parse/connectors/ml/config_parser.py     # MLConfigParser [NEW]
jj/services/parse/connectors/ml/script_parser.py     # MLScriptParser [NEW]
jj/tests/test_ml_parsers.py                          # ユニットテスト28件 [NEW]
shared/tests/test_asset_ml/                          # テストアセット [NEW]
docs/status/status-025.md                            # 本status [NEW]
docs/status/status-index.md                          # status一覧更新
```

## TODO

- [ ] Phase 3着手: TorchProjectParser実装（.pt/.pth/.ckptメタデータ抽出）
- [ ] Phase 3着手: SklearnProjectParser実装（.pkl/.joblibメタデータ抽出）
- [ ] Phase 3着手: ExperimentRunParser実装（実験ディレクトリ構造認識）
- [ ] MLパーサーのソルバープロファイル統合（config.yamlにml-pytorchプロファイル追加）
- [ ] test_plugin_integration.pyにMLプラグイン登録テストを追加
- [ ] status-024 TODO継続: Neo4j Docker E2E検証（WSLローカル環境）
- [ ] status-024 TODO継続: 検索UIでのNeo4j全文検索統合

## 確認事項・懸念

- MLScriptParserのAST解析はファイル内容を読み込むため、大規模プロジェクト（数百.pyファイル）ではパフォーマンスに注意が必要。必要に応じてファイルサイズ上限の導入を検討
- MLConfigParserの2階層探索は現状の設定ファイル構造で十分だが、深いネストの場合は再帰的探索が必要になる可能性あり
- preprocess.pyのようにpandas/numpyのみ使用するスクリプトはMLフレームワークとして検出されない（意図的な設計：pandas/numpyは汎用すぎるため）
- 既存テスト8件のpandas依存による失敗は今回の変更とは無関係（pymesh optional依存未インストール）
