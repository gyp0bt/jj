"""jj-sdk: プラグイン開発用公開インターフェース

外部プラグイン（parseコネクター、エクスポーター）の開発者がインポートすべき
公開APIを集約する。プラグインはこのパッケージからのみインポートすればよく、
内部実装（services.graph, services.parse.base 等）を直接参照しなくてよい。

使用例:
    from services.sdk import AbstractFileParser, AbstractExporter
    from services.sdk import Node, Relation, GraphModel
    from services.sdk import ProjectGraph, ProjectFile, ProjectDirectory
    from services.sdk import CacheProvider, PluginManifest

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

# 型定義（jj_types）
from jj_types import GraphModel, Node, Relation

# エクスポーター基盤
from services.export import AbstractExporter
from services.graph.project_graph import (
    ProjectDirectory,
    ProjectFile,
    ProjectGraph,
    ProjectNonFileNode,
)

# パーサー基盤
from services.parse.base import AbstractFileParser

# キャッシュプロバイダープロトコル
from services.sdk.cache import CacheProvider

# プラグインマニフェスト
from services.sdk.plugin_manifest import PluginInfo, PluginManifest

# プラグインレジストリ
from services.sdk.plugin_registry import (
    discover_entry_point_plugins,
    load_all_plugins,
    reset_plugins,
)

__all__ = [
    "AbstractExporter",
    "AbstractFileParser",
    "CacheProvider",
    "GraphModel",
    "Node",
    "PluginInfo",
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
