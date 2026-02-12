"""FastAPI ルート定義

jj serveで起動されるREST APIのエンドポイントを定義する。

エンドポイント一覧:
  GET /api/v1/graph           - グラフ全体
  GET /api/v1/nodes           - ノード一覧（フィルター対応）
  GET /api/v1/nodes/{id}      - ノード詳細
  GET /api/v1/nodes/{id}/related - 関連ノード
  GET /api/v1/relations       - リレーション一覧
  GET /api/v1/properties/keys - プロパティキー一覧
  GET /api/v1/summary         - サマリー統計
  GET /api/v1/status          - 実行ステータス

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from jj_types import GraphModel
from services.dashboard.data_provider import DashboardDataProvider
from services.graph import GraphService


def create_app(project_root: Path) -> FastAPI:
    """FastAPIアプリケーションを生成する

    Args:
        project_root: jjプロジェクトのルートパス

    Returns:
        設定済みのFastAPIインスタンス
    """
    app = FastAPI(
        title="jj API",
        description="CAE業務データグラフのREST API",
        version="1.0.0",
    )

    # CORS設定（ローカル開発用）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 状態保持
    state: dict[str, Any] = {
        "project_root": project_root,
        "graph": None,
        "provider": None,
    }

    def _get_graph() -> GraphModel:
        """GraphModelを取得（遅延ロード）"""
        if state["graph"] is None:
            svc = GraphService(project_root=state["project_root"])
            state["graph"] = svc.load()
        return state["graph"]

    def _get_provider() -> DashboardDataProvider:
        """DashboardDataProviderを取得（遅延ロード）"""
        if state["provider"] is None:
            graph = _get_graph()
            try:
                from config import GraphConfig

                config = GraphConfig.load(base_dir=state["project_root"])
                vocab = config.vocab
                units = config.export.units
            except Exception:
                vocab = {}
                units = {}
            state["provider"] = DashboardDataProvider(
                graph, vocab=vocab, units=units
            )
        return state["provider"]

    # ------------------------------------------
    # GET /api/v1/graph
    # ------------------------------------------
    @app.get("/api/v1/graph")
    def get_graph() -> dict[str, Any]:
        """グラフ全体（nodes + relations）を返す"""
        graph = _get_graph()
        return {
            "nodes": [n.model_dump() for n in graph.nodes],
            "relations": [r.model_dump() for r in graph.relations],
        }

    # ------------------------------------------
    # GET /api/v1/nodes
    # ------------------------------------------
    @app.get("/api/v1/nodes")
    def get_nodes(
        type: Optional[str] = Query(None, description="ノードタイプでフィルタ"),
        active: Optional[bool] = Query(None, description="activeフラグでフィルタ"),
        name: Optional[str] = Query(None, description="名前の部分一致フィルタ"),
        limit: int = Query(1000, description="取得件数上限", ge=1, le=10000),
        offset: int = Query(0, description="オフセット", ge=0),
    ) -> dict[str, Any]:
        """ノード一覧を返す（フィルター対応）"""
        graph = _get_graph()
        nodes = list(graph.nodes)

        if type is not None:
            nodes = [n for n in nodes if n.type == type]
        if active is not None:
            nodes = [
                n for n in nodes if n.properties.get("active") == active
            ]
        if name is not None:
            name_lower = name.lower()
            nodes = [n for n in nodes if name_lower in n.name.lower()]

        total = len(nodes)
        nodes = nodes[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "nodes": [n.model_dump() for n in nodes],
        }

    # ------------------------------------------
    # GET /api/v1/nodes/{node_id}
    # ------------------------------------------
    @app.get("/api/v1/nodes/{node_id}")
    def get_node(node_id: int) -> dict[str, Any]:
        """ノード詳細を返す"""
        provider = _get_provider()
        card = provider.get_node_card(node_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return card

    # ------------------------------------------
    # GET /api/v1/nodes/{node_id}/related
    # ------------------------------------------
    @app.get("/api/v1/nodes/{node_id}/related")
    def get_related_nodes(
        node_id: int,
        label: Optional[str] = Query(None, description="リレーションラベルでフィルタ"),
    ) -> dict[str, Any]:
        """関連ノードを返す"""
        provider = _get_provider()
        related = provider.get_related_files(node_id, label=label)
        return {"node_id": node_id, "related": related}

    # ------------------------------------------
    # GET /api/v1/relations
    # ------------------------------------------
    @app.get("/api/v1/relations")
    def get_relations(
        label: Optional[str] = Query(None, description="ラベルでフィルタ"),
        limit: int = Query(1000, description="取得件数上限", ge=1, le=10000),
        offset: int = Query(0, description="オフセット", ge=0),
    ) -> dict[str, Any]:
        """リレーション一覧を返す"""
        graph = _get_graph()
        relations = list(graph.relations)

        if label is not None:
            relations = [r for r in relations if r.label == label]

        total = len(relations)
        relations = relations[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "relations": [r.model_dump() for r in relations],
        }

    # ------------------------------------------
    # GET /api/v1/properties/keys
    # ------------------------------------------
    @app.get("/api/v1/properties/keys")
    def get_property_keys() -> dict[str, Any]:
        """利用可能なプロパティキー一覧を返す"""
        provider = _get_provider()
        keys = provider.get_property_keys()
        return {"keys": keys}

    # ------------------------------------------
    # GET /api/v1/summary
    # ------------------------------------------
    @app.get("/api/v1/summary")
    def get_summary() -> dict[str, Any]:
        """サマリー統計を返す"""
        graph = _get_graph()
        svc = GraphService(project_root=state["project_root"])
        summary = svc.summary(graph)

        # go_テーブル行数も追加
        provider = _get_provider()
        go_rows = provider.get_go_table()

        return {
            **summary,
            "go_file_count": len(go_rows),
        }

    # ------------------------------------------
    # GET /api/v1/status
    # ------------------------------------------
    @app.get("/api/v1/status")
    def get_status() -> dict[str, Any]:
        """実行ステータスを返す"""
        provider = _get_provider()
        return provider.get_status_summary()

    # ------------------------------------------
    # POST /api/v1/reload
    # ------------------------------------------
    @app.post("/api/v1/reload")
    def reload_graph() -> dict[str, str]:
        """グラフデータを再読み込みする"""
        state["graph"] = None
        state["provider"] = None
        _ = _get_graph()
        return {"status": "reloaded"}

    return app
