"""CaeRunDiscovererのテスト

CAE潜在Run発見パーサーの単体テスト。
入力ファイル（go_*.inp）と結果ファイル（.sta, .msg, .dat）のペアから
CAE Run候補が正しく生成されることを検証する。
"""

from __future__ import annotations

from pathlib import Path

from config import GraphConfig
from jj_types import (
    RUN_INPUT,
    RUN_OUTPUT,
    Node,
    NodeCategory,
    Relation,
)
from services.graph.project_graph import ProjectGraph
from services.parse.parsers.cae_run_discoverer import CaeRunDiscoverer


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


class TestCaeRunDiscovererBasic:
    """基本的なCAE Run発見テスト"""

    def test_discover_abaqus_run_from_basename_match(self):
        """同一basename（go_idx1_v1）の.inpと.staペアからRunが発見される"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")

        graph = _make_project_graph(nodes=[inp, sta])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        assert c.run_type == "cae_job"
        assert 1 in c.input_node_ids
        assert 2 in c.output_node_ids
        assert c.properties["solver"] == "abaqus"
        assert c.discovery == "static"

    def test_discover_multiple_result_files(self):
        """同一basenameで複数の結果ファイル（.sta, .msg, .dat）がある場合"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")
        msg = Node(id=3, type="go", name="go_idx1_v1", format="msg")
        dat = Node(id=4, type="go", name="go_idx1_v1", format="dat")

        graph = _make_project_graph(nodes=[inp, sta, msg, dat])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        assert 1 in c.input_node_ids
        assert 2 in c.output_node_ids
        assert 3 in c.output_node_ids
        assert 4 in c.output_node_ids

    def test_no_result_files_no_run(self):
        """結果ファイルがなければRunは発見されない"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        mesh = Node(id=2, type="mesh", name="mesh_t50", format="inp")

        graph = _make_project_graph(nodes=[inp, mesh])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 0

    def test_mesh_file_not_treated_as_run_input(self):
        """mesh_*.inpファイルは計算入力とみなされない"""
        mesh = Node(id=1, type="mesh", name="mesh_t50", format="inp")
        sta = Node(id=2, type="mesh", name="mesh_t50", format="sta")

        graph = _make_project_graph(nodes=[mesh, sta])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 0

    def test_empty_graph_no_runs(self):
        """空グラフではRunは発見されない"""
        graph = _make_project_graph()
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)
        assert len(candidates) == 0


class TestCaeRunDiscovererRelations:
    """リレーションを活用したCAE Run発見テスト"""

    def test_result_of_relation_adds_outputs(self):
        """result_of関係を辿って結果ノードが出力に含まれる"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")

        rels = [
            Relation(id=1, label="result_of", node1_id=2, node2_id=1),
        ]
        graph = _make_project_graph(nodes=[inp, sta], relations=rels)
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        assert 2 in candidates[0].output_node_ids

    def test_has_output_relation_adds_outputs(self):
        """has_output関係から出力ノードが追加される"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")
        csv_out = Node(id=3, type="file", name="go_idx1_v1_RF", format="csv")

        rels = [
            Relation(id=1, label="has_output", node1_id=1, node2_id=3),
        ]
        graph = _make_project_graph(nodes=[inp, sta, csv_out], relations=rels)
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        # .staはbasename一致で出力に含まれ、.csvはhas_output関係で含まれる
        assert 2 in candidates[0].output_node_ids
        assert 3 in candidates[0].output_node_ids

    def test_includes_relation_adds_inputs(self):
        """includes関係にあるファイルが追加入力に含まれる"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        mesh = Node(id=2, type="mesh", name="mesh_t50", format="inp")
        mat = Node(id=3, type="material", name="material_m01", format="inp")
        sta = Node(id=4, type="go", name="go_idx1_v1", format="sta")

        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
            Relation(id=2, label="includes", node1_id=1, node2_id=3),
        ]
        graph = _make_project_graph(nodes=[inp, mesh, mat, sta], relations=rels)
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 1
        c = candidates[0]
        # 入力: go_inp + mesh + material
        assert 1 in c.input_node_ids
        assert 2 in c.input_node_ids
        assert 3 in c.input_node_ids
        # 出力: .sta
        assert 4 in c.output_node_ids


