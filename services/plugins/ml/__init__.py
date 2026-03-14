"""MLプラグイン: 機械学習プロジェクトのデータフローグラフ化

機械学習タスク（PyTorch, scikit-learn）、実験管理、最適化タスクの
ファイル構造を解析し、グラフノード・リレーションとして構造化する。

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| MLDatasetParser | 55 | データセットファイル検出・メタデータ抽出 |
| MLConfigParser | 56 | ML設定ファイル解析（YAML/JSON/TOML） |
| MLScriptParser | 57 | Pythonスクリプトのimport解析・フレームワーク検出 |
| TorchCheckpointParser | 58 | PyTorchチェックポイント検出・メタデータ抽出 |
| SklearnModelParser | 59 | scikit-learnシリアライズ済みモデル検出 |
| ExperimentRunParser | 60 | 実験ディレクトリ構造認識・メトリクス抽出 |
| OptimizationRunParser | 62 | Optunaスタディ構造認識・メタデータ抽出 |
| MLDataFlowParser | 65 | スクリプト→データセット→モデル間リレーション構築 |
| SurrogateWorkflowDetector | 70 | CAE↔ML層間リレーション検出 |

## ファイル構造

- .py: 学習・評価スクリプト（import解析でフレームワーク検出）
- .pt/.pth/.ckpt: PyTorchモデルチェックポイント
- .pkl/.joblib: scikit-learnモデル
- .csv/.parquet/.h5/.npy: データセット
- .yaml/.json/.toml: 実験設定ファイル
- .db: Optuna最適化スタディ

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

from services.sdk.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_registered = False


def register() -> PluginManifest | None:
    """MLプラグインの全コンポーネントを登録する

    PluginManifest を返すことで PluginManager がメタデータを管理する。
    """
    global _registered
    if _registered:
        return None
    _registered = True

    # パーサーのインポート（自動登録が発動）
    # Phase 2-3: 基本MLパーサー (55-60)
    # Phase 4: 最適化・データフロー・サロゲートモデル (62-70)
    import services.parse.connectors.ml.checkpoint_parser
    import services.parse.connectors.ml.config_parser
    import services.parse.connectors.ml.dataflow_parser
    import services.parse.connectors.ml.dataset_parser
    import services.parse.connectors.ml.experiment_parser
    import services.parse.connectors.ml.model_parser
    import services.parse.connectors.ml.optimization_parser
    import services.parse.connectors.ml.script_parser
    import services.parse.connectors.ml.surrogate_detector

    # importの副作用（__init_subclass__）でパーサーが登録される
    del services

    logger.debug("MLプラグインを登録完了")

    return PluginManifest(
        name="ml",
        version="0.2.0",
        description="機械学習プロジェクトのデータフローグラフ化",
        parsers=[
            "services.parse.connectors.ml.dataset_parser",
            "services.parse.connectors.ml.config_parser",
            "services.parse.connectors.ml.script_parser",
            "services.parse.connectors.ml.checkpoint_parser",
            "services.parse.connectors.ml.model_parser",
            "services.parse.connectors.ml.experiment_parser",
            "services.parse.connectors.ml.optimization_parser",
            "services.parse.connectors.ml.dataflow_parser",
            "services.parse.connectors.ml.surrogate_detector",
        ],
    )


# モジュールインポート時に自動登録
register()
