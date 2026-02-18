[← README.md](../../README.md)

# サロゲートモデルフレームワーク仕様書

**日付**: 2026-02-18
**関連マイルストーン**: M6（ML/実験/最適化タスク対応）
**前提仕様**: [ml-task-roadmap.md](ml-task-roadmap.md)

---

## 1. 目的

CAEシミュレーション（Abaqus等）の結果を学習データとして用い、PyTorch等でサロゲートモデルを構築し、Optuna等で最適化ループを回すワークフロー全体を、jjのグラフ構造で表現・追跡するフレームワークを構築する。

既存のMLパーサー6種（Phase 2-3で実装済み）を基盤とし、以下の3パーサーを追加してワークフローを完成させる:

1. **OptimizationRunParser**: Optuna study構造認識
2. **MLDataFlowParser**: スクリプト→データセット→モデル間のリレーション自動構築
3. **SurrogateWorkflowDetector**: CAE↔ML層間リレーション検出

---

## 2. 対象ワークフロー

### 2.1 サロゲートモデル構築の典型フロー

```
[Abaqus入力(.inp)] × N件
    ↓ (CAEソルバー実行)
[Abaqus結果(.odb/.dat)] × N件
    ↓ (データ抽出スクリプト)
[学習データセット(.csv/.npy)]
    ↓ (学習スクリプト)
[PyTorchサロゲートモデル(.pt)]
    ↓ (最適化ループ)
[Optunaスタディ(.db)] → 最適パラメータ
    ↓ (検証)
[追加CAEシミュレーション] → 予測精度確認
```

### 2.2 プロジェクトディレクトリ構造例

```
surrogate_project/
├── cae/                         # CAEシミュレーション
│   ├── go_idx1_v1.inp           # Abaqus入力
│   ├── go_idx1_v1.odb           # Abaqus結果
│   ├── go_idx2_v1.inp
│   └── go_idx2_v1.odb
├── data/                        # 学習データ
│   ├── extract_data.py          # データ抽出スクリプト
│   ├── training_data.csv        # 抽出済み学習データ
│   └── features.npy             # 特徴量
├── ml/                          # サロゲートモデル
│   ├── configs/
│   │   └── surrogate_config.yaml
│   ├── src/
│   │   ├── model.py             # モデル定義
│   │   └── train.py             # 学習スクリプト
│   ├── checkpoints/
│   │   ├── best_model.pt
│   │   └── epoch_50.pt
│   └── experiments/
│       ├── exp_001/
│       │   └── metrics.json
│       └── exp_002/
│           └── metrics.json
├── optimization/                # 最適化
│   ├── optuna_study.db          # Optunaスタディ
│   ├── optuna_config.yaml       # 最適化設定
│   ├── trial_history.csv        # 試行履歴
│   └── optimize.py              # 最適化スクリプト
└── reports/
    └── results.json
```

---

## 3. 新規パーサー設計

### 3.1 OptimizationRunParser（priority: 62）

Optunaスタディ構造を認識し、最適化関連ファイルをグラフに統合する。

**検出対象**:
- `.db` ファイル（Optuna SQLiteスタディ）
- 最適化設定ファイル（`n_trials`, `objective`, `search_space`キーを含むYAML/JSON）
- 試行履歴ファイル（`trial_history.csv`, `pareto_front.csv`等）
- 最適化スクリプト（`optuna` importを含む `.py`）

**ノードタイプ昇格**:
| 元タイプ | 昇格先 | 条件 |
|---------|--------|------|
| `file` | `optimization_study` | `.db` ファイル + optimization/optuna関連パス |
| `file` | `optimization_config` | 最適化キーワードを含む設定ファイル |
| `dataset` | `trial_history` | trial/pareto関連名のCSV |

**付与プロパティ**:
- `ml_optimization`: True
- `optimization_framework`: "optuna" / "botorch" / "scipy"
- `study_name`: スタディ名（ファイル名から推定）
- `n_trials`: 試行数（設定ファイルから抽出）
- `objective`: 目的関数名（設定ファイルから抽出）
- `search_space`: 探索空間定義（設定ファイルから抽出）

**依存**: コア依存のみ（json, re, pathlib, sqlite3標準ライブラリ）。Optunaライブラリは不要。

