"""APIRoute 拡張ポイントのテスト

P-7: APIRoute dataclass と collect_api_routes() のテスト。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import types

import pytest

from services.sdk.api_extension import APIRoute, collect_api_routes


class TestAPIRoute:
    """APIRoute dataclass のテスト"""

    def test_create_minimal(self):
        """最小パラメータで作成できる"""
        route = APIRoute(path="/api/v1/test")
        assert route.path == "/api/v1/test"
        assert route.method == "GET"
        assert route.handler is None
        assert route.summary == ""
        assert route.tags == []
        assert route.metadata == {}

    def test_create_full(self):
        """全パラメータで作成できる"""

        def handler(app, **params):
            return {"ok": True}

        route = APIRoute(
            path="/api/v1/abaqus/materials",
            method="POST",
            handler=handler,
            summary="Create material",
            tags=["abaqus", "materials"],
            metadata={"version": "1.0"},
        )
        assert route.path == "/api/v1/abaqus/materials"
        assert route.method == "POST"
        assert route.handler is handler
        assert route.tags == ["abaqus", "materials"]

    def test_frozen(self):
        """frozen dataclass なので変更不可"""
        route = APIRoute(path="/test")
        with pytest.raises(AttributeError):
            route.path = "/other"

    def test_equality(self):
        """同一パラメータなら等値"""
        route1 = APIRoute(path="/test", method="GET")
        route2 = APIRoute(path="/test", method="GET")
        assert route1 == route2

    def test_different_method_not_equal(self):
        """異なるメソッドは非等値"""
        route1 = APIRoute(path="/test", method="GET")
        route2 = APIRoute(path="/test", method="POST")
        assert route1 != route2


class TestCollectApiRoutes:
    """collect_api_routes() のテスト"""

    def test_collect_from_valid_module(self, monkeypatch):
        """有効なモジュールからAPIRouteを収集できる"""
        mock_routes = [
            APIRoute(path="/api/v1/a", handler=lambda **k: {}),
            APIRoute(path="/api/v1/b", method="POST", handler=lambda **k: {}),
        ]

        mock_mod = types.ModuleType("mock_api_module")
        mock_mod.get_api_routes = lambda: mock_routes

        import importlib

        original_import = importlib.import_module
        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda path: mock_mod if path == "mock.api" else original_import(path),
        )

        result = collect_api_routes(["mock.api"])
        assert len(result) == 2
        assert result[0].path == "/api/v1/a"

    def test_collect_skips_missing_module(self):
        """存在しないモジュールはスキップされる"""
        result = collect_api_routes(["nonexistent.module.api"])
        assert result == []

    def test_collect_skips_module_without_getter(self, monkeypatch):
        """get_api_routes() がないモジュールはスキップ"""
        mock_mod = types.ModuleType("mock_no_getter")

        import importlib

        original_import = importlib.import_module
        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda path: mock_mod if path == "mock.no_getter" else original_import(path),
        )

        result = collect_api_routes(["mock.no_getter"])
        assert result == []

    def test_collect_empty_list(self):
        """空リストからは空結果"""
        result = collect_api_routes([])
        assert result == []
