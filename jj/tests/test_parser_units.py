"""パーサーサブクラス単体テスト

各AbstractFileParserサブクラスを個別にテストする。
ProjectGraphをモックで構築し、各パーサーのapply()の動作を検証する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import GraphConfig
from jj_types import Node, Relation
from services.graph.project_graph import ProjectGraph

ASSET_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "tests" / "test_asset1"


@pytest.fixture
def config() -> GraphConfig:
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb", ".sta", ".msg", ".dat"],
                "asset-extensions": [".modfem", ".cdb", ".stp"],
            },
        }
    )


def _make_graph(
    nodes: list[Node],
    relations: list[Relation] | None = None,
    config: GraphConfig | None = None,
    project_root: Path | None = None,
) -> ProjectGraph:
    """テスト用ProjectGraphを生成"""
    if config is None:
        config = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {
                    "input-extensions": [".inp"],
                    "result-extensions": [".odb", ".sta", ".msg", ".dat"],
                    "asset-extensions": [".modfem", ".cdb", ".stp"],
                },
            }
        )
    return ProjectGraph(
        nodes=list(nodes),
        relations=list(relations or []),
        project_root=project_root or ASSET_DIR,
        config=config,
    )


# ====================================================================
# VersionRelationParser テスト
# ====================================================================


class TestVersionRelationParser:
    """VersionRelationParser の単体テスト"""

    def test_creates_next_version_for_two_versions(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)

        next_ver = [r for r in result.relations if r.label == "next_version"]
        assert len(next_ver) == 1
        assert next_ver[0].node1_id == 1
        assert next_ver[0].node2_id == 2

    def test_creates_index_group_node(self, config: GraphConfig):
        """index_groupノードが作成され、belongs_to関係でメンバーにリンクされる"""
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
            Node(id=3, type="go", name="go_idx1_v3", format="inp",
                 properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)

        # index_groupノードが作成される
        group_nodes = [n for n in result.nodes if n.type == "index_group"]
        assert len(group_nodes) == 1
        group_node = group_nodes[0]
        assert group_node.name == "go_idx1"
        assert group_node.properties["member_count"] == 3

        # belongs_to関係が全メンバーに作成される
        belongs_to = [r for r in result.relations if r.label == "belongs_to"]
        assert len(belongs_to) == 3
        assert all(r.node2_id == group_node.id for r in belongs_to)

    def test_no_relation_for_single_node(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)
        assert len(result.relations) == 0

    def test_no_relation_without_index(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(id=1, type="go", name="go_v1", format="inp",
                 properties={"path": "go_v1.inp", "index": "", "version": "1"}),
            Node(id=2, type="go", name="go_v2", format="inp",
                 properties={"path": "go_v2.inp", "index": "", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)
        assert len(result.relations) == 0

    def test_different_types_not_grouped(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="mesh", name="mesh_idx1_v1", format="inp",
                 properties={"path": "mesh_idx1_v1.inp", "index": "1", "version": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)
        assert len(result.relations) == 0


# ====================================================================
# ResultRelationParser テスト
# ====================================================================


class TestResultRelationParser:
    """ResultRelationParser の単体テスト"""

    def test_creates_result_of_relation(self, config: GraphConfig):
        from services.parse.parsers.output_parser import ResultRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx1", format="odb",
                 properties={"path": "go_idx1.odb", "index": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = ResultRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "result_of"]
        assert len(rels) == 1
        assert rels[0].node1_id == 2  # result → input
        assert rels[0].node2_id == 1

    def test_no_relation_for_different_basenames(self, config: GraphConfig):
        from services.parse.parsers.output_parser import ResultRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx2", format="odb",
                 properties={"path": "go_idx2.odb", "index": "2"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = ResultRelationParser().apply(graph)
        assert len(result.relations) == 0


# ====================================================================
# AssetRelationParser テスト
# ====================================================================


class TestAssetRelationParser:
    """AssetRelationParser の単体テスト"""

    def test_creates_derived_from_relation(self, config: GraphConfig):
        from services.parse.parsers.output_parser import AssetRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="mesh", name="go_idx1", format="cdb",
                 properties={"path": "go_idx1.cdb", "index": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = AssetRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "derived_from"]
        assert len(rels) == 1
        assert rels[0].node1_id == 1  # input
        assert rels[0].node2_id == 2  # asset


# ====================================================================
# OutputRelationParser テスト
# ====================================================================


class TestOutputRelationParser:
    """OutputRelationParser の単体テスト"""

    def test_creates_has_output_for_prefixed_output(self, config: GraphConfig):
        from services.parse.parsers.output_parser import OutputRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="unknown", name="go_idx1_RF", format="csv",
                 properties={"path": "go_idx1_RF.csv", "index": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = OutputRelationParser().apply(graph)

        rels = [r for r in result.relations if r.label == "has_output"]
        assert len(rels) == 1
        assert rels[0].node1_id == 1
        assert rels[0].node2_id == 2

    def test_no_has_output_for_exact_match(self, config: GraphConfig):
        from services.parse.parsers.output_parser import OutputRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx1", format="csv",
                 properties={"path": "go_idx1.csv", "index": "1"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = OutputRelationParser().apply(graph)
        # 完全一致はresult_ofで処理するため has_outputは作らない
        assert len([r for r in result.relations if r.label == "has_output"]) == 0


# ====================================================================
# EnrichmentOnlyFilter テスト
# ====================================================================


class TestEnrichmentOnlyFilter:
    """EnrichmentOnlyFilter の単体テスト"""

    def test_removes_sta_msg_dat_nodes(self, config: GraphConfig):
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx1", format="sta",
                 properties={"path": "go_idx1.sta"}),
            Node(id=3, type="go", name="go_idx1", format="msg",
                 properties={"path": "go_idx1.msg"}),
            Node(id=4, type="go", name="go_idx1", format="dat",
                 properties={"path": "go_idx1.dat"}),
            Node(id=5, type="go", name="go_idx1", format="odb",
                 properties={"path": "go_idx1.odb"}),
        ]
        rels = [
            Relation(id=1, label="result_of", node1_id=2, node2_id=1),
            Relation(id=2, label="result_of", node1_id=5, node2_id=1),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = EnrichmentOnlyFilter().apply(graph)

        # .inp と .odb のみ残る
        assert len(result.nodes) == 2
        formats = {n.format for n in result.nodes}
        assert formats == {"inp", "odb"}

        # .sta に関するリレーションは除去、.odb は残る
        assert len(result.relations) == 1
        assert result.relations[0].node1_id == 5

    def test_no_removal_when_no_enrichment_nodes(self, config: GraphConfig):
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx1", format="odb",
                 properties={"path": "go_idx1.odb"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        assert len(result.nodes) == 2


# ====================================================================
# RootDirectoryParser テスト
# ====================================================================


class TestRootDirectoryParser:
    """RootDirectoryParser の単体テスト"""

    def test_creates_root_directory_node(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) == 1
        assert dir_nodes[0].properties["path"] == "."
        assert "root" in dir_nodes[0].properties["tags"]

    def test_contains_relation_for_root_files(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx2", format="inp",
                 properties={"path": "go_idx2.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        contains = [r for r in result.relations if r.label == "contains"]
        assert len(contains) == 2

    def test_no_root_for_nested_files_only(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "subdir/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) == 0

    def test_skips_directory_format_nodes(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp"}),
            Node(id=2, type="directory", name="subdir", format="directory",
                 properties={"path": "subdir"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        # rootノードが作られ、go_idx1.inpとsubdirへのcontains（ルート直下ディレクトリも含む）
        contains = [r for r in result.relations if r.label == "contains"]
        assert len(contains) == 2
        linked_ids = {r.node2_id for r in contains}
        assert 1 in linked_ids  # go_idx1.inp
        assert 2 in linked_ids  # subdir


# ====================================================================
# DirectoryRelationParser テスト（簡易テスト：ASSET_DIRベース）
# ====================================================================


class TestDirectoryRelationParser:
    """DirectoryRelationParser の単体テスト"""

    def test_creates_contains_for_nested_files(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "old/go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx2", format="inp",
                 properties={"path": "old/go_idx2.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = DirectoryRelationParser().apply(graph)

        # oldディレクトリノードが作られcontains関係ができる
        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) >= 1

        contains = [r for r in result.relations if r.label == "contains"]
        assert len(contains) >= 2

    def test_creates_intermediate_directories(self, config: GraphConfig):
        """深い階層の中間ディレクトリもNode化される"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "a/b/c/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = DirectoryRelationParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        dir_paths = {n.properties.get("path", "") for n in dir_nodes}
        # a, a/b, a/b/c の3階層すべてがNode化される
        assert "a" in dir_paths
        assert "a/b" in dir_paths
        assert "a/b/c" in dir_paths

    def test_directory_hierarchy_contains_relations(self, config: GraphConfig):
        """中間ディレクトリ間に親→子のcontains関係が構築される"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "a/b/c/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = DirectoryRelationParser().apply(graph)

        dir_by_path: dict[str, Node] = {}
        for n in result.nodes:
            if n.format == "directory":
                dir_by_path[n.properties.get("path", "")] = n

        # a → a/b のcontains関係
        a_to_ab = [
            r for r in result.relations
            if r.label == "contains"
            and r.node1_id == dir_by_path["a"].id
            and r.node2_id == dir_by_path["a/b"].id
        ]
        assert len(a_to_ab) == 1

        # a/b → a/b/c のcontains関係
        ab_to_abc = [
            r for r in result.relations
            if r.label == "contains"
            and r.node1_id == dir_by_path["a/b"].id
            and r.node2_id == dir_by_path["a/b/c"].id
        ]
        assert len(ab_to_abc) == 1

    def test_max_depth_limits_directories(self):
        """max-depthでディレクトリ階層を制限できる"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        config_with_depth = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {"input-extensions": [".inp"]},
                "directory-max-depth": 1,
            }
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "a/b/c/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config_with_depth)
        result = DirectoryRelationParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        dir_paths = {n.properties.get("path", "") for n in dir_nodes}
        # max-depth=1: "a" のみ
        assert "a" in dir_paths
        assert "a/b" not in dir_paths
        assert "a/b/c" not in dir_paths

    def test_max_depth_2(self):
        """max-depth=2で2階層までNode化"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        config_with_depth = GraphConfig.from_dict(
            {
                "vocab": {},
                "file-relations": {"input-extensions": [".inp"]},
                "directory-max-depth": 2,
            }
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "a/b/c/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config_with_depth)
        result = DirectoryRelationParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        dir_paths = {n.properties.get("path", "") for n in dir_nodes}
        # max-depth=2: "a" と "a/b" まで
        assert "a" in dir_paths
        assert "a/b" in dir_paths
        assert "a/b/c" not in dir_paths


# ====================================================================
# MeshInheritParser テスト
# ====================================================================


class TestMeshInheritParser:
    """MeshInheritParser の単体テスト"""

    def test_inherits_mesh_properties(self, config: GraphConfig):
        """go_*.inpがinclude先のmesh_*.inpからプロパティを継承する"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="mesh", name="mesh_t50_v1", format="inp",
                 properties={
                     "path": "mesh_t50_v1.inp", "index": "1", "version": "1",
                     "t": "50",
                     "mesh_node_count": 1000,
                     "mesh_element_count": 500,
                     "mesh_quality": {"volume": {"min": 0.1, "max": 1.0, "mean": 0.5}},
                 }),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        # mesh_qualityが継承されている
        assert "mesh_quality" in go_node.properties
        assert go_node.properties["mesh_quality"]["volume"]["mean"] == 0.5
        # t プロパティも継承
        assert go_node.properties["t"] == "50"
        # mesh_node_count/element_countも継承
        assert go_node.properties["mesh_node_count"] == 1000
        assert go_node.properties["mesh_element_count"] == 500

    def test_does_not_overwrite_existing_keys(self, config: GraphConfig):
        """go_*が既に持っているキーは上書きしない"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1", "version": "1",
                              "t": "100"}),  # go_*が持つ値を優先
            Node(id=2, type="mesh", name="mesh_t50_v1", format="inp",
                 properties={"path": "mesh_t50_v1.inp", "index": "1", "version": "1",
                              "t": "50"}),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node.properties["t"] == "100"  # 上書きされない

    def test_inherits_from_all_includes(self, config: GraphConfig):
        """mesh_*だけでなく全include先からプロパティを継承する"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="mesh", name="mesh_t50_v1", format="inp",
                 properties={"path": "mesh_t50_v1.inp", "index": "1", "version": "1",
                              "mesh_node_count": 500}),
            Node(id=3, type="step", name="step_stress_v1", format="inp",
                 properties={"path": "step_stress_v1.inp", "index": "1", "version": "1",
                              "step_type": "static"}),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
            Relation(id=2, label="includes", node1_id=1, node2_id=3),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # mesh_*からの継承
        assert go_node.properties["mesh_node_count"] == 500
        # step_*からの継承
        assert go_node.properties["step_type"] == "static"

    def test_skips_meta_properties(self, config: GraphConfig):
        """path, tags, active, verbose_name等のメタプロパティは継承しない"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1", "version": "1",
                              "active": "true"}),
            Node(id=2, type="mesh", name="mesh_t50_v1", format="inp",
                 properties={
                     "path": "mesh_t50_v1.inp", "index": "1", "version": "1",
                     "active": "false", "verbose_name": "メッシュ",
                     "custom_key": "value",
                 }),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node.properties["active"] == "true"  # 上書きされない
        assert "verbose_name" not in go_node.properties  # メタキーは継承しない
        assert go_node.properties["custom_key"] == "value"  # カスタムキーは継承


# ====================================================================
# IncludesRelationParser テスト（ASSET_DIRベース）
# ====================================================================


class TestIncludesRelationParser:
    """IncludesRelationParser の単体テスト"""

    def test_creates_includes_relation_from_asset(self, config: GraphConfig):
        """test_asset1のgo_idx1.v3.inpがmeshをincludeしている"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        svc = GraphService_stub(ASSET_DIR, config)
        nodes = svc.scan_and_create_nodes()
        graph = _make_graph(nodes, config=config, project_root=ASSET_DIR)

        result = IncludesRelationParser().apply(graph)

        includes = [r for r in result.relations if r.label == "includes"]
        assert len(includes) >= 1


