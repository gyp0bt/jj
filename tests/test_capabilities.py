"""CapabilityRegistry のテスト"""

from __future__ import annotations

import pytest

from services.sdk.capabilities import (
    Capability,
    CapabilityEntry,
    CapabilityRegistry,
)


class TestCapability:
    """Capability enum のテスト"""

    def test_all_members(self) -> None:
        expected = {
            "PARSER",
            "EXPORTER",
            "CLI_COMMAND",
            "API_ROUTE",
            "EVENT_HANDLER",
            "CONFIG_SECTION",
        }
        assert {c.name for c in Capability} == expected


class TestCapabilityEntry:
    """CapabilityEntry のテスト"""

    def test_creation(self) -> None:
        entry = CapabilityEntry(
            capability=Capability.PARSER,
            provider=str,
            plugin_name="abaqus",
            metadata={"priority": 60},
        )
        assert entry.capability == Capability.PARSER
        assert entry.provider is str
        assert entry.plugin_name == "abaqus"
        assert entry.metadata == {"priority": 60}

    def test_default_metadata(self) -> None:
        entry = CapabilityEntry(
            capability=Capability.EXPORTER,
            provider=int,
            plugin_name="test",
        )
        assert entry.metadata == {}

    def test_frozen(self) -> None:
        entry = CapabilityEntry(
            capability=Capability.PARSER,
            provider=str,
            plugin_name="test",
        )
        with pytest.raises(AttributeError):
            entry.plugin_name = "changed"  # type: ignore[misc]


class TestCapabilityRegistry:
    """CapabilityRegistry のテスト"""

    def test_register_and_get_all(self) -> None:
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "abaqus", {"priority": 60})
        reg.register(Capability.PARSER, int, "ml", {"priority": 55})

        parsers = reg.get_all(Capability.PARSER)
        assert len(parsers) == 2
        assert parsers[0].plugin_name == "abaqus"
        assert parsers[1].plugin_name == "ml"

    def test_get_all_empty(self) -> None:
        reg = CapabilityRegistry()
        assert reg.get_all(Capability.PARSER) == []

    def test_get_by_plugin(self) -> None:
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "abaqus")
        reg.register(Capability.EXPORTER, int, "abaqus")
        reg.register(Capability.PARSER, float, "ml")

        abaqus = reg.get_by_plugin("abaqus")
        assert Capability.PARSER in abaqus
        assert Capability.EXPORTER in abaqus
        assert len(abaqus[Capability.PARSER]) == 1
        assert len(abaqus[Capability.EXPORTER]) == 1

    def test_get_by_plugin_empty(self) -> None:
        reg = CapabilityRegistry()
        assert reg.get_by_plugin("nonexistent") == {}

    def test_get_plugins(self) -> None:
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "abaqus")
        reg.register(Capability.EXPORTER, int, "obsidian")
        reg.register(Capability.PARSER, float, "abaqus")

        plugins = reg.get_plugins()
        assert plugins == ["abaqus", "obsidian"]

    def test_entry_count(self) -> None:
        reg = CapabilityRegistry()
        assert reg.entry_count == 0

        reg.register(Capability.PARSER, str, "abaqus")
        assert reg.entry_count == 1

        reg.register(Capability.EXPORTER, int, "obsidian")
        assert reg.entry_count == 2

    def test_clear(self) -> None:
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "abaqus")
        reg.register(Capability.EXPORTER, int, "obsidian")
        assert reg.entry_count == 2

        reg.clear()
        assert reg.entry_count == 0
        assert reg.get_plugins() == []

    def test_multiple_capabilities_same_plugin(self) -> None:
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "office")
        reg.register(Capability.EXPORTER, int, "office")
        reg.register(Capability.CLI_COMMAND, float, "office")

        office = reg.get_by_plugin("office")
        assert len(office) == 3

    def test_metadata_preserved(self) -> None:
        reg = CapabilityRegistry()
        meta = {"priority": 60, "format": "inp"}
        reg.register(Capability.PARSER, str, "abaqus", meta)

        entries = reg.get_all(Capability.PARSER)
        assert entries[0].metadata == meta

    def test_get_all_returns_copy(self) -> None:
        """get_all は内部リストのコピーを返す"""
        reg = CapabilityRegistry()
        reg.register(Capability.PARSER, str, "abaqus")

        result = reg.get_all(Capability.PARSER)
        result.clear()  # 外部で変更しても内部に影響しない

        assert len(reg.get_all(Capability.PARSER)) == 1
