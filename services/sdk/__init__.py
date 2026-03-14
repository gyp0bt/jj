"""jj-sdk: プラグイン開発用公開インターフェース

外部プラグイン（parseコネクター、エクスポーター、ダッシュボードコネクター）の
開発者がインポートすべき公開APIを集約する。

プラグインはこのパッケージからのみインポートすればよく、
内部実装の詳細（services.graph, services.parse.base 等）を
直接参照する必要がない。

使用例:
    from services.sdk import AbstractFileParser, AbstractExporter
    from services.sdk import DashboardPageConnector
    from services.sdk import Node, Relation, GraphModel
    from services.sdk import ProjectGraph, ProjectFile, ProjectDirectory
    from services.sdk import CacheProvider

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

# --------------------------------------------------
# 型定義（jj_types）
# --------------------------------------------------
from jj_types import GraphModel, Node, Relation

# --------------------------------------------------
# ダッシュボードコネクター基盤
# --------------------------------------------------
from services.dashboard.connectors import DashboardPageConnector

# --------------------------------------------------
# エクスポーター基盤
# --------------------------------------------------
from services.export import AbstractExporter
from services.graph.project_graph import (
    ProjectDirectory,
    ProjectFile,
    ProjectGraph,
    ProjectNonFileNode,
)

# --------------------------------------------------
# パーサー基盤
# --------------------------------------------------
from services.parse.base import AbstractFileParser

# --------------------------------------------------
# キャッシュプロバイダープロトコル
# --------------------------------------------------
from services.sdk.cache import CacheProvider

# --------------------------------------------------
# CapabilityRegistry
# --------------------------------------------------
from services.sdk.capabilities import Capability, CapabilityEntry, CapabilityRegistry

# --------------------------------------------------
# EventBus・イベント定義
# --------------------------------------------------
from services.sdk.event_bus import EventBus
from services.sdk.events import Event, GraphExported, GraphParsed, PluginLoaded
from services.sdk.plugin_manager import PluginManager

# --------------------------------------------------
# プラグインマニフェスト・マネージャー
# --------------------------------------------------
from services.sdk.plugin_manifest import PluginInfo, PluginManifest

# --------------------------------------------------
# プラグインレジストリ
# --------------------------------------------------
from services.sdk.plugin_registry import (
    discover_entry_point_plugins,
    load_all_plugins,
    reset_plugins,
)

__all__ = [
    "AbstractExporter",
    "AbstractFileParser",
    "CacheProvider",
    "Capability",
    "CapabilityEntry",
    "CapabilityRegistry",
    "DashboardPageConnector",
    "Event",
    "EventBus",
    "GraphExported",
    "GraphModel",
    "GraphParsed",
    "Node",
    "PluginInfo",
    "PluginLoaded",
    "PluginManager",
    "PluginManifest",
    "ProjectDirectory",
    "ProjectFile",
    "ProjectGraph",
    "ProjectNonFileNode",
    "Relation",
    "discover_entry_point_plugins",
    "load_all_plugins",
    "reset_plugins",
]
