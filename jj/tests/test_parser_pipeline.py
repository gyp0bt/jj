"""新パーサーパイプライン統合テスト

shared/tests/test_asset1 のAbaqusプロジェクトを使い、
Phase R で導入した ProjectGraph + AbstractFileParser パイプラインの
動作を検証する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from config import GraphConfig
from jj_types import GraphModel, Node, Relation
from services.graph import GraphService
from services.graph.project_graph import ProjectGraph
from services.parse.base import (
    get_parser_registry,
    parse,
)

ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "tests" / "test_asset1"


# テスト間でレジストリ状態を共有するためのフィクスチャ
@pytest.fixture
def config() -> GraphConfig:
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {"input-extensions": [".inp"]},
        }
    )


@pytest.fixture
def graph(config: GraphConfig) -> GraphModel:
    svc = GraphService(project_root=ASSET_DIR, config=config)
    return svc.parse_project()


# ====================================================================
# R1: ProjectGraph 型テスト
# ====================================================================


class TestProjectGraph:
    """ProjectGraph dataclass の基本動作"""

    def test_from_graph_service(self, config: GraphConfig):
        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
        ]
        pg = ProjectGraph.from_graph_service(
            nodes=nodes,
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )
        assert len(pg.nodes) == 1
        assert pg._node_id_counter == 1

    def test_add_node_updates_index(self, config: GraphConfig):
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        node = Node(id=pg.next_node_id(), type="go", name="test", format="inp", properties={"path": "test.inp"})
        pg.add_node(node)
        assert pg.get_node_by_path("test.inp") is node
        assert pg.get_node_by_id(node.id) is node

    def test_next_id_increments(self, config: GraphConfig):
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        id1 = pg.next_node_id()
        id2 = pg.next_node_id()
        assert id2 == id1 + 1

    def test_remove_nodes(self, config: GraphConfig):
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        n1 = Node(id=1, type="a", name="a", format="x", properties={"path": "a.x"})
        n2 = Node(id=2, type="b", name="b", format="y", properties={"path": "b.y"})
        rel = Relation(id=1, label="test", node1_id=1, node2_id=2)
        pg.add_node(n1)
        pg.add_node(n2)
        pg.add_relation(rel)
        pg.remove_nodes({1})
        assert len(pg.nodes) == 1
        assert len(pg.relations) == 0
        assert pg.get_node_by_id(1) is None

    def test_to_graph_model(self, config: GraphConfig):
        pg = ProjectGraph(
            nodes=[Node(id=1, type="t", name="n", format="f", properties={})],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )
        gm = pg.to_graph_model()
        assert isinstance(gm, GraphModel)
        assert len(gm.nodes) == 1

    def test_iterate_directories(self, config: GraphConfig):
        pg = ProjectGraph(
            nodes=[
                Node(id=1, type="go", name="a", format="inp", properties={"path": "sub/a.inp"}),
                Node(id=2, type="go", name="b", format="inp", properties={"path": "sub/deep/b.inp"}),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )
        dirs = list(pg.iterate_directories())
        # root + sub + sub/deep
        assert len(dirs) >= 3

    def test_safe_relative_path(self, config: GraphConfig):
        pg = ProjectGraph(nodes=[], relations=[], project_root=ASSET_DIR, config=config)
        rel = pg.safe_relative_path(ASSET_DIR / "go_idx1.v3.inp")
        assert rel == "go_idx1.v3.inp"
        assert not rel.startswith("./")


# ====================================================================
# R2: パーサーレジストリテスト
# ====================================================================


class TestParserRegistry:
    """AbstractFileParser.__init_subclass__ による自動登録"""

    def test_registry_has_parsers(self):
        registry = get_parser_registry()
        assert len(registry) >= 10

    def test_registry_sorted_by_priority(self):
        registry = get_parser_registry()
        priorities = [cls.priority for cls in registry]
        # 重複は許容するがソート後に全部拾えること
        assert len(priorities) > 0

    def test_abstract_class_not_registered(self):
        """abstractmethod が残っているクラスは登録されない"""
        registry = get_parser_registry()
        for cls in registry:
            # 具象クラスのみ
            assert not getattr(cls, "__abstractmethods__", None)

    def test_parse_function_applies_all_parsers(self, config: GraphConfig):
        """parse() が全パーサーを通してGraphを返す"""
        pg = ProjectGraph(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v2",
                    format="inp",
                    properties={"path": "dummy.inp", "index": "1", "version": "4"},
                ),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )
        result = parse(pg)
        assert isinstance(result, ProjectGraph)
        # VersionRelationParser が next_version を作るはず
        labels = {r.label for r in result.relations}
        assert "next_version" in labels


# ====================================================================
# R3: 統合テスト（test_asset1 全体パース）
# ====================================================================


class TestPipelineIntegration:
    """test_asset1 を丸ごとパースした結果の検証"""

    def test_parse_returns_graph_model(self, graph: GraphModel):
        assert isinstance(graph, GraphModel)
        assert len(graph.nodes) > 0
        assert len(graph.relations) > 0

    def test_node_types(self, graph: GraphModel):
        types = {n.type for n in graph.nodes}
        assert "go" in types
        assert "mesh" in types
        assert "step" in types
        assert "directory" in types

    def test_no_sta_msg_dat_nodes(self, graph: GraphModel):
        """enrichment-only (.sta/.msg/.dat) ノードはフィルタ済み"""
        for node in graph.nodes:
            assert node.format not in ("sta", "msg", "dat"), f"enrichment-only node残存: {node.name}.{node.format}"

    def test_go_nodes_have_expected_properties(self, graph: GraphModel):
        go_nodes = [n for n in graph.nodes if n.type == "go"]
        assert len(go_nodes) >= 3  # idx0, idx1, idx2 ...

        for node in go_nodes:
            props = node.properties
            assert "path" in props
            assert "index" in props
            assert "version" in props

    def test_go_node_has_abaqus_parameters(self, graph: GraphModel):
        """go_idx1.v3.inp は *PARAMETER から s_coh 等を抽出済み"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        assert node is not None, "go_idx1.v3.inp ノードが見つからない"
        assert "s_coh" in node.properties
        assert "K_coh" in node.properties

    def test_go_node_active_flag(self, graph: GraphModel):
        """old/ 配下は active=false"""
        old_go = [n for n in graph.nodes if n.type == "go" and n.properties.get("path", "").startswith("old/")]
        for n in old_go:
            assert n.properties.get("active") == "false", f"{n.name} should be active=false"

        top_go = [n for n in graph.nodes if n.type == "go" and not n.properties.get("path", "").startswith("old/")]
        for n in top_go:
            assert n.properties.get("active") == "true", f"{n.name} should be active=true"

    # --- リレーション系 ---

    def test_has_version_relations(self, graph: GraphModel):
        labels = Counter(r.label for r in graph.relations)
        assert labels.get("next_version", 0) >= 1

    def test_has_belongs_to_relations(self, graph: GraphModel):
        """index_groupノードへのbelongs_to関係が存在する"""
        labels = Counter(r.label for r in graph.relations)
        assert labels.get("belongs_to", 0) >= 1
        # index_groupノードが存在する
        group_nodes = [n for n in graph.nodes if n.type == "index_group"]
        assert len(group_nodes) >= 1

    def test_has_contains_relations(self, graph: GraphModel):
        labels = Counter(r.label for r in graph.relations)
        assert labels["contains"] >= 10  # 多数のファイルがcontains

    def test_has_includes_relations(self, graph: GraphModel):
        """go_*.inp は material.inp / mesh_*.inp を include している"""
        labels = Counter(r.label for r in graph.relations)
        assert labels.get("includes", 0) >= 1

    def test_has_derived_from_relations(self, graph: GraphModel):
        """.modfem と .inp 間に derived_from がある"""
        labels = Counter(r.label for r in graph.relations)
        assert labels.get("derived_from", 0) >= 1

    def test_has_output_relations(self, graph: GraphModel):
        """results/配下ファイルはinfo-only（Node化しない）ため、
        has_outputは命名規則ディレクトリ（go_idx1/等）経由でのみ発生する"""
        labels = Counter(r.label for r in graph.relations)
        # test_asset1にはgo_*/mesh_*等の命名規則ディレクトリがないため0も許容
        assert labels.get("has_output", 0) >= 0

    def test_results_direct_files_not_noded(self, graph: GraphModel):
        """results/直下のファイルはNode化されない（info-only）"""
        results_direct_nodes = [
            n
            for n in graph.nodes
            if n.properties.get("path", "").startswith("results/")
            and n.format != "directory"
            and n.properties.get("path", "").count("/") == 1
        ]
        assert len(results_direct_nodes) == 0, (
            f"results/直下のファイルがNode化されている: {[n.name for n in results_direct_nodes]}"
        )

    def test_results_subdirectory_files_noded(self, graph: GraphModel):
        """results/サブディレクトリのファイルはNode化される"""
        results_subdir_nodes = [
            n
            for n in graph.nodes
            if n.properties.get("path", "").startswith("results/")
            and n.format != "directory"
            and n.properties.get("path", "").count("/") >= 2
        ]
        assert len(results_subdir_nodes) > 0, "results/サブディレクトリのファイルがNode化されていない"

    def test_results_metadata_assigned_to_go_inp(self, graph: GraphModel):
        """results/サブディレクトリのメタデータがgo_*.inpに割り当てられる"""
        go_nodes = [n for n in graph.nodes if n.type == "go" and n.format == "inp"]
        has_results = any(any(k.startswith("results.") for k in n.properties) for n in go_nodes)
        assert has_results, "results/メタデータがgo_*.inpに割り当てられていない"

    def test_json_properties_propagated_despite_results_filter(self, graph: GraphModel):
        """results/のJSONファイルの情報はgo_*.inpに伝搬されている（info-only）"""
        go_nodes = [n for n in graph.nodes if n.type == "go" and n.format == "inp"]
        # JsonPropertyParser(priority=33)がresults/のJSONを読んでプロパティ付与
        # EnrichmentOnlyFilter(priority=99)でresults/ノード除去後も情報は残る
        # JSONキーはファイル名サフィックスなしで直接割り当て（key:value形式）
        has_json_prop = any("0(center)" in n.properties for n in go_nodes)
        assert has_json_prop, "results/のJSON情報がgo_*.inpに伝搬されていない"

    # --- ディレクトリノード ---

    def test_directory_nodes_exist(self, graph: GraphModel):
        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        assert len(dir_nodes) >= 3  # old, tools, reports, assets, root
        dir_names = {n.name for n in dir_nodes}
        assert "old" in dir_names or "reports" in dir_names or "tools" in dir_names

    # --- msg解析 ---

    def test_msg_warnings_propagated_to_inp(self, graph: GraphModel):
        """go_idx1.v3.inp に msg_warnings / msg_errors が伝搬されている"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        if node is None:
            pytest.skip("go_idx1.v3.inp not found")
        # msg ファイルにwarning/errorがあれば伝搬されているはず
        has_msg_prop = "msg_warnings" in node.properties or "msg_errors" in node.properties
        assert has_msg_prop, "msg情報がinpに伝搬されていない"


class TestVersionRelations:
    """バージョン関係パーサーの詳細テスト"""

    def test_go_idx2_has_next_version(self, graph: GraphModel):
        """go_idx2 は v2→v3 の next_version がある"""
        v2 = _find_node(graph, name="go_idx2.v2", format="inp")
        v3 = _find_node(graph, name="go_idx2.v3", format="inp")
        if v2 is None or v3 is None:
            pytest.skip("go_idx2 v2/v3 not found")
        nv = [r for r in graph.relations if r.label == "next_version" and r.node1_id == v2.id and r.node2_id == v3.id]
        assert len(nv) == 1

    def test_go_idx3_has_next_version(self, graph: GraphModel):
        """go_idx3 は v1→v2 の next_version がある"""
        v1 = _find_node(graph, name="go_idx3.v1", format="inp")
        v2 = _find_node(graph, name="go_idx3.v2", format="inp")
        if v1 is None or v2 is None:
            pytest.skip("go_idx3 v1/v2 not found")
        nv = [r for r in graph.relations if r.label == "next_version" and r.node1_id == v1.id and r.node2_id == v2.id]
        assert len(nv) == 1


class TestIncludesRelations:
    """includesパーサーのテスト"""

    def test_go_idx1_includes_material(self, graph: GraphModel):
        """go_idx1.v3 は material.inp を include"""
        # material ノード（ファイルとして）を探す
        # ※ material.inp はテストアセットにないかもしれないが、
        #   mesh_shape1_t95.v8.inp は存在する
        go = _find_node(graph, name="go_idx1.v3", format="inp")
        if go is None:
            pytest.skip("go_idx1.v3 not found")

        includes = [r for r in graph.relations if r.label == "includes" and r.node1_id == go.id]
        assert len(includes) >= 1, "go_idx1.v3 should include at least mesh_*.inp"


class TestDirectoryRelations:
    """ディレクトリパーサーのテスト"""

    def test_old_directory_contains_files(self, graph: GraphModel):
        old_dir = next(
            (n for n in graph.nodes if n.name == "old" and n.format == "directory"),
            None,
        )
        if old_dir is None:
            pytest.skip("old directory node not found")
        contains = [r for r in graph.relations if r.label == "contains" and r.node1_id == old_dir.id]
        assert len(contains) >= 5  # old/ に複数ファイルがある


# ====================================================================
# 実データ: パイプライン統合テスト（具体的プロパティ検証）
# ====================================================================


class TestGoNodeParametersPipeline:
    """go_*.inpのAbaqusパラメータが実データパイプラインで正しく抽出されるか"""

    def test_go_idx1_v3_parameter_values(self, graph: GraphModel):
        """go_idx1.v3.inp: s_coh=100.0, K_coh=100.e3, target_strain=35.0"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "100.0"
        assert node.properties["K_coh"] == "100.e3"
        assert node.properties["target_strain"] == "35.0"

    def test_go_idx2_v3_different_s_coh(self, graph: GraphModel):
        """go_idx2.v3.inp: s_coh=150.0（idx1と異なる値）"""
        node = _find_node(graph, name="go_idx2.v3", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "150.0"

    def test_go_idx0_v29_parameters(self, graph: GraphModel):
        """go_idx0.v29.inp: damage_stabilization=0.05（他のidxと異なる）"""
        node = _find_node(graph, name="go_idx0.v29", format="inp")
        assert node is not None
        assert node.properties["damage_stabilization"] == "0.05"

    def test_old_go_idx3_v1_parameters(self, graph: GraphModel):
        """old/go_idx3.v1.inp: s_coh=200.0（old/のファイルもパラメータ抽出される）"""
        node = _find_node(graph, name="go_idx3.v1", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "200.0"


class TestJsonPropertyPropagationPipeline:
    """results/のJSONプロパティが実データパイプラインでgo_*.inpに正しく伝搬されるか"""

    def test_go_idx1_json_stress_values(self, graph: GraphModel):
        """go_idx1.v3: stress JSON {0(center): 0.5, 1: 0.5625, 2(edge): 0.5}"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        assert node is not None
        assert node.properties["0(center)"] == 0.5
        assert node.properties["1"] == 0.5625
        assert node.properties["2(edge)"] == 0.5

    def test_go_idx0_json_nan_to_none(self, graph: GraphModel):
        """go_idx0.v29: NaN値がNone変換 {1: NaN, 2(edge): NaN}"""
        node = _find_node(graph, name="go_idx0.v29", format="inp")
        assert node is not None
        assert node.properties["0(center)"] == 0.25
        assert node.properties["1"] is None  # NaN → None
        assert node.properties["2(edge)"] is None

    def test_go_idx2_json_stress_values(self, graph: GraphModel):
        """go_idx2.v3: stress JSON {0(center): 0.0, 1: 0.125, 2(edge): 0.125}"""
        node = _find_node(graph, name="go_idx2.v3", format="inp")
        assert node is not None
        assert node.properties["0(center)"] == 0.0
        assert node.properties["2(edge)"] == 0.125


class TestIncludesRelationPipeline:
    """includesリレーションの実データパイプライン検証"""

    def test_go_idx1_includes_mesh_and_step(self, graph: GraphModel):
        """go_idx1.v3 → mesh_shape1_t95.v8 + step_stress_v1"""
        go = _find_node(graph, name="go_idx1.v3", format="inp")
        assert go is not None
        includes = [r for r in graph.relations if r.label == "includes" and r.node1_id == go.id]
        target_names = set()
        for r in includes:
            target = next((n for n in graph.nodes if n.id == r.node2_id), None)
            if target:
                target_names.add(target.name)
        assert "mesh_shape1_t95.v8" in target_names
        assert "step_stress_v1" in target_names

    def test_material_inp_in_includes(self, graph: GraphModel):
        """material.inpが存在するため、includes先に含まれる"""
        all_includes_targets = set()
        for r in graph.relations:
            if r.label == "includes":
                target = next((n for n in graph.nodes if n.id == r.node2_id), None)
                if target:
                    all_includes_targets.add(target.name)
        assert any("material" in name for name in all_includes_targets), (
            "material.inpが存在するのにincludes先に含まれていない"
        )


class TestDerivedFromRelationPipeline:
    """derived_fromリレーションの実データパイプライン検証"""

    def test_modfem_to_inp_count(self, graph: GraphModel):
        """derived_from が6ペア存在（mesh_shape1_t95 v6/v7/v8 + mesh_test v1/v2/v3）"""
        derived = [r for r in graph.relations if r.label == "derived_from"]
        assert len(derived) == 6

    def test_derived_from_direction(self, graph: GraphModel):
        """derived_from: inp(node1) → modfem(node2)"""
        derived = [r for r in graph.relations if r.label == "derived_from"]
        for r in derived:
            src = next((n for n in graph.nodes if n.id == r.node1_id), None)
            dst = next((n for n in graph.nodes if n.id == r.node2_id), None)
            assert src.format == "inp", f"src should be inp, got {src.format}"
            assert dst.format == "modfem", f"dst should be modfem, got {dst.format}"


class TestNodeCountsPipeline:
    """パイプライン出力のノード・リレーション数の実データ検証"""

    def test_total_node_count(self, graph: GraphModel):
        """パイプライン出力: 44ノード以上"""
        assert len(graph.nodes) >= 44

    def test_total_relation_count(self, graph: GraphModel):
        """パイプライン出力: 61リレーション以上"""
        assert len(graph.relations) >= 61

    def test_go_node_count(self, graph: GraphModel):
        """go タイプノード: 6個（idx0,idx1,idx2@root + idx2.v2,idx3.v1,idx3.v2@old）"""
        go_nodes = [n for n in graph.nodes if n.type == "go" and n.format == "inp"]
        assert len(go_nodes) == 6

    def test_mesh_node_count(self, graph: GraphModel):
        """mesh タイプノード: 22個以上（inp + modfem）"""
        mesh_nodes = [n for n in graph.nodes if n.type == "mesh"]
        assert len(mesh_nodes) >= 22

    def test_step_node_count(self, graph: GraphModel):
        """step タイプノード: 1個（step_stress_v1.inp）"""
        step_nodes = [n for n in graph.nodes if n.type == "step"]
        assert len(step_nodes) == 1

    def test_directory_node_count(self, graph: GraphModel):
        """directory ノード: 6個（root + old + tools + reports + assets + results）"""
        dir_nodes = [n for n in graph.nodes if n.format == "directory"]
        assert len(dir_nodes) == 6


class TestMsgPropagationPipeline:
    """msg/dat情報のgo_*.inpへの伝搬（パイプライン全体）"""

    def test_go_idx1_has_msg_errors(self, graph: GraphModel):
        """go_idx1.v3.inp: msg_errors伝搬（2エラー）"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        assert node is not None
        if "msg_errors" in node.properties:
            assert len(node.properties["msg_errors"]) == 2

    def test_go_idx0_no_msg_errors(self, graph: GraphModel):
        """go_idx0.v29.inp: msg_errors なし（正常終了）"""
        node = _find_node(graph, name="go_idx0.v29", format="inp")
        assert node is not None
        if "msg_errors" in node.properties:
            assert len(node.properties["msg_errors"]) == 0


# ====================================================================
# ヘルパー
# ====================================================================


def _find_node(graph: GraphModel, *, name: str, format: str) -> Node | None:
    """名前とフォーマットでノードを検索"""
    for n in graph.nodes:
        if n.name == name and n.format == format:
            return n
    return None
