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

ASSET_DIR = Path(__file__).resolve().parent.parent / "shared" / "tests" / "test_asset1"


def _has_pandas() -> bool:
    """pandasが利用可能かチェック（pymeshの依存パッケージ）"""
    try:
        import pandas  # noqa: F401

        return True
    except ImportError:
        return False


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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
            Node(
                id=3,
                type="go",
                name="go_idx1_v3",
                format="inp",
                properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"},
            ),
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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)
        assert len(result.relations) == 0

    def test_no_relation_without_index(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_v1",
                format="inp",
                properties={"path": "go_v1.inp", "index": "", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_v2",
                format="inp",
                properties={"path": "go_v2.inp", "index": "", "version": "2"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = VersionRelationParser().apply(graph)
        assert len(result.relations) == 0

    def test_different_types_not_grouped(self, config: GraphConfig):
        from services.parse.parsers.version_parser import VersionRelationParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_idx1_v1",
                format="inp",
                properties={"path": "mesh_idx1_v1.inp", "index": "1", "version": "1"},
            ),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx1", format="odb", properties={"path": "go_idx1.odb", "index": "1"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx2", format="odb", properties={"path": "go_idx2.odb", "index": "2"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="mesh", name="go_idx1", format="cdb", properties={"path": "go_idx1.cdb", "index": "1"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_RF",
                format="csv",
                properties={"path": "go_idx1_RF.csv", "index": "1"},
            ),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="go", name="go_idx1", format="csv", properties={"path": "go_idx1.csv", "index": "1"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx1", format="sta", properties={"path": "go_idx1.sta"}),
            Node(id=3, type="go", name="go_idx1", format="msg", properties={"path": "go_idx1.msg"}),
            Node(id=4, type="go", name="go_idx1", format="dat", properties={"path": "go_idx1.dat"}),
            Node(id=5, type="go", name="go_idx1", format="odb", properties={"path": "go_idx1.odb"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx1", format="odb", properties={"path": "go_idx1.odb"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        assert len(result.nodes) == 2

    def test_results_direct_file_same_props_removed(self, config: GraphConfig):
        """results/直下でgo_inpと同じプロパティ（追加パラメータなし）のファイルは除外される"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_RF3",
                format="csv",
                properties={"path": "results/go_idx1_RF3.csv"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        assert len(result.nodes) == 1
        assert result.nodes[0].format == "inp"

    def test_results_direct_file_extra_params_preserved(self, config: GraphConfig):
        """results/直下でgo_inpと異なるプロパティ（追加パラメータあり）のファイルは残す"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_RF3_step0",
                format="csv",
                properties={"path": "results/go_idx1_RF3_step0.csv"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        assert len(result.nodes) == 2
        formats = {n.format for n in result.nodes}
        assert formats == {"inp", "csv"}

    def test_results_direct_file_no_go_match_removed(self, config: GraphConfig):
        """results/直下でgo_inpとマッチしないファイルは除外される"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_stress",
                format="json",
                properties={"path": "results/go_idx1_stress.json"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        # stressはresult_keyなのでパラメータなし → 除外される
        assert len(result.nodes) == 1
        assert result.nodes[0].format == "inp"

    def test_results_subdirectory_file_preserved(self, config: GraphConfig):
        """results/サブディレクトリ内のファイルは除外されない"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = EnrichmentOnlyFilter().apply(graph)
        assert len(result.nodes) == 2
        formats = {n.format for n in result.nodes}
        assert formats == {"inp", "png"}


# ====================================================================
# RootDirectoryParser テスト
# ====================================================================


class TestRootDirectoryParser:
    """RootDirectoryParser の単体テスト"""

    def test_creates_root_directory_node(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) == 1
        assert dir_nodes[0].properties["path"] == "."

    def test_contains_relation_for_root_files(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx2", format="inp", properties={"path": "go_idx2.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        contains = [r for r in result.relations if r.label == "contains"]
        assert len(contains) == 2

    def test_no_root_for_nested_files_only(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "subdir/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = RootDirectoryParser().apply(graph)

        dir_nodes = [n for n in result.nodes if n.format == "directory"]
        assert len(dir_nodes) == 0

    def test_skips_directory_format_nodes(self, config: GraphConfig):
        from services.parse.parsers.directory_parser import RootDirectoryParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp"}),
            Node(id=2, type="directory", name="subdir", format="directory", properties={"path": "subdir"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "old/go_idx1.inp"}),
            Node(id=2, type="go", name="go_idx2", format="inp", properties={"path": "old/go_idx2.inp"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "a/b/c/go_idx1.inp"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "a/b/c/go_idx1.inp"}),
        ]
        graph = _make_graph(nodes, config=config)
        result = DirectoryRelationParser().apply(graph)

        dir_by_path: dict[str, Node] = {}
        for n in result.nodes:
            if n.format == "directory":
                dir_by_path[n.properties.get("path", "")] = n

        # a → a/b のcontains関係
        a_to_ab = [
            r
            for r in result.relations
            if r.label == "contains" and r.node1_id == dir_by_path["a"].id and r.node2_id == dir_by_path["a/b"].id
        ]
        assert len(a_to_ab) == 1

        # a/b → a/b/c のcontains関係
        ab_to_abc = [
            r
            for r in result.relations
            if r.label == "contains" and r.node1_id == dir_by_path["a/b"].id and r.node2_id == dir_by_path["a/b/c"].id
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "a/b/c/go_idx1.inp"}),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "a/b/c/go_idx1.inp"}),
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
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50_v1",
                format="inp",
                properties={
                    "path": "mesh_t50_v1.inp",
                    "index": "1",
                    "version": "1",
                    "t": "50",
                    "mesh_node_count": 1000,
                    "mesh_element_count": 500,
                    "mesh_quality": {"volume": {"min": 0.1, "max": 1.0, "mean": 0.5}},
                },
            ),
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

    def test_prefix_escaping_on_key_conflict(self, config: GraphConfig):
        """キー競合時に「{child_name}:{key}」接頭辞付きで保存される"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "index": "1", "version": "1", "t": "100"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50_v1",
                format="inp",
                properties={"path": "mesh_t50_v1.inp", "index": "1", "version": "1", "t": "50"},
            ),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # go_*自身の値が優先される
        assert go_node.properties["t"] == "100"
        # 競合キーはベース名正規化済み接頭辞付きで保存
        # mesh_t50_v1 → mesh_t50（_v1除去）
        assert go_node.properties["mesh_t50:t"] == "50"

    def test_inherits_from_all_includes(self, config: GraphConfig):
        """mesh_*だけでなく全include先からプロパティを継承する"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50_v1",
                format="inp",
                properties={"path": "mesh_t50_v1.inp", "index": "1", "version": "1", "mesh_node_count": 500},
            ),
            Node(
                id=3,
                type="step",
                name="step_stress_v1",
                format="inp",
                properties={"path": "step_stress_v1.inp", "index": "1", "version": "1", "step_type": "static"},
            ),
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
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "index": "1", "version": "1", "active": "true"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50_v1",
                format="inp",
                properties={
                    "path": "mesh_t50_v1.inp",
                    "index": "1",
                    "version": "1",
                    "active": "false",
                    "verbose_name": "メッシュ",
                    "custom_key": "value",
                },
            ),
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

    def test_merges_mesh_dict_properties(self, config: GraphConfig):
        """複数include先のメッシュ辞書プロパティがマージされる"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_part1",
                format="inp",
                properties={
                    "path": "mesh_part1.inp",
                    "mesh_elset_summary": {"ELSET_A": 100, "ELSET_B": 200},
                    "mesh_element_quality": {"C3D8": {"element_count": 300, "quality": {"volume": {"mean": 0.5}}}},
                    "mesh_element_types": {"C3D8": 300},
                },
            ),
            Node(
                id=3,
                type="mesh",
                name="mesh_part2",
                format="inp",
                properties={
                    "path": "mesh_part2.inp",
                    "mesh_elset_summary": {"ELSET_C": 150},
                    "mesh_element_quality": {"C3D6": {"element_count": 150, "quality": {"volume": {"mean": 0.7}}}},
                    "mesh_element_types": {"C3D6": 150},
                },
            ),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
            Relation(id=2, label="includes", node1_id=1, node2_id=3),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # mesh_elset_summaryがマージされている
        summary = go_node.properties["mesh_elset_summary"]
        assert summary["ELSET_A"] == 100
        assert summary["ELSET_B"] == 200
        assert summary["ELSET_C"] == 150
        # mesh_element_qualityもマージされている
        quality = go_node.properties["mesh_element_quality"]
        assert "C3D8" in quality
        assert "C3D6" in quality
        # mesh_element_typesもマージされている
        elem_types = go_node.properties["mesh_element_types"]
        assert elem_types["C3D8"] == 300
        assert elem_types["C3D6"] == 150

    def test_versioned_includes_merge_to_base_name(self, config: GraphConfig):
        """バージョン付きinclude先のキー競合がベース名に正規化・後勝ちマージされる"""
        from services.parse.parsers.mesh_inherit_parser import MeshInheritParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "v": "1"},
            ),
            Node(
                id=2,
                type="mesh",
                name="mesh_v2",
                format="inp",
                properties={"path": "mesh_v2.inp", "v": "2", "mesh_node_count": 1000},
            ),
            Node(
                id=3,
                type="mesh",
                name="mesh_v3",
                format="inp",
                properties={"path": "mesh_v3.inp", "v": "3", "mesh_node_count": 2000},
            ),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
            Relation(id=2, label="includes", node1_id=1, node2_id=3),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = MeshInheritParser().apply(graph)

        go_node = result.get_node_by_id(1)
        # go自身の v=1 は保持
        assert go_node.properties["v"] == "1"
        # mesh_v2, mesh_v3 → ベース名 "mesh" に正規化
        # v は競合キーなので mesh:v として保存（後勝ち=v3の値）
        assert go_node.properties["mesh:v"] == "3"
        # mesh_node_count は競合しないので最初に来た v2 の値が入る
        assert go_node.properties["mesh_node_count"] == 1000


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
        # JSONファイル作成
        import json

        from services.parse.parsers.json_property_parser import JsonPropertyParser

        (tmp_path / "go_idx1_result1.json").write_text(json.dumps({"key1": "value1"}))

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_result1",
                format="json",
                properties={"path": "go_idx1_result1.json", "index": "1"},
            ),
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
        import json

        from services.parse.parsers.json_property_parser import JsonPropertyParser

        (tmp_path / "go_idx1_result2.json").write_text(json.dumps({"key1": {"key2": "v1"}, "key3": "v2"}))

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_result2",
                format="json",
                properties={"path": "go_idx1_result2.json", "index": "1"},
            ),
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
        import json

        from services.parse.parsers.json_property_parser import JsonPropertyParser

        (tmp_path / "go_idx1_stress.json").write_text(json.dumps({"center": 0.25, "edge": 1.0}))
        (tmp_path / "go_idx1_strain.json").write_text(json.dumps({"max_strain": 0.001}))

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_stress",
                format="json",
                properties={"path": "go_idx1_stress.json", "index": "1"},
            ),
            Node(
                id=3,
                type="unknown",
                name="go_idx1_strain",
                format="json",
                properties={"path": "go_idx1_strain.json", "index": "1"},
            ),
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
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_data",
                format="json",
                properties={"path": "go_idx1_data.json", "index": "1"},
            ),
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
        import json

        from services.parse.parsers.json_property_parser import JsonPropertyParser

        (tmp_path / "go_idx1_result.odb.json").write_text(json.dumps({"should_not_appear": True}))

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            # .odb.json: nameが"go_idx1_result.odb"でformatが"json"
            Node(
                id=2,
                type="unknown",
                name="go_idx1_result.odb",
                format="json",
                properties={"path": "go_idx1_result.odb.json", "index": "1"},
            ),
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
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = [n for n in result.nodes if n.type == "abaqus_elset"]
        assert len(elset_nodes) == 2
        elset_names = {n.name for n in elset_nodes}
        assert elset_names == {"BODY", "SKIN"}

    def test_elset_has_element_count(self, config: GraphConfig):
        """elsetノードにelement_countプロパティが付与される"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert elset_nodes["BODY"].properties["element_count"] == 100
        assert elset_nodes["SKIN"].properties["element_count"] == 50

    def test_elset_has_material_assignment(self, config: GraphConfig):
        """material_elsetsから各elsetに材料割り当てが付与される"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"BODY": 100},
                    "material_elsets": {"Steel_S235": ["BODY"]},
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert elset_nodes["BODY"].properties["material"] == "Steel_S235"

    def test_elset_from_include_child(self, config: GraphConfig):
        """include先のmesh_elset_summaryからもelset名とelement_countが取得される"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50",
                format="inp",
                properties={
                    "path": "mesh_t50.inp",
                    "mesh_elset_summary": {"PART_A": 200, "PART_B": 300},
                },
            ),
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
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"EALL": 10},
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        has_elset_rels = [r for r in result.relations if r.label == "has_elset"]
        assert len(has_elset_rels) == 1
        assert has_elset_rels[0].node1_id == 1

    def test_go_node_gets_elsets_property(self, config: GraphConfig):
        """go_*.inpノードにelsetsプロパティが設定される"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert "elsets" in go_node.properties
        assert go_node.properties["elsets"] == ["BODY", "SKIN"]

    def test_material_only_elset_no_element_count(self, config: GraphConfig):
        """material_elsetsのみにあるelsetはelement_countなし"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "material_elsets": {"Aluminum": ["WING"]},
                },
            ),
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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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
        assert "diff_unified" in diff_node.properties

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

        content_v1 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n"
        content_v2 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n3, 2.0, 0.0, 0.0\n"
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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

        content_v1 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*NSET, NSET=FIX\n1\n*ELSET, ELSET=BODY\n1\n"
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
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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
            "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*STEP, NAME=Step-1\n*STATIC\n1., 1.\n*END STEP\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
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
        """set_cached_plugin_data/get_cached_plugin_dataでプラグインデータを保存・取得できる"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        assert graph.get_cached_plugin_data("abaqus", "/path/to/file.inp") is None
        sentinel = object()
        graph.set_cached_plugin_data("abaqus", "/path/to/file.inp", sentinel)
        assert graph.get_cached_plugin_data("abaqus", "/path/to/file.inp") is sentinel

    def test_diff_parser_uses_cache(self, tmp_path: Path, config: GraphConfig):
        """AbaqusDiffParserがキャッシュを使い、同一ファイルの再パースを避ける"""
        from unittest.mock import patch

        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = (
            "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n*STEP, NAME=Step-1\n*STATIC\n1., 1.\n*END STEP\n"
        )
        content_v2 = (
            "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 2.0, 0.0, 0.0\n*STEP, NAME=Step-1\n*STATIC\n1., 1.\n*END STEP\n"
        )
        content_v3 = (
            "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 3.0, 0.0, 0.0\n*STEP, NAME=Step-1\n*STATIC\n1., 1.\n*END STEP\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")
        (tmp_path / "go_idx1_v3.inp").write_text(content_v3, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
            Node(
                id=3,
                type="go",
                name="go_idx1_v3",
                format="inp",
                properties={"path": "go_idx1_v3.inp", "index": "1", "version": "3"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # read_inp呼び出し回数を追跡
        call_count = 0
        original_read_inp = None

        def counting_read_inp(path, verbose=True, include_max_depth=5):
            nonlocal call_count
            call_count += 1
            return original_read_inp(path, verbose=verbose, include_max_depth=include_max_depth)

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

        content_v1 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n"
        content_v2 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n"
        (tmp_path / "go_idx1_v1.inp").write_text(content_v1, encoding="utf-8")
        (tmp_path / "go_idx1_v2.inp").write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # 実行前はキャッシュ空
        assert graph.get_cached_plugin_data("abaqus", str(tmp_path / "go_idx1_v1.inp")) is None

        AbaqusDiffParser().apply(graph)

        # 実行後はキャッシュに入っている
        cached_v1 = graph.get_cached_plugin_data("abaqus", str(tmp_path / "go_idx1_v1.inp"))
        cached_v2 = graph.get_cached_plugin_data("abaqus", str(tmp_path / "go_idx1_v2.inp"))
        assert cached_v1 is not None
        assert cached_v2 is not None


class TestABQDataDiskCache:
    """ABQData永続化キャッシュのテスト"""

    def test_save_and_load_abq_cache(self, tmp_path: Path):
        """プラグインデータをディスクに保存し、再読み込みできる"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        fake_abq = {"nodes": {"1": "data"}, "elements": {}}
        file_path = "/project/go_idx1_v1.inp"
        mtime = 1234567890.0

        storage.save_plugin_data(tmp_path, "abaqus", file_path, fake_abq, mtime)

        # 同じmtimeで再読み込み → ヒット
        loaded = storage.load_plugin_data(tmp_path, "abaqus", file_path, mtime)
        assert loaded is not None
        assert loaded == fake_abq

    def test_load_abq_cache_mtime_mismatch(self, tmp_path: Path):
        """mtime不一致時はNoneを返す"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        fake_abq = {"nodes": {}}
        file_path = "/project/go_idx1_v1.inp"

        storage.save_plugin_data(tmp_path, "abaqus", file_path, fake_abq, mtime=1000.0)

        # 異なるmtimeで読み込み → 不一致でNone
        loaded = storage.load_plugin_data(tmp_path, "abaqus", file_path, expected_mtime=2000.0)
        assert loaded is None

    def test_load_abq_cache_nonexistent(self, tmp_path: Path):
        """キャッシュファイルが存在しない場合はNone"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        loaded = storage.load_plugin_data(tmp_path, "abaqus", "/nonexistent.inp", expected_mtime=1000.0)
        assert loaded is None

    def test_clear_abq_cache(self, tmp_path: Path):
        """プラグインキャッシュの全削除"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        storage.save_plugin_data(tmp_path, "abaqus", "/a.inp", {}, 1.0)
        storage.save_plugin_data(tmp_path, "abaqus", "/b.inp", {}, 2.0)

        count = storage.clear_plugin_cache(tmp_path, "abaqus")
        assert count == 2

        # 削除後は読み込めない
        assert storage.load_plugin_data(tmp_path, "abaqus", "/a.inp", 1.0) is None


class TestIncludeSearchDepthConfig:
    """include-search-depth設定のテスト"""

    def test_default_include_search_depth(self):
        """デフォルトではinclude_search_depth=5"""
        config = GraphConfig.from_dict({"vocab": {}})
        assert config.include_search_depth == 5

    def test_custom_include_search_depth(self):
        """config.yamlからinclude-search-depthを設定できる"""
        config = GraphConfig.from_dict({"vocab": {}, "include-search-depth": 10})
        assert config.include_search_depth == 10

    def test_include_search_depth_zero(self):
        """include-search-depth=0（探索しない）も有効"""
        config = GraphConfig.from_dict({"vocab": {}, "include-search-depth": 0})
        assert config.include_search_depth == 0

    def test_include_search_depth_negative_raises(self):
        """include-search-depth < 0はエラー"""
        with pytest.raises(ValueError, match="include-search-depth"):
            GraphConfig.from_dict({"vocab": {}, "include-search-depth": -1})


class TestElementQualityStats:
    """*ELEMENTキーワードブロック（要素タイプ）ごとの品質統計テスト"""

    def test_elset_node_created_without_quality(self, config: GraphConfig):
        """elsetノードが作成される（qualityは要素タイプ別のため個別elsetにはない）"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={
                    "path": "go_idx1.inp",
                    "index": "1",
                    "mesh_elset_summary": {"BODY": 100, "SKIN": 50},
                    "mesh_element_quality": {
                        "C3D8": {
                            "element_count": 150,
                            "quality": {
                                "volume": {"min": 0.1, "max": 1.0, "mean": 0.5},
                            },
                        },
                    },
                },
            ),
        ]
        graph = _make_graph(nodes, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert "BODY" in elset_nodes
        assert "SKIN" in elset_nodes
        assert elset_nodes["BODY"].properties["element_count"] == 100
        assert elset_nodes["SKIN"].properties["element_count"] == 50

    def test_elset_from_include_child(self, config: GraphConfig):
        """include先のelsetもノード化される"""
        from services.parse.connectors.abaqus.inp_parser_base import AbaqusElsetParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="mesh",
                name="mesh_t50",
                format="inp",
                properties={
                    "path": "mesh_t50.inp",
                    "mesh_elset_summary": {"PART_A": 200},
                },
            ),
        ]
        rels = [
            Relation(id=1, label="includes", node1_id=1, node2_id=2),
        ]
        graph = _make_graph(nodes, rels, config=config)
        result = AbaqusElsetParser().apply(graph)

        elset_nodes = {n.name: n for n in result.nodes if n.type == "abaqus_elset"}
        assert "PART_A" in elset_nodes
        assert elset_nodes["PART_A"].properties["element_count"] == 200


