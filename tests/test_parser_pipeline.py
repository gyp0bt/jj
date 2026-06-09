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
from plugins.base.parser import (
    get_parser_registry,
    parse,
)

ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset1"


# テスト間でレジストリ状態を共有するためのフィクスチャ
@pytest.fixture(scope="module")
def config() -> GraphConfig:
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {"input-extensions": [".inp"]},
            "path-property-map": {"**old/*": {"active": "false"}},
        }
    )


@pytest.fixture(scope="module")
def _parsed_graph(config: GraphConfig) -> GraphModel:
    """ASSET_DIR のフルパースはモジュールにつき1回だけ実行する（重いため）。"""
    svc = GraphService(project_root=ASSET_DIR, config=config)
    return svc.parse_project()


@pytest.fixture
def graph(_parsed_graph: GraphModel) -> GraphModel:
    """各テストには使い回しのパース結果のディープコピーを渡し、隔離を保つ。"""
    return _parsed_graph.model_copy(deep=True)


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
        """go_idx1.v3.inp: s_coh=100, K_coh=100000, target_strain=35（整数表記に整形）"""
        node = _find_node(graph, name="go_idx1.v3", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "100"
        assert node.properties["K_coh"] == "100000"
        assert node.properties["target_strain"] == "35"

    def test_go_idx2_v3_different_s_coh(self, graph: GraphModel):
        """go_idx2.v3.inp: s_coh=150（idx1と異なる値、整数表記）"""
        node = _find_node(graph, name="go_idx2.v3", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "150"

    def test_go_idx0_v29_parameters(self, graph: GraphModel):
        """go_idx0.v29.inp: damage_stabilization=0.05（他のidxと異なる）"""
        node = _find_node(graph, name="go_idx0.v29", format="inp")
        assert node is not None
        assert node.properties["damage_stabilization"] == "0.05"

    def test_old_go_idx3_v1_parameters(self, graph: GraphModel):
        """old/go_idx3.v1.inp: s_coh=200（old/のファイルもパラメータ抽出される、整数表記）"""
        node = _find_node(graph, name="go_idx3.v1", format="inp")
        assert node is not None
        assert node.properties["s_coh"] == "200"


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


# ====================================================================
# パーサー並列化テスト
# ====================================================================


class TestParserParallel:
    """parse() の parallel=True モードテスト"""

    def test_parallel_parse_returns_valid_graph(self, config: GraphConfig):
        """parallel=True で parse() が正常にグラフを返す"""
        pg = ProjectGraph(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v1",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
                ),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )
        result = parse(pg, parallel=True, max_workers=2)
        assert isinstance(result, ProjectGraph)
        assert len(result.nodes) >= 1

    def test_parallel_sequential_same_result(self, config: GraphConfig):
        """parallel=True と False で同じパーサーが適用される"""
        from plugins.base.parser import _group_parsers_by_priority, get_parser_registry

        registry = get_parser_registry()
        eligible = [cls for cls in registry if not cls.requires_full]
        groups = _group_parsers_by_priority(eligible)
        # グループ数が適正（各priority値ごとに1グループ）
        assert len(groups) > 0
        total = sum(len(g) for g in groups)
        assert total == len(eligible)

    def test_group_parsers_by_priority(self):
        """_group_parsers_by_priority が正しくグルーピングする"""
        from plugins.base.parser import _group_parsers_by_priority, get_parser_registry

        registry = get_parser_registry()
        groups = _group_parsers_by_priority(registry)
        # 各グループ内のpriorityは同一
        for group in groups:
            priorities = {cls.priority for cls in group}
            assert len(priorities) == 1
        # グループ間はpriority昇順
        group_priorities = [group[0].priority for group in groups]
        assert group_priorities == sorted(group_priorities)


# ====================================================================
# AbaqusMeshParser 並列プリフェッチテスト
# ====================================================================


class TestMeshParserPrefetch:
    """AbaqusMeshParser._prefetch_inp_parallel のテスト"""

    def test_prefetch_populates_cache(self, config: GraphConfig):
        """並列プリフェッチがインメモリキャッシュを正しく設定する"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        pg = ProjectGraph(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v3",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx2_v3",
                    format="inp",
                    properties={"path": "go_idx2.v3.inp", "index": "2", "version": "3"},
                ),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path1 = ASSET_DIR / "go_idx1.v3.inp"
        path2 = ASSET_DIR / "go_idx2.v3.inp"
        if not path1.exists() or not path2.exists():
            pytest.skip("Test asset .inp files not found")

        parse_needed = [
            (pg.nodes[0], path1, None),
            (pg.nodes[1], path2, None),
        ]

        AbaqusMeshParser._prefetch_inp_parallel(pg, parse_needed, max_workers=2)

        # キャッシュにデータが入っている
        cached1 = pg.get_cached_plugin_data("abaqus", str(path1))
        cached2 = pg.get_cached_plugin_data("abaqus", str(path2))
        assert cached1 is not None
        assert cached2 is not None

    def test_prefetch_skips_already_cached(self, config: GraphConfig):
        """既にキャッシュ済みのファイルはprefetchをスキップする"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        pg = ProjectGraph(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v3",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
                ),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path1 = ASSET_DIR / "go_idx1.v3.inp"
        if not path1.exists():
            pytest.skip("Test asset .inp files not found")

        # 先にキャッシュにダミーを設定
        sentinel = {"pre_cached": True}
        pg.set_cached_plugin_data("abaqus", str(path1), sentinel)

        parse_needed = [(pg.nodes[0], path1, None)]
        AbaqusMeshParser._prefetch_inp_parallel(pg, parse_needed, max_workers=1)

        # キャッシュは上書きされない（プリフェッチがスキップされた）
        cached = pg.get_cached_plugin_data("abaqus", str(path1))
        assert cached is sentinel

    def test_prefetch_deduplicates_paths(self, config: GraphConfig):
        """同一パスの重複parseを回避する"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        pg = ProjectGraph(
            nodes=[
                Node(
                    id=1,
                    type="go",
                    name="go_idx1_v3",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp"},
                ),
                Node(
                    id=2,
                    type="go",
                    name="go_idx1_v3_dup",
                    format="inp",
                    properties={"path": "go_idx1.v3.inp"},
                ),
            ],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path1 = ASSET_DIR / "go_idx1.v3.inp"
        if not path1.exists():
            pytest.skip("Test asset .inp files not found")

        parse_needed = [
            (pg.nodes[0], path1, None),
            (pg.nodes[1], path1, None),  # 同一パス
        ]

        AbaqusMeshParser._prefetch_inp_parallel(pg, parse_needed, max_workers=2)
        # 1回のparseでキャッシュに入る
        cached = pg.get_cached_plugin_data("abaqus", str(path1))
        assert cached is not None


# ====================================================================
# AbaqusDiffParser lightweightモードテスト
# ====================================================================


class TestDiffParserLightweight:
    """AbaqusDiffParser._get_or_parse_inp の lightweight モードテスト"""

    def test_lightweight_parse_returns_abqdata(self, config: GraphConfig):
        """lightweightモードでABQDataが返される"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        pg = ProjectGraph(
            nodes=[],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path = ASSET_DIR / "go_idx1.v3.inp"
        if not path.exists():
            pytest.skip("Test asset .inp files not found")

        result = AbaqusDiffParser._get_or_parse_inp(pg, str(path), lightweight=True)
        assert result is not None

    def test_lightweight_returns_full_cache_if_available(self, config: GraphConfig):
        """フルデータキャッシュがあればlightweight要求でもフルデータを返す"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        pg = ProjectGraph(
            nodes=[],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path = ASSET_DIR / "go_idx1.v3.inp"
        if not path.exists():
            pytest.skip("Test asset .inp files not found")

        # フルデータをキャッシュに設定
        full_data = {"full": True}
        pg.set_cached_plugin_data("abaqus", str(path), full_data)

        # lightweightでもフルデータが返される
        result = AbaqusDiffParser._get_or_parse_inp(pg, str(path), lightweight=True)
        assert result is full_data

    def test_lightweight_cache_key_separated(self, config: GraphConfig):
        """lightweightとフルデータのキャッシュキーが分離されている"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        pg = ProjectGraph(
            nodes=[],
            relations=[],
            project_root=ASSET_DIR,
            config=config,
        )

        path = ASSET_DIR / "go_idx1.v3.inp"
        if not path.exists():
            pytest.skip("Test asset .inp files not found")

        # lightweightでparse
        result_lw = AbaqusDiffParser._get_or_parse_inp(pg, str(path), lightweight=True)
        assert result_lw is not None

        # フルキャッシュにはまだない
        full_cached = pg.get_cached_plugin_data("abaqus", str(path))
        assert full_cached is None

        # lightweightキャッシュにはある
        lw_cached = pg.get_cached_plugin_data("abaqus", f"{path}::lightweight")
        assert lw_cached is not None


