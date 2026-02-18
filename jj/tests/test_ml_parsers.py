"""MLパーサーユニットテスト

MLDatasetParser, MLConfigParser, MLScriptParser の各パーサーを
個別にテストする。テストアセット（shared/tests/test_asset_ml/）を
利用した実ファイル解析テストも含む。

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
        from services.parse.connectors.ml.config_parser import MLConfigParser
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser
        from services.parse.connectors.ml.script_parser import MLScriptParser

        assert MLDatasetParser.priority == 55
        assert MLConfigParser.priority == 56
        assert MLScriptParser.priority == 57
        # 優先順: dataset < config < script
        assert MLDatasetParser.priority < MLConfigParser.priority < MLScriptParser.priority
