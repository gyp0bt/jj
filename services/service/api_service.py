"""ApiService: REST API 向けビジネスロジック

API層（services/api/routes.py）が直接GraphServiceやDashboardDataProviderを
参照せず、このサービスを経由してすべての操作を行う。
これにより API→コア層の依存関係が一元化され、テストやプラグイン化が容易になる。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jj_types import GraphModel, Node, Relation


class ApiService:
    """REST API 向けサービスクラス

    GraphService / DashboardDataProvider / QueryService をラップし、
    API層に必要なすべてのビジネスロジックを集約する。
    API層（routes.py）はこのクラスのみに依存する。
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._graph: GraphModel | None = None
        self._provider: Any = None  # DashboardDataProvider（遅延ロード）
        self._graph_service: Any = None  # GraphService（遅延ロード）

    @property
    def project_root(self) -> Path:
        return self._project_root

    # --------------------------------------------------
    # 内部ヘルパー（遅延ロード）
    # --------------------------------------------------

    def _ensure_graph_service(self) -> Any:
        """GraphServiceを遅延初期化して返す"""
        if self._graph_service is None:
            from services.graph import GraphService

            self._graph_service = GraphService(project_root=self._project_root)
        return self._graph_service

    def _ensure_graph(self) -> GraphModel:
        """GraphModelを遅延ロードして返す"""
        if self._graph is None:
            svc = self._ensure_graph_service()
            self._graph = svc.load(resolve_externalized=True)
        return self._graph

    def _ensure_provider(self) -> Any:
        """DashboardDataProviderを遅延初期化して返す"""
        if self._provider is None:
            from services.dashboard.data_provider import DashboardDataProvider

            graph = self._ensure_graph()
            try:
                from config import GraphConfig

                config = GraphConfig.load(base_dir=self._project_root)
                vocab = config.vocab
                units = config.export.units
            except Exception:
                vocab = {}
                units = {}
            self._provider = DashboardDataProvider(graph, vocab=vocab, units=units, project_root=self._project_root)
        return self._provider

    # --------------------------------------------------
    # グラフ取得
    # --------------------------------------------------

    def get_graph(self) -> GraphModel:
        """GraphModelを取得（遅延ロード）"""
        return self._ensure_graph()

    def get_nodes(self) -> list[Node]:
        """全ノードリストを取得"""
        return list(self._ensure_graph().nodes)

    def get_relations(self) -> list[Relation]:
        """全リレーションリストを取得"""
        return list(self._ensure_graph().relations)

    # --------------------------------------------------
    # ノード詳細・関連
    # --------------------------------------------------

    def get_node_card(self, node_id: int) -> dict[str, Any] | None:
        """ノード詳細カード情報を返す

        Args:
            node_id: ノードID

        Returns:
            カード辞書 or None（見つからない場合）
        """
        provider = self._ensure_provider()
        return provider.get_node_card(node_id)

    def get_related_files(self, node_id: int, label: str | None = None) -> list[dict[str, Any]]:
        """関連ファイル/ノード一覧を返す

        Args:
            node_id: ノードID
            label: リレーションラベルフィルタ（Noneで全件）

        Returns:
            関連ノード情報リスト
        """
        provider = self._ensure_provider()
        return provider.get_related_files(node_id, label=label)

    # --------------------------------------------------
    # プロパティ・統計
    # --------------------------------------------------

    def get_property_keys(self) -> list[str]:
        """利用可能なプロパティキー一覧を返す"""
        provider = self._ensure_provider()
        return provider.get_property_keys()

    def get_summary(self) -> dict[str, Any]:
        """サマリー統計を返す（go_file_count含む）"""
        graph = self._ensure_graph()
        svc = self._ensure_graph_service()
        summary = svc.summary(graph)

        provider = self._ensure_provider()
        go_rows = provider.get_go_table()

        return {
            **summary,
            "go_file_count": len(go_rows),
        }

    def get_status_summary(self) -> dict[str, Any]:
        """実行ステータスサマリーを返す"""
        provider = self._ensure_provider()
        return provider.get_status_summary()

    # --------------------------------------------------
    # パース・リロード
    # --------------------------------------------------

    def parse_project(self, full: bool = False) -> dict[str, Any]:
        """プロジェクトを再パースしてグラフデータを更新する

        Args:
            full: Trueの場合、重い処理（メッシュ統計等）も実行する

        Returns:
            パース結果のサマリー辞書
        """
        svc = self._ensure_graph_service()
        graph, save_path = svc.parse_and_save(full_mode=full)

        # キャッシュをリセットして新しいグラフを反映
        self._graph = graph
        self._provider = None

        summary = svc.summary(graph)
        return {
            "status": "parsed",
            "save_path": str(save_path),
            **summary,
        }

    def reload_graph(self) -> None:
        """グラフデータのキャッシュをクリアして再読み込みする"""
        self._graph = None
        self._provider = None
        self._ensure_graph()

    # --------------------------------------------------
    # フィルタ付きリレーション取得
    # --------------------------------------------------

    def filter_relations(
        self,
        label: str | None = None,
    ) -> list[Relation]:
        """リレーション一覧を返す（ラベルフィルタ対応）

        Args:
            label: ラベルフィルタ（Noneで全件）

        Returns:
            リレーションリスト
        """
        relations = self.get_relations()
        if label is not None:
            relations = [r for r in relations if r.label == label]
        return relations