class TestIncludesParserCache:
    """IncludesRelationParserのキャッシュ機能テスト"""

    def test_includes_parser_caches_results(self, tmp_path: Path, config: GraphConfig):
        """IncludesRelationParserがキャッシュにincludeパスを保存する"""
        from services.parse.parsers.output_parser import IncludesRelationParser

        content = "*INCLUDE, INPUT=mesh_t50.inp\n*STEP, NAME=Step-1\n*END STEP\n"
        (tmp_path / "go_idx1.inp").write_text(content, encoding="utf-8")
        (tmp_path / "mesh_t50.inp").write_text("*NODE\n1, 0, 0, 0\n", encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(id=2, type="mesh", name="mesh_t50", format="inp", properties={"path": "mesh_t50.inp"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = IncludesRelationParser().apply(graph)

        includes = [r for r in result.relations if r.label == "includes"]
        assert len(includes) >= 1

        # キャッシュに保存されている
        cache_key = f"includes:{tmp_path / 'go_idx1.inp'}"
        cached = result.get_cache(cache_key)
        assert cached is not None
        assert "mesh_t50.inp" in cached


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
        nv = [r for r in result.relations if r.label == "next_version" and r.node1_id == v1.id and r.node2_id == v2.id]
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
            (n for n in result.nodes if n.name == "go_idx2.v2" and n.format == "inp"),
            None,
        )
        assert v2_inp is not None

        # v2.inp から始まる next_version がある（先は v3.dat かもしれない）
        nv = [r for r in result.relations if r.label == "next_version" and r.node1_id == v2_inp.id]
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
            (n for n in result.nodes if n.name == "go_idx1.v3" and n.format == "inp"),
            None,
        )
        assert go is not None
        includes = [r for r in result.relations if r.label == "includes" and r.node1_id == go.id]
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
            (n for n in result.nodes if n.name == "go_idx0.v29" and n.format == "inp"),
            None,
        )
        assert go is not None
        includes = [r for r in result.relations if r.label == "includes" and r.node1_id == go.id]
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
            (
                n
                for n in result.nodes
                if n.name == "go_idx2.v2" and n.format == "inp" and "old/" in n.properties.get("path", "")
            ),
            None,
        )
        assert go is not None
        includes = [r for r in result.relations if r.label == "includes" and r.node1_id == go.id]
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
            (n for n in result.nodes if n.name == "old" and n.format == "directory"),
            None,
        )
        assert old_dir is not None
        contains = [r for r in result.relations if r.label == "contains" and r.node1_id == old_dir.id]
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
        self,
        real_graph: ProjectGraph,
    ):
        """results/のJSONキーがgo_*.inpノードに伝搬される"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        result = JsonPropertyParser().apply(real_graph)
        go_idx1 = next(
            (n for n in result.nodes if n.name == "go_idx1.v3" and n.format == "inp"),
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
            (n for n in result.nodes if n.name == "go_idx0.v29" and n.format == "inp"),
            None,
        )
        assert go_idx0 is not None
        # go_idx0.v29_stress.json: {"0(center)": 0.25, "1": NaN, "2(edge)": NaN}
        assert go_idx0.properties["0(center)"] == 0.25
        assert go_idx0.properties["1"] is None  # NaN → None
        assert go_idx0.properties["2(edge)"] is None  # NaN → None

    def test_all_three_go_nodes_get_json_props(
        self,
        real_graph: ProjectGraph,
    ):
        """go_idx0, go_idx1, go_idx2 の3ノードにJSON情報が伝搬"""
        from services.parse.parsers.json_property_parser import JsonPropertyParser

        result = JsonPropertyParser().apply(real_graph)
        for name in ["go_idx0.v29", "go_idx1.v3", "go_idx2.v3"]:
            go = next(
                (n for n in result.nodes if n.name == name and n.format == "inp"),
                None,
            )
            assert go is not None, f"{name} not found"
            assert "0(center)" in go.properties, f"{name} missing JSON property '0(center)'"


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

    def test_results_direct_files_removed(self, real_graph: ProjectGraph):
        """results/ 直下のJSON(info-only)がフィルタで除去される"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        result = EnrichmentOnlyFilter().apply(real_graph)
        # results/直下のファイルは除去される
        direct_results = [
            n
            for n in result.nodes
            if n.properties.get("path", "").startswith("results/")
            and n.format != "directory"
            and n.properties.get("path", "").count("/") == 1
        ]
        assert len(direct_results) == 0

    def test_results_subdirectory_files_preserved(self, real_graph: ProjectGraph):
        """results/サブディレクトリ内のファイルはフィルタで除去されない"""
        from services.parse.parsers.enrichment_filter import EnrichmentOnlyFilter

        result = EnrichmentOnlyFilter().apply(real_graph)
        # results/サブディレクトリ内のファイルは残る
        subdir_results = [
            n
            for n in result.nodes
            if n.properties.get("path", "").startswith("results/")
            and n.format != "directory"
            and n.properties.get("path", "").count("/") >= 2
        ]
        assert len(subdir_results) > 0


