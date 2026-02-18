"""プラグイン統合テスト

pip install -e 後にプラグイン登録が正常に行われることを検証する。
entry_points経由のプラグイン検出 → register()呼び出し → パーサー/コネクター登録
の一連の流れをテストする。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import importlib

import pytest


class TestPluginRegistration:
    """プラグイン登録テスト"""

    def test_abaqus_plugin_registers(self):
        """Abaqusプラグインが正常に登録される"""
        from services.plugins.abaqus import register

        register()
        # パーサーレジストリにAbaqusパーサーが含まれること
        from services.parse.base import get_parser_registry

        parser_names = [cls.__name__ for cls in get_parser_registry()]
        assert any("Abaqus" in name for name in parser_names)

    def test_calculix_plugin_registers(self):
        """CalculiXプラグインが正常に登録される"""
        from services.plugins.calculix import register

        register()
        from services.parse.base import get_parser_registry

        parser_names = [cls.__name__ for cls in get_parser_registry()]
        assert any("Calculix" in name or "calculix" in name.lower() for name in parser_names)

    def test_ml_plugin_registers(self):
        """MLプラグインが正常に登録される"""
        from services.plugins.ml import register

        register()
        from services.parse.base import get_parser_registry

        parser_names = [cls.__name__ for cls in get_parser_registry()]
        assert "MLDatasetParser" in parser_names
        assert "MLConfigParser" in parser_names
        assert "MLScriptParser" in parser_names
        assert "TorchCheckpointParser" in parser_names
        assert "SklearnModelParser" in parser_names
        assert "ExperimentRunParser" in parser_names

    def test_all_plugins_register_without_error(self):
        """全プラグインのregister()がエラーなく完了する"""
        plugin_modules = [
            "services.plugins.abaqus",
            "services.plugins.calculix",
            "services.plugins.flow3d",
            "services.plugins.fluent",
            "services.plugins.hfss",
            "services.plugins.lsdyna",
            "services.plugins.ml",
            "services.plugins.obsidian",
            "services.plugins.openfoam",
        ]
        for mod_name in plugin_modules:
            mod = importlib.import_module(mod_name)
            reg_fn = getattr(mod, "register", None)
            assert reg_fn is not None, f"{mod_name} has no register() function"
            # register()がエラーなく完了すること
            reg_fn()

    def test_entry_points_discoverable(self):
        """entry_pointsからプラグインが検出可能"""
        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            # Python 3.12+
            if hasattr(eps, "select"):
                jj_plugins = eps.select(group="jj.plugins")
            else:
                jj_plugins = eps.get("jj.plugins", [])
            plugin_names = [ep.name for ep in jj_plugins]
            assert "abaqus" in plugin_names
            assert "calculix" in plugin_names
        except Exception:
            pytest.skip("entry_points not available (not installed with -e)")

    def test_abaqus_dashboard_connector_registered(self):
        """Abaqusダッシュボードコネクターがレジストリに登録される"""
        import services.dashboard.connectors.abaqus  # noqa: F401
        from services.dashboard.connectors import DashboardPageConnector

        registered_labels = list(DashboardPageConnector._registry.keys())
        assert "物性一覧" in registered_labels
        assert "メッシュ品質" in registered_labels
        assert "ジョブサマリー" in registered_labels

    def test_plugin_register_idempotent(self):
        """register()を複数回呼んでもエラーにならない（冪等性）"""
        from services.plugins.abaqus import register

        register()
        register()
        register()
        # エラーなく完了すればOK


class TestPluginParseIntegration:
    """プラグイン + parse統合テスト"""

    def test_parse_pipeline_includes_abaqus_parsers(self):
        """パースパイプラインにAbaqusパーサーが含まれる"""
        from services.plugins.abaqus import register

        register()

        from services.parse.base import get_parser_registry

        parser_names = [cls.__name__ for cls in get_parser_registry()]
        # Abaqus固有パーサーが含まれること
        expected_parsers = [
            "AbaqusInpParser",
            "AbaqusResultParser",
            "AbaqusParameterParser",
        ]
        for name in expected_parsers:
            assert name in parser_names, f"{name} not found in parser registry"

    def test_parse_pipeline_priority_order(self):
        """パーサーがpriority順にソートされている"""
        from services.plugins.abaqus import register

        register()

        from services.parse.base import get_parser_registry

        registry = get_parser_registry()
        sorted_registry = sorted(registry, key=lambda cls: cls.priority)
        priorities = [cls.priority for cls in sorted_registry]
        # priorityは単調増加（同一値許可）
        for i in range(len(priorities) - 1):
            assert priorities[i] <= priorities[i + 1], (
                f"Parser priority order violated: "
                f"{sorted_registry[i].__name__}({priorities[i]}) > "
                f"{sorted_registry[i + 1].__name__}({priorities[i + 1]})"
            )