# ====================================================================
# JsonPropertyParser テスト
# ====================================================================


class TestJsonPropertyParser:
    """JsonPropertyParser の単体テスト

    JSON内のキー名がプロパティキーとして使われ、
    ファイル名サフィックスはプレフィックスに使用されないことを検証する。
    """

    def test_flat_json_keys_used_as_property_keys(self, tmp_path: Path):
        """フラットなJSONのキーがそのままプロパティキーになる
        go_idx1_result1.json: {"key1": "value1"} → key1: "value1"
        """
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        # JSONファイル作成
        import json
        (tmp_path / "go_idx1_result1.json").write_text(
            json.dumps({"key1": "value1"})
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="unknown", name="go_idx1_result1", format="json",
                 properties={"path": "go_idx1_result1.json", "index": "1"}),
        ]
        graph = _make_graph(nodes, project_root=tmp_path)
        result = JsonPropertyParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # JSON内キー "key1" がそのままプロパティキーになる
        assert "key1" in go_node.properties
        assert go_node.properties["key1"] == "value1"
        # ファイル名サフィックス "result1" がプレフィックスに使われていない
        assert "result1.key1" not in go_node.properties
        assert "result1" not in go_node.properties

    def test_nested_json_keys_flattened_with_dot(self, tmp_path: Path):
        """ネストしたJSONは"."繋ぎで平坦化される
        go_idx1_result2.json: {"key1": {"key2": "v1"}, "key3": "v2"}
        → key1.key2: "v1", key3: "v2"
        """
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        import json
        (tmp_path / "go_idx1_result2.json").write_text(
            json.dumps({"key1": {"key2": "v1"}, "key3": "v2"})
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="unknown", name="go_idx1_result2", format="json",
                 properties={"path": "go_idx1_result2.json", "index": "1"}),
        ]
        graph = _make_graph(nodes, project_root=tmp_path)
        result = JsonPropertyParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # ネストされた key1.key2 が"."区切りで平坦化
        assert "key1.key2" in go_node.properties
        assert go_node.properties["key1.key2"] == "v1"
        # トップレベルキー key3
        assert "key3" in go_node.properties
        assert go_node.properties["key3"] == "v2"
        # ファイル名が使われていないことを確認
        assert "result2.key1.key2" not in go_node.properties
        assert "result2.key3" not in go_node.properties

    def test_multiple_json_files_merge_keys(self, tmp_path: Path):
        """複数のJSONファイルからキーがマージされる"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        import json
        (tmp_path / "go_idx1_stress.json").write_text(
            json.dumps({"center": 0.25, "edge": 1.0})
        )
        (tmp_path / "go_idx1_strain.json").write_text(
            json.dumps({"max_strain": 0.001})
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="unknown", name="go_idx1_stress", format="json",
                 properties={"path": "go_idx1_stress.json", "index": "1"}),
            Node(id=3, type="unknown", name="go_idx1_strain", format="json",
                 properties={"path": "go_idx1_strain.json", "index": "1"}),
        ]
        graph = _make_graph(nodes, project_root=tmp_path)
        result = JsonPropertyParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # 両方のJSONからキーが統合される
        assert go_node.properties["center"] == 0.25
        assert go_node.properties["edge"] == 1.0
        assert go_node.properties["max_strain"] == 0.001

    def test_nan_infinity_replaced_with_null(self, tmp_path: Path):
        """NaN/Infinityはnull(None)に変換される"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        (tmp_path / "go_idx1_data.json").write_text(
            '{"val_nan": NaN, "val_inf": Infinity, "val_neg_inf": -Infinity, "val_ok": 1.5}'
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="unknown", name="go_idx1_data", format="json",
                 properties={"path": "go_idx1_data.json", "index": "1"}),
        ]
        graph = _make_graph(nodes, project_root=tmp_path)
        result = JsonPropertyParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node.properties["val_nan"] is None
        assert go_node.properties["val_inf"] is None
        assert go_node.properties["val_neg_inf"] is None
        assert go_node.properties["val_ok"] == 1.5

    def test_odb_json_excluded(self, tmp_path: Path):
        """.odb.jsonファイルは除外される"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        import json
        (tmp_path / "go_idx1_result.odb.json").write_text(
            json.dumps({"should_not_appear": True})
        )

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            # .odb.json: nameが"go_idx1_result.odb"でformatが"json"
            Node(id=2, type="unknown", name="go_idx1_result.odb", format="json",
                 properties={"path": "go_idx1_result.odb.json", "index": "1"}),
        ]
        graph = _make_graph(nodes, project_root=tmp_path)
        result = JsonPropertyParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert "should_not_appear" not in go_node.properties


# ====================================================================
# AbaqusElsetParser テスト
# ====================================================================


class TestAbaqusElsetParser:
    """AbaqusElsetParser の単体テスト"""

    def test_creates_elset_nodes_from_mesh_elset_summary(self, config: GraphConfig):
        """mesh_elset_summaryからabaqus_elsetノードが生成される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = [n for n in result.nodes if n.type == "abaqus_elset"]
        assert len(elset_nodes) == 2
        elset_names = {n.name for n in elset_nodes}
        assert elset_names == {"BODY", "SKIN"}

    def test_elset_has_element_count(self, config: GraphConfig):
        """elsetノードにelement_countプロパティが付与される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert elset_nodes["BODY"].properties["element_count"] == 100
        assert elset_nodes["SKIN"].properties["element_count"] == 50

    def test_elset_has_material_assignment(self, config: GraphConfig):
        """material_elsetsから各elsetに材料割り当てが付与される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "mesh_elset_summary": {"BODY": 100},
                     "material_elsets": {"Steel_S235": ["BODY"]},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert elset_nodes["BODY"].properties["material"] == "Steel_S235"

    def test_elset_from_include_child(self, config: GraphConfig):
        """include先のmesh_elset_summaryからもelset名とelement_countが取得される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="mesh", name="mesh_t50", format="inp",
                 properties={
                     "path": "mesh_t50.inp",
                     "mesh_elset_summary": {"PART_A": 200, "PART_B": 300},
                 }),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert len(elset_nodes) == 2
        assert elset_nodes["PART_A"].properties["element_count"] == 200
        assert elset_nodes["PART_B"].properties["element_count"] == 300

    def test_has_elset_relation_created(self, config: GraphConfig):
        """go_*.inpとelsetの間にhas_elsetリレーションが生成される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "mesh_elset_summary": {"EALL": 10},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        has_elset_rels = [r for r in result.relations if r.label == "has_elset"]
        assert len(has_elset_rels) == 1
        assert has_elset_rels[0].node1_id == 1

    def test_go_node_gets_elsets_property(self, config: GraphConfig):
        """go_*.inpノードにelsetsプロパティが設定される"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert "elsets" in go_node.properties
        assert go_node.properties["elsets"] == ["BODY", "SKIN"]

    def test_material_only_elset_no_element_count(self, config: GraphConfig):
        """material_elsetsのみにあるelsetはelement_countなし"""
        from services.parse.connectors.abaqus.inp_parser import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp",
                 properties={
                     "path": "go_idx1.inp", "index": "1",
                     "material_elsets": {"Aluminum": ["WING"]},
                 }),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert "WING" in elset_nodes
        assert "element_count" not in elset_nodes["WING"].properties
        assert elset_nodes["WING"].properties["material"] == "Aluminum"


# ====================================================================
# AbaqusDiffParser パイプラインテスト
# ====================================================================


class TestAbaqusDiffParser:
    """AbaqusDiffParser の単体テスト"""

    def test_diff_node_created_for_version_pair(self, tmp_path: Path, config: GraphConfig):
        """隣接バージョン間でdiffノードが作成され、diff_from/diff_to relationが作られる"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 1, 2\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1., 1e-05, 1.\n"
            "*END STEP\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 2.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 3, 1\n"
            "2, 1, 2, 3, 2\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1., 1e-05, 1.\n"
            "*END STEP\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = AbaqusDiffParser().apply(graph)

        # diffノードが作成される
        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 1
        diff_node = diff_nodes[0]
        assert diff_node.properties["diff_from"] == "go_idx1_v1.inp"
        assert diff_node.properties["diff_to"] == "go_idx1_v2.inp"
        assert "diff_summary" in diff_node.properties
        assert "diff_details" in diff_node.properties

        # diff_from/diff_to relationが作成される
        diff_from_rels = [r for r in result.relations if r.label == "diff_from"]
        diff_to_rels = [r for r in result.relations if r.label == "diff_to"]
        assert len(diff_from_rels) == 1
        assert len(diff_to_rels) == 1
        assert diff_from_rels[0].node1_id == diff_node.id
        assert diff_from_rels[0].node2_id == 1  # v1
        assert diff_to_rels[0].node1_id == diff_node.id
        assert diff_to_rels[0].node2_id == 2  # v2

    def test_diff_contains_node_count_change(self, tmp_path: Path, config: GraphConfig):
        """diffノードのdiff_detailsにノード数変更が反映される"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 2.0, 0.0, 0.0\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = AbaqusDiffParser().apply(graph)

        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 1
        diff_node = diff_nodes[0]
        # diff_detailsにnode_countの差分が含まれる
        assert "diff_details" in diff_node.properties
        assert "node_count" in diff_node.properties["diff_details"]

    def test_diff_contains_element_count_change(self, tmp_path: Path, config: GraphConfig):
        """diffノードのdiff_detailsに要素数変更が反映される"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 3, 4\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 2.0, 0.0, 0.0\n"
            "3, 2.0, 2.0, 0.0\n"
            "4, 0.0, 2.0, 0.0\n"
            "5, 1.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 5, 4\n"
            "2, 2, 3, 4, 5\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = AbaqusDiffParser().apply(graph)

        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 1
        diff_node = diff_nodes[0]
        assert "diff_details" in diff_node.properties
        assert "element_count" in diff_node.properties["diff_details"]

    def test_diff_contains_nset_elset_changes(self, tmp_path: Path, config: GraphConfig):
        """diffノードのdiff_detailsにnset/elsetの変更が含まれる"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "*NSET, NSET=FIX\n"
            "1\n"
            "*ELSET, ELSET=BODY\n"
            "1\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "*NSET, NSET=FIX\n"
            "1, 2\n"
            "*ELSET, ELSET=BODY\n"
            "1\n"
            "*ELSET, ELSET=SKIN\n"
            "1\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = AbaqusDiffParser().apply(graph)

        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 1
        diff_node = diff_nodes[0]
        assert "diff_details" in diff_node.properties
        # NSETのFIXが変更（id_count 1→2）
        details = diff_node.properties["diff_details"]
        assert "nsets" in details.lower() or "elsets" in details.lower()

    def test_no_diff_for_identical_versions(self, tmp_path: Path, config: GraphConfig):
        """同一内容のバージョンではdiffプロパティが付与されない"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1.\n"
            "*END STEP\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = AbaqusDiffParser().apply(graph)

        v2_node = result.get_node_by_id(2)
        assert "diff_from" not in v2_node.properties