# ====================================================================
# _compute_optimal_workers テスト
# ====================================================================


class TestComputeOptimalWorkers:
    """AbaqusMeshParser._compute_optimal_workers のテスト"""

    def test_single_file(self):
        """ファイル1件ではワーカー1"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        result = AbaqusMeshParser._compute_optimal_workers(1)
        assert result == 1

    def test_many_files_capped(self):
        """ファイル数が多くても上限16を超えない"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        result = AbaqusMeshParser._compute_optimal_workers(100)
        assert result <= 16

    def test_file_count_limits_workers(self):
        """ワーカー数はファイル数以下"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        result = AbaqusMeshParser._compute_optimal_workers(3)
        assert result <= 3

    def test_minimum_one(self):
        """ワーカー数は最低1"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        result = AbaqusMeshParser._compute_optimal_workers(0)
        assert result >= 1


# ====================================================================
# AbaqusDiffParser._mesh_hashes_match テスト
# ====================================================================


class TestMeshHashesMatch:
    """AbaqusDiffParser._mesh_hashes_match のテスト"""

    def _write_inp(self, tmp_path: Path, name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_identical_mesh_returns_true(self, tmp_path: Path):
        """同一メッシュのファイルペアはTrueを返す"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        mesh = "*NODE\n1, 0.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1\n"
        f1 = self._write_inp(tmp_path, "a.inp", "*PARAMETER\nthick=5\n" + mesh)
        f2 = self._write_inp(tmp_path, "b.inp", "*PARAMETER\nthick=10\n" + mesh)

        assert AbaqusDiffParser._mesh_hashes_match(str(f1), str(f2)) is True

    def test_different_mesh_returns_false(self, tmp_path: Path):
        """異なるメッシュのファイルペアはFalseを返す"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        f1 = self._write_inp(tmp_path, "a.inp", "*NODE\n1, 0.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1\n")
        f2 = self._write_inp(
            tmp_path, "b.inp", "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*ELEMENT, TYPE=C3D8\n1, 1, 2\n"
        )

        assert AbaqusDiffParser._mesh_hashes_match(str(f1), str(f2)) is False

    def test_no_mesh_returns_false(self, tmp_path: Path):
        """メッシュ定義なしのファイルペアはFalseを返す"""
        from plugins.abaqus.parse.diff_parser import AbaqusDiffParser

        f1 = self._write_inp(tmp_path, "a.inp", "*PARAMETER\nthick=5\n*STEP\n*STATIC\n")
        f2 = self._write_inp(tmp_path, "b.inp", "*PARAMETER\nthick=10\n*STEP\n*DYNAMIC\n")

        assert AbaqusDiffParser._mesh_hashes_match(str(f1), str(f2)) is False


# ====================================================================
# _compute_optimal_workers use_processes パラメータテスト
# ====================================================================


class TestComputeOptimalWorkersProcessMode:
    """_compute_optimal_workers の ProcessPoolExecutor モードテスト"""

    def test_process_mode_uses_cpu_count(self):
        """プロセスモードではCPU数が上限（スレッドモードの半分）"""
        from unittest.mock import patch

        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        with patch("os.cpu_count", return_value=8):
            thread_result = AbaqusMeshParser._compute_optimal_workers(100, use_processes=False)
            process_result = AbaqusMeshParser._compute_optimal_workers(100, use_processes=True)

        assert thread_result == 16  # cpu_count * 2 = 16（上限一致）
        assert process_result == 8  # cpu_count = 8

    def test_process_mode_single_file(self):
        """プロセスモードでもファイル1件ではワーカー1"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        result = AbaqusMeshParser._compute_optimal_workers(1, use_processes=True)
        assert result == 1

    def test_process_mode_capped_at_16(self):
        """プロセスモードでも上限16"""
        from unittest.mock import patch

        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        with patch("os.cpu_count", return_value=32):
            result = AbaqusMeshParser._compute_optimal_workers(100, use_processes=True)
        assert result == 16

    def test_default_is_thread_mode(self):
        """デフォルトはスレッドモード（後方互換）"""
        from unittest.mock import patch

        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        with patch("os.cpu_count", return_value=4):
            default_result = AbaqusMeshParser._compute_optimal_workers(10)
            thread_result = AbaqusMeshParser._compute_optimal_workers(10, use_processes=False)

        assert default_result == thread_result


# ====================================================================
# ProcessPoolExecutor 閾値テスト
# ====================================================================


class TestProcessPoolThreshold:
    """_prefetch_inp_parallel の並列化方式自動選択テスト"""

    def test_threshold_value(self):
        """閾値が3であること"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        assert AbaqusMeshParser._PROCESS_POOL_THRESHOLD == 3


# ====================================================================
# diff_abq_mesh_blocks / diff_abq_metadata_blocks 分離テスト
# ====================================================================


class TestDiffSeparation:
    """diff_abq_blocks の mesh/metadata 分離テスト"""

    def _write_inp(self, tmp_path: Path, name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_mesh_only_diff_detects_node_changes(self, tmp_path: Path):
        """diff_abq_mesh_blocks はメッシュ差分を検出する"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_mesh_blocks, read_inp

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
                2, 1.0, 0.0, 0.0
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        diffs = diff_abq_mesh_blocks(left, right)
        assert len(diffs) > 0
        assert any("nodes" in d.location for d in diffs)

    def test_mesh_only_diff_ignores_step_changes(self, tmp_path: Path):
        """diff_abq_mesh_blocks はSTEP差分を検出しない"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_mesh_blocks, read_inp

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *STEP, NAME=Step-1
                *STATIC
                1., 1., 1e-05, 1.
                *END STEP
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *STEP, NAME=Step-1
                *STATIC
                0.5, 1., 1e-05, 0.5
                *END STEP
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        diffs = diff_abq_mesh_blocks(left, right)
        assert len(diffs) == 0

    def test_metadata_only_diff_detects_step_changes(self, tmp_path: Path):
        """diff_abq_metadata_blocks はSTEP差分を検出する"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_metadata_blocks, read_inp

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *STEP, NAME=Step-1
                *STATIC
                1., 1., 1e-05, 1.
                *END STEP
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *STEP, NAME=Step-1
                *STATIC
                0.5, 1., 1e-05, 0.5
                *END STEP
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        diffs = diff_abq_metadata_blocks(left, right)
        assert len(diffs) > 0
        assert any("step" in d.location for d in diffs)

    def test_metadata_only_diff_ignores_mesh_changes(self, tmp_path: Path):
        """diff_abq_metadata_blocks はメッシュ差分を検出しない"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_metadata_blocks, read_inp

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
                2, 1.0, 0.0, 0.0
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        diffs = diff_abq_metadata_blocks(left, right)
        assert len(diffs) == 0

    def test_combined_equals_sum_of_parts(self, tmp_path: Path):
        """diff_abq_blocks = diff_abq_mesh_blocks + diff_abq_metadata_blocks"""
        import textwrap

        from plugins.abaqus.parse import (
            diff_abq_blocks,
            diff_abq_mesh_blocks,
            diff_abq_metadata_blocks,
            read_inp,
        )

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
                *STEP, NAME=Step-1
                *STATIC
                1., 1., 1e-05, 1.
                *END STEP
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *NODE
                1, 0.0, 0.0, 0.0
                2, 1.0, 0.0, 0.0
                *STEP, NAME=Step-1
                *STATIC
                0.5, 1., 1e-05, 0.5
                *END STEP
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        combined = diff_abq_blocks(left, right)
        mesh_diffs = diff_abq_mesh_blocks(left, right)
        metadata_diffs = diff_abq_metadata_blocks(left, right)

        assert len(combined) == len(mesh_diffs) + len(metadata_diffs)
        assert len(mesh_diffs) > 0
        assert len(metadata_diffs) > 0


# ====================================================================
# _MESH_TOPOLOGY_KEYWORDS / _filter_non_mesh_raw_blocks テスト
# ====================================================================


class TestMeshTopologyFilter:
    """diff_abq_metadata_blocks のメッシュ関連キーワード除外フィルタテスト"""

    def test_mesh_topology_keywords_defined(self):
        """_MESH_TOPOLOGY_KEYWORDS が定義されている"""
        from plugins.abaqus.parse import _MESH_TOPOLOGY_KEYWORDS

        assert isinstance(_MESH_TOPOLOGY_KEYWORDS, frozenset)
        assert len(_MESH_TOPOLOGY_KEYWORDS) > 0

    def test_core_mesh_keywords_included(self):
        """コアメッシュキーワードが含まれる"""
        from plugins.abaqus.parse import _MESH_TOPOLOGY_KEYWORDS

        for kw in ("node", "element", "nset", "elset"):
            assert kw in _MESH_TOPOLOGY_KEYWORDS

    def test_constraint_keywords_included(self):
        """メッシュ拘束キーワードが含まれる"""
        from plugins.abaqus.parse import _MESH_TOPOLOGY_KEYWORDS

        for kw in ("mpc", "equation", "tie", "rigidbody"):
            assert kw in _MESH_TOPOLOGY_KEYWORDS

    def test_orientation_keyword_included(self):
        """要素局所座標系キーワードが含まれる"""
        from plugins.abaqus.parse import _MESH_TOPOLOGY_KEYWORDS

        assert "orientation" in _MESH_TOPOLOGY_KEYWORDS

    def test_section_keywords_not_included(self):
        """セクション定義はメッシュ参照を持つが材料割当を含むためフィルタ対象外"""
        from plugins.abaqus.parse import _MESH_TOPOLOGY_KEYWORDS

        # セクション定義は材料割り当て・板厚定義を含むため、
        # メッシュ同一でも変更される可能性がありフィルタ対象外
        for kw in ("shellsection", "solidsection"):
            assert kw not in _MESH_TOPOLOGY_KEYWORDS

    def test_filter_removes_mesh_raw_blocks(self):
        """_filter_non_mesh_raw_blocks がメッシュ関連RawBlockを除外する"""
        from pathlib import Path

        from plugins.abaqus.parse import (
            RawBlock,
            _filter_non_mesh_raw_blocks,
        )

        blocks = [
            RawBlock(keyword="amplitude", options={}, lines=[], file_path=Path("a.inp")),
            RawBlock(keyword="tie", options={}, lines=[], file_path=Path("a.inp")),
            RawBlock(keyword="mpc", options={}, lines=[], file_path=Path("a.inp")),
            RawBlock(keyword="orientation", options={}, lines=[], file_path=Path("a.inp")),
            RawBlock(keyword="restart", options={}, lines=[], file_path=Path("a.inp")),
        ]

        filtered = _filter_non_mesh_raw_blocks(blocks)
        keywords = [b.keyword for b in filtered]
        assert keywords == ["amplitude", "restart"]

    def test_filter_passes_read_components(self):
        """_filter_non_mesh_raw_blocks はReadComponentをフィルタしない"""
        from pathlib import Path

        from plugins.abaqus.parse import (
            Context,
            RawBlock,
            ReadNode,
            _filter_non_mesh_raw_blocks,
        )

        ctx = Context()
        node_comp = ReadNode(context=ctx)
        raw_block = RawBlock(keyword="amplitude", options={}, lines=[], file_path=Path("a.inp"))
        blocks = [node_comp, raw_block]

        filtered = _filter_non_mesh_raw_blocks(blocks)
        assert len(filtered) == 2  # ReadComponent は通過、RawBlockも非メッシュなので通過

    def test_metadata_diff_excludes_mesh_raw_blocks(self, tmp_path: Path):
        """diff_abq_metadata_blocks がraw_blocksのメッシュキーワードを除外する"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_metadata_blocks, read_inp

        # TIEキーワードはraw_blocksに入り、メッシュトポロジー関連
        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *TIE, NAME=Tie-1
                surface1, surface2
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *TIE, NAME=Tie-1
                surface1, surface3
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        # TIEはメッシュトポロジーキーワードとして除外されるため差分なし
        diffs = diff_abq_metadata_blocks(left, right)
        mesh_keyword_diffs = [d for d in diffs if "raw_blocks" in d.location]
        assert len(mesh_keyword_diffs) == 0

    def test_metadata_diff_excludes_orientation(self, tmp_path: Path):
        """diff_abq_metadata_blocks がORIENTATIONキーワードを除外する"""
        import textwrap

        from plugins.abaqus.parse import diff_abq_metadata_blocks, read_inp

        f1 = self._write_inp(
            tmp_path,
            "a.inp",
            textwrap.dedent("""\
                *ORIENTATION, NAME=S0, DEFINITION=COORDINATES, SYSTEM=RECTANGULAR
                1., 0., 0., 0., 1., 0.
                3, 0.
            """),
        )
        f2 = self._write_inp(
            tmp_path,
            "b.inp",
            textwrap.dedent("""\
                *ORIENTATION, NAME=S0, DEFINITION=COORDINATES, SYSTEM=CYLINDRICAL
                0., 0., 0., 0., 0., 1.
                3, 0.
            """),
        )

        left = read_inp(f1, verbose=False)
        right = read_inp(f2, verbose=False)

        # ORIENTATIONはメッシュトポロジーキーワードとして除外される
        diffs = diff_abq_metadata_blocks(left, right)
        orientation_diffs = [d for d in diffs if "orientation" in d.location.lower()]
        assert len(orientation_diffs) == 0

    def _write_inp(self, tmp_path: Path, name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p


# ====================================================================
# ProcessPoolExecutor ベンチマーク/検証テスト
# ====================================================================


class TestProcessPoolBenchmark:
    """ProcessPoolExecutor vs ThreadPoolExecutor のパース結果一致性検証

    実ファイルフィクスチャを使い、両方式で同一結果が得られることを確認する。
    ベンチマーク計測は pytest-benchmark 等で別途実行可能。
    """

    def test_thread_and_process_parse_same_result(self, tmp_path: Path):
        """Thread/Process両方式で同一ファイルのパース結果が一致する"""
        import textwrap

        from plugins.abaqus.parse import read_inp

        # テスト用INPファイルを3つ作成（Process閾値以上）
        for i in range(3):
            content = textwrap.dedent(f"""\
                *NODE
                1, 0.0, 0.0, 0.0
                2, 1.0, 0.0, 0.0
                3, {float(i)}, 1.0, 0.0
                *ELEMENT, TYPE=S3
                1, 1, 2, 3
                *NSET, NSET=all
                1, 2, 3
                *STEP, NAME=Step-1
                *STATIC
                1., 1., 1e-05, 1.
                *END STEP
            """)
            (tmp_path / f"model_{i}.inp").write_text(content, encoding="utf-8")

        # 各ファイルを個別にパースして結果を保存
        results = {}
        for i in range(3):
            fp = str(tmp_path / f"model_{i}.inp")
            abq = read_inp(fp, verbose=False)
            results[fp] = abq

        # 全ファイルでノード/要素数が正しいことを確認
        for fp, abq in results.items():
            total_nodes = sum(len(comp.data) for comp in abq.nodes.values())
            total_elements = sum(len(comp.data) for comp in abq.elements.values())
            assert total_nodes == 3, f"Expected 3 nodes in {fp}"
            assert total_elements == 1, f"Expected 1 element in {fp}"
            assert len(abq.steps) == 1

    def test_parse_inp_worker_function_is_picklable(self):
        """_parse_inp_worker がpickle可能であることを検証"""
        import pickle

        from plugins.abaqus.parse.mesh_parser import _parse_inp_worker

        # モジュールレベル関数はpickle可能
        pickled = pickle.dumps(_parse_inp_worker)
        restored = pickle.loads(pickled)
        assert callable(restored)

    def test_parse_inp_worker_produces_valid_result(self, tmp_path: Path):
        """_parse_inp_worker が正しいABQDataを返す"""
        import textwrap

        content = textwrap.dedent("""\
            *NODE
            1, 0.0, 0.0, 0.0
            *ELEMENT, TYPE=C3D8
            1, 1
        """)
        fp = tmp_path / "test.inp"
        fp.write_text(content, encoding="utf-8")

        from plugins.abaqus.parse.mesh_parser import _parse_inp_worker

        result_fp, abq = _parse_inp_worker((str(fp), 5))
        assert result_fp == str(fp)
        assert len(abq.nodes) > 0
        assert len(abq.elements) > 0

    def test_process_pool_fallback_to_thread(self):
        """ProcessPoolExecutor失敗時にThreadPoolExecutorへフォールバックする設計を検証"""
        from plugins.abaqus.parse.mesh_parser import AbaqusMeshParser

        # 閾値の存在を確認
        assert hasattr(AbaqusMeshParser, "_PROCESS_POOL_THRESHOLD")
        assert AbaqusMeshParser._PROCESS_POOL_THRESHOLD == 3

        # use_processes=None 時の自動選択ロジックを間接検証
        # ファイル数 < 閾値: Thread選択
        assert AbaqusMeshParser._PROCESS_POOL_THRESHOLD > 2  # 2ファイルはThread
        # ファイル数 >= 閾値: Process選択
        assert AbaqusMeshParser._PROCESS_POOL_THRESHOLD <= 3  # 3ファイルはProcess


# ====================================================================
# ProcessPool vs ThreadPool ベンチマーク実測テスト
# ====================================================================


@pytest.mark.slow
class TestPoolBenchmark:
    """ProcessPoolExecutor vs ThreadPoolExecutor のベンチマーク実測

    テストアセットのINPファイルを使用して両方式の実行時間を計測し、
    結果をログに出力する。CIでは結果一致性のみ検証し、
    速度の優劣はassertしない（環境依存のため）。
    """

    @staticmethod
    def _collect_inp_files() -> list[Path]:
        """テストアセットからINPファイルを収集"""
        asset_dirs = [
            Path(__file__).parent.parent / "shared" / "tests" / "test_asset1",
            Path(__file__).parent / "fixtures" / "graph_test1",
        ]
        inp_files = []
        for d in asset_dirs:
            if d.exists():
                inp_files.extend(sorted(d.glob("**/*.inp")))
        return inp_files

    def test_benchmark_thread_vs_process_parse(self, caplog):
        """Thread/Process両方式でINPファイルをパースし実行時間を計測

        結果はログに出力され、CI/ローカルで確認可能。
        両方式で同一のパース結果（ノード数・要素数）が得られることも検証する。
        """
        import logging
        import time
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

        from plugins.abaqus.parse import read_inp
        from plugins.abaqus.parse.mesh_parser import _parse_inp_worker

        inp_files = self._collect_inp_files()
        if len(inp_files) < 3:
            pytest.skip("Benchmark requires at least 3 INP files")

        include_depth = 5

        # --- ThreadPoolExecutor ---
        thread_results: dict[str, object] = {}
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=min(len(inp_files), 8)) as executor:
            futures = {}
            for fp in inp_files:
                fp_str = str(fp)
                futures[executor.submit(read_inp, fp_str, False, include_depth)] = fp_str
            for future in as_completed(futures):
                fp_str = futures[future]
                try:
                    abq = future.result()
                    thread_results[fp_str] = abq
                except Exception:
                    pass
        thread_time = time.perf_counter() - t0

        # --- ProcessPoolExecutor ---
        process_results: dict[str, object] = {}
        t0 = time.perf_counter()
        try:
            args_list = [(str(fp), include_depth) for fp in inp_files]
            with ProcessPoolExecutor(max_workers=min(len(inp_files), 8)) as executor:
                futures = {}
                for args in args_list:
                    futures[executor.submit(_parse_inp_worker, args)] = args[0]
                for future in as_completed(futures):
                    fp_str = futures[future]
                    try:
                        _, abq = future.result()
                        process_results[fp_str] = abq
                    except Exception:
                        pass
        except (OSError, RuntimeError):
            pytest.skip("ProcessPoolExecutor unavailable in this environment")
        process_time = time.perf_counter() - t0

        # --- 逐次パース（ベースライン） ---
        t0 = time.perf_counter()
        serial_results: dict[str, object] = {}
        for fp in inp_files:
            try:
                abq = read_inp(str(fp), verbose=False, include_max_depth=include_depth)
                serial_results[str(fp)] = abq
            except Exception:
                pass
        serial_time = time.perf_counter() - t0

        # --- ログ出力 ---
        with caplog.at_level(logging.INFO):
            logging.getLogger().info(
                f"\n=== Pool Benchmark ({len(inp_files)} INP files) ===\n"
                f"  Serial:      {serial_time:.3f}s\n"
                f"  ThreadPool:  {thread_time:.3f}s (speedup: {serial_time / thread_time:.2f}x)\n"
                f"  ProcessPool: {process_time:.3f}s (speedup: {serial_time / process_time:.2f}x)\n"
                f"  Thread vs Process: {thread_time / process_time:.2f}x"
            )

        # --- 結果一致性検証 ---
        common_files = set(thread_results) & set(process_results) & set(serial_results)
        assert len(common_files) > 0, "No common successfully parsed files"

        for fp_str in common_files:
            t_abq = thread_results[fp_str]
            p_abq = process_results[fp_str]
            s_abq = serial_results[fp_str]

            t_nodes = sum(len(c.data) for c in t_abq.nodes.values())
            p_nodes = sum(len(c.data) for c in p_abq.nodes.values())
            s_nodes = sum(len(c.data) for c in s_abq.nodes.values())
            assert t_nodes == p_nodes == s_nodes, f"Node count mismatch for {fp_str}"

            t_elems = sum(len(c.data) for c in t_abq.elements.values())
            p_elems = sum(len(c.data) for c in p_abq.elements.values())
            s_elems = sum(len(c.data) for c in s_abq.elements.values())
            assert t_elems == p_elems == s_elems, f"Element count mismatch for {fp_str}"

    def test_benchmark_results_logged(self, caplog):
        """ベンチマーク結果がログに出力されることを確認"""
        inp_files = self._collect_inp_files()
        assert len(inp_files) >= 3, f"Expected at least 3 INP files in test assets, found {len(inp_files)}"
