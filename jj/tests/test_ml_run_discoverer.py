"""MlTrainingRunDiscovererのテスト

ML学習潜在Run発見パーサーの単体テスト。
training_script + dataset + model_checkpoint のパターンから
ML学習Run候補が正しく生成されることを検証する。
"""

from __future__ import annotations

from pathlib import Path

from config import GraphConfig
from jj_types import (
    RUN_INPUT,
    RUN_MEDIA,
    RUN_OUTPUT,
    Node,
    NodeCategory,
    Relation,
)
from services.graph.project_graph import ProjectGraph
from services.parse.parsers.ml_run_discoverer import MlTrainingRunDiscoverer


def _make_config() -> GraphConfig:
    return GraphConfig.from_dict({})


def _make_project_graph(
    nodes: list[Node] | None = None,
    relations: list[Relation] | None = None,
) -> ProjectGraph:
    return ProjectGraph(
        nodes=nodes or [],
        relations=relations or [],
        project_root=Path("/tmp/test_project"),
        config=_make_config(),
    )


class TestMlTrainingRunDiscovererBasic:
    """基本的なML Run発見テスト"""

    def test_discover_training_run(self):
        """training_script + dataset + model からRunが発見される"""
        script = Node(
            id=1,
            type="training_script",
            name="train",
            format="py",
            properties={"path": "src/train.py", "ml_role": "training"},
        )
        dataset = Node(
            id=2,
            type="dataset",
            name="train_data",
            format="csv",
            properties={"path": "data/train_data.csv"},
        )
        model = Node(
            id=3,
            type="model_checkpoint",
            name="model_best",
            format="pt",
            properties={"path": "models/model_best.pt"},
        )

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=2),
            Relation(id=2, label="produces_model", node1_id=1, node2_id=3),
        ]
        graph = _make_project_graph(nodes=[script, dataset, model], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.run_type == "ml_training"
        assert 2 in c.input_node_ids  # dataset
        assert 3 in c.output_node_ids  # model
        assert 1 in c.media_node_ids  # script

    def test_no_scripts_no_runs(self):
        """training_scriptがなければRunは発見されない"""
        dataset = Node(id=1, type="dataset", name="data", format="csv")
        model = Node(id=2, type="model_checkpoint", name="model", format="pt")

        graph = _make_project_graph(nodes=[dataset, model])
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 0

    def test_script_without_relations_no_run(self):
        """training_scriptがあってもリレーションがなければRunは発見されない"""
        script = Node(
            id=1,
            type="training_script",
            name="train",
            format="py",
        )

        graph = _make_project_graph(nodes=[script])
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 0

    def test_empty_graph(self):
        """空グラフではRunは発見されない"""
        graph = _make_project_graph()
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)
        assert len(candidates) == 0


