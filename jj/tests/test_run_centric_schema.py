"""Run中心スキーマ再設計のテスト

NodeCategory, Run Node, ProjectGraph Run検索メソッド,
RunCandidate, AbstractRunDiscoverer, RunQueryServiceのテスト。
"""

from __future__ import annotations

from pathlib import Path

from config import GraphConfig
from jj_types import (
    RUN_INPUT,
    RUN_MEDIA,
    RUN_OUTPUT,
    RUN_RELATION_LABELS,
    GraphModel,
    Node,
    NodeCategory,
    Relation,
)
from services.graph.project_graph import ProjectGraph
from services.parse.run_discoverer import AbstractRunDiscoverer, RunCandidate
from services.run.query import (
    ComparisonAxis,
    RunQueryService,
)

# =========================================================
# ヘルパー
# =========================================================


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


# =========================================================
# NodeCategory テスト
# =========================================================


class TestNodeCategory:
    def test_enum_values(self):
        assert NodeCategory.FILE == "file"
        assert NodeCategory.DIRECTORY == "directory"
        assert NodeCategory.DATA == "data"
        assert NodeCategory.REPOSITORY == "repository"
        assert NodeCategory.RUN == "run"

    def test_node_default_category(self):
        """categoryフィールド未指定でデフォルトがfileになること"""
        node = Node(id=1, type="go", name="test.inp", format="inp")
        assert node.category == NodeCategory.FILE

    def test_node_explicit_category(self):
        node = Node(
            id=1,
            type="cae_job",
            name="run1",
            format="",
            category=NodeCategory.RUN,
        )
        assert node.category == NodeCategory.RUN

    def test_node_category_from_string(self):
        """文字列からNodeCategoryへの変換"""
        node = Node(
            id=1,
            type="test",
            name="test",
            format="",
            category="run",  # type: ignore[arg-type]
        )
        assert node.category == NodeCategory.RUN

    def test_node_category_serialization(self):
        """model_dump(mode='json')でcategoryがstrになること"""
        node = Node(
            id=1,
            type="cae_job",
            name="run1",
            format="",
            category=NodeCategory.RUN,
        )
        data = node.model_dump(mode="json")
        assert data["category"] == "run"
        assert isinstance(data["category"], str)

    def test_node_category_deserialization(self):
        """dictからNodeを復元してcategoryが正しく設定されること"""
        data = {
            "id": 1,
            "type": "cae_job",
            "name": "run1",
            "format": "",
            "category": "run",
        }
        node = Node.model_validate(data)
        assert node.category == NodeCategory.RUN

    def test_backward_compat_no_category(self):
        """categoryフィールドがないdictからNodeを復元した場合のデフォルト値"""
        data = {
            "id": 1,
            "type": "go",
            "name": "test.inp",
            "format": "inp",
        }
        node = Node.model_validate(data)
        assert node.category == NodeCategory.FILE


class TestRunRelationConstants:
    def test_run_relation_labels(self):
        assert RUN_INPUT == "run_input"
        assert RUN_OUTPUT == "run_output"
        assert RUN_MEDIA == "run_media"

    def test_run_relation_labels_frozenset(self):
        assert RUN_INPUT in RUN_RELATION_LABELS
        assert RUN_OUTPUT in RUN_RELATION_LABELS
        assert RUN_MEDIA in RUN_RELATION_LABELS
        assert "includes" not in RUN_RELATION_LABELS


# =========================================================
# GraphModel YAML/JSON シリアライゼーション
# =========================================================