### 3.2 MLDataFlowParser（priority: 65）

既にパース済みのML関連ノード間にリレーションを構築する。

**構築するリレーション**:

| ラベル | 始点タイプ → 終点タイプ | 検出ロジック |
|--------|----------------------|------------|
| `trains_with` | `training_script` → `dataset` | 同一プロジェクト内の学習スクリプトとデータセット |
| `produces_model` | `training_script` → `model_checkpoint` | 同一実験ディレクトリ内、または同一プロジェクト内 |
| `configured_by` | `training_script` → `experiment_config` | 同一ディレクトリまたは親子関係 |
| `evaluated_on` | `model_checkpoint` → `dataset` | 評価スクリプトとデータセットの共存 |
| `logs_to` | `experiment_metrics` → `model_checkpoint` | 同一experiment_id |

**マッチングロジック**:
1. **同一実験ディレクトリ**: `experiment_id` プロパティが一致するノード間
2. **同一親ディレクトリ**: パスの親ディレクトリが一致（configとscript等）
3. **プロジェクトスコープ**: 同一プロジェクト内で型が条件に合致（フォールバック）

**重複防止**: `(node1_id, node2_id, label)` の組み合わせを追跡し重複リレーションを排除。

### 3.3 SurrogateWorkflowDetector（priority: 70）

CAEタスク（Layer 1）とMLタスク（Layer 2）を跨ぐリレーションを検出・構築する。

**構築するリレーション**:

| ラベル | 始点 → 終点 | 検出ロジック |
|--------|-----------|------------|
| `extracted_from` | `dataset` → CAE結果ノード | データセットパスがCAE結果と同一プロジェクトに共存 |
| `surrogate_of` | `model_checkpoint` → CAE入力テンプレート | サロゲートモデルとCAE入力の共存 |
| `optimizes` | `optimization_study` → `model_checkpoint` | 最適化スタディとモデルの共存 |
| `uses_objective` | `optimization_study` → `training_script` | 最適化設定が参照するスクリプト |

**CAEノード判定**:
- `type` が `calculation_input`, `result`, `mesh` のいずれか
- または `format` が CAE固有拡張子（`.inp`, `.odb`, `.dat`, `.sta`）

**Layer分類ロジック**:
```
Layer 1 (CAE):   type ∈ {calculation_input, result, mesh, output, asset}
Layer 2 (ML):    type ∈ {dataset, model_checkpoint, training_script,
                         experiment_config, experiment_metrics, serialized_model}
Layer 3 (Optim): type ∈ {optimization_study, optimization_config, trial_history}
```

---

## 4. Neo4jスキーマ拡張

### 4.1 新規リレーションタイプ

`shared/neo4j_schema.py` に以下を追加:

```python
class RelType:
    # ML データフローリレーション
    TRAINS_WITH = "TRAINS_WITH"
    PRODUCES_MODEL = "PRODUCES_MODEL"
    CONFIGURED_BY = "CONFIGURED_BY"
    EVALUATED_ON = "EVALUATED_ON"
    LOGS_TO = "LOGS_TO"

    # サロゲートモデル/層間リレーション
    EXTRACTED_FROM = "EXTRACTED_FROM"
    SURROGATE_OF = "SURROGATE_OF"
    OPTIMIZES = "OPTIMIZES"
    USES_OBJECTIVE = "USES_OBJECTIVE"
```

### 4.2 新規ノードタイプマッピング

```python
TYPE_TO_LABEL = {
    # ML タイプ（既存パーサーが生成）
    "dataset": NodeLabel.JJ_FILE,
    "model_checkpoint": NodeLabel.JJ_FILE,
    "training_script": NodeLabel.JJ_FILE,
    "experiment_config": NodeLabel.JJ_FILE,
    "experiment_metrics": NodeLabel.JJ_FILE,
    "serialized_model": NodeLabel.JJ_FILE,

    # 最適化タイプ（新規）
    "optimization_study": NodeLabel.JJ_FILE,
    "optimization_config": NodeLabel.JJ_FILE,
    "trial_history": NodeLabel.JJ_FILE,
}
```

---

## 5. プラグイン分離設計

### 5.1 原則