class TestMlTrainingRunDiscovererRelations:
    """リレーション経由のRun発見テスト"""

    def test_configured_by_adds_config_to_inputs(self):
        """configured_by関係から設定ファイルが入力に含まれる"""
        script = Node(id=1, type="training_script", name="train", format="py")
        config = Node(id=2, type="experiment_config", name="config", format="yaml")
        dataset = Node(id=3, type="dataset", name="data", format="csv")
        model = Node(id=4, type="model_checkpoint", name="model", format="pt")

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=3),
            Relation(id=2, label="produces_model", node1_id=1, node2_id=4),
            Relation(id=3, label="configured_by", node1_id=1, node2_id=2),
        ]
        graph = _make_project_graph(nodes=[script, config, dataset, model], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        assert 2 in c.input_node_ids  # config
        assert 3 in c.input_node_ids  # dataset

    def test_logs_to_adds_metrics_to_outputs(self):
        """logs_to関係からメトリクスが出力に含まれる"""
        script = Node(id=1, type="training_script", name="train", format="py")
        dataset = Node(id=2, type="dataset", name="data", format="csv")
        model = Node(id=3, type="model_checkpoint", name="model", format="pt")
        metrics = Node(id=4, type="experiment_metrics", name="metrics", format="json")

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=2),
            Relation(id=2, label="produces_model", node1_id=1, node2_id=3),
            Relation(id=3, label="logs_to", node1_id=4, node2_id=3),
        ]
        graph = _make_project_graph(nodes=[script, dataset, model, metrics], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        assert 3 in c.output_node_ids  # model
        assert 4 in c.output_node_ids  # metrics

    def test_dataset_only_run(self):
        """データセットのみ（モデル出力なし）でもRunが発見される"""
        script = Node(id=1, type="training_script", name="preprocess", format="py")
        dataset = Node(id=2, type="dataset", name="raw_data", format="csv")

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=2),
        ]
        graph = _make_project_graph(nodes=[script, dataset], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        assert 2 in candidates[0].input_node_ids

    def test_model_only_run(self):
        """モデル出力のみ（データセット入力なし）でもRunが発見される"""
        script = Node(id=1, type="training_script", name="train", format="py")
        model = Node(id=2, type="model_checkpoint", name="model", format="pt")

        rels = [
            Relation(id=1, label="produces_model", node1_id=1, node2_id=2),
        ]
        graph = _make_project_graph(nodes=[script, model], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        assert 2 in candidates[0].output_node_ids


class TestMlTrainingRunDiscovererMultipleRuns:
    """複数ML Run発見テスト"""

    def test_multiple_scripts_multiple_runs(self):
        """複数のtraining_scriptから複数のRunが発見される"""
        script1 = Node(id=1, type="training_script", name="train_v1", format="py")
        script2 = Node(id=2, type="training_script", name="train_v2", format="py")
        dataset = Node(id=3, type="dataset", name="data", format="csv")
        model1 = Node(id=4, type="model_checkpoint", name="model_v1", format="pt")
        model2 = Node(id=5, type="model_checkpoint", name="model_v2", format="pt")

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=3),
            Relation(id=2, label="produces_model", node1_id=1, node2_id=4),
            Relation(id=3, label="trains_with", node1_id=2, node2_id=3),
            Relation(id=4, label="produces_model", node1_id=2, node2_id=5),
        ]
        graph = _make_project_graph(nodes=[script1, script2, dataset, model1, model2], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 2
        names = {c.name for c in candidates}
        assert any("train_v1" in n for n in names)
        assert any("train_v2" in n for n in names)


class TestMlTrainingRunDiscovererRunType:
    """Run種別判定テスト"""

    def test_training_role(self):
        """ml_role=trainingのスクリプトはml_trainingタイプ"""
        script = Node(
            id=1,
            type="training_script",
            name="train",
            format="py",
            properties={"ml_role": "training"},
        )
        dataset = Node(id=2, type="dataset", name="data", format="csv")

        rels = [Relation(id=1, label="trains_with", node1_id=1, node2_id=2)]
        graph = _make_project_graph(nodes=[script, dataset], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert candidates[0].run_type == "ml_training"

    def test_preprocessing_role(self):
        """ml_role=preprocessingのスクリプトはml_preprocessingタイプ"""
        script = Node(
            id=1,
            type="training_script",
            name="preprocess",
            format="py",
            properties={"ml_role": "preprocessing"},
        )
        dataset = Node(id=2, type="dataset", name="data", format="csv")

        rels = [Relation(id=1, label="trains_with", node1_id=1, node2_id=2)]
        graph = _make_project_graph(nodes=[script, dataset], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert candidates[0].run_type == "ml_preprocessing"

    def test_inference_role(self):
        """ml_role=inferenceのスクリプトはml_inferenceタイプ"""
        script = Node(
            id=1,
            type="training_script",
            name="predict",
            format="py",
            properties={"ml_role": "inference"},
        )
        model = Node(id=2, type="model_checkpoint", name="model", format="pt")

        rels = [Relation(id=1, label="produces_model", node1_id=1, node2_id=2)]
        graph = _make_project_graph(nodes=[script, model], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert candidates[0].run_type == "ml_inference"


class TestMlTrainingRunDiscovererApply:
    """apply()メソッドテスト"""

    def test_apply_creates_run_nodes(self):
        """apply()がRun Nodeをグラフに追加する"""
        script = Node(id=1, type="training_script", name="train", format="py")
        dataset = Node(id=2, type="dataset", name="data", format="csv")
        model = Node(id=3, type="model_checkpoint", name="model", format="pt")

        rels = [
            Relation(id=1, label="trains_with", node1_id=1, node2_id=2),
            Relation(id=2, label="produces_model", node1_id=1, node2_id=3),
        ]
        graph = _make_project_graph(nodes=[script, dataset, model], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        result_graph = discoverer.apply(graph)

        run_nodes = [n for n in result_graph.nodes if n.category == NodeCategory.RUN]
        assert len(run_nodes) == 1
        run_node = run_nodes[0]
        assert run_node.type == "ml_training"
        assert run_node.properties["run_status"] == "latent"

        # run_input/run_output/run_media リレーション
        run_rels = [r for r in result_graph.relations if r.node1_id == run_node.id]
        input_rels = [r for r in run_rels if r.label == RUN_INPUT]
        output_rels = [r for r in run_rels if r.label == RUN_OUTPUT]
        media_rels = [r for r in run_rels if r.label == RUN_MEDIA]

        assert len(input_rels) >= 1  # dataset
        assert len(output_rels) >= 1  # model
        assert len(media_rels) == 1  # script
        assert media_rels[0].node2_id == script.id

    def test_priority_is_210(self):
        """priorityが210（CaeRunDiscovererの後）"""
        assert MlTrainingRunDiscoverer.priority == 210

    def test_frameworks_propagated(self):
        """ml_frameworksプロパティがRunに伝搬される"""
        script = Node(
            id=1,
            type="training_script",
            name="train",
            format="py",
            properties={"ml_frameworks": ["pytorch"], "ml_role": "training"},
        )
        dataset = Node(id=2, type="dataset", name="data", format="csv")

        rels = [Relation(id=1, label="trains_with", node1_id=1, node2_id=2)]
        graph = _make_project_graph(nodes=[script, dataset], relations=rels)
        discoverer = MlTrainingRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert candidates[0].properties["frameworks"] == ["pytorch"]
