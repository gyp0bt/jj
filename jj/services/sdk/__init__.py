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
# パーサー基盤
# --------------------------------------------------
from services.parse.base import AbstractFileParser
from services.graph.project_graph import (
    ProjectGraph,
    ProjectFile,
    ProjectDirectory,
    ProjectNonFileNode,
)

# --------------------------------------------------
# エクスポーター基盤
# --------------------------------------------------
from services.export import AbstractExporter

# --------------------------------------------------
# ダッシュボードコネクター基盤
# --------------------------------------------------
from services.dashboard.connectors import DashboardPageConnector

# --------------------------------------------------
# キャッシュプロバイダープロトコル
# --------------------------------------------------
from services.sdk.cache import CacheProvider

__all__ = [
    # 型
    "Node",
    "Relation",
    "GraphModel",
    # パーサー
    "AbstractFileParser",
    "ProjectGraph",
    "ProjectFile",
    "ProjectDirectory",
    "ProjectNonFileNode",
    # エクスポーター
    "AbstractExporter",
    # ダッシュボード
    "DashboardPageConnector",
    # キャッシュ
    "CacheProvider",
]
