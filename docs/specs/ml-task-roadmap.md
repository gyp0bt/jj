[← README.md](../../README.md)

# 機械学習タスク対応仕様書

**日付**: 2026-02-18
**関連マイルストーン**: M6（ML/実験/最適化タスク対応）

---

## 1. 背景と目的

### 1.1 現行のスコープ

jjは現在、CAE業務データ（構造解析、流体解析、電磁界解析）のグラフ構造化に特化している。ファイル名命名規則によるメタデータ抽出、ソルバー入出力関係の自動構築、バージョン管理を通じて、CAEプロジェクトのデータフローを可視化する。

### 1.2 拡張の動機

実際のエンジニアリングワークフローでは、CAEシミュレーションは単独で実行されるのではなく、以下のタスクと密接に連携する:

1. **機械学習タスク**: サロゲートモデル構築、物理情報ニューラルネットワーク（PINN）、結果の異常検知
2. **実験タスク**: 実験計画法（DOE）、パラメータスイープ、ベンチマーク比較
3. **最適化タスク**: ベイジアン最適化、遺伝的アルゴリズム、CAE-ML連携最適化ループ

これらのタスクは共通して「入力データ → 処理 → 出力データ」のデータフローを持ち、既存のjjグラフモデル（Node/Relation）で自然に表現できる。

### 1.3 対象フレームワーク

| カテゴリ | フレームワーク | 備考 |
|---------|--------------|------|
| 深層学習 | PyTorch, PyTorch Lightning | `.pt`, `.pth`, `.ckpt` |
| 古典ML | scikit-learn | `.pkl`, `.joblib` |
| 実験管理 | MLflow, Weights & Biases, TensorBoard | メトリクスログ、アーティファクト |
| 最適化 | Optuna, BoTorch, scipy.optimize | 試行履歴、パレートフロント |
| データ | pandas, numpy, HDF5 | `.csv`, `.parquet`, `.h5`, `.npy` |

---

## 2. ドメイン分析

### 2.1 機械学習プロジェクトの典型的ディレクトリ構造

```
ml_project/
├── configs/                    # 実験設定
│   ├── train_config.yaml       # 学習ハイパーパラメータ
│   ├── model_config.yaml       # モデルアーキテクチャ定義
│   └── sweep_config.yaml       # ハイパーパラメータ探索定義
├── data/                       # データセット
│   ├── raw/                    # 生データ
│   │   ├── dataset_v1.csv
│   │   └── dataset_v2.parquet
│   ├── processed/              # 前処理済みデータ
│   │   ├── train.npy
│   │   ├── val.npy
│   │   └── test.npy
│   └── features/               # 特徴量
│       └── features_v1.h5
├── src/                        # ソースコード
│   ├── model.py                # モデル定義
│   ├── train.py                # 学習スクリプト
│   ├── evaluate.py             # 評価スクリプト
│   └── preprocess.py           # 前処理スクリプト
├── experiments/                # 実験結果
│   ├── exp_001/                # 実験1
│   │   ├── checkpoints/
│   │   │   ├── epoch_10.pt
│   │   │   └── best_model.pt
│   │   ├── logs/
│   │   │   └── events.out.tfevents.*
│   │   ├── metrics.json
│   │   └── config.yaml         # この実験で使用した設定のコピー
│   ├── exp_002/
│   └── exp_003/
├── outputs/                    # 推論・評価結果
│   ├── predictions.csv
│   └── evaluation_report.json
├── mlruns/                     # MLflow tracking
│   └── 0/
│       └── {run_id}/
│           ├── artifacts/
│           ├── metrics/
│           └── params/
└── optuna_studies/             # Optuna最適化
    └── study_v1.db
```

### 2.2 CAE-ML連携プロジェクトの構造

