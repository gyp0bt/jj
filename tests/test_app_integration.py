"""JJApp 統合テスト — EventBus・CapabilityRegistry統合

P-6/P-7/P-8: JJApp に EventBus と CapabilityRegistry を統合した際のテスト。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jj_types import GraphModel, Node
from services.app import JJApp
from services.sdk.capabilities import Capability
from services.sdk.event_bus import EventBus
from services.sdk.events import GraphExported, GraphParsed, PluginLoaded
from services.sdk.plugin_manager import PluginManager
from services.sdk.plugin_manifest import PluginManifest


class TestJJAppEventBus:
    """JJApp EventBus 統合テスト"""

    @pytest.fixture()
    def app(self, tmp_path):
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        return JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)

    def test_event_bus_initialized(self, app):
        """EventBus が初期化されている"""
        assert isinstance(app.event_bus, EventBus)

    def test_parse_publishes_event(self, app):
        """parse() 実行後に GraphParsed イベントが発行される"""
        events = []
        app.event_bus.subscribe(GraphParsed, lambda e: events.append(e))

        mock_graph = GraphModel(
            nodes=[Node(id=1, type="file", name="test.inp", format="inp", properties={})],
            relations=[],
        )
        mock_gs = MagicMock()
        mock_gs.parse_and_save.return_value = (mock_graph, Path("/tmp/graph.yaml"))
        app._graph_service = mock_gs

        app.parse()
        assert len(events) == 1
        assert events[0].node_count == 1
        assert events[0].relation_count == 0
        assert events[0].source == "core"

    def test_export_publishes_event(self, app):
        """export() 実行後に GraphExported イベントが発行される"""
        events = []
        app.event_bus.subscribe(GraphExported, lambda e: events.append(e))

        mock_graph = GraphModel(nodes=[], relations=[])
        mock_gs = MagicMock()
        mock_gs.load.return_value = mock_graph
        app._graph_service = mock_gs

        mock_exporter_cls = MagicMock()
        mock_exporter = MagicMock()
        mock_exporter.export.return_value = {"output_path": "/tmp/out.csv"}
        mock_exporter_cls.return_value = mock_exporter

        from unittest.mock import patch

        with patch("services.export.get_exporter_for_format", return_value=mock_exporter_cls):
            app.export("csv")

        assert len(events) == 1
        assert events[0].format == "csv"
        assert events[0].source == "core"

    def test_subscribe_to_multiple_events(self, app):
        """複数のイベントタイプに同時にサブスクライブできる"""
        parsed_events = []
        exported_events = []
        app.event_bus.subscribe(GraphParsed, lambda e: parsed_events.append(e))
        app.event_bus.subscribe(GraphExported, lambda e: exported_events.append(e))

        app.event_bus.publish(GraphParsed(source="test", node_count=5, relation_count=3, full_mode=False))
        app.event_bus.publish(GraphExported(source="test", format="json", output_path="/tmp/out"))

        assert len(parsed_events) == 1
        assert len(exported_events) == 1


class TestJJAppCapabilityRegistry:
    """JJApp CapabilityRegistry 統合テスト"""

    @pytest.fixture()
    def app_with_manifest(self, tmp_path):
        """マニフェスト付きプラグインを持つJJApp"""
        mock_config = MagicMock()

        manifest = PluginManifest(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            parsers=["test.parsers.parser1"],
            exporters=["test.exporters.exporter1"],
            cli_commands=["test.cli.commands"],
            api_routes=["test.api.routes"],
        )

        pm = PluginManager(_BUILTIN_PLUGINS=[])
        pm._loaded = True
        pm._register_manifest(manifest)

        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        return app

    def test_capability_registry_initialized(self, app_with_manifest):
        """CapabilityRegistry が初期化されている"""
        registry = app_with_manifest.capability_registry
        assert registry is not None

    def test_parsers_registered(self, app_with_manifest):
        """パーサーがCapabilityRegistryに登録される"""
        entries = app_with_manifest.capability_registry.get_all(Capability.PARSER)
        assert len(entries) == 1
        assert entries[0].plugin_name == "test_plugin"

    def test_exporters_registered(self, app_with_manifest):
        """エクスポーターがCapabilityRegistryに登録される"""
        entries = app_with_manifest.capability_registry.get_all(Capability.EXPORTER)
        assert len(entries) == 1

    def test_cli_commands_registered(self, app_with_manifest):
        """CLIコマンドが登録される"""
        entries = app_with_manifest.capability_registry.get_all(Capability.CLI_COMMAND)
        assert len(entries) == 1

    def test_api_routes_registered(self, app_with_manifest):
        """APIルートが登録される"""
        entries = app_with_manifest.capability_registry.get_all(Capability.API_ROUTE)
        assert len(entries) == 1

    def test_get_by_plugin(self, app_with_manifest):
        """プラグイン名でcapabilityを取得できる"""
        by_plugin = app_with_manifest.capability_registry.get_by_plugin("test_plugin")
        assert Capability.PARSER in by_plugin
        assert Capability.EXPORTER in by_plugin
        assert Capability.CLI_COMMAND in by_plugin

    def test_plugin_loaded_event(self, tmp_path):
        """プラグインロード時にPluginLoadedイベントが発行される"""
        events = []
        mock_config = MagicMock()

        manifest = PluginManifest(
            name="event_test",
            version="1.0.0",
            parsers=["test.parser"],
        )

        pm = PluginManager(_BUILTIN_PLUGINS=[])
        pm._loaded = True
        pm._register_manifest(manifest)

        event_bus = EventBus()
        event_bus.subscribe(PluginLoaded, lambda e: events.append(e))

        JJApp(
            project_root=tmp_path,
            config=mock_config,
            plugin_manager=pm,
            event_bus=event_bus,
        )

        assert len(events) == 1
        assert events[0].plugin_name == "event_test"
        assert "parsers" in events[0].capabilities


class TestJJAppCliCommands:
    """JJApp CLIコマンド取得テスト"""

    def test_get_cli_commands_empty(self, tmp_path):
        """CLIコマンドなしでは空リスト"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        result = app.get_cli_commands()
        assert result == []

    def test_get_api_routes_empty(self, tmp_path):
        """APIルートなしでは空リスト"""
        mock_config = MagicMock()
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        app = JJApp(project_root=tmp_path, config=mock_config, plugin_manager=pm)
        result = app.get_api_routes()
        assert result == []
