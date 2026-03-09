[← README.md](README.md)

# ML Usage Guide — 機械学習プロジェクト向け使用マニュアル

> PyTorch / scikit-learn / Optuna を用いた機械学習プロジェクト、および
> CAE-ML連携プロジェクトを jj で管理するための実践的なガイド。

---

## 目次

1. [前提条件](#1-前提条件)
2. [MLプロジェクトの典型構成](#2-mlプロジェクトの典型構成)
3. [セットアップ](#3-セットアップ)
4. [プロジェクトのパース](#4-プロジェクトのパース)
5. [MLノードタイプの確認](#5-mlノードタイプの確認)
6. [ダッシュボード](#6-ダッシュボード)
7. [三層データフロー](#7-三層データフロー)
8. [CAE-ML連携プロジェクト](#8-cae-ml連携プロジェクト)
9. [エクスポート](#9-エクスポート)
10. [設定のカスタマイズ](#10-設定のカスタマイズ)
11. [実践シナリオ](#11-実践シナリオ)
12. [トラブルシューティング](#12-トラブルシューティング)

---

## 1. 前提条件

### インストール

```bash
# ML機能 + ダッシュボードを使う場合
pip install -e ".[dashboard,dev]"
```

コア機能（パーサー群）はtorch / sklearnに依存しない。ファイル構造の認識と
import文の静的解析のみで動作する。

### 確認

```bash
# MLパーサーが正しく読み込まれるか確認
python -c "from services.parse.connectors.ml.dataset_parser import MLDatasetParser; print('OK')"
```

---

## 2. MLプロジェクトの典型構成

### 推奨ディレクトリ構成

```
ml-experiment-project/
├── configs/                        # 実験設定
│   ├── train_config.yaml           # 学習ハイパーパラメータ
│   └── model_config.yaml           # モデルアーキテクチャ定義
├── data/                           # データセット
│   ├── raw/
│   │   └── dataset_v1.csv          # → type: dataset
│   ├── processed/
│   │   ├── train.npy               # → type: dataset (split: train)
│   │   ├── val.npy                 # → type: dataset (split: val)
│   │   └── test.npy                # → type: dataset (split: test)
│   └── features/
│       └── features_v1.h5          # → type: dataset
├── src/
│   ├── train.py                    # → type: training_script
│   ├── evaluate.py                 # → role: evaluation
│   └── preprocess.py               # → role: preprocessing
├── experiments/
│   ├── exp_001/                    # 実験1
│   │   ├── checkpoints/
│   │   │   ├── epoch_10.pt         # → type: model_checkpoint
│   │   │   └── best_model.pt       # → type: model_checkpoint (is_best)
│   │   └── metrics.json            # → type: experiment_metrics
│   └── exp_002/
│       ├── checkpoints/
│       │   └── best_model.pt
│       └── metrics.json
├── models/
│   └── classifier.pkl              # → type: serialized_model
└── optimization/
    ├── optim_config.yaml           # → type: optimization_config
    ├── study.db                    # → type: optimization_study
    └── trial_history.csv           # → type: trial_history
```

### 自動検出されるファイル形式

| 拡張子 | 検出されるノードタイプ | パーサー |
|--------|----------------------|---------|
| `.csv`, `.parquet`, `.h5`, `.hdf5`, `.npy`, `.npz` | `dataset` | MLDatasetParser |
| `.yaml`, `.json`, `.toml` (ML設定) | `experiment_config` | MLConfigParser |
| `.py` (ML import検出) | `training_script` | MLScriptParser |
| `.pt`, `.pth`, `.ckpt` | `model_checkpoint` | TorchCheckpointParser |
| `.pkl`, `.joblib` | `serialized_model` | SklearnModelParser |
| `metrics.json`, `results.json` | `experiment_metrics` | ExperimentRunParser |
| `.db` (Optunaスキーマ) | `optimization_study` | OptimizationRunParser |

---

## 3. セットアップ

```bash
cd ml-experiment-project/

# jj初期化
jj init

# config.yamlの確認
cat .j2/config/config.yaml
```

### 推奨config設定

```yaml
# .j2/config/config.yaml
file-relations:
  input-extensions: [".py", ".yaml", ".json", ".toml"]
  result-extensions: [".pt", ".pth", ".ckpt", ".pkl", ".joblib", ".csv", ".json"]
  asset-extensions: [".h5", ".hdf5", ".npy", ".npz", ".parquet"]

ignore:
  - ".git"
  - "__pycache__"
  - ".venv"
  - "node_modules"
  - "*.pyc"
  - ".ipynb_checkpoints"
```

---

## 4. プロジェクトのパース

```bash
# 全ファイルをパース
jj parse

# 結果確認
jj ls
```

パース結果の例:

```
$ jj ls
Type                 Count  Examples
─────────────────────────────────────
dataset              5      train.csv, val.npy, test.npy
training_script      2      train.py, evaluate.py
model_checkpoint     4      best_model.pt, epoch_10.pt
serialized_model     1      classifier.pkl
experiment_config    2      train_config.yaml, model_config.yaml
experiment_metrics   2      metrics.json (exp_001, exp_002)
optimization_study   1      study.db
```

---

## 5. MLノードタイプの確認

### ノードプロパティの詳細

各MLノードタイプが持つ主要プロパティ:

#### dataset
| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `ml_dataset` | MLデータセットフラグ | `true` |
| `split` | データ分割（ファイル名推定） | `train`, `val`, `test` |
| `n_rows` | 行数（CSVのみ） | `1000` |
| `n_columns` | 列数（CSVのみ） | `10` |
| `columns` | カラム名リスト（CSVのみ） | `["x1", "x2", "y"]` |

#### training_script
| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `ml_frameworks` | 検出されたフレームワーク | `["pytorch", "optuna"]` |
| `ml_role` | スクリプトの役割 | `training`, `evaluation` |

#### model_checkpoint
| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `ml_checkpoint` | チェックポイントフラグ | `true` |
| `epoch` | エポック番号 | `50` |
| `step` | ステップ番号 | `10000` |
| `is_best` | ベストモデルフラグ | `true` |
| `file_size_bytes` | ファイルサイズ | `52428800` |

#### experiment_metrics
| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `experiment_id` | 実験ID | `"001"` |
| `experiment_dir` | 実験ディレクトリ名 | `"exp_001"` |
| `ml_key_metrics` | キーメトリクス辞書 | `{"best_val_accuracy": 0.95}` |

#### optimization_study
| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `optimization_framework` | 最適化フレームワーク | `"optuna"` |
| `study_name` | スタディ名 | `"surrogate_opt"` |
| `n_trials_completed` | 完了試行数 | `100` |
| `direction` | 最適化方向 | `"minimize"` |

---

## 6. ダッシュボード

```bash
jj dashboard
```

MLノードが存在する場合、サイドバーに以下のページが自動追加される:

### ML概要ページ

サマリーメトリクス（各ノードタイプの件数）と6つのタブで構成:

1. **実験メトリクス** — 実験ID、キーメトリクス（accuracy, loss等）の一覧
2. **データセット** — 形式、分割、行数/列数、カラム名の一覧
3. **モデル** — チェックポイント/シリアライズモデル、エポック、ファイルサイズ
4. **スクリプト** — フレームワーク、役割の一覧
5. **最適化** — スタディ情報、試行数、方向
6. **リレーション** — ML関連リレーション（trains_with, produces_model等）の一覧

### MLデータフローページ

三層データフロー図を表示:
- **Layer 1（CAE）**: 青色 — CAE入力/結果/メッシュ
- **Layer 2（ML/実験）**: 緑色 — データセット/モデル/スクリプト
- **Layer 3（最適化）**: 橙色 — スタディ/設定/試行履歴

`streamlit-agraph` がインストールされている場合はインタラクティブグラフで表示。
未インストールの場合はテーブル形式にフォールバック。

```bash
# agraphを使いたい場合
pip install streamlit-agraph
```

---

## 7. 三層データフロー

jjは機械学習プロジェクトのデータフローを3つの層で整理する:

```
┌──────────────────────────────────────────────────┐
│  Layer 3: 最適化タスク（橙色）                     │
│  optimization_study → optimizes → model           │
│  optimization_config, trial_history               │
├──────────────────────────────────────────────────┤
│  Layer 2: ML/実験タスク（緑色）                    │
│  dataset → trains_with → training_script          │
│  training_script → produces_model → checkpoint    │
│  experiment_config, experiment_metrics             │
├──────────────────────────────────────────────────┤
│  Layer 1: CAEタスク（青色）                        │
│  calculation_input → solver → result              │
│  mesh, output, asset                              │
└──────────────────────────────────────────────────┘
```

### 自動検出されるリレーション

#### Layer 2内リレーション（MLDataFlowParser, priority 65）
| リレーション | 始点 → 終点 | 検出条件 |
|-------------|-----------|---------|
| `trains_with` | training_script → dataset | 同一実験ID or 近接ディレクトリ |
| `produces_model` | training_script → model_checkpoint | 同一実験ID or 近接ディレクトリ |
| `configured_by` | training_script → experiment_config | 同一実験ID or 近接ディレクトリ |
| `logs_to` | experiment_metrics → model_checkpoint | 同一実験ID |

#### 層間リレーション（SurrogateWorkflowDetector, priority 70）
| リレーション | 始点層 → 終点層 | 検出条件 |
|-------------|----------------|---------|
| `extracted_from` | L2(dataset) → L1(result) | 同一プロジェクトルート |
| `surrogate_of` | L2(model) → L1(input) | 同一プロジェクトルート |
| `optimizes` | L3(study) → L2(model) | 同一プロジェクトルート |
| `uses_objective` | L3(study) → L2(script) | 同一プロジェクトルート |

---

## 8. CAE-ML連携プロジェクト

サロゲートモデルベースの最適化など、CAEとMLを組み合わせたプロジェクト:

### 推奨ディレクトリ構成

```
cae-ml-optimization/
├── cae/                          # CAE解析（Layer 1）
│   ├── go_idx1_v1/
│   │   ├── go_idx1_v1.inp
│   │   └── go_idx1_v1.odb
│   ├── go_idx2_v1/
│   │   ├── go_idx2_v1.inp
│   │   └── go_idx2_v1.odb
│   └── go_idx3_v1/
│       ├── go_idx3_v1.inp
│       └── go_idx3_v1.odb
├── ml/                           # サロゲートモデル（Layer 2）
│   ├── data/
│   │   └── training_data.csv     # CAE結果から抽出
│   ├── src/
│   │   └── surrogate.py
│   └── models/
│       └── surrogate_v1.pt
└── optimization/                 # 最適化ループ（Layer 3）
    ├── optim_config.yaml
    ├── study.db
    └── trial_history.csv
```

### ワークフロー

```bash
# 1. CAE解析結果を含むプロジェクトを初期化
cd cae-ml-optimization/
jj init

# 2. 全ファイルをパース（CAE + ML + 最適化を一括認識）
jj parse

# 3. グラフ確認（三層構造が自動構築される）
jj ls

# 4. ダッシュボードで三層データフローを確認
jj dashboard
# → サイドバーの「MLデータフロー」ページで可視化
```

パース結果の例:
```
$ jj ls
Type                  Count  Examples
─────────────────────────────────────────
calculation_input     3      go_idx1_v1.inp, go_idx2_v1.inp
result                3      go_idx1_v1.odb, go_idx2_v1.odb
dataset               1      training_data.csv
training_script       1      surrogate.py
model_checkpoint      1      surrogate_v1.pt
optimization_study    1      study.db
optimization_config   1      optim_config.yaml
trial_history         1      trial_history.csv

Relations:
  extracted_from:  training_data.csv → go_idx1_v1.odb (Layer 2→1)
  surrogate_of:    surrogate_v1.pt → go_idx1_v1.inp (Layer 2→1)
  optimizes:       study.db → surrogate_v1.pt (Layer 3→2)
```

---

## 9. エクスポート

### CSVエクスポート

```bash
# 全ノードをCSV出力
jj export csv

# ML関連ノードのフィルタリングはダッシュボードのActiveフィルタで
```

### HTMLエクスポート

ダッシュボードの「保存済みビュー」ページからHTMLエクスポートが可能:

1. ML概要やデータフローのビューを保存
2. 「HTMLエクスポート」ボタンでスタンドアロンHTMLを生成
3. ブラウザで閲覧・チーム共有が可能

### Python API

```python
import jj

# プロジェクトグラフをロード
graph = jj.load()

# ML関連ノードを取得
ml_nodes = [n for n in graph.nodes if n.type in {
    "dataset", "model_checkpoint", "training_script",
    "experiment_metrics", "optimization_study"
}]

# メトリクスの比較
for node in graph.nodes:
    metrics = node.properties.get("ml_key_metrics", {})
    if metrics:
        print(f"{node.name}: {metrics}")
```

---

## 10. 設定のカスタマイズ

### vocabによる表示名変換

```yaml
# .j2/config/config.yaml
vocab:
  ml_frameworks: "フレームワーク"
  ml_role: "役割"
  ml_key_metrics: "キーメトリクス"
  experiment_id: "実験ID"
  n_rows: "行数"
  n_columns: "列数"
  split: "データ分割"
  epoch: "エポック"
  is_best: "ベスト"
  file_size_bytes: "ファイルサイズ"
```

### ignoreパターン

大量のチェックポイントがある場合:

```yaml
ignore:
  - "**/__pycache__"
  - "**/wandb/run-*"        # W&Bの一時ファイル
  - "**/lightning_logs/**"  # PyTorch Lightning自動ログ
  - "**/epoch_*.pt"         # 中間チェックポイントを除外
```

---

## 11. 実践シナリオ

### シナリオ1: 実験結果の比較

```bash
# 複数実験のメトリクスを一覧比較
jj dashboard
# → ML概要 → 実験メトリクスタブ
# → best_val_accuracy でソートして最良の実験を特定
```

### シナリオ2: モデルレジストリ

```bash
# 全チェックポイントのエポック・サイズ・ベスト判定を確認
jj dashboard
# → ML概要 → モデルタブ
# → is_best=✓ のモデルを確認
```

### シナリオ3: サロゲートモデル構築のトレーサビリティ

```bash
# CAE→ML→最適化の三層データフローを確認
jj dashboard
# → MLデータフロー
# → 層間リレーション（extracted_from, surrogate_of, optimizes）を確認
# → どのCAE結果がどのデータセットに変換され、
#   どのモデルの学習に使われたかを追跡
```

### シナリオ4: Prefect / ジョブ管理との連携

```bash
# jj r でPython学習スクリプトを実行（Runとして記録）
jj r python src/train.py --epochs 100

# 結果確認
jj ls --type model_checkpoint
```

Prefect連携の詳細は [Prefect Integration Guide](prefect-integration-guide.md) を参照。

---

## 12. トラブルシューティング

### MLノードが検出されない

1. **拡張子の確認**: `jj ls` でファイルが認識されているか確認
2. **import解析の確認**: `.py`ファイルに`import torch`等のML importがあるか
3. **ignoreパターンの確認**: `.j2/config/config.yaml`のignoreで除外されていないか

### experiment_metricsが検出されない

- メトリクスファイル名が `metrics.json`, `results.json`, `scores.json` のいずれかであること
- JSON形式で、トップレベルが辞書であること
- 実験ディレクトリ（`exp_001/`, `run_001/` 等）配下にあること

### データフローリレーションが構築されない

- MLノードが最低2種類以上（例: script + dataset）存在すること
- ファイルがディレクトリ配下に配置されていること（ルート直下は対象外）
- 層間リレーションは、CAE/MLノードが同一プロジェクト内に共存する場合のみ構築

### ダッシュボードにMLページが表示されない

- ML関連ノードが1つ以上存在すること（`jj ls` で確認）
- `jj parse` を実行してグラフを更新すること

---

## 関連ドキュメント

- [ML対応仕様書](specs/ml-task-roadmap.md) — 詳細な技術仕様
- [Abaqus Usage Guide](abaqus-usage-guide.md) — CAE側のガイド
- [Prefect Integration Guide](prefect-integration-guide.md) — ジョブ管理連携
- [Migration Guide](migration-guide.md) — バージョンアップ移行手順
