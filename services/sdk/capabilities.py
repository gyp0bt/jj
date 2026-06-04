"""CapabilityRegistry — 拡張ポイントの型安全な管理

既存の _parser_registry, _exporter_registry を統合的に管理するメタデータレジストリ。

既存レジストリとの互換性を維持しつつ、「どのプラグインが何を提供しているか」を
横断的に問い合わせ可能にする。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Capability(Enum):
    """プラグインが提供できる拡張ポイント"""

    PARSER = auto()
    EXPORTER = auto()
    CLI_COMMAND = auto()
    API_ROUTE = auto()
    EVENT_HANDLER = auto()
    CONFIG_SECTION = auto()


@dataclass(frozen=True)
class CapabilityEntry:
    """レジストリ登録エントリ

    Attributes:
        capability: 拡張ポイントの種類
        provider: 実際のクラスまたは関数
        plugin_name: 提供元プラグイン名
        metadata: 追加メタデータ（priority, format名等）
    """

    capability: Capability
    provider: type | Callable[..., Any]
    plugin_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityRegistry:
    """プラグインが提供する機能の統合レジストリ

    既存の _parser_registry, _exporter_registry を統合的に管理する。
    既存レジストリとの互換性を維持しつつ、メタデータを付加する。
    """

    _entries: dict[Capability, list[CapabilityEntry]] = field(default_factory=dict)

    def register(
        self,
        capability: Capability,
        provider: type | Callable[..., Any],
        plugin_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """拡張ポイントを登録する

        Args:
            capability: 拡張ポイントの種類
            provider: 実際のクラスまたは関数
            plugin_name: 提供元プラグイン名
            metadata: 追加メタデータ
        """
        entry = CapabilityEntry(
            capability=capability,
            provider=provider,
            plugin_name=plugin_name,
            metadata=metadata or {},
        )
        if capability not in self._entries:
            self._entries[capability] = []
        self._entries[capability].append(entry)

    def get_all(self, capability: Capability) -> list[CapabilityEntry]:
        """特定の拡張ポイントの登録済み一覧を返す

        Args:
            capability: 取得する拡張ポイントの種類

        Returns:
            該当する CapabilityEntry のリスト
        """
        return list(self._entries.get(capability, []))

    def get_by_plugin(self, plugin_name: str) -> dict[Capability, list[CapabilityEntry]]:
        """プラグイン名で登録済み機能をグループ化して返す

        Args:
            plugin_name: プラグイン名

        Returns:
            Capability → CapabilityEntry リストの辞書
        """
        result: dict[Capability, list[CapabilityEntry]] = {}
        for cap, entries in self._entries.items():
            matching = [e for e in entries if e.plugin_name == plugin_name]
            if matching:
                result[cap] = matching
        return result

    def get_plugins(self) -> list[str]:
        """登録済みプラグイン名の一覧を返す（重複なし）

        Returns:
            プラグイン名のリスト
        """
        names: set[str] = set()
        for entries in self._entries.values():
            for entry in entries:
                names.add(entry.plugin_name)
        return sorted(names)

    @property
    def entry_count(self) -> int:
        """登録済みエントリの総数"""
        return sum(len(entries) for entries in self._entries.values())

    def clear(self) -> None:
        """全エントリをクリアする（テスト用）"""
        self._entries.clear()
