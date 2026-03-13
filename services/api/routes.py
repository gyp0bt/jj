"""FastAPI ルート定義

jj serveで起動されるREST APIのエンドポイントを定義する。

エンドポイント一覧:
  GET  /api/v1/graph           - グラフ全体
  GET  /api/v1/nodes           - ノード一覧（フィルター対応・プロパティ比較フィルター）
  GET  /api/v1/nodes/{id}      - ノード詳細
  GET  /api/v1/nodes/{id}/related - 関連ノード
  GET  /api/v1/relations       - リレーション一覧
  GET  /api/v1/properties/keys - プロパティキー一覧
  GET  /api/v1/summary         - サマリー統計
  GET  /api/v1/status          - 実行ステータス
  POST /api/v1/parse           - プロジェクト再パース実行
  POST /api/v1/reload          - グラフ再読み込み

プロパティ比較フィルター:
  GET /api/v1/nodes?props.RF3.gt=5&props.temperature.lt=400
  対応オペレータ: eq, ne, gt, ge, lt, le

依存関係:
  routes.py → services.service.ApiService → GraphService/DashboardDataProvider
  routes.py → services.service.QueryService (ノードフィルタのみ)

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from services.service import ApiService, QueryService


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

    # サービス層のみに依存
    api_svc = ApiService(project_root)

    # ------------------------------------------
    # GET /api/v1/graph
    # ------------------------------------------
    @app.get("/api/v1/graph")
    def get_graph() -> dict[str, Any]:
        """グラフ全体（nodes + relations）を返す"""
        graph = api_svc.get_graph()
        return {
            "nodes": [n.model_dump() for n in graph.nodes],
            "relations": [r.model_dump() for r in graph.relations],
        }

    # ------------------------------------------
    # GET /api/v1/nodes
    # ------------------------------------------
    @app.get("/api/v1/nodes")
    def get_nodes(
        request: Request,
        type: str | None = Query(None, description="ノードタイプでフィルタ"),
        active: bool | None = Query(None, description="activeフラグでフィルタ"),
        name: str | None = Query(None, description="名前の部分一致フィルタ"),
        limit: int = Query(1000, description="取得件数上限", ge=1, le=10000),
        offset: int = Query(0, description="オフセット", ge=0),
    ) -> dict[str, Any]:
        """ノード一覧を返す（フィルター対応）

        プロパティ比較フィルター:
            ?props.RF3.gt=5 → RF3 > 5 のノードのみ
            ?props.temperature.le=400 → temperature <= 400 のノードのみ
            対応オペレータ: eq, ne, gt, ge, lt, le
        """
        nodes = api_svc.get_nodes()

        # QueryServiceでフィルタリングを一括適用
        nodes = QueryService.filter_nodes(
            nodes,
            type_filter=type,
            active_filter=active,
            name_filter=name,
            query_params=dict(request.query_params),
        )

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
        card = api_svc.get_node_card(node_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return card

    # ------------------------------------------
    # GET /api/v1/nodes/{node_id}/related
    # ------------------------------------------
    @app.get("/api/v1/nodes/{node_id}/related")
    def get_related_nodes(
        node_id: int,
        label: str | None = Query(None, description="リレーションラベルでフィルタ"),
    ) -> dict[str, Any]:
        """関連ノードを返す"""
        related = api_svc.get_related_files(node_id, label=label)
        return {"node_id": node_id, "related": related}

    # ------------------------------------------
    # GET /api/v1/relations
    # ------------------------------------------
    @app.get("/api/v1/relations")
    def get_relations(
        label: str | None = Query(None, description="ラベルでフィルタ"),
        limit: int = Query(1000, description="取得件数上限", ge=1, le=10000),
        offset: int = Query(0, description="オフセット", ge=0),
    ) -> dict[str, Any]:
        """リレーション一覧を返す"""
        relations = api_svc.filter_relations(label=label)

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
        keys = api_svc.get_property_keys()
        return {"keys": keys}

    # ------------------------------------------
    # GET /api/v1/summary
    # ------------------------------------------
    @app.get("/api/v1/summary")
    def get_summary() -> dict[str, Any]:
        """サマリー統計を返す"""
        return api_svc.get_summary()

    # ------------------------------------------
    # GET /api/v1/status
    # ------------------------------------------
    @app.get("/api/v1/status")
    def get_status() -> dict[str, Any]:
        """実行ステータスを返す"""
        return api_svc.get_status_summary()

    # ------------------------------------------
    # POST /api/v1/parse
    # ------------------------------------------
    @app.post("/api/v1/parse")
    def parse_project(
        full: bool = Query(False, description="--fullモードで実行"),
    ) -> dict[str, Any]:
        """プロジェクトを再パースしてグラフデータを更新する

        Args:
            full: Trueの場合、重い処理（メッシュ統計等）も実行する

        Returns:
            パース結果のサマリー
        """
        return api_svc.parse_project(full=full)

    # ------------------------------------------
    # POST /api/v1/reload
    # ------------------------------------------
    @app.post("/api/v1/reload")
    def reload_graph() -> dict[str, str]:
        """グラフデータを再読み込みする"""
        api_svc.reload_graph()
        return {"status": "reloaded"}

    # ------------------------------------------
    # POST /api/v1/sync/push
    # ------------------------------------------
    @app.post("/api/v1/sync/push")
    def sync_push(
        backend: str = Query("shared_folder", description="バックエンド名"),
        target_dir: str | None = Query(None, description="pushするディレクトリ"),
        destination: str | None = Query(None, description="同期先パス"),
    ) -> dict[str, Any]:
        """プロジェクトを共有フォルダ/GitLabにプッシュ"""
        from services.sync.service import SyncService

        service = SyncService(project_root)
        try:
            state = service.push(
                backend_name=backend,
                target_dir=target_dir,
                destination=destination,
            )
            return state.model_dump(mode="json")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # ------------------------------------------
    # POST /api/v1/sync/clone
    # ------------------------------------------
    @app.post("/api/v1/sync/clone")
    def sync_clone(
        source: str = Query(..., description="同期元パス"),
        backend: str = Query("shared_folder", description="バックエンド名"),
        destination: str | None = Query(None, description="クローン先ディレクトリ"),
    ) -> dict[str, Any]:
        """共有フォルダ/GitLabからプロジェクトをクローン"""
        from pathlib import Path as _Path

        from services.sync.service import SyncService

        service = SyncService(project_root)
        try:
            dest = _Path(destination) if destination else None
            state = service.clone(
                source=source,
                backend_name=backend,
                destination=dest,
            )
            return state.model_dump(mode="json")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # ------------------------------------------
    # GET /api/v1/sync/status
    # ------------------------------------------
    @app.get("/api/v1/sync/status")
    def sync_status(
        sync_id: str | None = Query(None, description="同期ID"),
        status_filter: str | None = Query(None, description="ステータスフィルタ"),
    ) -> dict[str, Any]:
        """同期状態を取得"""
        from services.sync.models import SyncStatus
        from services.sync.service import SyncService

        service = SyncService(project_root)
        sf = SyncStatus(status_filter) if status_filter else None
        syncs = service.status(sync_id=sync_id, status_filter=sf)
        return {
            "total": len(syncs),
            "syncs": [s.model_dump(mode="json") for s in syncs],
        }

    # ------------------------------------------
    # GET /api/v1/sync/{sync_id}
    # ------------------------------------------
    @app.get("/api/v1/sync/{sync_id}")
    def sync_detail(sync_id: str) -> dict[str, Any]:
        """同期操作の詳細を取得"""
        from services.sync.service import SyncService

        service = SyncService(project_root)
        state = service.get_sync(sync_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Sync not found")
        return state.model_dump(mode="json")

    return app