class TestCaeRunDiscovererMultipleRuns:
    """複数Run発見テスト"""

    def test_multiple_runs_different_index(self):
        """異なるインデックスの入力ファイルから複数のRunが発見される"""
        inp1 = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta1 = Node(id=2, type="go", name="go_idx1_v1", format="sta")
        inp2 = Node(id=3, type="go", name="go_idx2_v1", format="inp")
        sta2 = Node(id=4, type="go", name="go_idx2_v1", format="sta")

        graph = _make_project_graph(nodes=[inp1, sta1, inp2, sta2])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 2
        names = {c.name for c in candidates}
        assert "go_idx1_v1 abaqus解析" in names
        assert "go_idx2_v1 abaqus解析" in names

    def test_different_versions_separate_runs(self):
        """異なるバージョンは別々のRunとして発見される"""
        inp_v1 = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta_v1 = Node(id=2, type="go", name="go_idx1_v1", format="sta")
        inp_v2 = Node(id=3, type="go", name="go_idx1_v2", format="inp")
        sta_v2 = Node(id=4, type="go", name="go_idx1_v2", format="sta")

        graph = _make_project_graph(nodes=[inp_v1, sta_v1, inp_v2, sta_v2])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert len(candidates) == 2


class TestCaeRunDiscovererApply:
    """apply()メソッド（基底クラスのグラフ更新ロジック）テスト"""

    def test_apply_creates_run_nodes(self):
        """apply()がRun Nodeとリレーションをグラフに追加する"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")

        graph = _make_project_graph(nodes=[inp, sta])
        discoverer = CaeRunDiscoverer()
        result_graph = discoverer.apply(graph)

        # Run Nodeが追加されている
        run_nodes = [n for n in result_graph.nodes if n.category == NodeCategory.RUN]
        assert len(run_nodes) == 1
        run_node = run_nodes[0]
        assert run_node.type == "cae_job"
        assert run_node.properties["run_type"] == "cae_job"
        assert run_node.properties["run_status"] == "latent"
        assert run_node.properties["solver"] == "abaqus"

        # run_input/run_output リレーションが追加されている
        run_rels = [r for r in result_graph.relations if r.node1_id == run_node.id]
        input_rels = [r for r in run_rels if r.label == RUN_INPUT]
        output_rels = [r for r in run_rels if r.label == RUN_OUTPUT]

        assert len(input_rels) >= 1
        assert len(output_rels) >= 1
        assert input_rels[0].node2_id == inp.id
        assert sta.id in [r.node2_id for r in output_rels]

    def test_apply_with_analysis_status(self):
        """analysis_statusがpropertyに伝搬される"""
        inp = Node(
            id=1,
            type="go",
            name="go_idx1_v1",
            format="inp",
            properties={"analysis_status": "completed"},
        )
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")

        graph = _make_project_graph(nodes=[inp, sta])
        discoverer = CaeRunDiscoverer()
        result_graph = discoverer.apply(graph)

        run_nodes = [n for n in result_graph.nodes if n.category == NodeCategory.RUN]
        assert len(run_nodes) == 1
        assert run_nodes[0].properties["analysis_status"] == "completed"


class TestCaeRunDiscovererSolverDetection:
    """ソルバー検出テスト"""

    def test_detect_abaqus_from_inp(self):
        """format=inpからAbaqusと判定"""
        inp = Node(id=1, type="go", name="go_idx1_v1", format="inp")
        sta = Node(id=2, type="go", name="go_idx1_v1", format="sta")

        graph = _make_project_graph(nodes=[inp, sta])
        discoverer = CaeRunDiscoverer()
        candidates = discoverer.discover_runs(graph)

        assert candidates[0].properties["solver"] == "abaqus"

    def test_priority_is_200(self):
        """priorityが200（ファイル解析パーサーの後）"""
        assert CaeRunDiscoverer.priority == 200
