"""JJApp 統一コアテスト

P-2: JJApp のインスタンス化、クエリ操作、プラグイン情報取得をテストする。
実際のプロジェクトディレクトリが不要なテストと、テストアセットを使うテストに分離。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jj_types import GraphModel, Node, Relation
from services.app import ExportResult, JJApp, ParseResult
from services.sdk.plugin_manager import PluginManager


class TestParseResult:
    """ParseResult dataclass のテスト"""

    def test_create(self):
        graph = GraphModel(nodes=[], relations=[])
        result = ParseResult(graph=graph, node_count=5, relation_count=3)
        assert result.node_count == 5
        assert result.relation_count == 3
        assert result.save_path is None


class TestExportResult:
    """ExportResult dataclass のテスト"""

    def test_create(self):
        result = ExportResult(format="csv", output_path=Path("/tmp/out.csv"))
        assert result.format == "csv"
        assert result.output_path == Path("/tmp/out.csv")


class TestJJAppInit:
    """JJApp の初期化テスト"""

    def test_init_with_mock_config(self, tmp_path):
        """モックConfigでインスタンス化できる"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        assert app.project_root == tmp_path.resolve()
        assert app.config is mock_config

    def test_plugin_manager_loaded(self, tmp_path):
        """初期化時にプラグインがロードされる"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        assert pm._loaded is True

    def test_graph_service_lazy_init(self, tmp_path):
        """GraphService は遅延初期化される"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        assert app._graph_service is None


class TestJJAppQuery:
    """JJApp のクエリ操作テスト"""

    @pytest.fixture()
    def sample_graph(self):
        """テスト用の小さなグラフ"""
        nodes = [
            Node(id=1, type="file", name="model.inp", format="inp", properties={"solver": "abaqus"}),
            Node(id=2, type="material", name="Steel", format="data", properties={"density": 7800}),
            Node(id=3, type="file", name="result.sta", format="sta", properties={"solver": "abaqus"}),
        ]
        relations = [
            Relation(id=1, label="CONTAINS", node1_id=1, node2_id=2),
            Relation(id=2, label="PRODUCES", node1_id=1, node2_id=3),
        ]
        return GraphModel(nodes=nodes, relations=relations)

    @pytest.fixture()
    def app(self, tmp_path):
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        return JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)

    def test_query_nodes_all(self, app, sample_graph):
        """フィルタなしで全ノード返す"""
        result = app.query_nodes(sample_graph)
        assert len(result) == 3

    def test_query_nodes_by_type(self, app, sample_graph):
        """タイプでフィルタ"""
        result = app.query_nodes(sample_graph, types=["file"])
        assert len(result) == 2
        assert all(n.type == "file" for n in result)

    def test_query_nodes_by_name(self, app, sample_graph):
        """名前でフィルタ"""
        result = app.query_nodes(sample_graph, names=["Steel"])
        assert len(result) == 1
        assert result[0].name == "Steel"

    def test_query_nodes_by_properties(self, app, sample_graph):
        """プロパティでフィルタ"""
        result = app.query_nodes(sample_graph, properties={"density": 7800})
        assert len(result) == 1
        assert result[0].name == "Steel"

    def test_query_nodes_combined_filter(self, app, sample_graph):
        """複合フィルタ"""
        result = app.query_nodes(sample_graph, types=["file"], properties={"solver": "abaqus"})
        assert len(result) == 2

    def test_query_nodes_no_match(self, app, sample_graph):
        """マッチなし"""
        result = app.query_nodes(sample_graph, types=["nonexistent"])
        assert len(result) == 0

    def test_query_relations_all(self, app, sample_graph):
        """フィルタなしで全リレーション返す"""
        result = app.query_relations(sample_graph)
        assert len(result) == 2

    def test_query_relations_by_label(self, app, sample_graph):
        """ラベルでフィルタ"""
        result = app.query_relations(sample_graph, labels=["CONTAINS"])
        assert len(result) == 1
        assert result[0].label == "CONTAINS"

    def test_query_relations_by_node_id(self, app, sample_graph):
        """ノードIDでフィルタ"""
        result = app.query_relations(sample_graph, node_id=1)
        assert len(result) == 2  # node1 has 2 relations

    def test_query_relations_by_label_and_node(self, app, sample_graph):
        """ラベル + ノードIDで複合フィルタ"""
        result = app.query_relations(sample_graph, labels=["PRODUCES"], node_id=1)
        assert len(result) == 1

    def test_get_summary(self, app, sample_graph):
        """サマリー統計"""
        mock_gs = MagicMock()
        mock_gs.summary.return_value = {
            "total_nodes": 3,
            "total_relations": 2,
            "nodes_by_type": {"file": 2, "material": 1},
            "relations_by_label": {"CONTAINS": 1, "PRODUCES": 1},
        }
        app._graph_service = mock_gs
        result = app.get_summary(sample_graph)
        assert result["total_nodes"] == 3

    def test_get_node_by_id(self, app, sample_graph):
        """IDでノード取得"""
        mock_gs = MagicMock()
        mock_gs.get_node_by_id.return_value = sample_graph.nodes[1]
        app._graph_service = mock_gs
        node = app.get_node_by_id(2, sample_graph)
        assert node is not None
        assert node.name == "Steel"


class TestJJAppPluginInfo:
    """プラグイン情報取得テスト"""

    def test_get_plugins_returns_list(self, tmp_path):
        """get_plugins() は PluginInfo のリストを返す"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        plugins = app.get_plugins()
        assert isinstance(plugins, list)

    def test_get_available_export_formats(self, tmp_path):
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        formats = app.get_available_export_formats()
        assert isinstance(formats, list)