```
cae_ml_optimization/
├── cae/                        # CAEシミュレーション
│   ├── go_idx1_v1.inp          # Abaqus入力
│   ├── go_idx1_v1.odb          # 結果
│   ├── go_idx2_v1.inp
│   └── go_idx2_v1.odb
├── ml/                         # サロゲートモデル
│   ├── configs/
│   │   └── surrogate_config.yaml
│   ├── data/
│   │   └── training_data.csv   # CAE結果から抽出した学習データ
│   ├── models/
│   │   └── surrogate_v1.pt
│   └── src/
│       └── surrogate.py
├── optimization/               # 最適化ループ
│   ├── configs/
│   │   └── optim_config.yaml   # 最適化設定（目的関数、制約、範囲）
│   ├── results/
│   │   ├── trial_history.csv   # 試行履歴
│   │   └── pareto_front.csv    # パレートフロント
│   └── src/
│       └── optimizer.py
└── reports/
    └── optimization_report.html
```

### 2.3 データフローグラフ

```
[Dataset]──uses_data──→[Training Script]──produces──→[Model Checkpoint]
    │                        │                              │
    │                   trains_with                     evaluated_by
    │                        │                              │
    │                        ▼                              ▼
    │               [Experiment Config]            [Evaluation Metrics]
    │
    ├──derived_from──→[Preprocessed Data]
    │
[CAE Result]──extracted_to──→[Training Data]──used_by──→[Surrogate Model]
    ▲                                                         │
    │                                                    predicts_for
    │                                                         │
    └──────────validates──────[Optimization Loop]◄──optimizes─┘
                                     │
                                uses_objective
                                     │
                                     ▼
                            [Objective Function Config]
```

---

## 3. データモデル拡張

### 3.1 新規ノードタイプ

既存のNode構造体（`id, type, name, format, properties`）を変更せず、新しいtypeを追加する。

| ノードタイプ | 説明 | 典型的なformat | 主要properties |
|-------------|------|---------------|---------------|
| `dataset` | データセットファイル | csv, parquet, h5, npy | `rows`, `cols`, `split`(train/val/test), `version` |
| `model_checkpoint` | 学習済みモデル | pt, pth, ckpt, pkl, joblib | `epoch`, `metric_value`, `framework`(torch/sklearn) |
| `training_script` | 学習スクリプト | py | `framework`, `model_class`, `imports` |
| `experiment_config` | 実験設定ファイル | yaml, json, toml | `learning_rate`, `batch_size`, `epochs`, `optimizer` |
| `experiment_run` | 実験実行（ディレクトリ単位） | directory | `status`(running/completed/failed), `duration`, `best_metric` |
| `metric_log` | メトリクスログ | json, csv, tfevents | `metric_names`, `final_values` |
| `optimization_study` | 最適化スタディ | db, json | `n_trials`, `best_value`, `algorithm`, `objective` |
| `optimization_trial` | 最適化の1試行 | — | `trial_number`, `params`, `value`, `state` |
| `feature_set` | 特徴量セット | h5, npy, parquet | `n_features`, `feature_names` |
| `prediction_output` | 推論結果 | csv, json, npy | `n_samples`, `model_version` |

### 3.2 新規リレーションラベル

| ラベル | 始点 → 終点 | 説明 |
|--------|------------|------|
| `trains_with` | training_script → dataset | スクリプトがデータセットを使用 |
| `produces_model` | experiment_run → model_checkpoint | 実験がモデルを生成 |
| `configured_by` | experiment_run → experiment_config | 実験の設定 |
| `logs_to` | experiment_run → metric_log | メトリクス記録先 |
| `evaluated_on` | model_checkpoint → dataset | モデルの評価データ |
| `extracted_from` | dataset → file(CAE result) | CAE結果からデータ抽出 |
| `surrogate_of` | model_checkpoint → file(CAE input) | サロゲートモデルの対象 |
| `optimizes` | optimization_study → model_checkpoint/file | 最適化の対象 |
| `trial_of` | optimization_trial → optimization_study | 試行とスタディの関係 |
| `uses_objective` | optimization_study → training_script/file | 目的関数の定義元 |
| `predicts_for` | prediction_output → model_checkpoint | 推論に使用したモデル |
| `derived_from_data` | feature_set → dataset | 特徴量の元データ |
| `preprocessed_by` | dataset(processed) → training_script | 前処理スクリプト |

### 3.3 既存ノードタイプとの関係