# ====================================================================
# タイムスタンプ差分キャッシュ テスト
# ====================================================================


class TestTimestampCache:
    """ProjectGraphのタイムスタンプ差分キャッシュ機能テスト"""

    def test_is_file_modified_no_prev_timestamps(self, config: GraphConfig, tmp_path: Path):
        """前回タイムスタンプなしの場合、常にTrue"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        assert graph.is_file_modified("/any/path") is True

    def test_is_file_modified_new_file(self, config: GraphConfig, tmp_path: Path):
        """前回タイムスタンプに存在しないファイルはTrue"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        graph._prev_timestamps = {"/some/old/file": 1000.0}
        assert graph.is_file_modified("/some/new/file") is True

    def test_is_file_modified_unchanged_file(self, config: GraphConfig, tmp_path: Path):
        """mtimeが変わっていないファイルはFalse"""
        f = tmp_path / "test.inp"
        f.write_text("test", encoding="utf-8")
        mtime = f.stat().st_mtime
        graph = _make_graph([], config=config, project_root=tmp_path)
        graph._prev_timestamps = {str(f): mtime}
        assert graph.is_file_modified(str(f)) is False

    def test_is_file_modified_changed_file(self, config: GraphConfig, tmp_path: Path):
        """mtimeが変わったファイルはTrue"""
        f = tmp_path / "test.inp"
        f.write_text("test", encoding="utf-8")
        graph = _make_graph([], config=config, project_root=tmp_path)
        graph._prev_timestamps = {str(f): 0.0}  # 古いタイムスタンプ
        assert graph.is_file_modified(str(f)) is True

    def test_record_file_timestamp(self, config: GraphConfig, tmp_path: Path):
        """タイムスタンプの記録と取得"""
        graph = _make_graph([], config=config, project_root=tmp_path)
        graph.record_file_timestamp("/path/to/file", 12345.0)
        ts = graph.collect_file_timestamps()
        assert ts["/path/to/file"] == 12345.0


class TestTimestampPersistence:
    """GraphStorageのタイムスタンプ永続化テスト"""

    def test_save_and_load_timestamps(self, tmp_path: Path):
        """タイムスタンプの保存と読み込み"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        timestamps = {"/path/a": 1000.0, "/path/b": 2000.0}
        storage.save_timestamps(tmp_path, timestamps)
        loaded = storage.load_timestamps(tmp_path)
        assert loaded == timestamps

    def test_load_timestamps_no_file(self, tmp_path: Path):
        """ファイルが存在しない場合は空辞書"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        loaded = storage.load_timestamps(tmp_path)
        assert loaded == {}


