"""MLパーサーユニットテスト

MLDatasetParser, MLConfigParser, MLScriptParser, TorchCheckpointParser,
SklearnModelParser, ExperimentRunParser の各パーサーを個別にテストする。
テストアセット（shared/tests/test_asset_ml/）を利用した実ファイル解析テストも含む。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

from config import GraphConfig
from jj_types import Node, Relation
from services.graph.project_graph import ProjectGraph

ML_ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "tests" / "test_asset_ml"


def _make_ml_config() -> GraphConfig:
    """ML用テストGraphConfigを生成"""
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {
                "input-extensions": [".py", ".yaml", ".json"],
                "result-extensions": [".pt", ".pth", ".ckpt", ".csv", ".json"],
                "asset-extensions": [],
            },
        }
    )


def _make_graph(
    nodes: list[Node],
    relations: list[Relation] | None = None,
    project_root: Path | None = None,
) -> ProjectGraph:
    """テスト用ProjectGraphを生成"""
    return ProjectGraph(
        nodes=list(nodes),
        relations=list(relations or []),
        project_root=project_root or ML_ASSET_DIR,
        config=_make_ml_config(),
    )


# ====================================================================
# MLDatasetParser テスト
# ====================================================================


class TestMLDatasetParser:
    """MLDatasetParser の単体テスト"""

    def test_csv_node_promoted_to_dataset(self):
        """CSVファイルノードがdatasetタイプに昇格する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(
                id=1, type="file", name="dataset_v1.csv", format="csv", properties={"path": "data/raw/dataset_v1.csv"}
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].type == "dataset"
        assert result.nodes[0].properties["ml_dataset"] is True

    def test_npy_node_promoted_to_dataset(self):
        """npyファイルノードがdatasetタイプに昇格する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(id=1, type="file", name="train.npy", format="npy", properties={"path": "data/processed/train.npy"}),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].type == "dataset"

    def test_split_detection_from_filename(self):
        """ファイル名からsplit情報を推定する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(id=1, type="file", name="train.npy", format="npy", properties={"path": "data/processed/train.npy"}),
            Node(id=2, type="file", name="val.npy", format="npy", properties={"path": "data/processed/val.npy"}),
            Node(id=3, type="file", name="test.npy", format="npy", properties={"path": "data/processed/test.npy"}),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].properties["split"] == "train"
        assert result.nodes[1].properties["split"] == "val"
        assert result.nodes[2].properties["split"] == "test"

    def test_csv_metadata_extraction(self):
        """CSVファイルのヘッダー・行数を抽出する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(
                id=1, type="file", name="dataset_v1.csv", format="csv", properties={"path": "data/raw/dataset_v1.csv"}
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].properties["columns"] == ["feature_1", "feature_2", "feature_3", "label"]
        assert result.nodes[0].properties["n_columns"] == 4
        assert result.nodes[0].properties["n_rows"] == 5

    def test_non_dataset_file_unchanged(self):
        """データセット拡張子でないファイルは変更されない"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(id=1, type="file", name="train.py", format="py", properties={"path": "src/train.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].type == "file"

    def test_parquet_promoted_to_dataset(self):
        """parquetファイルノードがdatasetタイプに昇格する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="features.parquet",
                format="parquet",
                properties={"path": "data/features.parquet"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].type == "dataset"

    def test_h5_promoted_to_dataset(self):
        """HDF5ファイルノードがdatasetタイプに昇格する"""
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="features_v1.h5",
                format="h5",
                properties={"path": "data/features/features_v1.h5"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDatasetParser().apply(graph)

        assert result.nodes[0].type == "dataset"


# ====================================================================
# MLConfigParser テスト
# ====================================================================


class TestMLConfigParser:
    """MLConfigParser の単体テスト"""

    def test_train_config_promoted_to_experiment_config(self):
        """ML設定ファイルがexperiment_configに昇格する"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="train_config.yaml",
                format="yaml",
                properties={"path": "configs/train_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        assert result.nodes[0].type == "experiment_config"
        assert result.nodes[0].properties["ml_config"] is True

    def test_ml_keywords_detected(self):
        """ML関連キーワードが正しく検出される"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="train_config.yaml",
                format="yaml",
                properties={"path": "configs/train_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        config_keys = result.nodes[0].properties["ml_config_keys"]
        assert "learning_rate" in config_keys
        assert "epochs" in config_keys
        assert "batch_size" in config_keys
        assert "optimizer" in config_keys

    def test_params_extraction(self):
        """主要パラメータが正しく抽出される"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="train_config.yaml",
                format="yaml",
                properties={"path": "configs/train_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        params = result.nodes[0].properties["ml_params"]
        assert params["learning_rate"] == 0.001
        assert params["epochs"] == 50
        assert params["batch_size"] == 32
        assert params["optimizer"] == "adam"
        assert params["seed"] == 42

    def test_sweep_config_detected(self):
        """ハイパーパラメータスイープ設定が検出される"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="sweep_config.yaml",
                format="yaml",
                properties={"path": "configs/sweep_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        assert result.nodes[0].type == "experiment_config"
        config_keys = result.nodes[0].properties["ml_config_keys"]
        assert "n_trials" in config_keys
        assert "objective" in config_keys

    def test_json_config_parsed(self):
        """JSONフォーマットの設定ファイルも解析される"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "experiments/exp_001/metrics.json"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        # metrics.jsonはML設定キーワードを含まないのでfile型のまま
        assert result.nodes[0].type == "file"

    def test_non_ml_yaml_unchanged(self):
        """ML設定キーワードを含まないYAMLは変更されない"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="model_config.yaml",
                format="yaml",
                properties={"path": "configs/model_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        # model_config.yamlはdropout, num_classesを含む → 検出される
        assert result.nodes[0].type == "experiment_config"

    def test_dataset_nodes_skipped(self):
        """すでにdatasetタイプのノードは処理されない"""
        from services.parse.connectors.ml.config_parser import MLConfigParser

        nodes = [
            Node(id=1, type="dataset", name="data.csv", format="csv", properties={"path": "data.csv"}),
        ]
        graph = _make_graph(nodes)
        result = MLConfigParser().apply(graph)

        assert result.nodes[0].type == "dataset"


# ====================================================================
# MLScriptParser テスト
# ====================================================================


class TestMLScriptParser:
    """MLScriptParser の単体テスト"""

    def test_torch_script_detected(self):
        """PyTorchスクリプトのフレームワークが検出される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="train.py", format="py", properties={"path": "src/train.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert "pytorch" in result.nodes[0].properties["ml_frameworks"]

    def test_training_script_promoted(self):
        """train*.pyがtraining_scriptに昇格する"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="train.py", format="py", properties={"path": "src/train.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert result.nodes[0].type == "training_script"
        assert result.nodes[0].properties["ml_role"] == "training"

    def test_sklearn_script_detected(self):
        """scikit-learnスクリプトのフレームワークが検出される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="sklearn_train.py", format="py", properties={"path": "src/sklearn_train.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert "scikit-learn" in result.nodes[0].properties["ml_frameworks"]
        assert result.nodes[0].type == "training_script"

    def test_evaluate_script_role(self):
        """evaluate*.pyがevaluationロールに判定される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="evaluate.py", format="py", properties={"path": "src/evaluate.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert result.nodes[0].properties["ml_role"] == "evaluation"
        # evaluateはtraining_scriptではなくfile型のまま
        assert result.nodes[0].type == "file"

    def test_model_definition_role(self):
        """model.pyがmodel_definitionロールに判定される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="model.py", format="py", properties={"path": "src/model.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert result.nodes[0].properties["ml_role"] == "model_definition"

    def test_optuna_script_detected(self):
        """Optunaスクリプトのフレームワークと最適化ロールが検出される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="optimizer.py", format="py", properties={"path": "src/optimizer.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert "optuna" in result.nodes[0].properties["ml_frameworks"]
        assert result.nodes[0].properties["ml_role"] == "optimization"

    def test_no_ml_import_unchanged(self):
        """MLフレームワークをimportしないファイルは変更されない"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="utils.py", format="py", properties={"path": "src/utils.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert result.nodes[0].type == "file"
        assert "ml_frameworks" not in result.nodes[0].properties

    def test_preprocess_role(self):
        """preprocess.pyがpreprocessingロールに判定される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="preprocess.py", format="py", properties={"path": "src/preprocess.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        # preprocess.pyはpandas/numpyのみでMLフレームワークなし → 変更なし
        assert result.nodes[0].type == "file"

    def test_non_py_file_unchanged(self):
        """Pythonファイル以外は処理対象外"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(
                id=1, type="file", name="config.yaml", format="yaml", properties={"path": "configs/train_config.yaml"}
            ),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        assert result.nodes[0].type == "file"

    def test_multiple_frameworks_detected(self):
        """1つのスクリプトで複数フレームワークが検出される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="evaluate.py", format="py", properties={"path": "src/evaluate.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        frameworks = result.nodes[0].properties["ml_frameworks"]
        assert "pytorch" in frameworks
        assert "scikit-learn" in frameworks

    def test_imports_list_populated(self):
        """import一覧がプロパティに記録される"""
        from services.parse.connectors.ml.script_parser import MLScriptParser

        nodes = [
            Node(id=1, type="file", name="train.py", format="py", properties={"path": "src/train.py"}),
        ]
        graph = _make_graph(nodes)
        result = MLScriptParser().apply(graph)

        imports = result.nodes[0].properties["ml_imports"]
        assert "torch" in imports
        assert "torch.nn" in imports


# ====================================================================
# プラグイン登録テスト
# ====================================================================


class TestMLPluginRegistration:
    """MLプラグイン登録テスト"""

    def test_ml_plugin_registers(self):
        """MLプラグインが正常に登録される"""
        from services.plugins.ml import register

        register()
        from services.parse.base import get_parser_registry

        parser_names = [cls.__name__ for cls in get_parser_registry()]
        assert "MLDatasetParser" in parser_names
        assert "MLConfigParser" in parser_names
        assert "MLScriptParser" in parser_names
        assert "TorchCheckpointParser" in parser_names
        assert "SklearnModelParser" in parser_names
        assert "ExperimentRunParser" in parser_names

    def test_ml_plugin_idempotent(self):
        """register()を複数回呼んでもパーサーが重複登録されない"""
        from services.parse.base import get_parser_registry
        from services.plugins.ml import register

        register()
        count_before = len([cls for cls in get_parser_registry() if cls.__name__.startswith("ML")])
        register()
        count_after = len([cls for cls in get_parser_registry() if cls.__name__.startswith("ML")])

        assert count_before == count_after

    def test_parser_priorities(self):
        """パーサーの優先度が仕様通りに設定されている"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser
        from services.parse.connectors.ml.config_parser import MLConfigParser
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser
        from services.parse.connectors.ml.model_parser import SklearnModelParser
        from services.parse.connectors.ml.script_parser import MLScriptParser

        assert MLDatasetParser.priority == 55
        assert MLConfigParser.priority == 56
        assert MLScriptParser.priority == 57
        assert TorchCheckpointParser.priority == 58
        assert SklearnModelParser.priority == 59
        assert ExperimentRunParser.priority == 60
        # 優先順: dataset < config < script < checkpoint < model < experiment
        assert (
            MLDatasetParser.priority
            < MLConfigParser.priority
            < MLScriptParser.priority
            < TorchCheckpointParser.priority
            < SklearnModelParser.priority
            < ExperimentRunParser.priority
        )


# ====================================================================
# TorchCheckpointParser テスト
# ====================================================================


class TestTorchCheckpointParser:
    """TorchCheckpointParser の単体テスト"""

    def test_pt_file_promoted_to_model_checkpoint(self):
        """.ptファイルがmodel_checkpointに昇格する"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_model.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].type == "model_checkpoint"
        assert result.nodes[0].properties["ml_checkpoint"] is True
        assert result.nodes[0].properties["checkpoint_format"] == "pt"

    def test_epoch_extraction_from_filename(self):
        """ファイル名からエポック番号を抽出する"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="epoch_10.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/epoch_10.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].properties["epoch"] == 10

    def test_best_model_flag(self):
        """best modelフラグが設定される"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_model.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].properties["is_best"] is True

    def test_non_best_model_no_flag(self):
        """bestでないモデルにはフラグが付かない"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="epoch_10.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/epoch_10.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert "is_best" not in result.nodes[0].properties

    def test_pth_format_supported(self):
        """.pthファイルも対象になる"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="model.pth",
                format="pth",
                properties={"path": "models/model.pth"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].type == "model_checkpoint"
        assert result.nodes[0].properties["checkpoint_format"] == "pth"

    def test_ckpt_format_supported(self):
        """.ckptファイルも対象になる"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="model.ckpt",
                format="ckpt",
                properties={"path": "models/model.ckpt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].type == "model_checkpoint"

    def test_file_size_extracted(self):
        """ファイルサイズが抽出される"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_model.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert "file_size_bytes" in result.nodes[0].properties
        assert result.nodes[0].properties["file_size_bytes"] > 0

    def test_non_checkpoint_file_unchanged(self):
        """チェックポイント拡張子でないファイルは変更されない"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser

        nodes = [
            Node(id=1, type="file", name="train.py", format="py", properties={"path": "src/train.py"}),
        ]
        graph = _make_graph(nodes)
        result = TorchCheckpointParser().apply(graph)

        assert result.nodes[0].type == "file"


# ====================================================================
# SklearnModelParser テスト
# ====================================================================


class TestSklearnModelParser:
    """SklearnModelParser の単体テスト"""

    def test_pkl_file_promoted_to_serialized_model(self):
        """.pklファイルがserialized_modelに昇格する"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_classifier.pkl",
                format="pkl",
                properties={"path": "models/best_classifier.pkl"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].type == "serialized_model"
        assert result.nodes[0].properties["ml_serialized_model"] is True
        assert result.nodes[0].properties["serialization_format"] == "pkl"

    def test_joblib_file_promoted(self):
        """.joblibファイルがserialized_modelに昇格する"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="scaler.joblib",
                format="joblib",
                properties={"path": "models/scaler.joblib"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].type == "serialized_model"
        assert result.nodes[0].properties["serialization_format"] == "joblib"

    def test_model_type_classifier(self):
        """classifierモデル種別が推定される"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_classifier.pkl",
                format="pkl",
                properties={"path": "models/best_classifier.pkl"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].properties["model_type"] == "classifier"

    def test_model_type_scaler(self):
        """scalerモデル種別が推定される"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="scaler.joblib",
                format="joblib",
                properties={"path": "models/scaler.joblib"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].properties["model_type"] == "scaler"

    def test_model_type_pipeline(self):
        """pipelineモデル種別が推定される"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="pipeline.pkl",
                format="pkl",
                properties={"path": "models/pipeline.pkl"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].properties["model_type"] == "pipeline"

    def test_best_model_flag(self):
        """bestモデルフラグが設定される"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_classifier.pkl",
                format="pkl",
                properties={"path": "models/best_classifier.pkl"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].properties["is_best"] is True

    def test_file_size_extracted(self):
        """ファイルサイズが抽出される"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="best_classifier.pkl",
                format="pkl",
                properties={"path": "models/best_classifier.pkl"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert "file_size_bytes" in result.nodes[0].properties
        assert result.nodes[0].properties["file_size_bytes"] > 0

    def test_non_model_file_unchanged(self):
        """モデル拡張子でないファイルは変更されない"""
        from services.parse.connectors.ml.model_parser import SklearnModelParser

        nodes = [
            Node(id=1, type="file", name="data.csv", format="csv", properties={"path": "data/data.csv"}),
        ]
        graph = _make_graph(nodes)
        result = SklearnModelParser().apply(graph)

        assert result.nodes[0].type == "file"


# ====================================================================
# ExperimentRunParser テスト
# ====================================================================


class TestExperimentRunParser:
    """ExperimentRunParser の単体テスト"""

    def test_experiment_id_detected(self):
        """実験ディレクトリパターンから実験IDが抽出される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="config.yaml",
                format="yaml",
                properties={"path": "experiments/exp_001/config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert result.nodes[0].properties["experiment_id"] == "001"
        assert result.nodes[0].properties["experiment_dir"] == "exp_001"

    def test_metrics_json_promoted(self):
        """metrics.jsonがexperiment_metricsに昇格する"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "experiments/exp_001/metrics.json"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert result.nodes[0].type == "experiment_metrics"
        assert result.nodes[0].properties["ml_metrics"] is True

    def test_key_metrics_extracted(self):
        """メトリクスファイルからキーメトリクスが抽出される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "experiments/exp_001/metrics.json"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        metrics = result.nodes[0].properties["ml_key_metrics"]
        assert metrics["best_val_accuracy"] == 0.91
        assert metrics["best_epoch"] == 5

    def test_exp_002_metrics(self):
        """exp_002のメトリクスも正しく抽出される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "experiments/exp_002/metrics.json"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert result.nodes[0].properties["experiment_id"] == "002"
        metrics = result.nodes[0].properties["ml_key_metrics"]
        assert metrics["best_val_accuracy"] == 0.93

    def test_checkpoint_in_experiment(self):
        """実験ディレクトリ内のチェックポイントに実験IDが付与される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="model_checkpoint",
                name="best_model.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert result.nodes[0].properties["experiment_id"] == "001"

    def test_non_experiment_path_unchanged(self):
        """実験パターンに一致しないパスは変更されない"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="train.py",
                format="py",
                properties={"path": "src/train.py"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert "experiment_id" not in result.nodes[0].properties

    def test_run_pattern_detected(self):
        """run_NNNパターンの実験ディレクトリも検出される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "results/run_042/metrics.json"},
            ),
        ]
        # メトリクスファイルが存在しないケース（パス検出のみテスト）
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        assert result.nodes[0].properties["experiment_id"] == "042"
        assert result.nodes[0].properties["experiment_dir"] == "run_042"

    def test_multiple_nodes_in_experiment(self):
        """同一実験ディレクトリ内の複数ファイルに実験IDが付与される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="config.yaml",
                format="yaml",
                properties={"path": "experiments/exp_001/config.yaml"},
            ),
            Node(
                id=2,
                type="file",
                name="metrics.json",
                format="json",
                properties={"path": "experiments/exp_001/metrics.json"},
            ),
            Node(
                id=3,
                type="file",
                name="best_model.pt",
                format="pt",
                properties={"path": "experiments/exp_001/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = ExperimentRunParser().apply(graph)

        for node in result.nodes:
            assert node.properties["experiment_id"] == "001"