| 既存ノードタイプ | ML文脈での利用 |
|----------------|---------------|
| `file` | Python スクリプト、設定ファイル等（汎用） |
| `run` | 学習・評価の実行履歴 |
| `directory` | experiments/exp_001/ 等のコンテナ |

ML固有のノードタイプは、既存の`file`タイプの**特化型**として扱う。パーサーがファイル内容を解析し、`type`を`file`から`dataset`や`model_checkpoint`に**昇格**させる。

---

## 4. パーサー設計

### 4.1 MLプラグイン構成

```
services/plugins/ml/
├── __init__.py                  # register() — エントリーポイント
├── torch_parser.py              # PyTorchプロジェクト解析
├── sklearn_parser.py            # scikit-learnプロジェクト解析
├── experiment_parser.py         # 実験ディレクトリ構造解析
├── config_parser.py             # ML設定ファイル解析
├── dataset_parser.py            # データセットメタデータ抽出
└── optimization_parser.py       # 最適化スタディ解析

services/plugins/ml/connectors/
├── mlflow_parser.py             # MLflow tracking解析
├── tensorboard_parser.py        # TensorBoardイベント解析
├── optuna_parser.py             # Optunaスタディ解析
└── wandb_parser.py              # W&Bアーティファクト解析
```

### 4.2 パーサー優先度

| priority | パーサー | 責務 |
|----------|---------|------|
| 55 | MLDatasetParser | データセットファイル検出・メタデータ抽出 |
| 56 | MLConfigParser | ML設定ファイル解析（YAML/JSON/TOML） |
| 57 | MLScriptParser | Pythonスクリプトのimport解析・フレームワーク検出 |
| 60 | TorchProjectParser | PyTorchモデル・チェックポイント解析 |
| 60 | SklearnProjectParser | scikit-learnモデル解析 |
| 65 | ExperimentRunParser | 実験ディレクトリ構造の認識・関係構築 |
| 70 | MLflowParser | MLflow tracking解析 |
| 70 | TensorBoardParser | TensorBoardイベント解析 |
| 70 | OptunaParser | Optunaスタディ解析 |
| 75 | OptimizationLoopParser | CAE-ML最適化ループの関係構築 |

### 4.3 パーサー詳細

#### MLScriptParser（priority: 57）

Pythonスクリプトの**import文を静的解析**し、使用フレームワークを検出する。

```python
class MLScriptParser(AbstractFileParser):
    priority = 57

    # 検出対象import
    FRAMEWORK_IMPORTS = {
        "torch": "pytorch",
        "torch.nn": "pytorch",
        "pytorch_lightning": "pytorch-lightning",
        "lightning": "pytorch-lightning",
        "sklearn": "scikit-learn",
        "tensorflow": "tensorflow",
        "optuna": "optuna",
        "botorch": "botorch",
        "mlflow": "mlflow",
    }

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.graph_model.nodes:
            if node.format != "py":
                continue
            # AST解析でimport文を抽出
            imports = self._extract_imports(node, graph)
            frameworks = self._detect_frameworks(imports)
            if frameworks:
                node.properties["ml_frameworks"] = frameworks
                node.properties["ml_role"] = self._infer_role(node.name, imports)
                # training_script等への型昇格
                if node.properties["ml_role"] == "training":
                    node.type = "training_script"
        return graph
```

**検出ロジック**:
- `import torch` / `from torch import ...` → framework: pytorch
- `from sklearn.ensemble import ...` → framework: scikit-learn
- ファイル名ヒューリスティクス: `train*.py` → role: training, `eval*.py` → role: evaluation

#### TorchProjectParser（priority: 60）

PyTorchモデルファイル（`.pt`, `.pth`, `.ckpt`）のメタデータ抽出。

```python
class TorchProjectParser(AbstractFileParser):
    priority = 60
    MODEL_EXTENSIONS = {".pt", ".pth", ".ckpt"}

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.graph_model.nodes:
            if f".{node.format}" not in self.MODEL_EXTENSIONS:
                continue
            node.type = "model_checkpoint"
            node.properties["framework"] = "pytorch"
            # ファイルサイズからモデル規模を推定
            self._enrich_model_metadata(node, graph)
            # 同一ディレクトリ内の設定ファイルとの関連付け
            self._link_config(node, graph)
        return graph
```

