"""JJApp — jjアプリケーションの統一コア

CLI / Dashboard / API のすべてのインターフェースがこのオブジェクトのみに依存する。
GraphService, PluginManager, EventBus を内包し、DIコンテナとして機能する。

設計判断:
  - CLI起動時にインスタンス化（軽量なので問題なし）
  - 既存の GraphService / GraphCommandService はそのまま動作（後方互換）
  - 新機能は JJApp の API として追加する

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import GraphConfig
from jj_types import GraphModel, Node, Relation
from services.sdk.capabilities import Capability, CapabilityRegistry
from services.sdk.event_bus import EventBus
from services.sdk.events import GraphExported, GraphParsed, PluginLoaded
from services.sdk.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """パース結果

    Attributes:
        graph: 生成されたグラフモデル
        save_path: 保存先パス（保存した場合）
        node_count: ノード数
        relation_count: リレーション数
    """

    graph: GraphModel
    save_path: Path | None = None
    node_count: int = 0
    relation_count: int = 0


@dataclass
class ExportResult:
    """エクスポート結果

    Attributes:
        format: エクスポート形式
        output_path: 出力先パス
        metadata: エクスポーターが返すメタデータ
    """

    format: str
    output_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JJApp:
    """jjアプリケーションの統一コア

    CLI / Dashboard / API のすべてのインターフェースが
    このオブジェクトのみに依存する。

    Attributes:
        project_root: プロジェクトルートパス
        config: GraphConfig（遅延初期化）
        plugin_manager: PluginManager
    """

    project_root: Path
    config: GraphConfig | None = field(default=None, repr=False)
    plugin_manager: PluginManager = field(default_factory=PluginManager)
    event_bus: EventBus = field(default_factory=EventBus)
    capability_registry: CapabilityRegistry = field(default_factory=CapabilityRegistry)

    # 内部サービス（遅延初期化）
    _graph_service: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.project_root = Path(self.project_root).resolve()
        if self.config is None:
            self.config = GraphConfig.load(base_dir=self.project_root)
        self.plugin_manager.load_all()
        self._register_plugin_capabilities()

    # === Graph操作 ===

    @property
    def graph_service(self) -> Any:
        """GraphService の遅延取得"""
        if self._graph_service is None:
            from services.graph import GraphService

            self._graph_service = GraphService(
                project_root=self.project_root,
                config=self.config,
            )
        return self._graph_service

    def parse(self, *, full: bool = False, debug: bool = False) -> ParseResult:
        """プロジェクトをパースしてグラフを生成・保存する

        Args:
            full: Trueの場合 requires_full=True のパーサーも実行
            debug: デバッグモード（パーサーエラーをraise）

        Returns:
            ParseResult
        """
        graph, save_path = self.graph_service.parse_and_save(full_mode=full, debug=debug)
        result = ParseResult(
            graph=graph,
            save_path=save_path,
            node_count=len(graph.nodes),
            relation_count=len(graph.relations),
        )
        self.event_bus.publish(
            GraphParsed(
                source="core",
                node_count=result.node_count,
                relation_count=result.relation_count,
                full_mode=full,
            )
        )
        return result

    def load_graph(self, *, resolve_externalized: bool = False) -> GraphModel:
        """保存済みグラフをロードする

        Args:
            resolve_externalized: 外部化プロパティを結合してフルロード

        Returns:
            GraphModel
        """
        return self.graph_service.load(resolve_externalized=resolve_externalized)

    def export(self, format: str, **kwargs: Any) -> ExportResult:
        """グラフを指定形式でエクスポートする

        Args:
            format: エクスポート形式（"csv", "json", "obsidian"等）
            **kwargs: エクスポーター固有のパラメータ

        Returns:
            ExportResult
        """
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format(format)
        if exporter_cls is None:
            raise ValueError(f"未対応のエクスポート形式: {format}")

        graph = self.load_graph(resolve_externalized=True)
        exporter = exporter_cls(
            project_root=self.project_root,
            config=self.config,
        )
        metadata = exporter.export(graph, **kwargs)
        output_path = metadata.get("output_path")
        if output_path is not None:
            output_path = Path(output_path)

        export_result = ExportResult(
            format=format,
            output_path=output_path,
            metadata=metadata,
        )
        self.event_bus.publish(
            GraphExported(
                source="core",
                format=format,
                output_path=str(output_path) if output_path else "",
            )
        )
        return export_result

    # === クエリ操作 ===

    def query_nodes(
        self,
        graph: GraphModel | None = None,
        *,
        types: list[str] | None = None,
        names: list[str] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> list[Node]:
        """ノード検索

        Args:
            graph: 検索対象のグラフ（Noneの場合は保存済みグラフをロード）
            types: タイプフィルタ
            names: 名前フィルタ
            properties: プロパティフィルタ（部分一致）

        Returns:
            マッチしたノードのリスト
        """
        if graph is None:
            graph = self.load_graph()

        results = list(graph.nodes)

        if types:
            results = [n for n in results if n.type in types]
        if names:
            results = [n for n in results if n.name in names]
        if properties:
            results = [n for n in results if all(n.properties.get(k) == v for k, v in properties.items())]

        return results

    def query_relations(
        self,
        graph: GraphModel | None = None,
        *,
        labels: list[str] | None = None,
        node_id: int | None = None,
    ) -> list[Relation]:
        """リレーション検索

        Args:
            graph: 検索対象のグラフ
            labels: ラベルフィルタ
            node_id: ノードIDフィルタ（関連リレーション）

        Returns:
            マッチしたリレーションのリスト
        """
        if graph is None:
            graph = self.load_graph()

        results = list(graph.relations)

        if labels:
            results = [r for r in results if r.label in labels]
        if node_id is not None:
            results = [r for r in results if r.node1_id == node_id or r.node2_id == node_id]

        return results

    def get_summary(self, graph: GraphModel | None = None) -> dict[str, Any]:
        """グラフサマリー統計

        Args:
            graph: 対象グラフ（Noneで保存済みをロード）

        Returns:
            サマリー辞書
        """
        if graph is None:
            graph = self.load_graph()
        return self.graph_service.summary(graph)

    def get_node_by_id(self, node_id: int, graph: GraphModel | None = None) -> Node | None:
        """IDでノードを取得する

        Args:
            node_id: ノードID
            graph: 対象グラフ（Noneで保存済みをロード）

        Returns:
            該当ノードまたはNone
        """
        if graph is None:
            graph = self.load_graph()
        return self.graph_service.get_node_by_id(graph, node_id)

    # === プラグイン情報 ===

    def get_plugins(self) -> list[Any]:
        """ロード済みプラグイン一覧"""
        return self.plugin_manager.get_plugins()

    def get_available_export_formats(self) -> list[str]:
        """利用可能なエクスポート形式の一覧"""
        from services.export import _exporter_registry

        return sorted({cls.format for cls in _exporter_registry})

    def get_cli_commands(self) -> list[Any]:
        """プラグインが提供するCLIコマンドを収集して返す"""
        from services.sdk.cli_extension import CLICommand, collect_cli_commands

        all_commands: list[CLICommand] = []
        for manifest in self.plugin_manager.get_all_manifests().values():
            if manifest.cli_commands:
                all_commands.extend(collect_cli_commands(manifest.cli_commands))
        return all_commands

    def get_api_routes(self) -> list[Any]:
        """プラグインが提供するAPIルートを収集して返す"""
        from services.sdk.api_extension import APIRoute, collect_api_routes

        all_routes: list[APIRoute] = []
        for manifest in self.plugin_manager.get_all_manifests().values():
            if manifest.api_routes:
                all_routes.extend(collect_api_routes(manifest.api_routes))
        return all_routes

    # === 内部メソッド ===

    def _register_plugin_capabilities(self) -> None:
        """PluginManagerのマニフェスト情報をCapabilityRegistryに登録する"""
        for manifest in self.plugin_manager.get_all_manifests().values():
            # パーサー
            for parser_path in manifest.parsers:
                self.capability_registry.register(Capability.PARSER, parser_path, manifest.name)
            # エクスポーター
            for exporter_path in manifest.exporters:
                self.capability_registry.register(Capability.EXPORTER, exporter_path, manifest.name)
            # CLIコマンド
            for cli_path in manifest.cli_commands:
                self.capability_registry.register(Capability.CLI_COMMAND, cli_path, manifest.name)
            # APIルート
            for api_path in manifest.api_routes:
                self.capability_registry.register(Capability.API_ROUTE, api_path, manifest.name)

            # PluginLoadedイベント発行
            capabilities = []
            if manifest.parsers:
                capabilities.append("parsers")
            if manifest.exporters:
                capabilities.append("exporters")
            if manifest.cli_commands:
                capabilities.append("cli_commands")
            if manifest.api_routes:
                capabilities.append("api_routes")

            self.event_bus.publish(
                PluginLoaded(
                    source="core",
                    plugin_name=manifest.name,
                    capabilities=capabilities,
                )
            )
