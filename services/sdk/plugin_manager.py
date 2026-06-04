"""PluginManager — プラグインの発見・登録・ライフサイクル管理

既存の load_all_plugins() を PluginManager クラスとして再構成し、
PluginManifest ベースの新方式と __init_subclass__ ベースの旧方式を統合管理する。

後方互換性:
  - 旧方式（register() が None を返す）のプラグインはそのまま動作
  - 新方式（register() が PluginManifest を返す）のプラグインはメタデータが追加管理される
  - 既存の load_all_plugins() / reset_plugins() も引き続き利用可能

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any

from services.sdk.plugin_manifest import PluginInfo, PluginManifest

logger = logging.getLogger(__name__)


@dataclass
class PluginManager:
    """プラグインの発見・登録・ライフサイクル管理

    Attributes:
        _manifests: マニフェストベースのプラグイン情報
        _legacy_plugins: 旧方式（Manifest なし）のプラグイン名リスト
        _loaded: ロード済みフラグ
    """

    _manifests: dict[str, PluginManifest] = field(default_factory=dict)
    _legacy_plugins: list[str] = field(default_factory=list)
    _loaded: bool = field(default=False, repr=False)

    # 内蔵プラグインモジュール（entry_points が利用できない環境用のフォールバック）
    _BUILTIN_PLUGINS: list[str] = field(
        default_factory=lambda: [
            "services.plugins.abaqus",
            "services.plugins.obsidian",
        ],
        repr=False,
    )

    def load_all(self) -> None:
        """全プラグインを発見・ロードする（1回のみ実行）

        実行順序:
        1. 内蔵プラグインのインポート（フォールバック）
        2. entry_points("jj.plugins") による外部プラグイン発見
        3. 各プラグインの register() 関数を呼び出し
        4. PluginManifest を返すプラグインはメタデータを管理
        """
        if self._loaded:
            return
        self._loaded = True

        # 1. 内蔵プラグインのロード
        self._load_builtin_plugins()

        # 2. entry_points による外部プラグイン発見
        plugins = self._discover_entry_point_plugins("jj.plugins")
        for plugin in plugins:
            if callable(plugin):
                self._invoke_register(plugin)

        # 3. 個別のレジストリグループも発見
        self._discover_entry_point_plugins("jj.parsers")
        self._discover_entry_point_plugins("jj.exporters")

        # 4. マニフェストのライフサイクルフック実行
        for manifest in self._manifests.values():
            if manifest.on_load is not None:
                try:
                    manifest.on_load()
                except Exception as e:
                    logger.warning(f"プラグイン on_load フック失敗: {manifest.name}: {e}")

    def _invoke_register(self, register_fn: Any) -> None:
        """register() 関数を呼び出し、結果に応じて登録方式を分岐する"""
        try:
            result = register_fn()
            if isinstance(result, PluginManifest):
                self._register_manifest(result)
            else:
                # 旧方式: __init_subclass__ で暗黙登録済み
                name = getattr(register_fn, "__module__", str(register_fn))
                # モジュール名からプラグイン名を推定
                parts = name.split(".")
                plugin_name = parts[-2] if len(parts) >= 2 and parts[-1] == "__init__" else parts[-1]
                if plugin_name not in self._legacy_plugins:
                    self._legacy_plugins.append(plugin_name)
                    logger.debug(f"レガシープラグインを登録: {plugin_name}")
        except Exception as e:
            logger.warning(f"プラグインの初期化に失敗: {register_fn}: {e}")

    def _register_manifest(self, manifest: PluginManifest) -> None:
        """PluginManifest を登録する"""
        if manifest.name in self._manifests:
            logger.warning(f"プラグイン名が重複: {manifest.name}（上書き）")
        self._manifests[manifest.name] = manifest
        logger.debug(f"マニフェストプラグインを登録: {manifest.name} v{manifest.version}")

    def _load_builtin_plugins(self) -> None:
        """内蔵プラグインをインポートして自動登録を発動させる"""
        for module_name in self._BUILTIN_PLUGINS:
            try:
                mod = importlib.import_module(module_name)
                # register() 関数があれば呼び出して Manifest を検査
                register_fn = getattr(mod, "register", None)
                if register_fn is not None and callable(register_fn):
                    self._invoke_register(register_fn)
                else:
                    logger.debug(f"内蔵プラグインをロード（register なし）: {module_name}")
            except ImportError as e:
                logger.debug(f"内蔵プラグインのロードをスキップ: {module_name}: {e}")
            except Exception as e:
                logger.warning(f"内蔵プラグインのロードに失敗: {module_name}: {e}")

    def _discover_entry_point_plugins(self, group: str) -> list[Any]:
        """entry_points グループからプラグインを発見・ロードする"""
        loaded = []
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group=group)

            for ep in eps:
                try:
                    obj = ep.load()
                    loaded.append(obj)
                    logger.debug(f"プラグイン発見: {group}::{ep.name} -> {ep.value}")
                except Exception as e:
                    logger.warning(f"プラグインのロードに失敗: {group}::{ep.name}: {e}")
        except Exception as e:
            logger.debug(f"entry_points({group})の発見に失敗: {e}")

        return loaded

    # === 公開クエリAPI ===

    def get_manifest(self, name: str) -> PluginManifest | None:
        """指定プラグインのマニフェストを取得する"""
        return self._manifests.get(name)

    def get_all_manifests(self) -> dict[str, PluginManifest]:
        """全マニフェストを返す"""
        return dict(self._manifests)

    def get_plugins(self) -> list[PluginInfo]:
        """ロード済みプラグインの情報一覧を返す"""
        result: list[PluginInfo] = []

        # マニフェストベース
        for manifest in self._manifests.values():
            capabilities = []
            if manifest.parsers:
                capabilities.append("parsers")
            if manifest.exporters:
                capabilities.append("exporters")
            if manifest.cli_commands:
                capabilities.append("cli_commands")
            if manifest.api_routes:
                capabilities.append("api_routes")

            result.append(
                PluginInfo(
                    name=manifest.name,
                    version=manifest.version,
                    description=manifest.description,
                    capabilities=capabilities,
                    has_manifest=True,
                )
            )

        # レガシープラグイン
        for name in self._legacy_plugins:
            result.append(
                PluginInfo(
                    name=name,
                    version="unknown",
                    description="",
                    capabilities=[],
                    has_manifest=False,
                )
            )

        return result

    def is_loaded(self, name: str) -> bool:
        """指定プラグインがロード済みかどうか"""
        return name in self._manifests or name in self._legacy_plugins

    def reset(self) -> None:
        """全状態をリセットする（テスト用）"""
        # アンロードフック実行
        for manifest in self._manifests.values():
            if manifest.on_unload is not None:
                try:
                    manifest.on_unload()
                except Exception as e:
                    logger.warning(f"プラグイン on_unload フック失敗: {manifest.name}: {e}")

        self._manifests.clear()
        self._legacy_plugins.clear()
        self._loaded = False

    @property
    def plugin_count(self) -> int:
        """ロード済みプラグイン総数"""
        return len(self._manifests) + len(self._legacy_plugins)
