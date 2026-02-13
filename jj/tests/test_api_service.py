"""ApiServiceの単体テスト

services/service/api_service.py のテスト。
GraphService/DashboardDataProviderをモックして、
ApiServiceの各メソッドが正しく動作することを検証する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from jj_types import GraphModel, Node, Relation
from services.service.api_service import ApiService


@pytest.fixture
def sample_graph():
    """テスト用のGraphModel"""
    nodes = [
        Node(id=1, type="go", name="go_model1.inp", format=".inp",
             properties={"active": True, "RF3": 10.5}),
        Node(id=2, type="mesh", name="mesh_model1.inp", format=".inp",
             properties={"active": False}),
        Node(id=3, type="go", name="go_model2.inp", format=".inp",
             properties={"active": True, "RF3": 3.0}),
    ]
    relations = [
        Relation(id=1, label="has_output", node1_id=1, node2_id=2),
    ]
    return GraphModel(nodes=nodes, relations=relations)


@pytest.fixture
def api_svc(tmp_path, sample_graph):
    """ApiServiceインスタンス（GraphServiceモック付き）"""
    svc = ApiService(project_root=tmp_path)

    mock_graph_svc = MagicMock()
    mock_graph_svc.load.return_value = sample_graph
    mock_graph_svc.summary.return_value = {
        "total_nodes": 3,
        "total_relations": 1,
        "nodes_by_type": {"go": 2, "mesh": 1},
        "relations_by_label": {"has_output": 1},
    }
    svc._graph_service = mock_graph_svc
    return svc


class TestApiServiceGetGraph:
    """get_graph / get_nodes / get_relations"""

    def test_get_graph_returns_graph_model(self, api_svc, sample_graph):
        result = api_svc.get_graph()
        assert len(result.nodes) == 3
        assert len(result.relations) == 1

    def test_get_nodes_returns_list(self, api_svc):
        nodes = api_svc.get_nodes()
        assert isinstance(nodes, list)
        assert len(nodes) == 3

    def test_get_relations_returns_list(self, api_svc):
        rels = api_svc.get_relations()
        assert isinstance(rels, list)
        assert len(rels) == 1

    def test_lazy_loading(self, api_svc):
        """2回呼んでもGraphService.load()は1回だけ"""
        api_svc.get_graph()
        api_svc.get_graph()
        api_svc._graph_service.load.assert_called_once()


class TestApiServiceFilter:
    """filter_relations"""

    def test_filter_by_label(self, api_svc):
        rels = api_svc.filter_relations(label="has_output")
        assert len(rels) == 1

    def test_filter_no_match(self, api_svc):
        rels = api_svc.filter_relations(label="nonexistent")
        assert len(rels) == 0

    def test_filter_none_returns_all(self, api_svc):
        rels = api_svc.filter_relations(label=None)
        assert len(rels) == 1


class TestApiServiceReload:
    """reload_graph / parse_project"""

    def test_reload_clears_cache(self, api_svc):
        api_svc.get_graph()
        assert api_svc._graph is not None

        api_svc.reload_graph()
        # reloadでキャッシュがクリアされ、再ロードされる
        assert api_svc._graph is not None  # reload内で再ロードされる
        assert api_svc._graph_service.load.call_count == 2

    def test_parse_project(self, api_svc, sample_graph):
        api_svc._graph_service.parse_and_save.return_value = (
            sample_graph,
            Path("/tmp/graph.yaml"),
        )
        result = api_svc.parse_project(full=True)
        assert result["status"] == "parsed"
        assert "total_nodes" in result
        api_svc._graph_service.parse_and_save.assert_called_once_with(full_mode=True)


class TestApiServiceProvider:
    """get_node_card / get_related_files / get_property_keys / get_summary"""

    def test_get_summary(self, api_svc):
        """get_summaryはGraphService.summary() + go_file_countを返す"""
        # providerもモックする
        mock_provider = MagicMock()
        mock_provider.get_go_table.return_value = [{"name": "go1"}, {"name": "go2"}]
        api_svc._provider = mock_provider

        result = api_svc.get_summary()
        assert result["total_nodes"] == 3
        assert result["go_file_count"] == 2

    def test_get_node_card_found(self, api_svc):
        mock_provider = MagicMock()
        mock_provider.get_node_card.return_value = {"id": 1, "name": "go_model1"}
        api_svc._provider = mock_provider

        card = api_svc.get_node_card(1)
        assert card["id"] == 1

    def test_get_node_card_not_found(self, api_svc):
        mock_provider = MagicMock()
        mock_provider.get_node_card.return_value = None
        api_svc._provider = mock_provider

        card = api_svc.get_node_card(999)
        assert card is None

    def test_get_property_keys(self, api_svc):
        mock_provider = MagicMock()
        mock_provider.get_property_keys.return_value = ["RF3", "active"]
        api_svc._provider = mock_provider

        keys = api_svc.get_property_keys()
        assert "RF3" in keys

    def test_get_status_summary(self, api_svc):
        mock_provider = MagicMock()
        mock_provider.get_status_summary.return_value = {"completed": 5}
        api_svc._provider = mock_provider

        result = api_svc.get_status_summary()
        assert result["completed"] == 5