@pytest.mark.skipif(
    not _has_pandas(),
    reason="pymesh（modules/pymesh/）の依存パッケージ(pandas)が未インストール",
)
class TestMeshTopologyGroups:
    """extract_mesh_topology_groups のテスト

    pymeshはmodules/pymesh/に存在するプロジェクト内パッケージ。
    pymeshの依存パッケージ（pandas等）が未インストールの場合のみスキップ。
    """

    def test_single_connected_group(self, tmp_path: Path):
        """ノード共有で全要素が1つの連結成分を形成"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_topology_groups

        # *ELSETは*ELEMENTのELSET=とは別に定義する
        # （pymeshはELSET=を要素ブロック名に使い、elset_dataには格納しない）
        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 2.0, 0.0, 0.0\n"
            "6, 2.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4\n"
            "1, 1, 2, 3, 4\n"
            "2, 2, 5, 6, 3\n"
            "*ELSET, ELSET=PART_A\n"
            "1\n"
            "*ELSET, ELSET=PART_B\n"
            "2\n"
        )
        inp_file = tmp_path / "connected.inp"
        inp_file.write_text(content, encoding="utf-8")

        result = extract_mesh_topology_groups(inp_file, verbose=False)
        assert result is not None
        # ノード2,3を共有するので1つのグループ
        assert len(result) == 1
        assert sorted(result[0]) == ["part_a", "part_b"]

    def test_two_disconnected_groups(self, tmp_path: Path):
        """ノード非共有で2つの独立した連結成分"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_topology_groups

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 10.0, 0.0, 0.0\n"
            "6, 11.0, 0.0, 0.0\n"
            "7, 11.0, 1.0, 0.0\n"
            "8, 10.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4\n"
            "1, 1, 2, 3, 4\n"
            "2, 5, 6, 7, 8\n"
            "*ELSET, ELSET=BODY\n"
            "1\n"
            "*ELSET, ELSET=SKIN\n"
            "2\n"
        )
        inp_file = tmp_path / "disconnected.inp"
        inp_file.write_text(content, encoding="utf-8")

        result = extract_mesh_topology_groups(inp_file, verbose=False)
        assert result is not None
        assert len(result) == 2
        group_names = [sorted(g) for g in result]
        assert ["body"] in group_names
        assert ["skin"] in group_names

    def test_no_elsets_returns_none(self, tmp_path: Path):
        """elsetが定義されていない場合はNone"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_topology_groups

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4\n"
            "1, 1, 2, 3, 4\n"
        )
        inp_file = tmp_path / "no_elset.inp"
        inp_file.write_text(content, encoding="utf-8")

        result = extract_mesh_topology_groups(inp_file, verbose=False)
        assert result is None

    def test_topology_groups_assigned_to_node(self, tmp_path: Path, config: GraphConfig):
        """AbaqusMeshParserがmesh_topology_groupsをノードに付与する"""
        from services.parse.connectors.abaqus.mesh_parser import AbaqusMeshParser

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 0.0, 0.0, 1.0\n"
            "6, 1.0, 0.0, 1.0\n"
            "7, 1.0, 1.0, 1.0\n"
            "8, 0.0, 1.0, 1.0\n"
            "*ELEMENT, TYPE=C3D8\n"
            "1, 1, 2, 3, 4, 5, 6, 7, 8\n"
            "*ELSET, ELSET=BODY\n"
            "1\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # キャッシュを投入してread_inp()のネットワーク呼び出しを避ける
        from services.parse.connectors.abaqus import read_inp as abq_read_inp

        abq_data = abq_read_inp(str(tmp_path / "go_idx1_v1.inp"), verbose=False)
        graph.set_cached_plugin_data("abaqus", str(tmp_path / "go_idx1_v1.inp"), abq_data)

        result = AbaqusMeshParser().apply(graph)
        node = result.nodes[0]

        # mesh_topology_groupsが付与されていること
        assert "mesh_topology_groups" in node.properties
        groups = node.properties["mesh_topology_groups"]
        assert isinstance(groups, list)
        assert len(groups) >= 1
        # bodyがいずれかのグループに含まれる（pymeshは小文字化する）
        all_elsets = [name for group in groups for name in group]
        assert "body" in all_elsets


class TestMeshParserCache:
    """AbaqusMeshParserのキャッシュ機能テスト"""

    def test_mesh_parser_uses_cache(self, tmp_path: Path, config: GraphConfig):
        """AbaqusMeshParserがキャッシュを使い、同一ファイルの再パースを避ける"""
        from unittest.mock import patch

        from services.parse.connectors.abaqus.mesh_parser import AbaqusMeshParser

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 3, 4\n"
        )
        (tmp_path / "go_idx1_v1.inp").write_text(content, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)

        # 先にキャッシュを投入
        from services.parse.connectors.abaqus import read_inp as abq_read_inp

        abq_data = abq_read_inp(str(tmp_path / "go_idx1_v1.inp"), verbose=False)
        graph.set_cached_plugin_data("abaqus", str(tmp_path / "go_idx1_v1.inp"), abq_data)

        # read_inp呼び出しをカウント
        call_count = 0
        original_read_inp = None

        def counting_read_inp(path, verbose=True, include_max_depth=5):
            nonlocal call_count
            call_count += 1
            return original_read_inp(path, verbose=verbose, include_max_depth=include_max_depth)

        from services.parse.connectors import abaqus

        original_read_inp = abaqus.read_inp

        with patch.object(abaqus, "read_inp", side_effect=counting_read_inp):
            AbaqusMeshParser().apply(graph)

        # キャッシュヒットによりread_inpは呼ばれない
        assert call_count == 0

    def test_mesh_parser_skips_unchanged_file(self, tmp_path: Path, config: GraphConfig):
        """タイムスタンプが変わっていないファイルをスキップ"""
        from services.parse.connectors.abaqus.mesh_parser import AbaqusMeshParser

        content = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n"
        f = tmp_path / "go_idx1_v1.inp"
        f.write_text(content, encoding="utf-8")
        mtime = f.stat().st_mtime

        nodes = [
            Node(id=1, type="go", name="go_idx1_v1", format="inp", properties={"path": "go_idx1_v1.inp"}),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        graph._prev_timestamps = {str(f): mtime}

        AbaqusMeshParser().apply(graph)

        # スキップされたのでmesh_node_countは付与されない
        assert "mesh_node_count" not in graph.nodes[0].properties


class TestDiffParserTimestamp:
    """AbaqusDiffParserのタイムスタンプ差分テスト"""

    def test_diff_parser_skips_unchanged_pair(self, tmp_path: Path, config: GraphConfig):
        """両方のファイルが未変更の場合、diffノードが作成されない"""
        from services.parse.connectors.abaqus.diff_parser import AbaqusDiffParser

        content_v1 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n"
        content_v2 = "*NODE, NSET=ALL\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n"

        f1 = tmp_path / "go_idx1_v1.inp"
        f2 = tmp_path / "go_idx1_v2.inp"
        f1.write_text(content_v1, encoding="utf-8")
        f2.write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        # 両方を「未変更」に設定
        graph._prev_timestamps = {
            str(f1): f1.stat().st_mtime,
            str(f2): f2.stat().st_mtime,
        }

        result = AbaqusDiffParser().apply(graph)

        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 0

    def test_diff_parser_runs_when_one_changed(self, tmp_path: Path, config: GraphConfig):
        """片方のファイルが変更されている場合、diffノードが作成される"""
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

        f1 = tmp_path / "go_idx1_v1.inp"
        f2 = tmp_path / "go_idx1_v2.inp"
        f1.write_text(content_v1, encoding="utf-8")
        f2.write_text(content_v2, encoding="utf-8")

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_v1",
                format="inp",
                properties={"path": "go_idx1_v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="go",
                name="go_idx1_v2",
                format="inp",
                properties={"path": "go_idx1_v2.inp", "index": "1", "version": "2"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        # v1は未変更、v2は変更済み
        graph._prev_timestamps = {
            str(f1): f1.stat().st_mtime,
            str(f2): 0.0,  # 古いタイムスタンプ
        }

        result = AbaqusDiffParser().apply(graph)

        diff_nodes = [n for n in result.nodes if n.type == "version_diff"]
        assert len(diff_nodes) == 1


@pytest.mark.skipif(
    not _has_pandas(),
    reason="pymesh（modules/pymesh/）の依存パッケージ(pandas)が未インストール",
)
class TestPymeshWithModules:
    """modules/pymeshを使ったテスト

    pymeshはmodules/pymesh/に存在するプロジェクト内パッケージ。
    依存パッケージ（pandas等）が未インストールの場合のみスキップ。
    """

    def test_mesher_with_cached_abq_data(self, tmp_path: Path):
        """cached_abq_dataを渡した場合、read_inp()がスキップされる"""
        from modules.pymesh.read_inp import read_inp

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 3, 4\n"
        )
        inp_file = tmp_path / "test.inp"
        inp_file.write_text(content, encoding="utf-8")

        # 事前にread_inp()で解析
        abq_data = read_inp(str(inp_file), verbose=False)

        # cached_abq_dataを渡してmesher生成
        from modules.pymesh.mesh import mesher

        mesh = mesher(str(inp_file), verbose=False, cached_abq_data=abq_data)

        assert mesh.get_number_of_nodes() == 4

    def test_extract_mesh_stats_with_cache(self, tmp_path: Path):
        """extract_mesh_statsにcached_abq_dataを渡した場合の動作"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "*ELEMENT, TYPE=CPS4, ELSET=EALL\n"
            "1, 1, 2, 3, 4\n"
        )
        inp_file = tmp_path / "test.inp"
        inp_file.write_text(content, encoding="utf-8")

        from modules.pymesh.read_inp import read_inp

        abq_data = read_inp(str(inp_file), verbose=False)

        stats = extract_mesh_stats(inp_file, verbose=False, cached_abq_data=abq_data)
        assert stats is not None
        assert stats["node_count"] == 4
        # キャッシュ経由でもキャッシュなしと同じ結果になること
        stats_no_cache = extract_mesh_stats(inp_file, verbose=False)
        assert stats["node_count"] == stats_no_cache["node_count"]
        assert stats["element_count"] == stats_no_cache["element_count"]

    def test_extract_mesh_stats_mixed_element_types(self, tmp_path: Path):
        """要素タイプ混在（C3D8+C3D4）でも品質計算が成功すること"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 0.0, 0.0, 1.0\n"
            "6, 1.0, 0.0, 1.0\n"
            "7, 1.0, 1.0, 1.0\n"
            "8, 0.0, 1.0, 1.0\n"
            "9, 2.0, 0.0, 0.0\n"
            "10, 2.0, 1.0, 0.5\n"
            "*ELEMENT, TYPE=C3D8, ELSET=HEXES\n"
            "1, 1, 2, 3, 4, 5, 6, 7, 8\n"
            "*ELEMENT, TYPE=C3D4, ELSET=TETS\n"
            "2, 2, 3, 9, 10\n"
        )
        inp_file = tmp_path / "mixed.inp"
        inp_file.write_text(content, encoding="utf-8")

        stats = extract_mesh_stats(inp_file, verbose=False)
        assert stats is not None
        assert stats["node_count"] == 10
        assert stats["element_count"] == 2
        # pymeshは要素タイプを小文字で保持する
        types_lower = {k.lower() for k in stats["element_types"]}
        assert "c3d8" in types_lower
        assert "c3d4" in types_lower
        # 品質統計が計算されていること（以前はallow_polymorphism=Falseで失敗していた）
        if "quality" in stats:
            for metric in ["volume", "detJ", "aspect_ratio", "skewness"]:
                if metric in stats["quality"]:
                    assert "min" in stats["quality"][metric]
                    assert "max" in stats["quality"][metric]
                    assert "mean" in stats["quality"][metric]

    def test_extract_element_quality_mixed_element_types(self, tmp_path: Path):
        """要素タイプ混在でも*ELEMENTキーワード別品質統計が計算されること"""
        from services.parse.connectors.abaqus.mesh import extract_element_quality_stats

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 0.0, 0.0, 1.0\n"
            "6, 1.0, 0.0, 1.0\n"
            "7, 1.0, 1.0, 1.0\n"
            "8, 0.0, 1.0, 1.0\n"
            "9, 2.0, 0.0, 0.0\n"
            "10, 2.0, 1.0, 0.5\n"
            "*ELEMENT, TYPE=C3D8, ELSET=HEXES\n"
            "1, 1, 2, 3, 4, 5, 6, 7, 8\n"
            "*ELEMENT, TYPE=C3D4, ELSET=TETS\n"
            "2, 2, 3, 9, 10\n"
        )
        inp_file = tmp_path / "mixed.inp"
        inp_file.write_text(content, encoding="utf-8")

        result = extract_element_quality_stats(inp_file, verbose=False)
        assert result is not None
        # 要素タイプ別にキーが生成される
        result_lower = {k.lower(): v for k, v in result.items()}
        assert "c3d8" in result_lower
        assert "c3d4" in result_lower
        assert result_lower["c3d8"]["element_count"] == 1
        assert result_lower["c3d4"]["element_count"] == 1
        for entry in result_lower.values():
            if "quality" in entry:
                for metric in entry["quality"].values():
                    assert "min" in metric
                    assert "max" in metric
                    assert "mean" in metric

    def test_compute_quality_single_element_type(self, tmp_path: Path):
        """単一要素タイプでの品質計算（回帰テスト）"""
        from services.parse.connectors.abaqus.mesh import extract_mesh_stats

        content = (
            "*NODE, NSET=ALL\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 1.0, 1.0, 0.0\n"
            "4, 0.0, 1.0, 0.0\n"
            "5, 0.0, 0.0, 1.0\n"
            "6, 1.0, 0.0, 1.0\n"
            "7, 1.0, 1.0, 1.0\n"
            "8, 0.0, 1.0, 1.0\n"
            "*ELEMENT, TYPE=C3D8, ELSET=ALL\n"
            "1, 1, 2, 3, 4, 5, 6, 7, 8\n"
        )
        inp_file = tmp_path / "single_type.inp"
        inp_file.write_text(content, encoding="utf-8")

        stats = extract_mesh_stats(inp_file, verbose=False)
        assert stats is not None
        assert stats["element_count"] == 1
        # 単一C3D8要素の品質が計算されること
        if "quality" in stats:
            assert "volume" in stats["quality"]
            vol = stats["quality"]["volume"]
            # 単位立方体の体積は1.0
            assert abs(vol["mean"] - 1.0) < 0.1


# =========================================================================
# AbstractExporter 基底クラス テスト
# =========================================================================


class TestAbstractExporter:
    """AbstractExporter基底クラスと自動登録のテスト"""

    def test_exporter_registry_contains_csv_json(self):
        """CSV/JSONエクスポーターがレジストリに登録されていること"""
        from services.export import get_exporter_registry

        registry = get_exporter_registry()
        cls_names = [cls.__name__ for cls in registry]
        assert "CsvExporter" in cls_names
        assert "JsonExporter" in cls_names

    def test_get_exporter_for_format_csv(self):
        """format="csv"でCsvExporterが返ること"""
        from services.export import get_exporter_for_format
        from services.export.connectors.csv_json import CsvExporter

        exporter_cls = get_exporter_for_format("csv")
        assert exporter_cls is CsvExporter

    def test_get_exporter_for_format_json(self):
        """format="json"でJsonExporterが返ること"""
        from services.export import get_exporter_for_format
        from services.export.connectors.csv_json import JsonExporter

        exporter_cls = get_exporter_for_format("json")
        assert exporter_cls is JsonExporter

    def test_get_exporter_for_format_unknown(self):
        """未知のformatではNoneが返ること"""
        from services.export import get_exporter_for_format

        assert get_exporter_for_format("unknown_format_xyz") is None

    def test_csv_exporter_export(self, tmp_path: Path):
        """CsvExporterのexport()がCSVファイルを生成すること"""
        from jj_types import GraphModel
        from services.export.connectors.csv_json import CsvExporter

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={"index": "1"}),
            Node(id=2, type="go", name="test2", format="inp", properties={"index": "2"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = CsvExporter()
        result = exporter.export(graph, project_root=tmp_path)
        assert result["count"] == 2
        assert result["output_path"].exists()
        content = result["output_path"].read_text(encoding="utf-8-sig")
        assert "test1" in content
        assert "test2" in content

    def test_json_exporter_export(self, tmp_path: Path):
        """JsonExporterのexport()がJSONファイルを生成すること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.csv_json import JsonExporter

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={"version": "1"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = JsonExporter()
        result = exporter.export(graph, project_root=tmp_path)
        assert result["count"] == 1
        data = json.loads(result["output_path"].read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["name"] == "test1"


# =========================================================================
# CSV/JSONエクスポーターのElset品質統計平坦化テスト
# =========================================================================


class TestElsetCsvExport:
    """Elsetノードの品質統計がCSVエクスポートで平坦化されること"""

    def test_elset_quality_flattened_in_csv(self, tmp_path: Path):
        """quality辞書が"."区切りで平坦化されたカラムになること"""
        from jj_types import GraphModel
        from services.export.connectors.csv_json import CsvExporter

        nodes = [
            Node(
                id=1,
                type="abaqus_elset",
                name="ELSET1",
                format="",
                properties={
                    "element_count": 100,
                    "material": "Steel",
                    "quality": {
                        "volume": {"min": 0.1, "max": 1.0, "mean": 0.5},
                        "aspect_ratio": {"min": 1.0, "max": 3.0, "mean": 1.5},
                    },
                },
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = CsvExporter()
        result = exporter.export(graph, project_root=tmp_path)
        content = result["output_path"].read_text(encoding="utf-8-sig")
        # 平坦化されたキーがヘッダーに含まれること
        assert "quality.volume.min" in content
        assert "quality.volume.max" in content
        assert "quality.aspect_ratio.mean" in content

    def test_elset_type_filter_in_csv(self, tmp_path: Path):
        """type_filter="abaqus_elset"でelsetノードのみエクスポートされること"""
        from jj_types import GraphModel
        from services.export.connectors.csv_json import CsvExporter

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={}),
            Node(id=2, type="abaqus_elset", name="ELSET1", format="", properties={"element_count": 50}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = CsvExporter()
        result = exporter.export(graph, project_root=tmp_path, type_filter="abaqus_elset")
        assert result["count"] == 1
        content = result["output_path"].read_text(encoding="utf-8-sig")
        assert "ELSET1" in content
        assert "test1" not in content


# =========================================================================
# ABQDataキャッシュ自動クリーンアップテスト
# =========================================================================


class TestABQCacheCleanup:
    """ABQDataキャッシュの自動クリーンアップテスト"""

    def test_cleanup_removes_old_cache(self, tmp_path: Path):
        """max_age_daysを超えたキャッシュファイルが削除されること"""
        import time

        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        project_root = tmp_path
        cache_dir = project_root / ".j2" / "storage" / "plugin_cache" / "abaqus"
        cache_dir.mkdir(parents=True)

        # 古いキャッシュファイルを作成（mtimeを31日前に設定）
        old_file = cache_dir / "old_cache.pickle"
        old_file.write_bytes(b"old")
        old_mtime = time.time() - (31 * 86400)
        import os

        os.utime(old_file, (old_mtime, old_mtime))

        # 新しいキャッシュファイルを作成
        new_file = cache_dir / "new_cache.pickle"
        new_file.write_bytes(b"new")

        deleted = storage.cleanup_plugin_cache(project_root, "abaqus", max_age_days=30)
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_respects_max_count(self, tmp_path: Path):
        """max_countを超えたキャッシュが古い順に削除されること"""
        import time

        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        project_root = tmp_path
        cache_dir = project_root / ".j2" / "storage" / "plugin_cache" / "abaqus"
        cache_dir.mkdir(parents=True)

        # 5つのキャッシュファイルを作成（異なるmtimeで）
        now = time.time()
        for i in range(5):
            f = cache_dir / f"cache_{i}.pickle"
            f.write_bytes(f"data_{i}".encode())
            import os

            os.utime(f, (now - (5 - i) * 100, now - (5 - i) * 100))

        # max_count=3に制限
        deleted = storage.cleanup_plugin_cache(project_root, "abaqus", max_age_days=365, max_count=3)
        assert deleted == 2  # 古い2つが削除される
        remaining = list(cache_dir.glob("*.pickle"))
        assert len(remaining) == 3

    def test_cleanup_empty_dir(self, tmp_path: Path):
        """空のキャッシュディレクトリで0が返ること"""
        from services.graph.storage import GraphStorage

        storage = GraphStorage()
        deleted = storage.cleanup_plugin_cache(tmp_path, max_age_days=30)
        assert deleted == 0

    def test_cleanup_called_after_parse_and_save(self):
        """parse_and_save後にcleanup_plugin_cacheが呼ばれること"""
        from unittest.mock import MagicMock, patch

        from services.graph import GraphService

        with patch.object(GraphService, "parse_project") as mock_parse, patch.object(GraphService, "save") as mock_save:
            mock_graph = MagicMock()
            mock_parse.return_value = mock_graph
            mock_save.return_value = Path("/tmp/test.yaml")

            service = GraphService(project_root=Path("/tmp/test_project"))
            # cleanup_plugin_cacheをモック
            service.storage.cleanup_plugin_cache = MagicMock(return_value=0)
            service.parse_and_save()

            service.storage.cleanup_plugin_cache.assert_called_once()


# =========================================================================
# Obsidian Elset-材料 Dataviewクエリテスト
# =========================================================================


class TestObsidianElsetDataview:
    """Obsidianエクスポートのelsetノード用Dataviewクエリのテスト"""

    def test_elset_node_has_dataview_query(self):
        """abaqus_elsetノードのmd出力にDataviewクエリが含まれること"""
        from services.export.connectors.obsidian import ObsidianConnector

        connector = ObsidianConnector(project_root=Path("/tmp/test"))
        node = Node(
            id=1,
            type="abaqus_elset",
            name="ELSET_A",
            format="",
            properties={
                "element_count": 100,
                "material": "Steel_S235",
                "source_file": "go_test_v1.inp",
            },
        )
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)
        assert "```dataview" in content
        assert 'WHERE material = "Steel_S235"' in content
        assert "TABLE material" in content

    def test_material_node_has_elset_dataview(self):
        """abaqus_materialノードのmd出力にelset用Dataviewクエリが含まれること"""
        from services.export.connectors.obsidian import ObsidianConnector

        connector = ObsidianConnector(project_root=Path("/tmp/test"))
        node = Node(
            id=1,
            type="abaqus_material",
            name="Steel_S235",
            format="material",
            properties={},
        )
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)
        assert "```dataview" in content
        assert 'WHERE material = "Steel_S235"' in content
        assert "使用Elset" in content

    def test_go_node_with_elsets_has_dataview(self):
        """elsets propertyを持つgoノードにDataviewクエリが含まれること"""
        from services.export.connectors.obsidian import ObsidianConnector

        connector = ObsidianConnector(project_root=Path("/tmp/test"))
        node = Node(
            id=1,
            type="go",
            name="go_test_v1",
            format="inp",
            properties={
                "elsets": ["ELSET_A", "ELSET_B"],
                "path": "go_test_v1.inp",
            },
        )
        frontmatter = connector.node_to_frontmatter(node)
        content = connector._format_md(frontmatter, node)
        assert "```dataview" in content
        assert "所属Elset一覧" in content


# =========================================================================
# Obsidian Canvas 出力テスト
# =========================================================================


class TestObsidianElsetCanvas:
    """Obsidian Canvasのelset-材料マップ生成テスト"""

    def test_canvas_generated_with_elsets(self, tmp_path: Path):
        """elsetノードが存在する場合にcanvasファイルが生成されること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
            Node(
                id=2,
                type="abaqus_elset",
                name="ELSET_A",
                format="",
                properties={"material": "Steel", "element_count": 100},
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_canvas(graph)

        assert canvas_path is not None
        assert canvas_path.exists()
        assert canvas_path.suffix == ".canvas"

        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["label"] == "uses_material"

    def test_canvas_not_generated_without_elsets(self, tmp_path: Path):
        """elsetノードがない場合にcanvasが生成されないこと"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="test", format="inp", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_canvas(graph)
        assert canvas_path is None

    def test_canvas_unassigned_elsets(self, tmp_path: Path):
        """材料が割り当てられていないelsetもcanvasに含まれること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="abaqus_elset", name="ELSET_A", format="", properties={"element_count": 50}),  # 材料なし
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_canvas(graph)

        assert canvas_path is not None
        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0  # 材料がないのでエッジなし


# =========================================================================
# AbstractExporterレジストリ統合テスト
# =========================================================================


class TestExporterRegistry:
    """全エクスポーターがレジストリに登録されていることを確認するテスト"""

    def test_all_exporters_registered(self):
        """全6形式のエクスポーターがレジストリに登録されていること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_registry

        registry = get_exporter_registry()
        formats = {cls.format for cls in registry}
        assert "csv" in formats
        assert "json" in formats
        assert "obsidian" in formats
        assert "neo4j" in formats
        assert "cypher" in formats
        assert "dashboard-json" in formats

    def test_exporter_priority_order(self):
        """エクスポーターがpriority順で取得できること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_registry

        registry = get_exporter_registry()
        sorted_exporters = sorted(registry, key=lambda cls: cls.priority)
        priorities = [cls.priority for cls in sorted_exporters]
        assert priorities == sorted(priorities)

    def test_obsidian_exporter_via_registry(self, tmp_path: Path):
        """ObsidianExporterがレジストリ経由で取得・実行できること"""
        import services.export.connectors  # noqa: F401
        from jj_types import GraphModel
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("obsidian")
        assert exporter_cls is not None
        assert exporter_cls.format == "obsidian"
        assert exporter_cls.priority == 20

        # 実際にexport実行（空グラフ）
        graph = GraphModel(nodes=[], relations=[])
        exporter = exporter_cls()
        result = exporter.export(graph, project_root=tmp_path)
        assert "written_paths" in result
        # 空グラフでもVault設定（3ファイル）が初回生成される
        assert result["count"] == 3
        assert result["vault_initialized"] is True

    def test_cypher_exporter_via_registry(self, tmp_path: Path):
        """CypherExporterがレジストリ経由で取得・実行できること"""
        import services.export.connectors  # noqa: F401
        from jj_types import GraphModel
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("cypher")
        assert exporter_cls is not None
        assert exporter_cls.format == "cypher"

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = exporter_cls()
        result = exporter.export(graph, project_root=tmp_path)
        assert result["output_path"].exists()
        assert result["node_count"] == 1

    def test_dashboard_json_exporter_via_registry(self, tmp_path: Path):
        """DashboardJsonExporterがレジストリ経由で取得・実行できること"""
        import services.export.connectors  # noqa: F401
        from jj_types import GraphModel
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("dashboard-json")
        assert exporter_cls is not None
        assert exporter_cls.format == "dashboard-json"

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={"index": "1", "version": "1"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = exporter_cls()
        result = exporter.export(graph, project_root=tmp_path)
        assert result["output_path"].exists()
        assert result["node_count"] == 1

    def test_export_by_format_method(self, tmp_path: Path):
        """GraphCommandService.export_by_format()が動作すること"""
        from jj_types import GraphModel
        from services.service.graph_command import GraphCommandService

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        service = GraphCommandService(tmp_path)
        result = service.export_by_format(graph, "csv")
        assert result["count"] == 1
        assert result["output_path"].exists()

    def test_export_by_format_unknown_raises(self, tmp_path: Path):
        """未知の形式でValueErrorが発生すること"""
        from jj_types import GraphModel
        from services.service.graph_command import GraphCommandService

        graph = GraphModel(nodes=[], relations=[])
        service = GraphCommandService(tmp_path)
        try:
            service.export_by_format(graph, "unknown_format_xyz")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "未対応のエクスポート形式" in str(e)


# =========================================================================
# Obsidian Canvas 3層（Elset-材料-go）テスト
# =========================================================================


class TestObsidianElsetMaterialGoCanvas:
    """Obsidian Canvasのelset-材料-go 3層マップ生成テスト"""

    def test_three_layer_canvas_generated(self, tmp_path: Path):
        """elset/material/goが揃っている場合に3層canvasが生成されること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
            Node(id=2, type="abaqus_material", name="Steel", format="material", properties={}),
            Node(
                id=3,
                type="abaqus_elset",
                name="ELSET_A",
                format="",
                properties={
                    "material": "Steel",
                    "element_count": 100,
                    "source_file": "go_test_v1.inp",
                },
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_go_canvas(graph)

        assert canvas_path is not None
        assert canvas_path.exists()
        assert "elset_material_go_map" in canvas_path.name

        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        # 3ノード: go, material, elset
        assert len(data["nodes"]) == 3

        # エッジ: uses_material + defined_in = 2
        edge_labels = {e["label"] for e in data["edges"]}
        assert "uses_material" in edge_labels
        assert "defined_in" in edge_labels
        assert len(data["edges"]) == 2

    def test_three_layer_canvas_no_go_nodes(self, tmp_path: Path):
        """goノードがなくてもelset-materialのcanvasが生成されること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="abaqus_material", name="Steel", format="material", properties={}),
            Node(
                id=2,
                type="abaqus_elset",
                name="ELSET_A",
                format="",
                properties={"material": "Steel", "element_count": 50},
            ),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_go_canvas(graph)

        assert canvas_path is not None
        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        # 2ノード: material + elset (goなし)
        assert len(data["nodes"]) == 2
        # 1エッジ: uses_material のみ (defined_inなし)
        assert len(data["edges"]) == 1
        assert data["edges"][0]["label"] == "uses_material"

    def test_three_layer_canvas_unassigned_with_go(self, tmp_path: Path):
        """材料未割り当てelsetでもsource_fileがあればgoへのエッジが生成されること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
            Node(
                id=2,
                type="abaqus_elset",
                name="ELSET_A",
                format="",
                properties={
                    "element_count": 50,
                    "source_file": "go_test_v1.inp",
                },
            ),  # 材料なし
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_go_canvas(graph)

        assert canvas_path is not None
        data = json.loads(canvas_path.read_text(encoding="utf-8"))
        # 2ノード: go + elset
        assert len(data["nodes"]) == 2
        # 1エッジ: defined_in (材料エッジなし)
        assert len(data["edges"]) == 1
        assert data["edges"][0]["label"] == "defined_in"

    def test_three_layer_canvas_not_generated_without_elsets(self, tmp_path: Path):
        """elsetがない場合にcanvasが生成されないこと"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="test", format="inp", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        canvas_path = connector._write_elset_material_go_canvas(graph)
        assert canvas_path is None


# =========================================================================
# format_cli_result テスト
# =========================================================================


class TestFormatCliResult:
    """各エクスポーターのformat_cli_result()メソッドのテスト"""

    def test_csv_exporter_cli_result(self, tmp_path: Path):
        """CsvExporterのCLI出力が正しくフォーマットされること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("csv")
        exporter = exporter_cls()
        result = {
            "output_path": tmp_path / "export.csv",
            "count": 42,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "CSV" in output
        assert "42" in output
        assert "export.csv" in output

    def test_json_exporter_cli_result(self, tmp_path: Path):
        """JsonExporterのCLI出力が正しくフォーマットされること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("json")
        exporter = exporter_cls()
        result = {
            "output_path": tmp_path / "export.json",
            "count": 10,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "JSON" in output
        assert "10" in output

    def test_obsidian_exporter_cli_result(self, tmp_path: Path):
        """ObsidianExporterのCLI出力にファイル数が含まれること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("obsidian")
        exporter = exporter_cls()
        result = {
            "written_paths": [tmp_path / "a.md", tmp_path / "b.md"],
            "count": 2,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "2" in output
        assert "エクスポート完了" in output

    def test_cypher_exporter_cli_result(self, tmp_path: Path):
        """CypherExporterのCLI出力にノード/リレーション数が含まれること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("cypher")
        exporter = exporter_cls()
        result = {
            "output_path": tmp_path / "export.cypher",
            "node_count": 5,
            "relation_count": 3,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "Cypher" in output
        assert "5" in output
        assert "3" in output

    def test_dashboard_json_cli_result(self, tmp_path: Path):
        """DashboardJsonExporterのCLI出力にテーブル行数が含まれること"""
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format("dashboard-json")
        exporter = exporter_cls()
        result = {
            "output_path": tmp_path / "dashboard.json",
            "node_count": 10,
            "relation_count": 5,
            "row_count": 8,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "dashboard-json" in output
        assert "8" in output


# =========================================================================
# export_unified テスト
# =========================================================================


class TestExportUnified:
    """GraphCommandService.export_unified()のテスト"""

    def test_export_unified_csv(self, tmp_path: Path):
        """CSVエクスポートがexport_unified経由で実行できること"""
        from jj_types import GraphModel
        from services.service.graph_command import GraphCommandService

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={"index": "1", "version": "1"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        service = GraphCommandService(tmp_path)
        result, exporter = service.export_unified(graph, "csv")
        assert result["count"] == 1
        assert result["output_path"].exists()
        assert exporter.format == "csv"

    def test_export_unified_obsidian(self, tmp_path: Path):
        """Obsidianエクスポートがexport_unified経由で実行できること"""
        from jj_types import GraphModel
        from services.service.graph_command import GraphCommandService

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={"path": "test1.inp"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        service = GraphCommandService(tmp_path)
        result, exporter = service.export_unified(graph, "obsidian")
        assert result["count"] > 0
        assert exporter.format == "obsidian"

    def test_export_unified_unknown_raises(self, tmp_path: Path):
        """未知の形式でValueErrorが発生すること"""
        from jj_types import GraphModel
        from services.service.graph_command import GraphCommandService

        graph = GraphModel(nodes=[], relations=[])
        service = GraphCommandService(tmp_path)
        try:
            service.export_unified(graph, "unknown_format")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "未対応のエクスポート形式" in str(e)

    def test_export_unified_returns_exporter_instance(self, tmp_path: Path):
        """export_unifiedがエクスポーターインスタンスを返すこと"""
        from jj_types import GraphModel
        from services.export import AbstractExporter
        from services.service.graph_command import GraphCommandService

        nodes = [
            Node(id=1, type="go", name="test1", format="inp", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        service = GraphCommandService(tmp_path)
        result, exporter = service.export_unified(graph, "cypher")
        assert isinstance(exporter, AbstractExporter)
        # format_cli_resultが呼べること
        output = exporter.format_cli_result(result, tmp_path)
        assert isinstance(output, str)
        assert len(output) > 0


# =========================================================================
# Obsidianサマリーノート テスト
# =========================================================================


class TestObsidianSummaryNote:
    """Obsidianサマリーノート（jj-summary.md）生成テスト"""

    def test_summary_note_generated(self, tmp_path: Path):
        """ノードがある場合にサマリーノートが生成されること"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
            Node(id=2, type="abaqus_material", name="Steel", format="material", properties={}),
        ]
        graph = GraphModel(
            nodes=nodes,
            relations=[
                Relation(id=1, label="uses_material", node1_id=1, node2_id=2),
            ],
        )
        connector = ObsidianConnector(project_root=tmp_path)
        summary_path = connector._write_summary_note(graph)

        assert summary_path is not None
        assert summary_path.exists()
        assert summary_path.name == "jj-summary.md"

        content = summary_path.read_text(encoding="utf-8")
        # frontmatter
        assert "tags:" in content
        # 概要テーブル
        assert "go" in content
        assert "abaqus_material" in content
        # 統計情報
        assert "2" in content  # 総ノード数
        assert "1" in content  # 総リレーション数
        # Dataviewクエリ
        assert "dataview" in content

    def test_summary_note_not_generated_for_empty_graph(self, tmp_path: Path):
        """空のグラフではサマリーノートが生成されないこと"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        graph = GraphModel(nodes=[], relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        summary_path = connector._write_summary_note(graph)
        assert summary_path is None

    def test_summary_note_type_sections(self, tmp_path: Path):
        """各タイプごとにDataviewセクションが生成されること"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="go1", format="inp", properties={}),
            Node(id=2, type="go", name="go2", format="inp", properties={}),
            Node(id=3, type="mesh", name="mesh1", format="cdb", properties={}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        summary_path = connector._write_summary_note(graph)

        content = summary_path.read_text(encoding="utf-8")
        # タイプ別セクション
        assert "### go" in content
        assert "### mesh" in content
        assert "2件" in content  # go: 2件


# =========================================================================
# Obsidian Vault設定自動生成 テスト
# =========================================================================


class TestObsidianVaultConfig:
    """Obsidian Vault設定ファイル（.obsidian/）自動生成テスト"""

    def test_vault_config_created_on_first_export(self, tmp_path: Path):
        """初回エクスポート時に.obsidian/ディレクトリが生成されること"""
        import json

        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        written = connector.export_graph(graph)

        obsidian_dir = tmp_path / ".obsidian"
        assert obsidian_dir.exists()

        # app.json が生成される
        app_path = obsidian_dir / "app.json"
        assert app_path.exists()
        app_config = json.loads(app_path.read_text(encoding="utf-8"))
        assert app_config["useMarkdownLinks"] is False
        assert app_config["showFrontmatter"] is True

        # community-plugins.json が生成される
        cp_path = obsidian_dir / "community-plugins.json"
        assert cp_path.exists()
        plugins = json.loads(cp_path.read_text(encoding="utf-8"))
        assert "dataview" in plugins
        assert "dbfolder" in plugins

        # core-plugins-migration.json が生成される
        core_path = obsidian_dir / "core-plugins-migration.json"
        assert core_path.exists()
        core_config = json.loads(core_path.read_text(encoding="utf-8"))
        assert core_config["canvas"] is True

        # written リストに .obsidian/ 配下のファイルが含まれる
        obsidian_paths = [p for p in written if ".obsidian" in str(p)]
        assert len(obsidian_paths) == 3

    def test_vault_config_not_overwritten(self, tmp_path: Path):
        """既存の.obsidian/ディレクトリがある場合は変更しないこと"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianConnector

        # 事前に.obsidian/を作成（ユーザーの既存Vault）
        obsidian_dir = tmp_path / ".obsidian"
        obsidian_dir.mkdir()
        (obsidian_dir / "app.json").write_text('{"custom": true}', encoding="utf-8")

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        connector = ObsidianConnector(project_root=tmp_path)
        written = connector.export_graph(graph)

        # 既存のapp.jsonは変更されない
        app_content = (obsidian_dir / "app.json").read_text(encoding="utf-8")
        assert '"custom": true' in app_content

        # .obsidian/配下のファイルはwrittenに含まれない
        obsidian_paths = [p for p in written if ".obsidian" in str(p)]
        assert len(obsidian_paths) == 0

    def test_vault_config_standalone(self, tmp_path: Path):
        """_write_vault_config()を単独で呼んだ場合のテスト"""

        from services.export.connectors.obsidian import ObsidianConnector

        connector = ObsidianConnector(project_root=tmp_path)
        written = connector._write_vault_config()
        assert len(written) == 3

        # 2回目は空リスト（既にディレクトリが存在するため）
        written2 = connector._write_vault_config()
        assert len(written2) == 0

    def test_exporter_vault_initialized_flag(self, tmp_path: Path):
        """ObsidianExporterのexport結果にvault_initializedフラグが含まれること"""
        from jj_types import GraphModel
        from services.export.connectors.obsidian import ObsidianExporter

        nodes = [
            Node(id=1, type="go", name="go_test_v1", format="inp", properties={"path": "go_test_v1.inp"}),
        ]
        graph = GraphModel(nodes=nodes, relations=[])
        exporter = ObsidianExporter()
        result = exporter.export(graph, project_root=tmp_path)

        assert result["vault_initialized"] is True
        assert result["count"] > 0

        # 2回目はvault_initialized=False
        result2 = exporter.export(graph, project_root=tmp_path, overwrite=True)
        assert result2["vault_initialized"] is False

    def test_format_cli_result_with_vault_init(self, tmp_path: Path):
        """Vault初期化時のCLI出力に案内が含まれること"""
        from services.export.connectors.obsidian import ObsidianExporter

        exporter = ObsidianExporter()
        result = {
            "written_paths": [tmp_path / ".obsidian" / "app.json"],
            "count": 1,
            "vault_initialized": True,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "Vault初期化" in output
        assert "Dataview" in output
        assert "DB Folder" in output

    def test_format_cli_result_without_vault_init(self, tmp_path: Path):
        """Vault初期化なしの場合は案内が表示されないこと"""
        from services.export.connectors.obsidian import ObsidianExporter

        exporter = ObsidianExporter()
        result = {
            "written_paths": [],
            "count": 0,
            "vault_initialized": False,
        }
        output = exporter.format_cli_result(result, tmp_path)
        assert "Vault初期化" not in output


# ====================================================================
# ResultsMetadataParser テスト
# ====================================================================


class TestResultsMetadataParser:
    """ResultsMetadataParser の単体テスト"""

    def test_extracts_metadata_from_results_subdirectory(self, config: GraphConfig, tmp_path: Path):
        """results/サブディレクトリのファイルからメタデータを抽出する"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        # ファイルノードにメタデータが付与される
        png_node = result.get_node_by_id(2)
        assert png_node is not None
        assert png_node.properties["step"] == "0"
        assert png_node.properties["frame"] == "10"
        assert png_node.properties["vmax"] == "10.0"
        assert png_node.properties["vmin"] == "5.0"
        assert png_node.properties["result_key"] == "S-S33"

    def test_assigns_results_to_go_inp_node(self, config: GraphConfig, tmp_path: Path):
        """go_*.inpノードにresults.{result_key}プロパティが割り当てられる"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        assert "results.S-S33" in inp_node.properties
        entries = inp_node.properties["results.S-S33"]
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert entries[0]["path"] == "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"
        assert entries[0]["step"] == "0"
        assert entries[0]["frame"] == "10"
        assert entries[0]["vmax"] == "10.0"
        assert entries[0]["vmin"] == "5.0"

    def test_multiple_entries_same_result_key_different_params(self, config: GraphConfig, tmp_path: Path):
        """同じresult_keyでstep/frame/vmax/vmin違いは別エントリとして格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
            Node(
                id=3,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax15.0_vmin3.0",
                format="png",
                properties={"path": "results/step1_frame20/go_idx1.v1_S-S33_vmax15.0_vmin3.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        entries = inp_node.properties["results.S-S33"]
        assert isinstance(entries, list)
        assert len(entries) == 2

        # 各エントリのパラメータが異なることを確認
        steps = {e["step"] for e in entries}
        assert steps == {"0", "1"}
        frames = {e["frame"] for e in entries}
        assert frames == {"10", "20"}

    def test_different_result_keys_separate_properties(self, config: GraphConfig, tmp_path: Path):
        """異なるresult_keyは別のプロパティキーとして格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
            Node(
                id=3,
                type="unknown",
                name="go_idx1.v1_U-U3_vmax1.0_vmin0.5",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_U-U3_vmax1.0_vmin0.5.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        assert "results.S-S33" in inp_node.properties
        assert "results.U-U3" in inp_node.properties
        assert len(inp_node.properties["results.S-S33"]) == 1
        assert len(inp_node.properties["results.U-U3"]) == 1

    def test_no_match_when_no_go_inp(self, config: GraphConfig, tmp_path: Path):
        """go_*.inpノードがない場合は何も変更しない"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)
        assert len(result.nodes) == 1

    def test_results_direct_file_ignored(self, config: GraphConfig, tmp_path: Path):
        """results/直下のファイルはResultsMetadataParserの対象外"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(id=1, type="go", name="go_idx1", format="inp", properties={"path": "go_idx1.inp", "index": "1"}),
            Node(
                id=2,
                type="unknown",
                name="go_idx1_stress",
                format="json",
                properties={"path": "results/go_idx1_stress.json"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        # go_inp ノードにresults.* プロパティが追加されていないことを確認
        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        results_keys = [k for k in inp_node.properties if k.startswith("results.")]
        assert len(results_keys) == 0


class TestResultsMetadataParserHelpers:
    """ResultsMetadataParser のヘルパー関数テスト"""

    def test_parse_directory_metadata(self):
        """ディレクトリ名からメタデータを抽出する"""
        from services.parse.parsers.results_metadata_parser import _parse_directory_metadata

        result = _parse_directory_metadata("step0_frame10")
        assert result == {"step": "0", "frame": "10"}

    def test_parse_directory_metadata_single_key(self):
        """ディレクトリ名にキーが1つの場合"""
        from services.parse.parsers.results_metadata_parser import _parse_directory_metadata

        result = _parse_directory_metadata("step5")
        assert result == {"step": "5"}

    def test_is_in_results_subdirectory(self):
        """results/サブディレクトリの判定"""
        from services.parse.parsers.results_metadata_parser import _is_in_results_subdirectory

        assert _is_in_results_subdirectory("results/step0_frame10/foo.png") == (True, "step0_frame10")
        assert _is_in_results_subdirectory("results/foo.json") == (False, "")
        assert _is_in_results_subdirectory("other/foo.png") == (False, "")

    def test_parse_result_filename(self):
        """結果ファイル名のパース"""
        from services.parse.parsers.results_metadata_parser import _parse_result_filename

        go_basenames = {"go_idx1.v1", "go_idx2.v3"}

        basename, key, params = _parse_result_filename("go_idx1.v1_S-S33_vmax10.0_vmin5.0", go_basenames)
        assert basename == "go_idx1.v1"
        assert key == "S-S33"
        assert params == {"vmax": "10.0", "vmin": "5.0"}

    def test_parse_result_filename_single_component(self):
        """ダッシュなしの結果キー（PEEQ等）"""
        from services.parse.parsers.results_metadata_parser import _parse_result_filename

        go_basenames = {"go_idx1.v1"}

        basename, key, params = _parse_result_filename("go_idx1.v1_PEEQ_vmax0.1_vmin0.0", go_basenames)
        assert basename == "go_idx1.v1"
        assert key == "PEEQ"
        assert params == {"vmax": "0.1", "vmin": "0.0"}

    def test_parse_result_filename_no_match(self):
        """マッチしないファイル名"""
        from services.parse.parsers.results_metadata_parser import _parse_result_filename

        go_basenames = {"go_idx1.v1"}

        basename, key, _params = _parse_result_filename("unknown_file", go_basenames)
        assert basename == ""
        assert key == ""

    def test_parse_result_filename_with_separate_vmin_value(self):
        """vmin_5.0のように値が別トークンの場合"""
        from services.parse.parsers.results_metadata_parser import _parse_result_filename

        go_basenames = {"go_idx1.v1"}

        basename, key, params = _parse_result_filename("go_idx1.v1_S-S33_vmax10.0_vmin_5.0", go_basenames)
        assert basename == "go_idx1.v1"
        assert key == "S-S33"
        assert params["vmax"] == "10.0"
        assert params["vmin"] == "5.0"


class TestResultsMetadataParserRealData:
    """test_asset1の実データを使ったResultsMetadataParserテスト"""

    def test_results_subdirectory_metadata_extracted(self, real_graph: ProjectGraph):
        """results/サブディレクトリのPNGファイルからメタデータが抽出される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        result = ResultsMetadataParser().apply(real_graph)

        # results/step0_frame10/ 内のファイルノードを検索
        subdir_nodes = [n for n in result.nodes if "step0_frame10" in n.properties.get("path", "")]
        assert len(subdir_nodes) > 0

        # メタデータが付与されていることを確認
        for node in subdir_nodes:
            assert node.properties.get("step") == "0"
            assert node.properties.get("frame") == "10"

    def test_go_inp_gets_results_property(self, real_graph: ProjectGraph):
        """go_*.inpノードにresults.{key}プロパティが割り当てられる"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        result = ResultsMetadataParser().apply(real_graph)

        # go_idx1.v3.inp ノードを検索
        go_node = None
        for n in result.nodes:
            if n.name == "go_idx1.v3" and n.format == "inp":
                go_node = n
                break
        assert go_node is not None

        # results.S-S33 プロパティが存在する
        assert "results.S-S33" in go_node.properties
        entries = go_node.properties["results.S-S33"]
        assert isinstance(entries, list)
        assert len(entries) >= 1

    def test_multiple_steps_create_separate_entries(self, real_graph: ProjectGraph):
        """異なるstepのファイルが同じresult_keyに別エントリとして格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        result = ResultsMetadataParser().apply(real_graph)

        go_node = None
        for n in result.nodes:
            if n.name == "go_idx1.v3" and n.format == "inp":
                go_node = n
                break
        assert go_node is not None

        entries = go_node.properties.get("results.S-S33", [])
        # step0_frame10 と step1_frame20 の2エントリがある
        assert len(entries) == 2
        steps = {e["step"] for e in entries}
        assert steps == {"0", "1"}


# ====================================================================
# ResultsMetadataParser 負の値対応テスト
# ====================================================================


class TestResultsMetadataParserNegativeValues:
    """ResultsMetadataParser の負の値対応テスト"""

    def test_negative_vmin_parsed(self, config: GraphConfig, tmp_path: Path):
        """vmin-50.0 が vmin="-50.0" として解析される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v3",
                format="inp",
                properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13",
                format="png",
                properties={"path": "results/contours/go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        png_node = result.get_node_by_id(2)
        assert png_node is not None
        assert png_node.properties["vmax"] == "50.0"
        assert png_node.properties["vmin"] == "-50.0"
        assert png_node.properties["step"] == "0"
        assert png_node.properties["frame"] == "10"
        assert png_node.properties["result_key"] == "S-S13"

    def test_negative_value_in_results_entry(self, config: GraphConfig, tmp_path: Path):
        """go_ノードのresultsエントリに負の値が正しく格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v3",
                format="inp",
                properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
            ),
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13",
                format="png",
                properties={"path": "results/contours/go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        entries = go_node.properties.get("results.S-S13", [])
        assert len(entries) == 1
        assert entries[0]["vmin"] == "-50.0"
        assert entries[0]["vmax"] == "50.0"


# ====================================================================
# ResultsMetadataParser 新構造（GOノードベースディレクトリ）テスト
# ====================================================================


class TestResultsMetadataParserNewStructure:
    """ResultsMetadataParser の新構造（GOノードベースディレクトリ）テスト

    新構造: results/{go_basename}/ ディレクトリに結果ファイルを配置
    ファイル名パターン: {result_key}[_{step_info}][_{params}].{ext}
    """

    def test_new_structure_extracts_metadata(self, config: GraphConfig, tmp_path: Path):
        """新構造のファイルからメタデータを抽出する"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S33_step0_frame10_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/go_idx1.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        png_node = result.get_node_by_id(2)
        assert png_node is not None
        assert png_node.properties["step"] == "0"
        assert png_node.properties["frame"] == "10"
        assert png_node.properties["vmax"] == "10.0"
        assert png_node.properties["vmin"] == "5.0"
        assert png_node.properties["result_key"] == "S-S33"

    def test_new_structure_assigns_results_to_go_inp(self, config: GraphConfig, tmp_path: Path):
        """新構造: go_*.inpノードにresults.{result_key}プロパティが割り当てられる"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S33_step0_frame10_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/go_idx1.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        assert "results.S-S33" in inp_node.properties
        entries = inp_node.properties["results.S-S33"]
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert entries[0]["path"] == "results/go_idx1.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"
        assert entries[0]["step"] == "0"
        assert entries[0]["frame"] == "10"
        assert entries[0]["vmax"] == "10.0"
        assert entries[0]["vmin"] == "5.0"

    def test_new_structure_multiple_result_keys(self, config: GraphConfig, tmp_path: Path):
        """新構造: 異なるresult_keyは別のプロパティキーとして格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S33_step0_frame10_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/go_idx1.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"},
            ),
            Node(
                id=3,
                type="unknown",
                name="U-U3_step0_frame10_vmax1.0_vmin0.5",
                format="png",
                properties={"path": "results/go_idx1.v1/U-U3_step0_frame10_vmax1.0_vmin0.5.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        assert "results.S-S33" in inp_node.properties
        assert "results.U-U3" in inp_node.properties
        assert len(inp_node.properties["results.S-S33"]) == 1
        assert len(inp_node.properties["results.U-U3"]) == 1

    def test_new_structure_json_metadata_file(self, config: GraphConfig, tmp_path: Path):
        """新構造: JSONメタデータファイル（stress.json等）もresult_keyとして扱う"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="stress",
                format="json",
                properties={"path": "results/go_idx1.v1/stress.json"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        assert "results.stress" in inp_node.properties
        entries = inp_node.properties["results.stress"]
        assert len(entries) == 1
        assert entries[0]["path"] == "results/go_idx1.v1/stress.json"

    def test_new_structure_multiple_entries_different_steps(self, config: GraphConfig, tmp_path: Path):
        """新構造: 同じresult_keyでstep違いは別エントリとして格納される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S33_step0_frame10_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/go_idx1.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"},
            ),
            Node(
                id=3,
                type="unknown",
                name="S-S33_step1_frame20_vmax15.0_vmin3.0",
                format="png",
                properties={"path": "results/go_idx1.v1/S-S33_step1_frame20_vmax15.0_vmin3.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        entries = inp_node.properties["results.S-S33"]
        assert isinstance(entries, list)
        assert len(entries) == 2
        steps = {e["step"] for e in entries}
        assert steps == {"0", "1"}

    def test_new_structure_unmatched_go_dir_ignored(self, config: GraphConfig, tmp_path: Path):
        """新構造: go_basenamesに存在しないディレクトリは無視する"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S33_step0_frame10_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/go_idx99.v1/S-S33_step0_frame10_vmax10.0_vmin5.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        results_keys = [k for k in inp_node.properties if k.startswith("results.")]
        assert len(results_keys) == 0

    def test_new_structure_negative_values(self, config: GraphConfig, tmp_path: Path):
        """新構造: 負の値を含むパラメータが正しくパースされる"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v3",
                format="inp",
                properties={"path": "go_idx1.v3.inp", "index": "1", "version": "3"},
            ),
            Node(
                id=2,
                type="unknown",
                name="S-S13_step0_frame10_vmax50.0_vmin-50.0",
                format="png",
                properties={"path": "results/go_idx1.v3/S-S13_step0_frame10_vmax50.0_vmin-50.0.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        png_node = result.get_node_by_id(2)
        assert png_node is not None
        assert png_node.properties["vmax"] == "50.0"
        assert png_node.properties["vmin"] == "-50.0"
        assert png_node.properties["result_key"] == "S-S13"

    def test_mixed_old_and_new_structure(self, config: GraphConfig, tmp_path: Path):
        """旧構造と新構造が混在するケースで両方正しく処理される"""
        from services.parse.parsers.results_metadata_parser import ResultsMetadataParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1.v1",
                format="inp",
                properties={"path": "go_idx1.v1.inp", "index": "1", "version": "1"},
            ),
            # 旧構造
            Node(
                id=2,
                type="unknown",
                name="go_idx1.v1_S-S33_vmax10.0_vmin5.0",
                format="png",
                properties={"path": "results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png"},
            ),
            # 新構造
            Node(
                id=3,
                type="unknown",
                name="U-U3_step0_frame10_vmax1.0_vmin0.5",
                format="png",
                properties={"path": "results/go_idx1.v1/U-U3_step0_frame10_vmax1.0_vmin0.5.png"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = ResultsMetadataParser().apply(graph)

        inp_node = result.get_node_by_id(1)
        assert inp_node is not None
        # 旧構造のresult
        assert "results.S-S33" in inp_node.properties
        assert len(inp_node.properties["results.S-S33"]) == 1
        # 新構造のresult
        assert "results.U-U3" in inp_node.properties
        assert len(inp_node.properties["results.U-U3"]) == 1


class TestNewResultFilenameParser:
    """_parse_new_result_filename のヘルパー関数テスト"""

    def test_basic_with_step_frame_params(self):
        """基本パターン: result_key + step/frame + vmax/vmin"""
        from services.parse.parsers.results_metadata_parser import _parse_new_result_filename

        key, params = _parse_new_result_filename("S-S33_step0_frame10_vmax10.0_vmin5.0")
        assert key == "S-S33"
        assert params == {"step": "0", "frame": "10", "vmax": "10.0", "vmin": "5.0"}

    def test_simple_name_no_params(self):
        """パラメータなしのシンプルなファイル名"""
        from services.parse.parsers.results_metadata_parser import _parse_new_result_filename

        key, params = _parse_new_result_filename("stress")
        assert key == "stress"
        assert params == {}

    def test_result_key_with_step_frame_only(self):
        """step/frameのみ（vmax/vminなし）"""
        from services.parse.parsers.results_metadata_parser import _parse_new_result_filename

        key, params = _parse_new_result_filename("PEEQ_step0_frame10")
        assert key == "PEEQ"
        assert params == {"step": "0", "frame": "10"}

    def test_empty_string(self):
        """空文字列"""
        from services.parse.parsers.results_metadata_parser import _parse_new_result_filename

        key, params = _parse_new_result_filename("")
        assert key == ""
        assert params == {}

    def test_negative_value(self):
        """負の値"""
        from services.parse.parsers.results_metadata_parser import _parse_new_result_filename

        key, params = _parse_new_result_filename("S-S13_vmax50.0_vmin-50.0")
        assert key == "S-S13"
        assert params == {"vmax": "50.0", "vmin": "-50.0"}

    def test_is_go_node_directory(self):
        """GOノードディレクトリ判定"""
        from services.parse.parsers.results_metadata_parser import _is_go_node_directory

        assert _is_go_node_directory("go_idx1.v1") is True
        assert _is_go_node_directory("go_idx2.v3") is True
        assert _is_go_node_directory("go") is True
        assert _is_go_node_directory("step0_frame10") is False
        assert _is_go_node_directory("contours") is False


# ====================================================================
# DisplayNameParser テスト
# ====================================================================


class TestDisplayNameParser:
    """DisplayNameParser のテスト"""

    def test_verbose_name_format_applied(self, config: GraphConfig, tmp_path: Path):
        """verbose_name_formatテンプレートがgo_ノードに適用される"""
        from services.parse.parsers.display_name_parser import DisplayNameParser

        config_data = {
            "vocab": {},
            "verbose-name-format": "条件{idx}(高さ{t})",
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".cdb"],
            },
        }
        cfg = GraphConfig.from_dict(config_data)
        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_t20",
                format="inp",
                properties={"path": "go_idx1_t20.inp", "idx": "1", "t": "20"},
            ),
        ]
        graph = _make_graph(nodes, config=cfg, project_root=tmp_path)
        result = DisplayNameParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        assert go_node.properties["verbose_name"] == "条件1(高さ20)"

    def test_verbose_name_format_with_vocab(self, config: GraphConfig, tmp_path: Path):
        """生キーでフォーマットが展開され、verbose_nameキーに格納される"""
        from services.parse.parsers.display_name_parser import DisplayNameParser

        config_data = {
            "vocab": {"idx": "条件", "t": "高さ", "verbose_name": "表示名"},
            "verbose-name-format": "条件{idx}(高さ{t})",
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".cdb"],
            },
        }
        cfg = GraphConfig.from_dict(config_data)
        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1_t20",
                format="inp",
                properties={"path": "go_idx1_t20.inp", "idx": "1", "t": "20"},
            ),
        ]
        graph = _make_graph(nodes, config=cfg, project_root=tmp_path)
        result = DisplayNameParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        # 生キー（verbose_name）に格納される
        assert go_node.properties["verbose_name"] == "条件1(高さ20)"

    def test_no_format_skips(self, config: GraphConfig, tmp_path: Path):
        """verbose_name_format未設定ではスキップされる"""
        from services.parse.parsers.display_name_parser import DisplayNameParser

        nodes = [
            Node(
                id=1,
                type="go",
                name="go_idx1",
                format="inp",
                properties={"path": "go_idx1.inp", "idx": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=config, project_root=tmp_path)
        result = DisplayNameParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        assert "verbose_name" not in go_node.properties

    def test_missing_key_replaced_with_empty(self, config: GraphConfig, tmp_path: Path):
        """存在しないキーは空文字に置換される"""
        from services.parse.parsers.display_name_parser import DisplayNameParser

        config_data = {
            "vocab": {"idx": "条件"},
            "verbose-name-format": "条件{条件}(高さ{高さ})",
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".cdb"],
            },
        }
        cfg = GraphConfig.from_dict(config_data)
        nodes = [
            Node(
                id=1,
                type="go",
                name="go_a",
                format="inp",
                properties={"path": "a.inp", "条件": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=cfg, project_root=tmp_path)
        result = DisplayNameParser().apply(graph)

        go_node = result.get_node_by_id(1)
        assert go_node is not None
        assert go_node.properties["verbose_name"] == "条件1(高さ)"

    def test_non_go_nodes_skipped(self, config: GraphConfig, tmp_path: Path):
        """go_以外のノードはスキップされる"""
        from services.parse.parsers.display_name_parser import DisplayNameParser

        config_data = {
            "vocab": {},
            "verbose-name-format": "名前{idx}",
            "file-relations": {
                "input-extensions": [".inp"],
                "result-extensions": [".odb"],
                "asset-extensions": [".cdb"],
            },
        }
        cfg = GraphConfig.from_dict(config_data)
        nodes = [
            Node(
                id=1,
                type="unknown",
                name="mesh_idx1",
                format="inp",
                properties={"path": "mesh_idx1.inp", "idx": "1"},
            ),
        ]
        graph = _make_graph(nodes, config=cfg, project_root=tmp_path)
        result = DisplayNameParser().apply(graph)

        mesh_node = result.get_node_by_id(1)
        assert mesh_node is not None
        assert "verbose_name" not in mesh_node.properties


# ====================================================================
# 画像パスメタデータ抽出テスト
# ====================================================================


class TestExtractPathMetadata:
    """extract_path_metadata の単体テスト"""

    def test_extract_result_key_and_props(self):
        """パスからresult_keyとプロパティが正しく抽出される"""
        from services.dashboard.query import extract_path_metadata

        result_key, props = extract_path_metadata(
            "results/contours/go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13.png"
        )
        assert result_key == "S-S13"
        assert props["vmax"] == "50.0"
        assert props["vmin"] == "-50.0"
        assert props["step"] == "0"
        assert props["frame"] == "10"

    def test_extract_result_key_without_negative(self):
        """負の値がないパスも正しく抽出される"""
        from services.dashboard.query import extract_path_metadata

        result_key, props = extract_path_metadata("results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png")
        assert result_key == "S-S33"
        assert props["vmax"] == "10.0"
        assert props["vmin"] == "5.0"

    def test_extract_from_directory_tokens(self):
        """ディレクトリ名からもプロパティが抽出される"""
        from services.dashboard.query import extract_path_metadata

        result_key, props = extract_path_metadata("results/step0_frame10/go_idx1.v1_S-S33_vmax10.0.png")
        assert result_key == "S-S33"
        assert props["step"] == "0"
        assert props["frame"] == "10"
        assert props["vmax"] == "10.0"

    def test_no_result_key(self):
        """result_keyがない場合は空文字を返す"""
        from services.dashboard.query import extract_path_metadata

        result_key, _props = extract_path_metadata("go_idx1.v1_vmax10.0.png")
        assert result_key == ""

    def test_empty_path(self):
        """空パスの場合は空を返す"""
        from services.dashboard.query import extract_path_metadata

        result_key, props = extract_path_metadata("")
        assert result_key == ""
        assert props == {}

    def test_peeq_result_key(self):
        """PEEQ（ダッシュなし）のresult_keyが抽出される"""
        from services.dashboard.query import extract_path_metadata

        result_key, props = extract_path_metadata("results/step0_frame5/go_idx1.v1_PEEQ_vmax0.1.png")
        assert result_key == "PEEQ"
        assert props["vmax"] == "0.1"


# =========================================================================
# プラグインレジストリ テスト
# =========================================================================


class TestPluginRegistry:
    """プラグインレジストリとentry_points発見メカニズムのテスト"""

    def test_load_all_plugins_is_idempotent(self):
        """load_all_pluginsは複数回呼んでも安全"""
        from services.sdk import load_all_plugins, reset_plugins

        reset_plugins()
        load_all_plugins()
        load_all_plugins()  # 2回目は何もしない

    def test_discover_entry_point_plugins_empty_group(self):
        """存在しないグループに対してエラーを出さない"""
        from services.sdk import discover_entry_point_plugins

        # 存在しないグループでもエラーにならない
        discover_entry_point_plugins("jj.nonexistent_group")

    def test_builtin_plugins_registered(self):
        """ビルトインプラグイン（abaqus, obsidian）が登録される"""
        from services.sdk import load_all_plugins, reset_plugins

        reset_plugins()
        load_all_plugins()

        from services.parse.base import get_parser_registry

        registry = get_parser_registry()
        cls_names = [cls.__name__ for cls in registry]
        # Abaqusパーサーが登録されていること
        assert any("Abaqus" in name for name in cls_names)

    def test_plugin_sdk_exports(self):
        """services.sdkが必要な公開APIをすべてエクスポートしている"""
        from services.sdk import (  # noqa: F401
            AbstractExporter,
            AbstractFileParser,
            CacheProvider,
            DashboardPageConnector,
            GraphModel,
            Node,
            ProjectDirectory,
            ProjectFile,
            ProjectGraph,
            Relation,
        )
