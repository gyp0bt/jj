"""イベント定義 — コア⇔プラグイン間の疎結合通信用

コアやプラグインが発行するイベントの型定義。
EventBus の subscribe/publish で使用する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    """基底イベント

    Attributes:
        source: 発行元プラグイン名 or "core"
    """

    source: str


@dataclass(frozen=True)
class GraphParsed(Event):
    """グラフパース完了イベント

    Attributes:
        node_count: パース後のノード数
        relation_count: パース後のリレーション数
        full_mode: フルモードでパースしたかどうか
    """

    node_count: int = 0
    relation_count: int = 0
    full_mode: bool = False


@dataclass(frozen=True)
class GraphExported(Event):
    """グラフエクスポート完了イベント

    Attributes:
        format: エクスポート形式
        output_path: 出力先パス
    """

    format: str = ""
    output_path: str = ""


@dataclass(frozen=True)
class PluginLoaded(Event):
    """プラグインロード完了イベント

    Attributes:
        plugin_name: プラグイン名
        capabilities: 提供機能カテゴリのリスト
    """

    plugin_name: str = ""
    capabilities: list[str] = field(default_factory=list)