class TestGraphModelSerialization:
    def test_graph_model_with_category_roundtrip(self):
        """GraphModelのシリアライズ→デシリアライズで情報が保持されること"""
        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="test.inp", format="inp", category=NodeCategory.FILE),
                Node(
                    id=2,
                    type="cae_job",
                    name="run1",
                    format="",
                    category=NodeCategory.RUN,
                    properties={"run_type": "cae_job", "run_status": "latent"},
                ),
            ],
            relations=[
                Relation(id=1, label=RUN_INPUT, node1_id=2, node2_id=1),
            ],
        )
        data = graph.model_dump(mode="json")
        restored = GraphModel.model_validate(data)
        assert restored.nodes[0].category == NodeCategory.FILE
        assert restored.nodes[1].category == NodeCategory.RUN
        assert restored.relations[0].label == RUN_INPUT

    def test_graph_model_backward_compat(self):
        """categoryフィールドがないYAML/JSONから読み込めること"""
        data = {
            "nodes": [
                {"id": 1, "type": "go", "name": "test.inp", "format": "inp"},
                {"id": 2, "type": "directory", "name": "cae", "format": "directory"},
            ],
            "relations": [],
        }
        graph = GraphModel.model_validate(data)
        assert graph.nodes[0].category == NodeCategory.FILE
        assert graph.nodes[1].category == NodeCategory.FILE  # デフォルト


# =========================================================
# ProjectGraph Run検索メソッド テスト
# =========================================================


class TestProjectGraphRunMethods:
    def _build_graph_with_runs(self) -> ProjectGraph:
        """テスト用のRun入りグラフを構築"""
        nodes = [
            Node(id=1, type="go", name="go_idx1_v1.inp", format="inp", category=NodeCategory.FILE),
            Node(id=2, type="calculation_output", name="go_idx1_v1.odb", format="odb", category=NodeCategory.FILE),
            Node(id=3, type="script", name="abaqus", format="", category=NodeCategory.FILE),
            Node(
                id=10,
                type="cae_job",
                name="go_idx1_v1 解析",
                format="",
                category=NodeCategory.RUN,
                properties={"run_type": "cae_job", "run_status": "latent", "discovery": "static"},
            ),
            Node(id=4, type="dataset", name="data.csv", format="csv", category=NodeCategory.FILE),
            Node(id=5, type="model_checkpoint", name="model.pt", format="pt", category=NodeCategory.FILE),
            Node(id=6, type="training_script", name="train.py", format="py", category=NodeCategory.FILE),
            Node(
                id=20,
                type="ml_training",
                name="学習Run",
                format="",
                category=NodeCategory.RUN,
                properties={"run_type": "ml_training", "run_status": "latent", "discovery": "static"},
            ),
        ]
        relations = [
            Relation(id=100, label=RUN_INPUT, node1_id=10, node2_id=1),
            Relation(id=101, label=RUN_OUTPUT, node1_id=10, node2_id=2),
            Relation(id=102, label=RUN_MEDIA, node1_id=10, node2_id=3),
            Relation(id=200, label=RUN_INPUT, node1_id=20, node2_id=4),
            Relation(id=201, label=RUN_OUTPUT, node1_id=20, node2_id=5),
            Relation(id=202, label=RUN_MEDIA, node1_id=20, node2_id=6),
            # 意味的リレーション（既存互換）
            Relation(id=1, label="output", node1_id=1, node2_id=2),
        ]
        return _make_project_graph(nodes, relations)

    def test_get_run_nodes_all(self):
        graph = self._build_graph_with_runs()
        runs = graph.get_run_nodes()
        assert len(runs) == 2
        assert all(n.category == NodeCategory.RUN for n in runs)

    def test_get_run_nodes_by_type(self):
        graph = self._build_graph_with_runs()
        cae_runs = graph.get_run_nodes(run_type="cae_job")
        assert len(cae_runs) == 1
        assert cae_runs[0].name == "go_idx1_v1 解析"

        ml_runs = graph.get_run_nodes(run_type="ml_training")
        assert len(ml_runs) == 1
        assert ml_runs[0].name == "学習Run"

    def test_get_run_inputs(self):
        graph = self._build_graph_with_runs()
        run = graph.get_run_nodes(run_type="cae_job")[0]
        inputs = graph.get_run_inputs(run)
        assert len(inputs) == 1
        assert inputs[0].name == "go_idx1_v1.inp"

    def test_get_run_outputs(self):
        graph = self._build_graph_with_runs()
        run = graph.get_run_nodes(run_type="cae_job")[0]
        outputs = graph.get_run_outputs(run)
        assert len(outputs) == 1
        assert outputs[0].name == "go_idx1_v1.odb"

    def test_get_run_media(self):
        graph = self._build_graph_with_runs()
        run = graph.get_run_nodes(run_type="cae_job")[0]
        media = graph.get_run_media(run)
        assert len(media) == 1
        assert media[0].name == "abaqus"

    def test_get_nodes_by_category(self):
        graph = self._build_graph_with_runs()
        files = graph.get_nodes_by_category(NodeCategory.FILE)
        assert len(files) == 6
        runs = graph.get_nodes_by_category(NodeCategory.RUN)
        assert len(runs) == 2

    def test_add_run_node(self):
        graph = _make_project_graph(
            nodes=[
                Node(id=1, type="go", name="input.inp", format="inp"),
                Node(id=2, type="file", name="output.odb", format="odb"),
            ],
        )
        run = graph.add_run_node(
            name="test run",
            run_type="cae_job",
            input_node_ids=[1],
            output_node_ids=[2],
            properties={"solver": "abaqus"},
        )
        assert run.category == NodeCategory.RUN
        assert run.properties["run_type"] == "cae_job"
        assert run.properties["run_status"] == "latent"
        assert run.properties["discovery"] == "static"
        assert run.properties["solver"] == "abaqus"

        # リレーションが追加されていること
        input_rels = [r for r in graph.relations if r.label == RUN_INPUT]
        output_rels = [r for r in graph.relations if r.label == RUN_OUTPUT]
        assert len(input_rels) == 1
        assert input_rels[0].node1_id == run.id
        assert input_rels[0].node2_id == 1
        assert len(output_rels) == 1
        assert output_rels[0].node1_id == run.id
        assert output_rels[0].node2_id == 2

    def test_add_run_node_runtime(self):
        graph = _make_project_graph()
        run = graph.add_run_node(
            name="live run",
            run_type="script",
            discovery="runtime",
        )
        assert run.properties["run_status"] == "completed"
        assert run.properties["discovery"] == "runtime"


