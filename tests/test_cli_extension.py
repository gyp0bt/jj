"""CLICommand 拡張ポイントのテスト

P-6: CLICommand dataclass と collect_cli_commands() のテスト。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import types

import pytest

from services.sdk.cli_extension import CLICommand, collect_cli_commands


class TestCLICommand:
    """CLICommand dataclass のテスト"""

    def test_create_minimal(self):
        """最小パラメータで作成できる"""
        cmd = CLICommand(name="test", help="Test command", handler=lambda app, args: 0)
        assert cmd.name == "test"
        assert cmd.help == "Test command"
        assert cmd.parent == "root"
        assert cmd.aliases == ()
        assert cmd.metadata == {}

    def test_create_full(self):
        """全パラメータで作成できる"""

        def handler(app, args):
            return 0

        def add_args(parser):
            pass

        cmd = CLICommand(
            name="submit",
            help="Submit job",
            handler=handler,
            add_arguments=add_args,
            parent="abaqus",
            aliases=("sub",),
            metadata={"solver": "abaqus"},
        )
        assert cmd.name == "submit"
        assert cmd.add_arguments is add_args
        assert cmd.parent == "abaqus"
        assert cmd.aliases == ("sub",)
        assert cmd.metadata["solver"] == "abaqus"

    def test_frozen(self):
        """frozen dataclass なので変更不可"""
        cmd = CLICommand(name="test", help="Test", handler=lambda a, b: 0)
        with pytest.raises(AttributeError):
            cmd.name = "other"

    def test_equality(self):
        """同一パラメータなら等値"""

        def handler(app, args):
            return 0

        cmd1 = CLICommand(name="test", help="Test", handler=handler)
        cmd2 = CLICommand(name="test", help="Test", handler=handler)
        assert cmd1 == cmd2


class TestCollectCliCommands:
    """collect_cli_commands() のテスト"""

    def test_collect_from_valid_module(self, monkeypatch):
        """有効なモジュールからCLICommandを収集できる"""
        mock_commands = [
            CLICommand(name="cmd1", help="Help1", handler=lambda a, b: 0),
            CLICommand(name="cmd2", help="Help2", handler=lambda a, b: 0),
        ]

        mock_mod = types.ModuleType("mock_cli_module")
        mock_mod.get_cli_commands = lambda: mock_commands

        import importlib

        original_import = importlib.import_module
        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda path: mock_mod if path == "mock.cli" else original_import(path),
        )

        result = collect_cli_commands(["mock.cli"])
        assert len(result) == 2
        assert result[0].name == "cmd1"
        assert result[1].name == "cmd2"

    def test_collect_skips_missing_module(self):
        """存在しないモジュールはスキップされる"""
        result = collect_cli_commands(["nonexistent.module.cli"])
        assert result == []

    def test_collect_skips_module_without_getter(self, monkeypatch):
        """get_cli_commands() がないモジュールはスキップ"""
        mock_mod = types.ModuleType("mock_no_getter")

        import importlib

        original_import = importlib.import_module
        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda path: mock_mod if path == "mock.no_getter" else original_import(path),
        )

        result = collect_cli_commands(["mock.no_getter"])
        assert result == []

    def test_collect_multiple_modules(self, monkeypatch):
        """複数モジュールから収集"""
        mod1 = types.ModuleType("mod1")
        mod1.get_cli_commands = lambda: [CLICommand(name="a", help="A", handler=lambda a, b: 0)]
        mod2 = types.ModuleType("mod2")
        mod2.get_cli_commands = lambda: [CLICommand(name="b", help="B", handler=lambda a, b: 0)]

        import importlib

        original_import = importlib.import_module
        modules = {"mock.mod1": mod1, "mock.mod2": mod2}
        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda path: modules.get(path) or original_import(path),
        )

        result = collect_cli_commands(["mock.mod1", "mock.mod2"])
        assert len(result) == 2

    def test_collect_empty_list(self):
        """空リストからは空結果"""
        result = collect_cli_commands([])
        assert result == []