class TestParserCache:
    """ProjectGraphのパーサーキャッシュ機能テスト"""

    def test_cache_set_and_get(self, config: GraphConfig, tmp_path: Path):
        """set_cache/get_cacheで値を保存・取得できる"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        assert graph.get_cache("key1") is None
        graph.set_cache("key1", {"data": 42})
        assert graph.get_cache("key1") == {"data": 42}

    def test_abq_cache_set_and_get(self, config: GraphConfig, tmp_path: Path):
        """set_cached_abq_data/get_cached_abq_dataでABQDataを保存・取得できる"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        assert graph.get_cached_abq_data("/path/to/file.inp") is None
        sentinel = object()
        graph.set_cached_abq_data("/path/to/file.inp", sentinel)
        assert graph.get_cached_abq_data("/path/to/file.inp") is sentinel

    def test_diff_parser_uses_cache(self, tmp_path: Path, config: GraphConfig):
        """AbaqusDiffParserがキャッシュを使い、同一ファイルの再パースを避ける"""
        from unittest.mock import patch

        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1.\n"
            "*END STEP\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 2.0, 0.0, 0.0\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1.\n"
            "*END STEP\n"
        )
        content_v3 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 3.0, 0.0, 0.0\n"
            "*STEP, NAME=Step-1\n"
            "*STATIC\n"
            "1., 1.\n"
            "*END STEP\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")
        (tmp_path / "go_idx1_v3.inp").write_text(content_v3, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
            Node(id=3, type="go", name="go_idx1_v3", format="inp",
                 properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # read_inp呼び出し回数を追跡
        call_count = 0
        original_read_inp = None

        def counting_read_inp(path, verbose=True):
            nonlocal call_count
            call_count += 1
            return original_read_inp(path, verbose=verbose)

        from services.parse.connectors import abaqus
        original_read_inp = abaqus.read_inp

        with patch.object(abaqus, "read_inp", side_effect=counting_read_inp):
            AbaqusDiffParser().apply(graph)

        # v1, v2, v3の3ファイル。v2は(v1,v2)と(v2,v3)の両方で使われるが
        # キャッシュにより3回のみ呼ばれる（キャッシュなしだと4回）
        assert call_count == 3

    def test_diff_parser_populates_cache(self, tmp_path: Path, config: GraphConfig):
        """AbaqusDiffParser実行後にキャッシュが populated される"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp",
                 properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"}),
            Node(id=2, type="go", name="go_idx1_v2", format="inp",
                 properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # 実行前はキャッシュ空
        assert graph.get_cached_abq_data(str(tmp_path / "go_idx1_v1.inp")) is None

        AbaqusDiffParser().apply(graph)

        # 実行後はキャッシュに入っている
        cached_v1 = graph.get_cached_abq_data(str(tmp_path / "go_idx1_v1.inp"))
        cached_v2 = graph.get_cached_abq_data(str(tmp_path / "go_idx1_v2.inp"))
        assert cached_v1 is not None
        assert cached_v2 is not None


# ====================================================================
# ヘルパー: GraphServiceの最小スタブ
# ====================================================================


class GraphService_stub:
    """テスト用にGraphServiceのscan_files + file_to_nodeのみ実行"""

    def __init__(self, project_root: Path, config: GraphConfig):
        from services.graph import GraphService
        self._svc = GraphService(project_root=project_root, config=config)

    def scan_and_create_nodes(self) -> list[Node]:
        merged_ext = self._svc._build_scan_extensions()
        files = self._svc.scan_files(extensions=merged_ext)
        return [self._svc.file_to_node(f) for f in files]


# ====================================================================
# 実データ用フィクスチャ（test_asset1スキャン結果）
# ====================================================================


@pytest.fixture
def real_config() -> GraphConfig:
    """実データ用の拡張コンフィグ"""
    return GraphConfig.from_dict(
        {
            "vocab": {},
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb", ".sta", ".msg", ".dat"],
                "asset-extensions": [".modfem", ".cdb", ".stp"],
            },
        }
    )


@pytest.fixture
def real_nodes(real_config: GraphConfig) -> list[Node]:
    """test_asset1をスキャンした実ノードリスト"""
    svc = GraphService_stub(ASSET_DIR, real_config)
    return svc.scan_and_create_nodes()


@pytest.fixture
def real_graph(real_nodes: list[Node], real_config: GraphConfig) -> ProjectGraph:
    """test_asset1の実ノードから構築したProjectGraph（リレーションなし）"""
    return _make_graph(real_nodes, config=real_config, project_root=ASSET_DIR)


# ====================================================================
# 実データ: VersionRelationParser テスト
# ====================================================================


class TestVersionRelationParserRealData:
    """test_asset1の実データを使ったVersionRelationParserテスト"""

    def test_go_idx3_next_version(self, real_graph: ProjectGraph):
        """go_idx3: v1→v2 の next_version が生成される"""
        from services.parse.parsers.version_parser import VersionRelationParser

        result = VersionRelationParser().apply(real_graph)

        v1 = next((n for n in result.nodes if n.name == "go_idx3.v1"), None)
        v2 = next((n for n in result.nodes if n.name == "go_idx3.v2"), None)
        assert v1 is not None and v2 is not None
        nv = [
            r for r in result.relations
            if r.label == "next_version"
            and r.node1_id == v1.id and r.node2_id == v2.id
        ]
        assert len(nv) == 1

    def test_go_idx2_cross_directory_version(self, real_graph: ProjectGraph):
        """go_idx2: old/v2.inp→root/v3 のバージョンチェーン（ディレクトリ跨ぎ）

        想定外の発見: VersionRelationParserはフォーマット混合でチェーンを構築する。
        go_idx2.v2.inp → go_idx2.v3.dat → go_idx2.v3.inp → go_idx2.v3.msg
        のように、v2.inp→v3.datが先に接続され、v3.inp直結ではない。
        """
        from services.parse.parsers.version_parser import VersionRelationParser

        result = VersionRelationParser().apply(real_graph)

        v2_inp = next(
            (n for n in result.nodes
             if n.name == "go_idx2.v2" and n.format == "inp"),
            None,
        )
        assert v2_inp is not None

        # v2.inp から始まる next_version がある（先は v3.dat かもしれない）
        nv = [
            r for r in result.relations
            if r.label == "next_version" and r.node1_id == v2_inp.id
        ]
        assert len(nv) == 1
        next_node = result.get_node_by_id(nv[0].node2_id)
        assert next_node.properties.get("version") == "3"
        assert next_node.type == "go"

    def test_index_group_nodes_created(self, real_graph: ProjectGraph):
        """index_groupノードが複数生成される"""
        from services.parse.parsers.version_parser import VersionRelationParser

        result = VersionRelationParser().apply(real_graph)

        group_nodes = [n for n in result.nodes if n.type == "index_group"]
        assert len(group_nodes) >= 2  # idx0, idx1 等のグループ
        belongs_to = [r for r in result.relations if r.label == "belongs_to"]
        assert len(belongs_to) >= 4  # 各グループに2つ以上のメンバー


# ====================================================================
# 実データ: ResultRelationParser テスト
# ====================================================================


class TestResultRelationParserRealData:
    """test_asset1の実データを使ったResultRelationParserテスト"""

    def test_dat_result_of_inp(self, real_graph: ProjectGraph):
        """go_*.dat → go_*.inp の result_of が生成される"""
        from services.parse.parsers.output_parser import ResultRelationParser

        result = ResultRelationParser().apply(real_graph)
        result_rels = [r for r in result.relations if r.label == "result_of"]

        dat_to_inp = []
        for r in result_rels:
            src = result.get_node_by_id(r.node1_id)
            dst = result.get_node_by_id(r.node2_id)
            if src and dst and src.format == "dat" and dst.format == "inp":
                dat_to_inp.append((src.name, dst.name))
        # go_idx0, go_idx1, go_idx2 の3ペア
        assert len(dat_to_inp) == 3

    def test_msg_result_of_inp(self, real_graph: ProjectGraph):
        """go_*.msg → go_*.inp の result_of が生成される"""
        from services.parse.parsers.output_parser import ResultRelationParser

        result = ResultRelationParser().apply(real_graph)
        result_rels = [r for r in result.relations if r.label == "result_of"]

        msg_to_inp = []
        for r in result_rels:
            src = result.get_node_by_id(r.node1_id)
            dst = result.get_node_by_id(r.node2_id)
            if src and dst and src.format == "msg" and dst.format == "inp":
                msg_to_inp.append((src.name, dst.name))
        assert len(msg_to_inp) == 3


# ====================================================================
# 実データ: AssetRelationParser テスト
# ====================================================================


class TestAssetRelationParserRealData:
    """test_asset1の実データを使ったAssetRelationParserテスト"""

    def test_modfem_derived_from_inp(self, real_graph: ProjectGraph):
        """mesh_*.modfem と mesh_*.inp 間に derived_from が生成される"""
        from services.parse.parsers.output_parser import AssetRelationParser

        result = AssetRelationParser().apply(real_graph)
        derived = [r for r in result.relations if r.label == "derived_from"]

        # mesh_shape1_t95 v6/v7/v8 + mesh_test v1/v2/v3 = 6ペア
        assert len(derived) == 6

    def test_derived_from_links_inp_to_modfem(self, real_graph: ProjectGraph):
        """derived_from: inp → modfem（入力元→アセット）の方向"""
        from services.parse.parsers.output_parser import AssetRelationParser

        result = AssetRelationParser().apply(real_graph)
        derived = [r for r in result.relations if r.label == "derived_from"]

        for r in derived:
            src = result.get_node_by_id(r.node1_id)
            dst = result.get_node_by_id(r.node2_id)
            assert src.format == "inp"
            assert dst.format == "modfem"


# ====================================================================
# 実データ: IncludesRelationParser テスト
# ====================================================================


class TestIncludesRelationParserRealData:
    """test_asset1の実データを使ったIncludesRelationParserテスト"""

    def test_total_includes_count(self, real_graph: ProjectGraph):
        """14件の includes リレーションが生成される（material.inp追加後）"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        result = IncludesRelationParser().apply(real_graph)
        includes = [r for r in result.relations if r.label == "includes"]
        assert len(includes) == 14

    def test_go_idx1_includes_mesh_and_step(self, real_graph: ProjectGraph):
        """go_idx1.v3 → mesh_shape1_t95.v8 + step_stress_v1"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        result = IncludesRelationParser().apply(real_graph)
        go = next(
            (n for n in result.nodes
             if n.name == "go_idx1.v3" and n.format == "inp"),
            None,
        )
        assert go is not None
        includes = [
            r for r in result.relations
            if r.label == "includes" and r.node1_id == go.id
        ]
        target_names = set()
        for r in includes:
            target = result.get_node_by_id(r.node2_id)
            target_names.add(target.name)
        assert "mesh_shape1_t95.v8" in target_names
        assert "step_stress_v1" in target_names

    def test_go_idx0_includes_mesh_and_material(self, real_graph: ProjectGraph):
        """go_idx0.v29 → mesh_shape1_t95.v7 + material（material.inp追加後）"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        result = IncludesRelationParser().apply(real_graph)
        go = next(
            (n for n in result.nodes
             if n.name == "go_idx0.v29" and n.format == "inp"),
            None,
        )
        assert go is not None
        includes = [
            r for r in result.relations
            if r.label == "includes" and r.node1_id == go.id
        ]
        target_names = set()
        for r in includes:
            target = result.get_node_by_id(r.node2_id)
            target_names.add(target.name)
        assert "mesh_shape1_t95.v7" in target_names
        # material.inpが存在するのでincludesに含まれる
        assert any("material" in name for name in target_names)

    def test_old_go_includes_cross_directory(self, real_graph: ProjectGraph):
        """old/go_idx2.v2 → mesh_shape1_t95.v7 + material（ディレクトリ跨ぎのinclude検出）"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        result = IncludesRelationParser().apply(real_graph)
        go = next(
            (n for n in result.nodes
             if n.name == "go_idx2.v2" and n.format == "inp"
             and "old/" in n.properties.get("path", "")),
            None,
        )
        assert go is not None
        includes = [
            r for r in result.relations
            if r.label == "includes" and r.node1_id == go.id
        ]
        assert len(includes) >= 1
        target_names = set()
        for r in includes:
            target = result.get_node_by_id(r.node2_id)
            target_names.add(target.name)
        assert any("mesh_shape1_t95" in name for name in target_names)


# ====================================================================
# 実データ: DirectoryRelationParser テスト
# ====================================================================


class TestDirectoryRelationParserRealData:
    """test_asset1の実データを使ったDirectoryRelationParserテスト"""

    def test_creates_known_directories(self, real_graph: ProjectGraph):
        """old, tools, reports, assets, results のディレクトリが作成される"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        result = DirectoryRelationParser().apply(real_graph)
        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        dir_names = {n.name for n in dir_nodes}
        for expected in ["old", "tools", "reports", "assets", "results"]:
            assert expected in dir_names, f"directory '{expected}' not found"

    def test_old_directory_contains_files(self, real_graph: ProjectGraph):
        """old/ 配下に多数のファイルが contains される"""
        from services.parse.parsers.directory_parser import DirectoryRelationParser

        result = DirectoryRelationParser().apply(real_graph)
        old_dir = next(
            (n for n in result.nodes
             if n.name == "old" and n.format == "directory"),
            None,
        )
        assert old_dir is not None
        contains = [
            r for r in result.relations
            if r.label == "contains" and r.node1_id == old_dir.id
        ]
        # old/ has go_idx2.v2, go_idx3.v1, go_idx3.v2, mesh_*... (>15 files)
        assert len(contains) >= 15


# ====================================================================
# 実データ: JsonPropertyParser テスト
# ====================================================================


class TestJsonPropertyParserRealData:
    """test_asset1の実データを使ったJsonPropertyParserテスト

    results/go_idx0.v29_stress.json → go_idx0.v29.inp
    results/go_idx1.v3_stress.json → go_idx1.v3.inp
    results/go_idx2.v3_stress.json → go_idx2.v3.inp
    """

    def test_json_properties_propagated_to_go_node(
        self, real_graph: ProjectGraph,
    ):
        """results/のJSONキーがgo_*.inpノードに伝搬される"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        result = JsonPropertyParser().apply(real_graph)
        go_idx1 = next(
            (n for n in result.nodes
             if n.name == "go_idx1.v3" and n.format == "inp"),
            None,
        )
        assert go_idx1 is not None
        # go_idx1.v3_stress.json: {"0(center)": 0.5, "1": 0.5625, "2(edge)": 0.5}
        assert "0(center)" in go_idx1.properties
        assert go_idx1.properties["0(center)"] == 0.5
        assert go_idx1.properties["2(edge)"] == 0.5

    def test_nan_converted_to_none(self, real_graph: ProjectGraph):
        """go_idx0.v29_stress.json のNaN値がNone変換される"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        result = JsonPropertyParser().apply(real_graph)
        go_idx0 = next(
            (n for n in result.nodes
             if n.name == "go_idx0.v29" and n.format == "inp"),
            None,
        )
        assert go_idx0 is not None
        # go_idx0.v29_stress.json: {"0(center)": 0.25, "1": NaN, "2(edge)": NaN}
        assert go_idx0.properties["0(center)"] == 0.25
        assert go_idx0.properties["1"] is None  # NaN → None
        assert go_idx0.properties["2(edge)"] is None  # NaN → None

    def test_all_three_go_nodes_get_json_props(
        self, real_graph: ProjectGraph,
    ):
        """go_idx0, go_idx1, go_idx2 の3ノードにJSON情報が伝搬"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        result = JsonPropertyParser().apply(real_graph)
        for name in ["go_idx0.v29", "go_idx1.v3", "go_idx2.v3"]:
            go = next(
                (n for n in result.nodes
                 if n.name == name and n.format == "inp"),
                None,
            )
            assert go is not None, f"{name} not found"
            assert "0(center)" in go.properties, (
                f"{name} missing JSON property '0(center)'"
            )


# ====================================================================
# 実データ: EnrichmentOnlyFilter テスト
# ====================================================================


class TestEnrichmentOnlyFilterRealData:
    """test_asset1の実データを使ったEnrichmentOnlyFilterテスト"""

    def test_dat_msg_nodes_removed(self, real_graph: ProjectGraph):
        """フィルタ後、.dat/.msg ノードが除去される"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        result = EnrichmentOnlyFilter().apply(real_graph)
        remaining_formats = {n.format for n in result.nodes}
        assert "dat" not in remaining_formats
        assert "msg" not in remaining_formats

    def test_inp_nodes_preserved(self, real_graph: ProjectGraph):
        """フィルタ後も .inp ノードは残る"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        before_inp = [n for n in real_graph.nodes if n.format == "inp"]
        result = EnrichmentOnlyFilter().apply(real_graph)
        after_inp = [n for n in result.nodes if n.format == "inp"]
        assert len(after_inp) == len(before_inp)

    def test_results_directory_files_removed(self, real_graph: ProjectGraph):
        """results/ 配下のJSON(info-only)がフィルタで除去される"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        result = EnrichmentOnlyFilter().apply(real_graph)
        results_nodes = [
            n for n in result.nodes
            if n.properties.get("path", "").startswith("results/")
            and n.format != "directory"
        ]
        assert len(results_nodes) == 0
