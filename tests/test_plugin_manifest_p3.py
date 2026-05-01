"""P-3: 既存プラグインのマニフェスト対応テスト

abaqus, obsidian の register() が PluginManifest を返すことを検証する。
"""

from __future__ import annotations

import importlib

from services.sdk.plugin_manifest import PluginManifest


def _reset_plugin(module_name: str) -> None:
    """プラグインの _registered フラグをリセットしてリロード可能にする"""
    mod = importlib.import_module(module_name)
    if hasattr(mod, "_registered"):
        mod._registered = False


class TestAbaqusManifest:
    """Abaqusプラグインのマニフェストテスト"""

    def test_returns_manifest(self) -> None:
        _reset_plugin("plugins.abaqus")
        from plugins.abaqus import register

        result = register()
        assert isinstance(result, PluginManifest)
        assert result.name == "abaqus"

    def test_has_parsers(self) -> None:
        _reset_plugin("plugins.abaqus")
        from plugins.abaqus import register

        result = register()
        assert isinstance(result, PluginManifest)
        assert len(result.parsers) >= 6

    def test_has_description(self) -> None:
        _reset_plugin("plugins.abaqus")
        from plugins.abaqus import register

        result = register()
        assert isinstance(result, PluginManifest)
        assert result.description != ""


class TestObsidianManifest:
    """Obsidianプラグインのマニフェストテスト"""

    def test_returns_manifest(self) -> None:
        _reset_plugin("plugins.obsidian")
        from plugins.obsidian import register

        result = register()
        assert isinstance(result, PluginManifest)
        assert result.name == "obsidian"

    def test_has_parsers(self) -> None:
        _reset_plugin("plugins.obsidian")
        from plugins.obsidian import register

        result = register()
        assert isinstance(result, PluginManifest)
        assert len(result.parsers) >= 1