- 全パーサーは `AbstractFileParser` のサブクラスとして `__init_subclass__` で自動登録
- パーサーのコードは `services/parse/connectors/ml/` に配置
- プラグインエントリーポイント `services/plugins/ml/__init__.py` でimport集約
- コア層（`services/parse/base.py`）への変更は不要

### 5.2 ファイル配置

```
services/parse/connectors/ml/
├── dataset_parser.py           # [既存] MLDatasetParser (55)
├── config_parser.py            # [既存] MLConfigParser (56)
├── script_parser.py            # [既存] MLScriptParser (57)
├── checkpoint_parser.py        # [既存] TorchCheckpointParser (58)
├── model_parser.py             # [既存] SklearnModelParser (59)
├── experiment_parser.py        # [既存] ExperimentRunParser (60)
├── optimization_parser.py      # [新規] OptimizationRunParser (62)
├── dataflow_parser.py          # [新規] MLDataFlowParser (65)
└── surrogate_detector.py       # [新規] SurrogateWorkflowDetector (70)
```

### 5.3 汎用化のポイント

1. **ソルバー非依存**: パーサーはAbaqus固有のロジックを持たない。CAEノードはtype/formatで判定し、特定のソルバーに結合しない
2. **設定駆動**: 将来的にはsolverプロファイルで「どのCAE結果タイプからデータ抽出が可能か」を設定可能にする
3. **プラグイン単位**: `services/plugins/ml/` は1つのentry-pointとして登録済み。他ソルバーのプラグインと同様のパターン

---

## 6. テスト計画

### 6.1 テストアセット拡張

`shared/tests/test_asset_ml/` に最適化関連ファイルを追加:

```
shared/tests/test_asset_ml/
├── optimization/                        # [新規]
│   ├── optuna_study.db                  # Optuna SQLite DB（空スキーマ）
│   ├── optuna_config.yaml               # 最適化設定
│   ├── trial_history.csv                # 試行履歴
│   └── optimize.py                      # 最適化スクリプト（optuna import）
└── (既存ファイルはそのまま)
```

### 6.2 ユニットテスト

| テストクラス | テスト数 | 検証内容 |
|-------------|---------|---------|
| TestOptimizationRunParser | 8-10 | .db昇格、設定解析、試行履歴検出、フレームワーク判定 |
| TestMLDataFlowParser | 8-10 | trains_with/produces_model/configured_by等のリレーション構築 |
| TestSurrogateWorkflowDetector | 6-8 | extracted_from/surrogate_of/optimizesの層間リレーション |

### 6.3 E2Eテスト

`test_asset_ml` 全体をパースし、以下を検証:
- 全MLパーサーが正しい順序で動作
- リレーションの循環がないこと
- ノードタイプの昇格が正しいこと
- 重複リレーションがないこと

---

## 7. 実装順序

| ステップ | 内容 | コミット単位 |
|---------|------|------------|
| 1 | 本仕様書作成 | docs: サロゲートモデルフレームワーク仕様書 |
| 2 | OptimizationRunParser + テスト | feat: OptimizationRunParser実装 |
| 3 | MLDataFlowParser + テスト | feat: MLDataFlowParser実装 |
| 4 | SurrogateWorkflowDetector + テストアセット + E2Eテスト | feat: SurrogateWorkflowDetector実装 |
| 5 | Neo4jスキーマ更新 + lint | chore: Neo4jスキーマML拡張 |
| 6 | status-027作成・push | docs: status-027 |

---

## 8. 設計上の懸念

1. **MLDataFlowParserのマッチング精度**: 同一プロジェクト内の型マッチングだけでは、無関係なデータセットとスクリプト間に誤ったリレーションが生成される可能性あり。experiment_idやディレクトリ近接性で絞り込む
2. **CAEノードの判定**: 既存パーサーがCAEノードに付与するtype/formatに依存。新規ソルバープラグインが追加されても動作するよう、判定を汎用的に設計する
3. **Optuna DBの読み込み**: sqlite3標準ライブラリでスキーマを検証するが、DBファイルが破損している場合のエラーハンドリングが必要
4. **パフォーマンス**: MLDataFlowParser/SurrogateWorkflowDetectorはO(n²)の組み合わせ検索を行う。大規模プロジェクトではインデックス化が必要になる可能性
