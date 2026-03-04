"""サロゲートモデルフレームワーク テスト

OptimizationRunParser, MLDataFlowParser, SurrogateWorkflowDetector の
各パーサーを個別にテストする。テストアセット（shared/tests/test_asset_ml/）
を利用した実ファイル解析テストおよびE2E統合テストも含む。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

from config import GraphConfig
from jj_types import Node, Relation
from services.graph.project_graph import ProjectGraph

ML_ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset_ml"


def _make_ml_config() -> GraphConfig:
    """ML用テストGraphConfigを生成"""
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {
                "input-extensions": [".py", ".yaml", ".json"],
                "result-extensions": [".pt", ".pth", ".ckpt", ".csv", ".json", ".db"],
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
# OptimizationRunParser テスト
# ====================================================================


class TestOptimizationRunParser:
    """OptimizationRunParser の単体テスト"""

    def test_optuna_db_promoted_to_optimization_study(self):
        """Optuna DBがoptimization_studyに昇格する"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optuna_study.db",
                format="db",
                properties={"path": "optimization/optuna_study.db"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].type == "optimization_study"
        assert result.nodes[0].properties["ml_optimization"] is True
        assert result.nodes[0].properties["optimization_framework"] == "optuna"

    def test_optuna_db_metadata_extracted(self):
        """Optuna DBからメタデータ（study_name, n_trials等）が抽出される"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optuna_study.db",
                format="db",
                properties={"path": "optimization/optuna_study.db"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].properties["study_name"] == "surrogate_optimization"
        assert result.nodes[0].properties["n_trials_completed"] == 5
        assert result.nodes[0].properties["direction"] == "minimize"

    def test_non_optuna_db_unchanged(self):
        """Optunaスキーマでない.dbファイルは変更されない"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="other_data.db",
                format="db",
                properties={"path": "data/other_data.db"},
            ),
        ]
        # ファイルが存在しないケース
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            graph = _make_graph(nodes, project_root=Path(tmpdir))
            result = OptimizationRunParser().apply(graph)
            assert result.nodes[0].type == "file"

    def test_optuna_db_name_fallback(self):
        """.dbファイルが存在しなくても名前にoptunaを含む場合は昇格"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optuna_study.db",
                format="db",
                properties={"path": "nonexistent/optuna_study.db"},
            ),
        ]
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            graph = _make_graph(nodes, project_root=Path(tmpdir))
            result = OptimizationRunParser().apply(graph)
            assert result.nodes[0].type == "optimization_study"

    def test_optimization_config_detected(self):
        """最適化設定ファイルがoptimization_configに昇格する"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optuna_config.yaml",
                format="yaml",
                properties={"path": "optimization/optuna_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].type == "optimization_config"
        assert result.nodes[0].properties["ml_optimization"] is True

    def test_optimization_config_params_extracted(self):
        """最適化設定からパラメータが抽出される"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optuna_config.yaml",
                format="yaml",
                properties={"path": "optimization/optuna_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        params = result.nodes[0].properties.get("optimization_params", {})
        assert params["n_trials"] == 100
        assert params["objective"] == "minimize"
        assert params["study_name"] == "surrogate_optimization"

    def test_trial_history_csv_detected(self):
        """試行履歴CSVがtrial_historyに昇格する"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="dataset",
                name="trial_history.csv",
                format="csv",
                properties={"path": "optimization/trial_history.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].type == "trial_history"
        assert result.nodes[0].properties["ml_optimization"] is True

    def test_pareto_front_csv_detected(self):
        """パレートフロントCSVがtrial_historyに昇格する"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="dataset",
                name="pareto_front.csv",
                format="csv",
                properties={"path": "optimization/pareto_front.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].type == "trial_history"

    def test_optimization_script_enriched(self):
        """最適化ディレクトリ内のスクリプトにml_optimizationフラグが付与される"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        nodes = [
            Node(
                id=1,
                type="file",
                name="optimize.py",
                format="py",
                properties={
                    "path": "optimization/optimize.py",
                    "ml_frameworks": ["optuna", "pytorch"],
                },
            ),
        ]
        graph = _make_graph(nodes)
        result = OptimizationRunParser().apply(graph)

        assert result.nodes[0].properties["ml_optimization"] is True
        assert result.nodes[0].properties["optimization_framework"] == "optuna"

    def test_non_optimization_yaml_unchanged(self):
        """最適化キーワードを含まないYAMLは変更されない"""
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

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
        result = OptimizationRunParser().apply(graph)

        # model_configにはoptimization系キーワードが不十分なので変更なし
        assert result.nodes[0].type != "optimization_config"


# ====================================================================
# MLDataFlowParser テスト
# ====================================================================


class TestMLDataFlowParser:
    """MLDataFlowParser の単体テスト"""

    def test_trains_with_same_experiment(self):
        """同一experiment_id内のスクリプトとデータセットにtrains_withリレーション"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "exp_001/train.py", "experiment_id": "001"},
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "exp_001/data.csv", "experiment_id": "001"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "trains_with"
        assert rel.node1_id == 1
        assert rel.node2_id == 2

    def test_produces_model_same_experiment(self):
        """同一experiment_id内のスクリプトとモデルにproduces_modelリレーション"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "exp_001/train.py", "experiment_id": "001"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="best_model.pt",
                format="pt",
                properties={
                    "path": "exp_001/checkpoints/best_model.pt",
                    "experiment_id": "001",
                },
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "produces_model"
        assert rel.node1_id == 1
        assert rel.node2_id == 2

    def test_configured_by_sibling_directory(self):
        """兄弟ディレクトリのスクリプトと設定ファイルにconfigured_byリレーション"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "project/src/train.py"},
            ),
            Node(
                id=2,
                type="experiment_config",
                name="train_config.yaml",
                format="yaml",
                properties={"path": "project/configs/train_config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "configured_by"
        assert rel.node1_id == 1
        assert rel.node2_id == 2

    def test_logs_to_same_experiment(self):
        """同一experiment_idのmetricsとモデルにlogs_toリレーション"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="experiment_metrics",
                name="metrics.json",
                format="json",
                properties={"path": "exp_001/metrics.json", "experiment_id": "001"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="best_model.pt",
                format="pt",
                properties={
                    "path": "exp_001/checkpoints/best_model.pt",
                    "experiment_id": "001",
                },
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "logs_to"
        assert rel.node1_id == 1
        assert rel.node2_id == 2

    def test_no_duplicate_relations(self):
        """同一ペアの重複リレーションは作成されない"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "exp_001/train.py", "experiment_id": "001"},
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "exp_001/data.csv", "experiment_id": "001"},
            ),
        ]
        graph = _make_graph(nodes)
        # 2回適用しても重複しない
        result = MLDataFlowParser().apply(graph)
        result = MLDataFlowParser().apply(result)

        trains_with_rels = [r for r in result.relations if r.label == "trains_with"]
        assert len(trains_with_rels) == 1

    def test_no_relations_without_ml_nodes(self):
        """ML関連ノードがない場合はリレーション生成なし"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="file",
                name="readme.md",
                format="md",
                properties={"path": "README.md"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        assert len(result.relations) == 0

    def test_trains_with_sibling_directory(self):
        """兄弟ディレクトリのスクリプトとデータセットにtrains_withリレーション"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "project/src/train.py"},
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "project/data/data.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        train_rels = [r for r in result.relations if r.label == "trains_with"]
        assert len(train_rels) == 1

    def test_multiple_relations_created(self):
        """複数種類のリレーションが同時に構築される"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "exp_001/train.py", "experiment_id": "001"},
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "exp_001/data.csv", "experiment_id": "001"},
            ),
            Node(
                id=3,
                type="model_checkpoint",
                name="model.pt",
                format="pt",
                properties={"path": "exp_001/model.pt", "experiment_id": "001"},
            ),
            Node(
                id=4,
                type="experiment_config",
                name="config.yaml",
                format="yaml",
                properties={"path": "exp_001/config.yaml", "experiment_id": "001"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        labels = {r.label for r in result.relations}
        assert "trains_with" in labels
        assert "produces_model" in labels
        assert "configured_by" in labels

    def test_project_root_scope_fallback_trains_with(self):
        """親/祖父母が異なるディレクトリでもプロジェクトルートスコープでマッチ"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        # 典型的なMLプロジェクト構造: src/ と data/ が別ディレクトリ
        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "src/train.py"},
            ),
            Node(
                id=2,
                type="dataset",
                name="dataset_v1.csv",
                format="csv",
                properties={"path": "data/raw/dataset_v1.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        train_rels = [r for r in result.relations if r.label == "trains_with"]
        assert len(train_rels) == 1
        assert train_rels[0].node1_id == 1
        assert train_rels[0].node2_id == 2

    def test_project_root_scope_fallback_produces_model(self):
        """プロジェクトルートスコープでモデル生成もマッチ"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "src/train.py"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="best_model.pt",
                format="pt",
                properties={"path": "models/checkpoints/best_model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        model_rels = [r for r in result.relations if r.label == "produces_model"]
        assert len(model_rels) == 1

    def test_project_root_scope_fallback_configured_by(self):
        """プロジェクトルートスコープで設定ファイルもマッチ"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "src/train.py"},
            ),
            Node(
                id=2,
                type="experiment_config",
                name="config.yaml",
                format="yaml",
                properties={"path": "configs/experiment/config.yaml"},
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        cfg_rels = [r for r in result.relations if r.label == "configured_by"]
        assert len(cfg_rels) == 1

    def test_root_level_files_excluded_from_project_scope(self):
        """ルート直下のファイルはプロジェクトスコープフォールバックの対象外"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "train.py"},  # ルート直下
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "data.csv"},  # ルート直下
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        # ルート直下同士はparent matchingで処理される（parentが空）のでマッチしない
        train_rels = [r for r in result.relations if r.label == "trains_with"]
        assert len(train_rels) == 0

    def test_sibling_dir_preferred_over_project_scope(self):
        """兄弟ディレクトリマッチが優先され、プロジェクトスコープはフォールバック"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser

        nodes = [
            Node(
                id=1,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "project/src/train.py"},
            ),
            Node(
                id=2,
                type="dataset",
                name="near.csv",
                format="csv",
                properties={"path": "project/data/near.csv"},  # 兄弟ディレクトリ
            ),
            Node(
                id=3,
                type="dataset",
                name="far.csv",
                format="csv",
                properties={"path": "other/data/far.csv"},  # 別プロジェクト
            ),
        ]
        graph = _make_graph(nodes)
        result = MLDataFlowParser().apply(graph)

        train_rels = [r for r in result.relations if r.label == "trains_with"]
        # 兄弟ディレクトリの near.csv のみマッチ（フォールバックに行かない）
        assert len(train_rels) == 1
        assert train_rels[0].node2_id == 2


# ====================================================================
# SurrogateWorkflowDetector テスト
# ====================================================================


class TestSurrogateWorkflowDetector:
    """SurrogateWorkflowDetector の単体テスト"""

    def test_extracted_from_cae_result(self):
        """データセットとCAE結果間にextracted_fromリレーションが構築される"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="result",
                name="go_idx1_v1.odb",
                format="odb",
                properties={"path": "project/cae/go_idx1_v1.odb"},
            ),
            Node(
                id=2,
                type="dataset",
                name="training_data.csv",
                format="csv",
                properties={"path": "project/data/training_data.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "extracted_from"
        assert rel.node1_id == 2  # dataset → CAE result
        assert rel.node2_id == 1

    def test_surrogate_of_cae_input(self):
        """モデルとCAE入力間にsurrogate_ofリレーションが構築される"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="calculation_input",
                name="go_idx1_v1.inp",
                format="inp",
                properties={"path": "project/cae/go_idx1_v1.inp"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="surrogate_v1.pt",
                format="pt",
                properties={"path": "project/ml/surrogate_v1.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "surrogate_of"
        assert rel.node1_id == 2  # model → CAE input
        assert rel.node2_id == 1

    def test_optimizes_model(self):
        """最適化スタディとモデル間にoptimizesリレーションが構築される"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="optimization_study",
                name="optuna_study.db",
                format="db",
                properties={"path": "project/optimization/optuna_study.db"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="surrogate_v1.pt",
                format="pt",
                properties={"path": "project/ml/surrogate_v1.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "optimizes"
        assert rel.node1_id == 1  # study → model
        assert rel.node2_id == 2

    def test_uses_objective_script(self):
        """最適化スタディと学習スクリプト間にuses_objectiveリレーション"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="optimization_study",
                name="optuna_study.db",
                format="db",
                properties={"path": "project/optimization/optuna_study.db"},
            ),
            Node(
                id=2,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "project/src/train.py"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 1
        rel = result.relations[0]
        assert rel.label == "uses_objective"

    def test_no_relations_single_layer(self):
        """単一レイヤーのノードのみでは層間リレーションは生成されない"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "ml/data/data.csv"},
            ),
            Node(
                id=2,
                type="model_checkpoint",
                name="model.pt",
                format="pt",
                properties={"path": "ml/models/model.pt"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 0

    def test_full_surrogate_workflow(self):
        """完全なサロゲートモデルワークフローで複数の層間リレーションが構築される"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            # Layer 1: CAE
            Node(
                id=1,
                type="calculation_input",
                name="go_idx1_v1.inp",
                format="inp",
                properties={"path": "project/cae/go_idx1_v1.inp"},
            ),
            Node(
                id=2,
                type="result",
                name="go_idx1_v1.odb",
                format="odb",
                properties={"path": "project/cae/go_idx1_v1.odb"},
            ),
            # Layer 2: ML
            Node(
                id=3,
                type="dataset",
                name="training_data.csv",
                format="csv",
                properties={"path": "project/data/training_data.csv"},
            ),
            Node(
                id=4,
                type="model_checkpoint",
                name="surrogate_v1.pt",
                format="pt",
                properties={"path": "project/ml/surrogate_v1.pt"},
            ),
            Node(
                id=5,
                type="training_script",
                name="train.py",
                format="py",
                properties={"path": "project/src/train.py"},
            ),
            # Layer 3: Optimization
            Node(
                id=6,
                type="optimization_study",
                name="study.db",
                format="db",
                properties={"path": "project/optimization/study.db"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        labels = {r.label for r in result.relations}
        # extracted_from: dataset → result
        assert "extracted_from" in labels
        # surrogate_of: model → input
        assert "surrogate_of" in labels
        # optimizes: study → model
        assert "optimizes" in labels
        # uses_objective: study → script
        assert "uses_objective" in labels
        assert len(result.relations) >= 4

    def test_different_projects_no_relations(self):
        """異なるプロジェクトルートのノード間ではリレーションが構築されない"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            Node(
                id=1,
                type="result",
                name="go_idx1_v1.odb",
                format="odb",
                properties={"path": "project_a/cae/go_idx1_v1.odb"},
            ),
            Node(
                id=2,
                type="dataset",
                name="data.csv",
                format="csv",
                properties={"path": "project_b/data/data.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 0

    def test_shallow_path_fallback_matches(self):
        """浅いパス（depth==2）の機能ディレクトリ同士はフォールバックでマッチ"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        # cae/ と data/ は同一プロジェクト内の機能ディレクトリと判定
        nodes = [
            Node(
                id=1,
                type="result",
                name="result.odb",
                format="odb",
                properties={"path": "cae/result.odb"},
            ),
            Node(
                id=2,
                type="dataset",
                name="features.csv",
                format="csv",
                properties={"path": "data/features.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        rels = [r for r in result.relations if r.label == "extracted_from"]
        assert len(rels) == 1

    def test_deep_path_no_fallback(self):
        """深いパス（depth>=3）ではroot segment不一致時にフォールバックしない"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        # project_a/ と project_b/ は異なるプロジェクトと判定
        nodes = [
            Node(
                id=1,
                type="result",
                name="result.odb",
                format="odb",
                properties={"path": "project_a/cae/result.odb"},
            ),
            Node(
                id=2,
                type="dataset",
                name="features.csv",
                format="csv",
                properties={"path": "project_b/data/features.csv"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        assert len(result.relations) == 0

    def test_shallow_path_full_workflow(self):
        """浅いパスで三層ワークフロー全体がフォールバックでマッチ"""
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        nodes = [
            # Layer 1
            Node(id=1, type="calculation_input", name="go.inp", format="inp", properties={"path": "cae/go.inp"}),
            Node(id=2, type="result", name="go.odb", format="odb", properties={"path": "cae/go.odb"}),
            # Layer 2
            Node(id=3, type="dataset", name="data.csv", format="csv", properties={"path": "data/data.csv"}),
            Node(id=4, type="model_checkpoint", name="model.pt", format="pt", properties={"path": "ml/model.pt"}),
            Node(id=5, type="training_script", name="train.py", format="py", properties={"path": "ml/train.py"}),
            # Layer 3
            Node(
                id=6,
                type="optimization_study",
                name="study.db",
                format="db",
                properties={"path": "optimization/study.db"},
            ),
        ]
        graph = _make_graph(nodes)
        result = SurrogateWorkflowDetector().apply(graph)

        labels = {r.label for r in result.relations}
        assert "extracted_from" in labels
        assert "surrogate_of" in labels
        assert "optimizes" in labels
        assert "uses_objective" in labels


# ====================================================================
# プラグイン登録テスト
# ====================================================================


class TestSurrogateFrameworkRegistration:
    """サロゲートモデルフレームワーク パーサー登録テスト"""

    def test_all_new_parsers_registered(self):
        """新規3パーサーがレジストリに登録されている"""
        from services.parse.base import get_parser_registry
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser  # noqa: F401
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,  # noqa: F401
        )
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,  # noqa: F401
        )

        registry = get_parser_registry()
        registry_classes = {cls.__name__ for cls in registry}

        assert "OptimizationRunParser" in registry_classes
        assert "MLDataFlowParser" in registry_classes
        assert "SurrogateWorkflowDetector" in registry_classes

    def test_priority_ordering(self):
        """新パーサーの優先度が正しい順序"""
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        assert OptimizationRunParser.priority == 62
        assert MLDataFlowParser.priority == 65
        assert SurrogateWorkflowDetector.priority == 70
        # 既存パーサーの後に実行される
        assert OptimizationRunParser.priority < MLDataFlowParser.priority < SurrogateWorkflowDetector.priority

    def test_priority_after_existing_parsers(self):
        """新パーサーは既存MLパーサーの後に実行される"""
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )

        assert ExperimentRunParser.priority < OptimizationRunParser.priority


# ====================================================================
# Neo4jスキーマ テスト
# ====================================================================


class TestNeo4jSchemaExtension:
    """Neo4jスキーマ拡張テスト"""

    def test_ml_relation_types_defined(self):
        """MLデータフローリレーションタイプが定義されている"""
        from shared.neo4j_schema import RelType

        assert RelType.TRAINS_WITH == "TRAINS_WITH"
        assert RelType.PRODUCES_MODEL == "PRODUCES_MODEL"
        assert RelType.CONFIGURED_BY == "CONFIGURED_BY"
        assert RelType.EVALUATED_ON == "EVALUATED_ON"
        assert RelType.LOGS_TO == "LOGS_TO"

    def test_surrogate_relation_types_defined(self):
        """サロゲートモデルリレーションタイプが定義されている"""
        from shared.neo4j_schema import RelType

        assert RelType.EXTRACTED_FROM == "EXTRACTED_FROM"
        assert RelType.SURROGATE_OF == "SURROGATE_OF"
        assert RelType.OPTIMIZES == "OPTIMIZES"
        assert RelType.USES_OBJECTIVE == "USES_OBJECTIVE"

    def test_label_to_reltype_mapping(self):
        """label → RelTypeマッピングが正しい"""
        from shared.neo4j_schema import LABEL_TO_RELTYPE

        assert LABEL_TO_RELTYPE["trains_with"] == "TRAINS_WITH"
        assert LABEL_TO_RELTYPE["extracted_from"] == "EXTRACTED_FROM"
        assert LABEL_TO_RELTYPE["surrogate_of"] == "SURROGATE_OF"
        assert LABEL_TO_RELTYPE["optimizes"] == "OPTIMIZES"

    def test_ml_node_types_mapped(self):
        """MLノードタイプがNeo4jラベルにマッピングされている"""
        from shared.neo4j_schema import TYPE_TO_LABEL, NodeLabel

        assert TYPE_TO_LABEL["optimization_study"] == NodeLabel.JJ_FILE
        assert TYPE_TO_LABEL["optimization_config"] == NodeLabel.JJ_FILE
        assert TYPE_TO_LABEL["trial_history"] == NodeLabel.JJ_FILE
        assert TYPE_TO_LABEL["dataset"] == NodeLabel.JJ_FILE
        assert TYPE_TO_LABEL["model_checkpoint"] == NodeLabel.JJ_FILE


# ====================================================================
# E2Eテスト: test_asset_ml全体パース
# ====================================================================


class TestSurrogateFrameworkE2E:
    """E2E統合テスト: test_asset_ml全体をパースしてグラフ検証"""

    def _build_full_graph(self) -> ProjectGraph:
        """test_asset_ml全体からノードを生成しパーサーを適用"""
        from services.parse.connectors.ml.checkpoint_parser import (
            TorchCheckpointParser,
        )
        from services.parse.connectors.ml.config_parser import MLConfigParser
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser
        from services.parse.connectors.ml.model_parser import SklearnModelParser
        from services.parse.connectors.ml.optimization_parser import (
            OptimizationRunParser,
        )
        from services.parse.connectors.ml.script_parser import MLScriptParser
        from services.parse.connectors.ml.surrogate_detector import (
            SurrogateWorkflowDetector,
        )

        # test_asset_mlからノードを収集
        nodes: list[Node] = []
        node_id = 0
        for path in sorted(ML_ASSET_DIR.rglob("*")):
            if path.is_file():
                rel_path = path.relative_to(ML_ASSET_DIR)
                node_id += 1
                nodes.append(
                    Node(
                        id=node_id,
                        type="file",
                        name=path.name,
                        format=path.suffix.lstrip(".") if path.suffix else "",
                        properties={"path": str(rel_path)},
                    )
                )

        graph = _make_graph(nodes)

        # 全パーサーをpriority順に適用
        parsers = sorted(
            [
                MLDatasetParser,
                MLConfigParser,
                MLScriptParser,
                TorchCheckpointParser,
                SklearnModelParser,
                ExperimentRunParser,
                OptimizationRunParser,
                MLDataFlowParser,
                SurrogateWorkflowDetector,
            ],
            key=lambda cls: cls.priority,
        )
        for parser_cls in parsers:
            graph = parser_cls().apply(graph)

        return graph

    def test_all_parsers_execute_without_error(self):
        """全パーサーがエラーなく実行される"""
        graph = self._build_full_graph()
        assert len(graph.nodes) > 0

    def test_optimization_nodes_created(self):
        """最適化関連ノードが正しく作成される"""
        graph = self._build_full_graph()

        optim_studies = [n for n in graph.nodes if n.type == "optimization_study"]
        optim_configs = [n for n in graph.nodes if n.type == "optimization_config"]
        trial_histories = [n for n in graph.nodes if n.type == "trial_history"]

        assert len(optim_studies) >= 1, "Optuna DB should be promoted"
        assert len(optim_configs) >= 1, "Optimization config should be promoted"
        assert len(trial_histories) >= 1, "Trial history CSV should be promoted"

    def test_ml_dataflow_relations_created(self):
        """MLデータフローリレーションが構築される"""
        graph = self._build_full_graph()

        relation_labels = {r.label for r in graph.relations}
        # 何らかのMLデータフローリレーションが生成される
        ml_relation_labels = {
            "trains_with",
            "produces_model",
            "configured_by",
            "logs_to",
            "evaluated_on",
        }
        found = relation_labels & ml_relation_labels
        assert found, f"Expected ML dataflow relations, got: {relation_labels}"

    def test_no_duplicate_relations(self):
        """重複リレーションがないことを検証"""
        graph = self._build_full_graph()

        seen: set[tuple[int, int, str]] = set()
        for rel in graph.relations:
            key = (rel.node1_id, rel.node2_id, rel.label)
            assert key not in seen, f"Duplicate relation: {key}"
            seen.add(key)

    def test_node_type_consistency(self):
        """ノードタイプが有効な値のみ含む"""
        graph = self._build_full_graph()

        valid_types = {
            "file",
            "dataset",
            "model_checkpoint",
            "serialized_model",
            "training_script",
            "experiment_config",
            "experiment_metrics",
            "optimization_study",
            "optimization_config",
            "trial_history",
        }

        for node in graph.nodes:
            assert node.type in valid_types, f"Unexpected node type: {node.type} for {node.name}"


# ====================================================================
# CAE+ML混在 E2Eテスト: test_asset_surrogate
# ====================================================================

SURROGATE_ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset_surrogate"


class TestSurrogateE2EWithCAE:
    """CAE+ML混在テストアセットを使った三層ワークフローE2Eテスト

    test_asset_surrogate/ は以下の構造:
      cae/          - CAE入力ファイル (.inp)
      data/         - CAE結果から抽出したデータセット (.csv)
      ml/           - 学習スクリプト・設定・モデル (.py, .yaml, .pt)
      optimization/ - 最適化スタディ (.db, .csv)
    """

    def _build_surrogate_graph(self) -> ProjectGraph:
        """test_asset_surrogateからノードを生成し全パーサーを適用"""
        from services.parse.connectors.ml.checkpoint_parser import TorchCheckpointParser
        from services.parse.connectors.ml.config_parser import MLConfigParser
        from services.parse.connectors.ml.dataflow_parser import MLDataFlowParser
        from services.parse.connectors.ml.dataset_parser import MLDatasetParser
        from services.parse.connectors.ml.experiment_parser import ExperimentRunParser
        from services.parse.connectors.ml.model_parser import SklearnModelParser
        from services.parse.connectors.ml.optimization_parser import OptimizationRunParser
        from services.parse.connectors.ml.script_parser import MLScriptParser
        from services.parse.connectors.ml.surrogate_detector import SurrogateWorkflowDetector

        nodes: list[Node] = []
        node_id = 0
        for path in sorted(SURROGATE_ASSET_DIR.rglob("*")):
            if path.is_file():
                rel_path = path.relative_to(SURROGATE_ASSET_DIR)
                node_id += 1
                # .inp ファイルは calculation_input として初期化（実際のパーサーが行う処理を模擬）
                file_type = "file"
                if path.suffix == ".inp":
                    file_type = "calculation_input"
                nodes.append(
                    Node(
                        id=node_id,
                        type=file_type,
                        name=path.name,
                        format=path.suffix.lstrip(".") if path.suffix else "",
                        properties={"path": str(rel_path)},
                    )
                )

        graph = _make_graph(nodes, project_root=SURROGATE_ASSET_DIR)

        parsers = sorted(
            [
                MLDatasetParser,
                MLConfigParser,
                MLScriptParser,
                TorchCheckpointParser,
                SklearnModelParser,
                ExperimentRunParser,
                OptimizationRunParser,
                MLDataFlowParser,
                SurrogateWorkflowDetector,
            ],
            key=lambda cls: cls.priority,
        )
        for parser_cls in parsers:
            graph = parser_cls().apply(graph)

        return graph

    def test_all_three_layers_detected(self):
        """三層全てのノードタイプが検出される"""
        graph = self._build_surrogate_graph()

        types = {n.type for n in graph.nodes}

        # Layer 1: CAE
        assert "calculation_input" in types, f"CAE input missing, got: {types}"
        # Layer 2: ML
        assert "dataset" in types, f"Dataset missing, got: {types}"
        assert "experiment_config" in types, f"Config missing, got: {types}"
        # Layer 3: Optimization
        assert "optimization_study" in types, f"Optuna study missing, got: {types}"

    def test_cross_layer_relations_created(self):
        """三層間のリレーションが生成される"""
        graph = self._build_surrogate_graph()

        labels = {r.label for r in graph.relations}

        # L1→L2: CAE結果からデータ抽出は.odbが無いのでextracted_fromは不要
        # L1→L2: サロゲートモデルがCAE入力を近似
        assert "surrogate_of" in labels, f"surrogate_of missing, got: {labels}"
        # L2→L3: 最適化スタディがモデルを最適化
        assert "optimizes" in labels, f"optimizes missing, got: {labels}"

    def test_intra_ml_dataflow_relations(self):
        """ML層内のデータフローリレーションが生成される"""
        graph = self._build_surrogate_graph()

        labels = {r.label for r in graph.relations}
        ml_labels = {"trains_with", "produces_model", "configured_by", "logs_to"}
        found = labels & ml_labels
        assert found, f"Expected intra-ML dataflow relations, got: {labels}"

    def test_cae_nodes_preserved(self):
        """CAEノードのタイプがML昇格で上書きされない"""
        graph = self._build_surrogate_graph()

        inp_nodes = [n for n in graph.nodes if n.name.endswith(".inp")]
        for node in inp_nodes:
            assert node.type == "calculation_input", f"CAE input type overwritten: {node.name} → {node.type}"

    def test_no_duplicate_relations_in_surrogate(self):
        """CAE+ML混在でも重複リレーションが発生しない"""
        graph = self._build_surrogate_graph()

        seen: set[tuple[int, int, str]] = set()
        for rel in graph.relations:
            key = (rel.node1_id, rel.node2_id, rel.label)
            assert key not in seen, f"Duplicate relation: {key}"
            seen.add(key)

    def test_node_count_matches_files(self):
        """ノード数がファイル数と一致する"""
        graph = self._build_surrogate_graph()
        file_count = sum(1 for p in SURROGATE_ASSET_DIR.rglob("*") if p.is_file())
        assert len(graph.nodes) == file_count

    def test_optimization_metadata_extracted(self):
        """最適化スタディのメタデータが抽出される"""
        graph = self._build_surrogate_graph()

        studies = [n for n in graph.nodes if n.type == "optimization_study"]
        assert len(studies) >= 1
        study = studies[0]
        assert study.properties.get("study_name") == "surrogate_opt"
        assert study.properties.get("n_trials_completed") == 5
