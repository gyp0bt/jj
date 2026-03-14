"""APIRoute — プラグインによるAPIルート拡張ポイント

プラグインがAPIルートを宣言的に追加するための定義。
PluginManifest の api_routes フィールドにモジュールパスを指定し、
各モジュールが get_api_routes() 関数で APIRoute リストを返す。

使用例:
    # services/plugins/abaqus/api.py
    from services.sdk.api_extension import APIRoute

    def get_api_routes() -> list[APIRoute]:
        return [
            APIRoute(
                path="/api/v1/abaqus/materials",
                method="GET",
                handler=handle_get_materials,
                summary="Abaqus物性一覧を取得",
                tags=["abaqus"],
            ),
        ]

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class APIRoute:
    """プラグインが提供するAPIルート定義

    Attributes:
        path: エンドポイントパス（例: "/api/v1/abaqus/materials"）
        method: HTTPメソッド（"GET", "POST", "PUT", "DELETE"等）
        handler: リクエストハンドラ関数。(app: JJApp, **params) -> dict を想定
        summary: OpenAPI summary 文字列
        tags: OpenAPI タグリスト
        response_model: レスポンスモデル（Pydantic model class等、オプション）
        metadata: 追加メタデータ
    """

    path: str
    method: str = "GET"
    handler: Callable[..., Any] | None = None
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    response_model: type | None = field(default=None, compare=False, hash=False)
    metadata: dict[str, Any] = field(default_factory=dict)


def collect_api_routes(module_paths: list[str]) -> list[APIRoute]:
    """指定モジュールパスからAPIRouteを収集する

    各モジュールの get_api_routes() 関数を呼び出し、
    返された APIRoute リストを集約する。

    Args:
        module_paths: APIRoute定義モジュールのパスリスト

    Returns:
        収集された APIRoute のリスト
    """
    import importlib
    import logging

    logger = logging.getLogger(__name__)
    routes: list[APIRoute] = []

    for path in module_paths:
        try:
            mod = importlib.import_module(path)
            getter = getattr(mod, "get_api_routes", None)
            if getter is not None and callable(getter):
                result = getter()
                if isinstance(result, list):
                    routes.extend(result)
                else:
                    logger.warning(f"get_api_routes() がリストを返さなかった: {path}")
            else:
                logger.debug(f"get_api_routes() が見つからない: {path}")
        except ImportError as e:
            logger.debug(f"APIルートモジュールのインポートをスキップ: {path}: {e}")
        except Exception as e:
            logger.warning(f"APIルートの収集に失敗: {path}: {e}")

    return routes
