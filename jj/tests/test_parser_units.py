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

    def test_creates_same_index_group(self, config: GraphConfig):
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

        groups = [r for r in result.relations if r.label == "same_index_group"]
        assert len(groups) == 2
        # representative(v1) → v2, v1 → v3
        assert all(r.node1_id == 1 for r in groups)

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