#### ExperimentRunParser（priority: 65）

実験ディレクトリ（`experiments/exp_001/`等）を認識し、内部ファイルとの関係を構築。

**ディレクトリパターン認識**:
- `experiments/exp_*` または `experiments/run_*`
- `mlruns/{experiment_id}/{run_id}/`
- `outputs/{timestamp}/` (Hydra形式)
- `logs/{experiment_name}/`

#### OptimizationLoopParser（priority: 75）

CAEシミュレーション結果とMLモデルを結ぶ最適化ループを検出・グラフ化。

**検出パターン**:
1. `optimization/` ディレクトリの存在
2. Optuna DB ファイル（`.db` with sqlite3 + optuna schema）
3. 設定ファイル内の最適化パラメータ（`objective`, `search_space`, `n_trials`）
4. CAE入力パラメータとML予測結果の対応関係

---

## 5. ソルバープロファイル拡張

### 5.1 MLプロファイル定義

```yaml
# .j2/config/config.yaml
solver-profiles:
  # ... 既存プロファイル ...

  ml-pytorch:
    source-unit: directory        # 実験ディレクトリ単位
    filename-pattern: standard
    input-extensions: [".py", ".yaml", ".json", ".toml"]
    result-extensions: [".pt", ".pth", ".ckpt", ".csv", ".json"]
    dataset-extensions: [".csv", ".parquet", ".h5", ".hdf5", ".npy", ".npz"]
    model-extensions: [".pt", ".pth", ".ckpt"]
    experiment-directory-pattern: "^exp_\\d+$|^run_\\d+$"

  ml-sklearn:
    source-unit: file
    filename-pattern: standard
    input-extensions: [".py", ".yaml", ".json"]
    result-extensions: [".pkl", ".joblib", ".csv", ".json"]
    dataset-extensions: [".csv", ".parquet", ".h5"]
    model-extensions: [".pkl", ".joblib"]

  optimization:
    source-unit: directory
    filename-pattern: standard
    input-extensions: [".py", ".yaml", ".json"]
    result-extensions: [".db", ".csv", ".json"]
    study-extensions: [".db"]

solver-detection:
  # ... 既存パターン ...
  "**/*.pt | **/*.pth | **/*.ckpt":    ml-pytorch
  "**/*.joblib":                        ml-sklearn
  "**/mlruns/**":                       ml-pytorch
  "**/optuna_studies/*.db":             optimization
```

### 5.2 ML検出ヒューリスティクス

ファイル拡張子だけでは不十分なため、以下の複合条件で検出する:

| 条件 | 判定 |
|------|------|
| `.pt`/`.pth`/`.ckpt` ファイルが存在 | ml-pytorch |
| `.py` に `import torch` を含む | ml-pytorch |
| `.joblib`/`.pkl` + sklearn import | ml-sklearn |
| `requirements.txt` に torch/sklearn | MLプロジェクト |
| `mlruns/` ディレクトリが存在 | MLflow使用 |
| `*.db` + optunaテーブル | Optuna使用 |

---

## 6. タスク横断データフロー

### 6.1 三層データフローモデル

jjが管理するデータフローを3つの層に整理する:

```
┌─────────────────────────────────────────────────────┐
│  Layer 3: 最適化タスク（Optimization）              │
│  ┌───────────┐     ┌───────────┐                    │
│  │ Objective │────→│  Search   │────→ Pareto Front  │
│  │ Function  │     │  Space    │                    │
│  └─────┬─────┘     └─────┬─────┘                    │
│        │                 │                          │
├────────┼─────────────────┼──────────────────────────┤
│  Layer 2: ML/実験タスク                              │
│        │                 │                          │
│  ┌─────▼─────┐     ┌─────▼─────┐     ┌───────────┐ │
│  │  Dataset  │────→│ Training  │────→│   Model   │ │
│  │           │     │  Script   │     │Checkpoint │ │
│  └─────┬─────┘     └───────────┘     └─────┬─────┘ │
│        │                                   │       │
├────────┼───────────────────────────────────┼───────┤
│  Layer 1: CAE/実験タスク                    │       │
│        │                                   │       │
│  ┌─────▼─────┐     ┌───────────┐     ┌─────▼─────┐ │
│  │CAE Input  │────→│ Solver    │────→│CAE Result │ │
│  │ (.inp等)  │     │(Abaqus等) │     │ (.odb等)  │ │
│  └───────────┘     └───────────┘     └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### 6.2 層間リレーション

| リレーション | 始点層 → 終点層 | 説明 |
|-------------|----------------|------|
| `extracted_from` | L2(dataset) → L1(CAE result) | CAE結果をML学習データに変換 |
| `surrogate_of` | L2(model) → L1(CAE input template) | サロゲートモデルがCAEを近似 |
| `validates` | L1(CAE result) → L2(model) | CAE結果でモデルを検証 |
| `optimizes` | L3(study) → L1(CAE input)/L2(model) | 最適化対象の指定 |
| `suggested_by` | L1(CAE input params) → L3(trial) | 最適化が提案したパラメータ |

### 6.3 典型的ワークフロー例

#### ワークフロー1: サロゲートモデルベース最適化

```
1. [CAE入力] × N件 → [CAEソルバー] → [CAE結果] × N件
2. [CAE結果] × N件 → extracted_from → [学習データセット]
3. [学習データセット] → trains_with → [学習スクリプト] → produces_model → [サロゲートモデル]
4. [サロゲートモデル] → optimizes ← [最適化スタディ]
5. [最適化スタディ] → trial × M件 → [推奨パラメータ]
6. [推奨パラメータ] → [追加CAE入力] → [CAEソルバー] → [検証結果]
```

#### ワークフロー2: 物理情報ニューラルネットワーク（PINN）

```
1. [支配方程式定義] (yaml/py) → configured_by ← [PINNモデル定義]
2. [境界条件データ] → trains_with → [PINN学習スクリプト]
3. [PINN学習スクリプト] → produces_model → [学習済みPINN]
4. [学習済みPINN] → predicts_for → [場の予測結果]
5. [場の予測結果] ←validates→ [CAEシミュレーション結果]
```

#### ワークフロー3: パラメータスイープ + 統計分析

```
1. [パラメータ空間定義] (yaml) → generates → [CAE入力] × N件
2. [CAE入力] × N件 → [CAEソルバー] → [CAE結果] × N件
3. [CAE結果] × N件 → extracted_from → [統合データセット]
4. [統合データセット] → trains_with → [回帰分析/感度分析スクリプト]
5. [回帰分析スクリプト] → produces → [感度分析レポート]
```

---

## 7. ダッシュボード拡張

### 7.1 新規ダッシュボードページ

| ページ | 説明 | PageComponent |
|--------|------|--------------|
| MLOverview | ML実験一覧・メトリクス比較 | ExperimentTableComponent |
| ModelRegistry | モデルチェックポイント管理 | ModelRegistryComponent |
| OptimizationView | 最適化スタディ可視化 | OptimizationComponent |
| DataFlowDiagram | 三層データフロー図 | DataFlowComponent |

### 7.2 ExperimentTableComponent

実験の一覧表示。各行は1実験 = 1 `experiment_run` ノード。

| カラム | ソース |
|--------|--------|
| 実験名 | node.name |
| ステータス | node.properties["status"] |
| フレームワーク | node.properties["framework"] |
| ベストメトリクス | node.properties["best_metric"] |
| エポック数 | node.properties["epochs"] |
| 学習率 | node.properties["learning_rate"] |
| データセット | trains_with → dataset.name |
| モデル | produces_model → model_checkpoint.name |

### 7.3 DataFlowComponent

三層データフローをインタラクティブなグラフとして表示。

- **Layer 1（CAE）**: 青色ノード
- **Layer 2（ML/実験）**: 緑色ノード
- **Layer 3（最適化）**: 橙色ノード
- **層間リレーション**: 破線矢印
- **層内リレーション**: 実線矢印

---

## 8. 依存管理

### 8.1 optional-dependencies 追加

```toml
[project.optional-dependencies]
# ... 既存 ...
ml = [
    "torch>=2.0.0",
    "torchvision>=0.15.0",
]
sklearn = [
    "scikit-learn>=1.3.0",
    "joblib>=1.3.0",
]
optuna = [
    "optuna>=3.0.0",
]
ml-all = [
    "jj[ml,sklearn,optuna]",
]
```

### 8.2 コア層への依存禁止

MLパーサーの**ファイル構造認識**（拡張子、ディレクトリパターン、import文解析）はコア依存のみで動作する。torch/sklearnへの依存は、**モデルファイルの内部メタデータ抽出**（チェックポイントのロード、モデルアーキテクチャの読取り）にのみ必要。

```python
# 例: torch依存を遅延importで隔離
class TorchProjectParser(AbstractFileParser):
    def _load_checkpoint_metadata(self, path: Path) -> dict:
        try:
            torch = importlib.import_module("torch")
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
            return {"keys": list(checkpoint.keys())}
        except ImportError:
            return {"note": "torch not installed, metadata unavailable"}