# =========================================================
# RunCandidate / AbstractRunDiscoverer テスト
# =========================================================


class _TestDiscoverer(AbstractRunDiscoverer):
    """テスト用の具象RunDiscoverer"""

    priority = 200

    def __init__(self, candidates: list[RunCandidate] | None = None):
        self._candidates = candidates or []

    def discover_runs(self, graph: ProjectGraph) -> list[RunCandidate]:
        return self._candidates


class TestRunCandidate:
    def test_basic_creation(self):
        candidate = RunCandidate(
            name="test run",
            run_type="cae_job",
            input_node_ids=[1, 2],
            output_node_ids=[3],
            media_node_ids=[4],
        )
        assert candidate.name == "test run"
        assert candidate.run_type == "cae_job"
        assert candidate.discovery == "static"

    def test_default_values(self):
        candidate = RunCandidate(name="minimal", run_type="script")
        assert candidate.input_node_ids == []
        assert candidate.output_node_ids == []
        assert candidate.media_node_ids == []
        assert candidate.properties == {}
        assert candidate.discovery == "static"


class TestAbstractRunDiscoverer:
    def test_apply_creates_run_nodes(self):
        graph = _make_project_graph(
            nodes=[
                Node(id=1, type="go", name="input.inp", format="inp"),
                Node(id=2, type="file", name="output.odb", format="odb"),
            ],
        )
        candidates = [
            RunCandidate(
                name="CAE Run",
                run_type="cae_job",
                input_node_ids=[1],
                output_node_ids=[2],
            ),
        ]
        discoverer = _TestDiscoverer(candidates)
        result = discoverer.apply(graph)

        runs = result.get_run_nodes()
        assert len(runs) == 1
        assert runs[0].name == "CAE Run"
        assert runs[0].category == NodeCategory.RUN

        inputs = result.get_run_inputs(runs[0])
        assert len(inputs) == 1
        assert inputs[0].id == 1

    def test_apply_multiple_candidates(self):
        graph = _make_project_graph(
            nodes=[
                Node(id=1, type="go", name="input.inp", format="inp"),
                Node(id=2, type="file", name="output.odb", format="odb"),
                Node(id=3, type="dataset", name="data.csv", format="csv"),
                Node(id=4, type="model_checkpoint", name="model.pt", format="pt"),
            ],
        )
        candidates = [
            RunCandidate(name="CAE Run", run_type="cae_job", input_node_ids=[1], output_node_ids=[2]),
            RunCandidate(name="ML Run", run_type="ml_training", input_node_ids=[3], output_node_ids=[4]),
        ]
        discoverer = _TestDiscoverer(candidates)
        result = discoverer.apply(graph)
        runs = result.get_run_nodes()
        assert len(runs) == 2

    def test_apply_no_candidates(self):
        graph = _make_project_graph()
        discoverer = _TestDiscoverer([])
        result = discoverer.apply(graph)
        assert result.get_run_nodes() == []

    def test_discoverer_priority(self):
        discoverer = _TestDiscoverer()
        assert discoverer.priority == 200


