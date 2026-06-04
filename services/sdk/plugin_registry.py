"""プラグイン動的発見・登録メカニズム

entry_points（pyproject.tomlベース）を使用して、外部プラグインパッケージを
動的に発見・ロードする。各プラグインはentry_pointで指定されたモジュールを
importすることで、__init_subclass__による自動登録が発動する。

## entry_pointグループ

| グループ | 説明 | 登録先 |
|----------|------|--------|
| `jj.plugins` | プラグインパッケージ全体のエントリ | 各プラグインの__init__.py |
| `jj.parsers` | AbstractFileParserサブクラス | _parser_registry |
| `jj.exporters` | AbstractExporterサブクラス | _exporter_registry |

## 使用例

### pyproject.toml（外部プラグインパッケージ）

```toml
[project.entry-points."jj.plugins"]
abaqus = "jj_abaqus:register"

[project.entry-points."jj.parsers"]
abaqus_inp = "jj_abaqus.parsers.inp_parser"
abaqus_result = "jj_abaqus.parsers.result_parser"
```

### 内蔵プラグイン（jj本体のpyproject.toml）

```toml
[project.entry-points."jj.plugins"]
abaqus = "services.plugins.abaqus:register"
obsidian = "services.plugins.obsidian:register"
```

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import importlib
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

# プラグインがロード済みかどうかを追跡
_plugins_loaded: bool = False

# 内蔵プラグインの登録関数リスト（entry_pointsが利用できない環境用のフォールバック）
_BUILTIN_PLUGINS: list[str] = [
    "services.plugins.abaqus",
    "services.plugins.obsidian",
]


def discover_entry_point_plugins(group: str) -> list[Any]:
    """entry_pointsグループからプラグインモジュールを発見・ロードする

    Args:
        group: entry_pointsグループ名（例: "jj.plugins", "jj.parsers"）

    Returns:
        ロードされたentry_pointオブジェクトのリスト
    """
    loaded = []
    try:
        if sys.version_info >= (3, 12) or sys.version_info >= (3, 10):
            from importlib.metadata import entry_points

            eps = entry_points(group=group)
        else:
            from importlib.metadata import entry_points

            all_eps = entry_points()
            eps = all_eps.get(group, [])

        for ep in eps:
            try:
                obj = ep.load()
                loaded.append(obj)
                logger.debug(f"プラグイン発見: {group}::{ep.name} -> {ep.value}")
            except Exception as e:
                logger.warning(f"プラグインのロードに失敗: {group}::{ep.name}: {e}")
    except Exception as e:
        logger.debug(f"entry_points({group})の発見に失敗（正常動作の可能性あり）: {e}")

    return loaded


def _load_builtin_plugins() -> None:
    """内蔵プラグインをインポートして自動登録を発動させる

    entry_pointsが利用できない開発環境（pip install -e なし）でも
    内蔵のAbaqus/Obsidianプラグインが動作するようにするフォールバック。
    """
    for module_name in _BUILTIN_PLUGINS:
        try:
            importlib.import_module(module_name)
            logger.debug(f"内蔵プラグインをロード: {module_name}")
        except ImportError as e:
            logger.debug(f"内蔵プラグインのロードをスキップ: {module_name}: {e}")
        except Exception as e:
            logger.warning(f"内蔵プラグインのロードに失敗: {module_name}: {e}")


def load_all_plugins() -> None:
    """全プラグインを発見・ロードする（1回のみ実行）

    実行順序:
    1. 内蔵プラグインのインポート（フォールバック）
    2. entry_points("jj.plugins")による外部プラグイン発見
    3. 各プラグインのregister()関数を呼び出し

    この関数は冪等性を持つ（複数回呼んでも2回目以降は何もしない）。
    """
    global _plugins_loaded
    if _plugins_loaded:
        return
    _plugins_loaded = True

    # 1. 内蔵プラグインのロード（Abaqus/Obsidian）
    _load_builtin_plugins()

    # 2. entry_pointsによる外部プラグイン発見
    plugins = discover_entry_point_plugins("jj.plugins")
    for plugin in plugins:
        if callable(plugin):
            try:
                plugin()  # register()関数を呼び出し
            except Exception as e:
                logger.warning(f"プラグインの初期化に失敗: {plugin}: {e}")

    # 3. 個別のレジストリグループも発見（外部プラグインが個別登録する場合）
    discover_entry_point_plugins("jj.parsers")
    discover_entry_point_plugins("jj.exporters")


def reset_plugins() -> None:
    """プラグインのロード状態をリセットする（テスト用）"""
    global _plugins_loaded
    _plugins_loaded = False
