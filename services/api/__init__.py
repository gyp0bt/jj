"""REST API モジュール (jj serve)

FastAPIベースのREST APIサーバー。
GraphModelを読み込み、ノード/リレーション/サマリー等のエンドポイントを提供する。

[READMEへ戻る](../../../README.md)
"""

from services.api.routes import create_app

__all__ = ["create_app"]