# =========================================================
# RunQueryService テスト
# =========================================================


def _build_comparison_graph() -> GraphModel:
    """比較テスト用のグラフを構築

    2つのCAE Run（同じ媒体、異なる入力）と1つのML Runを含む。
    """
    nodes = [
        # ファイル群
        Node(id=1, type="go", name="go_idx1_v1.inp", format="inp"),
        Node(id=2, type="go", name="go_idx2_v1.inp", format="inp"),
        Node(id=3, type="file", name="go_idx1_v1.odb", format="odb"),
        Node(id=4, type="file", name="go_idx2_v1.odb", format="odb"),
        Node(id=5, type="file", name="abaqus", format=""),
        # データ/モデル
        Node(id=6, type="dataset", name="data.csv", format="csv"),
        Node(id=7, type="model_checkpoint", name="model.pt", format="pt"),
        Node(id=8, type="training_script", name="train.py", format="py"),
        # Run群
        Node(
            id=100,
            type="cae_job",
            name="Run 1",
            format="",
            category=NodeCategory.RUN,
            properties={"run_type": "cae_job", "run_status": "latent", "solver": "abaqus"},
        ),
        Node(
            id=101,
            type="cae_job",
            name="Run 2",
            format="",
            category=NodeCategory.RUN,
            properties={"run_type": "cae_job", "run_status": "latent", "solver": "abaqus"},
        ),
        Node(
            id=200,
            type="ml_training",
            name="ML Run",
            format="",
            category=NodeCategory.RUN,
            properties={"run_type": "ml_training", "run_status": "completed"},
        ),
    ]
    relations = [
        # Run 1: input=inp1, output=odb1, media=abaqus
        Relation(id=1, label=RUN_INPUT, node1_id=100, node2_id=1),
        Relation(id=2, label=RUN_OUTPUT, node1_id=100, node2_id=3),
        Relation(id=3, label=RUN_MEDIA, node1_id=100, node2_id=5),
        # Run 2: input=inp2, output=odb2, media=abaqus
        Relation(id=4, label=RUN_INPUT, node1_id=101, node2_id=2),
        Relation(id=5, label=RUN_OUTPUT, node1_id=101, node2_id=4),
        Relation(id=6, label=RUN_MEDIA, node1_id=101, node2_id=5),
        # ML Run: input=data, output=model, media=train.py
        Relation(id=7, label=RUN_INPUT, node1_id=200, node2_id=6),
        Relation(id=8, label=RUN_OUTPUT, node1_id=200, node2_id=7),
        Relation(id=9, label=RUN_MEDIA, node1_id=200, node2_id=8),
    ]
    return GraphModel(nodes=nodes, relations=relations)


