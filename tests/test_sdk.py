"""jj-sdk パッケージのテスト

services/sdk/ の公開インターフェースが正しくエクスポートされていること、
CacheProviderプロトコルが正しく動作することを検証する。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSdkExports:
    """SDK公開APIのエクスポート確認"""

    def test_import_types(self):
        from services.sdk import GraphModel, Node, Relation

        assert Node is not None
        assert Relation is not None
        assert GraphModel is not None

    def test_import_parser_base(self):
        from services.sdk import AbstractFileParser, ProjectGraph

        assert AbstractFileParser is not None
        assert ProjectGraph is not None

    def test_import_project_types(self):
        from services.sdk import ProjectDirectory, ProjectFile, ProjectNonFileNode

        assert ProjectFile is not None
        assert ProjectDirectory is not None
        assert ProjectNonFileNode is not None

    def test_import_exporter_base(self):
        from services.sdk import AbstractExporter

        assert AbstractExporter is not None

    def test_import_cache_provider(self):
        from services.sdk import CacheProvider

        assert CacheProvider is not None


class TestCacheProviderProtocol:
    """CacheProviderプロトコルのテスト"""

    def test_graph_storage_implements_protocol(self):
        """GraphStorageがCacheProviderプロトコルを満たすことを確認"""
        from services.graph.storage import GraphStorage
        from services.sdk.cache import CacheProvider

        storage = GraphStorage()
        assert isinstance(storage, CacheProvider)

    def test_protocol_methods_exist(self):
        """プロトコルに必要なメソッドが定義されていることを確認"""
        from services.sdk.cache import CacheProvider

        required_methods = [
            "load",
            "save",
            "load_timestamps",
            "save_timestamps",
            "load_plugin_data",
            "save_plugin_data",
        ]
        for method_name in required_methods:
            assert hasattr(CacheProvider, method_name), f"{method_name} not in CacheProvider"

    def test_mock_cache_provider(self, tmp_path):
        """カスタムCacheProviderの実装テスト"""
        from jj_types import GraphModel
        from services.sdk.cache import CacheProvider

        class MockCacheProvider:
            def __init__(self):
                self._data = {}

            def load(self, project_root, filename=None):
                return self._data.get("graph", GraphModel.empty())

            def save(self, project_root, graph, filename=None):
                self._data["graph"] = graph
                return project_root / "graph.yaml"

            def load_timestamps(self, project_root):
                return {}

            def save_timestamps(self, project_root, timestamps):
                return project_root / "ts.json"

            def load_plugin_data(self, project_root, namespace, file_path, expected_mtime):
                return None

            def save_plugin_data(self, project_root, namespace, file_path, data, mtime):
                return project_root / "cache.pickle"

            def load_node_properties(self, project_root, node_id):
                return {}

            def save_node_properties(self, project_root, node_id, properties):
                return project_root / f"node_{node_id}.json"

        mock = MockCacheProvider()
        assert isinstance(mock, CacheProvider)

        # 動作確認
        graph = GraphModel.empty()
        mock.save(tmp_path, graph)
        loaded = mock.load(tmp_path)
        assert loaded.nodes == []


class TestSdkTypes:
    """SDK経由の型がjj_typesと同一であることを確認"""

    def test_node_identity(self):
        from jj_types import Node as OrigNode
        from services.sdk import Node

        assert Node is OrigNode

    def test_relation_identity(self):
        from jj_types import Relation as OrigRelation
        from services.sdk import Relation

        assert Relation is OrigRelation

    def test_graph_model_identity(self):
        from jj_types import GraphModel as OrigGraphModel
        from services.sdk import GraphModel

        assert GraphModel is OrigGraphModel

    def test_parser_identity(self):
        from plugins.base.parser import AbstractFileParser as OrigParser
        from services.sdk import AbstractFileParser

        assert AbstractFileParser is OrigParser

    def test_exporter_identity(self):
        from plugins.base.exporter import AbstractExporter as OrigExporter
        from services.sdk import AbstractExporter

        assert AbstractExporter is OrigExporter
