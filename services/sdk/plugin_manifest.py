"""PluginManifest — プラグインの宣言的メタデータ

プラグインが「何を提供するか」を明示的に宣言するための frozen dataclass。
entry_points の register() 関数からこのオブジェクトを返すことで、
PluginManager がプラグインの能力を把握する。

既存の __init_subclass__ パターンとの共存:
  - PluginManifest は「何が登録されるか」のメタデータを提供するのみ
  - 実際の登録メカニズム（__init_subclass__）は変更しない
  - register() が PluginManifest を返さない既存プラグインも動作し続ける

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PluginManifest:
    """プラグインの宣言的メタデータ

    Attributes:
        name: 一意識別子（例: "abaqus"）
        version: プラグインバージョン
        description: 説明文
        parsers: パーサーモジュールパスのリスト
        exporters: エクスポーターモジュールパスのリスト
        dashboard_pages: ダッシュボードコネクターモジュールパスのリスト
        cli_commands: CLIサブコマンド拡張モジュールパスのリスト
        api_routes: APIルート拡張モジュールパスのリスト
        depends_on: 依存プラグイン名のリスト
        optional_dependencies: オプション依存 {パッケージ名: pip名}
        config_schema: プラグイン固有設定のJSONスキーマ
        on_load: プラグインロード時に実行されるフック
        on_unload: プラグインアンロード時に実行されるフック
    """

    # === 識別 ===
    name: str
    version: str = "0.0.0"
    description: str = ""

    # === 提供機能 (Capabilities) ===
    parsers: list[str] = field(default_factory=list)
    exporters: list[str] = field(default_factory=list)
    dashboard_pages: list[str] = field(default_factory=list)
    cli_commands: list[str] = field(default_factory=list)
    api_routes: list[str] = field(default_factory=list)

    # === 依存関係 ===
    depends_on: list[str] = field(default_factory=list)
    optional_dependencies: dict[str, str] = field(default_factory=dict)

    # === 設定 ===
    config_schema: dict[str, Any] = field(default_factory=dict)

    # === ライフサイクルフック ===
    on_load: Callable[[], None] | None = field(default=None, compare=False, hash=False)
    on_unload: Callable[[], None] | None = field(default=None, compare=False, hash=False)


@dataclass(frozen=True)
class PluginInfo:
    """ロード済みプラグインの情報（外部公開用）

    Attributes:
        name: プラグイン名
        version: バージョン
        description: 説明文
        capabilities: 提供機能カテゴリのリスト
        has_manifest: マニフェストベースかどうか
    """

    name: str
    version: str = "0.0.0"
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    has_manifest: bool = False