class TestRunQueryService:
    def test_get_runs_all(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        runs = svc.get_runs()
        assert len(runs) == 3

    def test_get_runs_by_type(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        cae = svc.get_runs(run_type="cae_job")
        assert len(cae) == 2
        ml = svc.get_runs(run_type="ml_training")
        assert len(ml) == 1

    def test_get_runs_by_status(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        latent = svc.get_runs(run_status="latent")
        assert len(latent) == 2
        completed = svc.get_runs(run_status="completed")
        assert len(completed) == 1

    def test_get_run_io(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        run1 = svc.get_runs(run_type="cae_job")[0]
        io = svc.get_run_io(run1)
        assert len(io.inputs) == 1
        assert len(io.outputs) == 1
        assert len(io.media) == 1
        assert io.inputs[0].name == "go_idx1_v1.inp"
        assert io.outputs[0].name == "go_idx1_v1.odb"
        assert io.media[0].name == "abaqus"

    def test_find_comparable_runs_same_media(self):
        """同じ媒体（abaqus）、異なる入力のRunが比較対象になること"""
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        run1 = next(r for r in svc.get_runs() if r.id == 100)
        groups = svc.find_comparable_runs(run1)

        # 同一media・異なるinputのグループがあるはず
        input_groups = [g for g in groups if g.axis == ComparisonAxis.INPUT]
        assert len(input_groups) == 1
        assert len(input_groups[0].runs) == 2

    def test_diff_runs(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        runs = svc.get_runs(run_type="cae_job")
        run1 = next(r for r in runs if r.id == 100)
        run2 = next(r for r in runs if r.id == 101)

        diff = svc.diff_runs(run1, run2)
        # 入力は異なる（inp1 vs inp2）
        assert len(diff.diff_inputs[0]) == 1
        assert len(diff.diff_inputs[1]) == 1
        assert diff.diff_inputs[0][0].name == "go_idx1_v1.inp"
        assert diff.diff_inputs[1][0].name == "go_idx2_v1.inp"
        # 出力も異なる
        assert len(diff.diff_outputs[0]) == 1
        assert len(diff.diff_outputs[1]) == 1
        # 媒体は共通（abaqus）
        assert len(diff.common_media) == 1
        assert diff.common_media[0].name == "abaqus"

    def test_diff_runs_property_diffs(self):
        graph = _build_comparison_graph()
        svc = RunQueryService(graph)
        runs = svc.get_runs(run_type="cae_job")
        run1 = next(r for r in runs if r.id == 100)
        ml_run = svc.get_runs(run_type="ml_training")[0]

        diff = svc.diff_runs(run1, ml_run)
        # run_typeが異なる
        assert "run_type" in diff.property_diffs
        assert diff.property_diffs["run_type"] == ("cae_job", "ml_training")

    def test_empty_graph(self):
        graph = GraphModel.empty()
        svc = RunQueryService(graph)
        assert svc.get_runs() == []


# =========================================================
# GraphStorage 後方互換性テスト
# =========================================================


class TestStorageBackwardCompat:
    def test_load_graph_without_category(self, tmp_path: Path):
        """categoryフィールドがないgraph.yamlの読み込み"""
        import yaml

        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        storage_dir = tmp_path / ".jj" / "storage"
        storage_dir.mkdir(parents=True)
        graph_path = storage_dir / "graph.yaml"

        data = {
            "nodes": [
                {"id": 1, "type": "go", "name": "test.inp", "format": "inp", "properties": {}},
            ],
            "relations": [],
        }
        with graph_path.open("w") as f:
            yaml.safe_dump(data, f)

        graph = storage.load(tmp_path)
        assert len(graph.nodes) == 1
        assert graph.nodes[0].category == NodeCategory.FILE

    def test_save_and_load_with_category(self, tmp_path: Path):
        """category付きNodeの保存→読み込みラウンドトリップ"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()

        graph = GraphModel(
            nodes=[
                Node(id=1, type="go", name="test.inp", format="inp", category=NodeCategory.FILE),
                Node(
                    id=2,
                    type="cae_job",
                    name="run1",
                    format="",
                    category=NodeCategory.RUN,
                    properties={"run_type": "cae_job"},
                ),
                Node(id=3, type="material_def", name="Steel", format="", category=NodeCategory.DATA),
            ],
            relations=[
                Relation(id=1, label=RUN_INPUT, node1_id=2, node2_id=1),
            ],
        )

        storage.save(tmp_path, graph)
        loaded = storage.load(tmp_path)

        assert len(loaded.nodes) == 3
        assert loaded.nodes[0].category == NodeCategory.FILE
        assert loaded.nodes[1].category == NodeCategory.RUN
        assert loaded.nodes[2].category == NodeCategory.DATA
        assert loaded.relations[0].label == RUN_INPUT