```

### 8.3 entry-points 追加

```toml
[project.entry-points."jj.plugins"]
# ... 既存 ...
ml = "services.plugins.ml:register"
```

---

## 9. 実装計画

### Phase 1: 基盤設計（本PR）

- [x] ML対応仕様書の作成（本ドキュメント）
- [x] ロードマップへのM6マイルストーン追加
- [ ] MLプロジェクト用テストアセット設計

### Phase 2: コアパーサー実装

- [ ] MLScriptParser: Pythonスクリプトのimport静的解析
- [ ] MLDatasetParser: データセットファイル検出（csv/parquet/h5/npy）
- [ ] MLConfigParser: ML設定ファイル解析
- [ ] テスト: 各パーサーのユニットテスト

### Phase 3: フレームワーク固有パーサー

- [ ] TorchProjectParser: PyTorchチェックポイント解析
- [ ] SklearnProjectParser: scikit-learnモデル解析
- [ ] ExperimentRunParser: 実験ディレクトリ構造認識
- [ ] テスト: フレームワーク固有テスト

### Phase 4: 実験管理連携

- [ ] MLflowParser: MLflow tracking解析
- [ ] TensorBoardParser: TensorBoardイベント解析
- [ ] OptunaParser: Optunaスタディ解析
- [ ] テスト: 実験管理ツール連携テスト

### Phase 5: 最適化ループ・横断統合

- [ ] OptimizationLoopParser: CAE-ML最適化ループ検出
- [ ] 三層データフローグラフの構築
- [ ] ダッシュボードページ追加
- [ ] E2Eテスト

---

## 10. 設計上の懸念

### 10.1 スコープ管理

MLエコシステムは広大であり、全フレームワーク対応はスコープ外とする。PyTorch + scikit-learn を主軸とし、他フレームワーク（TensorFlow, JAX等）はプラグインで後から追加可能な設計にする。

### 10.2 ファイル内容解析のコスト

Pythonスクリプトのimport解析はAST解析を用いるが、大量の`.py`ファイルがある場合のパフォーマンスに注意が必要。ファイルサイズ上限やディレクトリスコープの制限を検討する。

### 10.3 CAEプロジェクトとの共存

MLプロジェクトのディレクトリ構造はCAEプロジェクトと異なるため、ソルバー検出ロジックが誤検出しないようにする。`.py`ファイルの存在だけでMLプロジェクトと判定せず、MLフレームワークのimportが確認できた場合のみ昇格させる。

### 10.4 モデルファイルの安全性

`.pt`/`.pkl`ファイルのデシリアライズはセキュリティリスクがある（pickle任意コード実行）。`torch.load(weights_only=True)` や `joblib.load` のサンドボックス化を検討する。本フェーズではファイルメタデータ（サイズ、拡張子）のみを扱い、デシリアライズは `requires_full=True` フラグで制御する。

---

## 11. 参考資料

- [コアデータモデル仕様書](01-core-data-model.md) — Node/Relation定義
- [パーサー仕様書](02-parser.md) — AbstractFileParser パターン
- [マルチソルバー仕様書](multi-solver.md) — プラグイン拡張パターン
- [CLAUDE.md](../../CLAUDE.md) — プラグイン拡張・CacheProviderパターン
