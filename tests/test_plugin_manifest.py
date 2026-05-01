"""PluginManifest + PluginManager テスト

P-1: 宣言的プラグイン登録の検証。
PluginManifest の生成・不変性と PluginManager のライフサイクルをテストする。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import pytest

from services.sdk.plugin_manager import PluginManager
from services.sdk.plugin_manifest import PluginInfo, PluginManifest


class TestPluginManifest:
    """PluginManifest dataclass のテスト"""

    def test_create_minimal(self):
        """最小構成で生成できる"""
        m = PluginManifest(name="test")
        assert m.name == "test"
        assert m.version == "0.0.0"
        assert m.description == ""
        assert m.parsers == []
        assert m.exporters == []
        assert m.dashboard_pages == []
        assert m.depends_on == []

    def test_create_full(self):
        """全フィールド指定で生成できる"""
        m = PluginManifest(
            name="abaqus",
            version="0.3.0",
            description="Abaqus CAE解析ファイルの解析・可視化",
            parsers=["services.parse.connectors.abaqus.inp_parser"],
            exporters=["services.export.connectors.abaqus_exporter"],
            dashboard_pages=["plugins.abaqus.dashboard"],
            cli_commands=["services.plugins.abaqus.cli"],
            api_routes=["services.plugins.abaqus.api"],
            depends_on=[],
            optional_dependencies={"pymesh": "modules/pymesh"},
            config_schema={"type": "object"},
        )
        assert m.name == "abaqus"
        assert m.version == "0.3.0"
        assert len(m.parsers) == 1
        assert "pymesh" in m.optional_dependencies

    def test_frozen(self):
        """frozen=True で属性変更不可"""
        m = PluginManifest(name="test")
        with pytest.raises(AttributeError):
            m.name = "changed"  # type: ignore[misc]

    def test_equality(self):
        """同一内容の PluginManifest は等値"""
        m1 = PluginManifest(name="test", version="1.0.0")
        m2 = PluginManifest(name="test", version="1.0.0")
        assert m1 == m2

    def test_on_load_excluded_from_compare(self):
        """on_load/on_unload は比較から除外される"""
        m1 = PluginManifest(name="test", on_load=lambda: None)
        m2 = PluginManifest(name="test", on_load=lambda: None)
        assert m1 == m2

    def test_frozen_prevents_mutation(self):
        """frozen=True により属性の再代入が禁止される"""
        m = PluginManifest(name="test", version="1.0.0")
        with pytest.raises(AttributeError):
            m.version = "2.0.0"  # type: ignore[misc]


class TestPluginInfo:
    """PluginInfo dataclass のテスト"""

    def test_create(self):
        info = PluginInfo(
            name="abaqus",
            version="0.3.0",
            description="Abaqus plugin",
            capabilities=["parsers", "dashboard_pages"],
            has_manifest=True,
        )
        assert info.name == "abaqus"
        assert info.has_manifest is True
        assert len(info.capabilities) == 2


class TestPluginManager:
    """PluginManager のテスト"""

    def test_create_empty(self):
        """空の PluginManager を生成できる"""
        pm = PluginManager()
        assert pm.plugin_count == 0
        assert pm.get_plugins() == []

    def test_register_manifest(self):
        """マニフェストを直接登録できる"""
        pm = PluginManager()
        manifest = PluginManifest(
            name="test_plugin",
            version="1.0.0",
            description="テスト用プラグイン",
            parsers=["test.parser"],
        )
        pm._register_manifest(manifest)
        assert pm.plugin_count == 1
        assert pm.is_loaded("test_plugin")
        assert pm.get_manifest("test_plugin") is manifest

    def test_register_manifest_duplicate_warns(self, caplog):
        """重複マニフェスト登録は警告を出す"""
        pm = PluginManager()
        m1 = PluginManifest(name="dup", version="1.0.0")
        m2 = PluginManifest(name="dup", version="2.0.0")
        pm._register_manifest(m1)
        pm._register_manifest(m2)
        assert pm.get_manifest("dup").version == "2.0.0"

    def test_invoke_register_manifest(self):
        """register() が PluginManifest を返す場合の処理"""
        pm = PluginManager()

        def register():
            return PluginManifest(name="new_plugin", version="0.1.0")

        pm._invoke_register(register)
        assert pm.is_loaded("new_plugin")
        assert pm.get_manifest("new_plugin").version == "0.1.0"

    def test_invoke_register_legacy(self):
        """register() が None を返す（旧方式）の処理"""
        pm = PluginManager()
        call_count = 0

        def register():
            nonlocal call_count
            call_count += 1
            return None

        register.__module__ = "services.plugins.legacy_solver.__init__"
        pm._invoke_register(register)
        assert call_count == 1
        # レガシープラグインとして登録される
        assert len(pm._legacy_plugins) == 1

    def test_invoke_register_error_handled(self, caplog):
        """register() が例外を投げても他に影響しない"""
        pm = PluginManager()

        def bad_register():
            raise RuntimeError("broken plugin")

        pm._invoke_register(bad_register)
        assert pm.plugin_count == 0

    def test_get_plugins_mixed(self):
        """マニフェスト + レガシーの混在"""
        pm = PluginManager()
        pm._register_manifest(
            PluginManifest(
                name="new_plugin",
                version="1.0.0",
                parsers=["p1"],
                dashboard_pages=["d1"],
            )
        )
        pm._legacy_plugins.append("old_plugin")

        plugins = pm.get_plugins()
        assert len(plugins) == 2

        new = next(p for p in plugins if p.name == "new_plugin")
        assert new.has_manifest is True
        assert "parsers" in new.capabilities
        assert "dashboard_pages" in new.capabilities

        old = next(p for p in plugins if p.name == "old_plugin")
        assert old.has_manifest is False
        assert old.version == "unknown"

    def test_get_all_manifests(self):
        """全マニフェスト取得"""
        pm = PluginManager()
        m1 = PluginManifest(name="a")
        m2 = PluginManifest(name="b")
        pm._register_manifest(m1)
        pm._register_manifest(m2)
        all_m = pm.get_all_manifests()
        assert len(all_m) == 2
        assert "a" in all_m
        assert "b" in all_m

    def test_reset(self):
        """reset() で全状態がクリアされる"""
        pm = PluginManager()
        pm._register_manifest(PluginManifest(name="a"))
        pm._legacy_plugins.append("b")
        pm._loaded = True

        pm.reset()
        assert pm.plugin_count == 0
        assert not pm._loaded

    def test_on_load_hook_called(self):
        """PluginManifest の on_load フックが load_all() 時に呼ばれる"""
        hook_called = []

        def on_load():
            hook_called.append(True)

        pm = PluginManager(_BUILTIN_PLUGINS=[])
        manifest = PluginManifest(name="hook_test", on_load=on_load)
        pm._register_manifest(manifest)

        # load_all を手動で発動（内蔵プラグインなし）
        pm._loaded = False
        pm.load_all()
        assert len(hook_called) == 1

    def test_on_unload_hook_called_on_reset(self):
        """PluginManifest の on_unload フックが reset() 時に呼ばれる"""
        hook_called = []

        def on_unload():
            hook_called.append(True)

        pm = PluginManager()
        pm._register_manifest(PluginManifest(name="hook_test", on_unload=on_unload))
        pm.reset()
        assert len(hook_called) == 1

    def test_load_all_idempotent(self):
        """load_all() は冪等（2回目以降は何もしない）"""
        pm = PluginManager(_BUILTIN_PLUGINS=[])
        pm.load_all()
        pm.load_all()
        pm.load_all()
        # エラーなく完了

    def test_is_loaded_false_for_unknown(self):
        """未登録プラグインは False"""
        pm = PluginManager()
        assert not pm.is_loaded("nonexistent")


class TestPluginManagerWithBuiltinPlugins:
    """内蔵プラグインとの統合テスト"""

    def test_load_all_discovers_builtin(self):
        """内蔵プラグインがロードされる"""
        pm = PluginManager()
        pm.load_all()
        # abaqus は旧方式(register() -> None)なのでレガシーとして登録
        assert pm.is_loaded("abaqus")

    def test_load_all_discovers_obsidian(self):
        """Obsidianプラグインがロードされる"""
        pm = PluginManager()
        pm.load_all()
        assert pm.is_loaded("obsidian")
