"""CLICommand — プラグインによるCLIサブコマンド拡張ポイント

プラグインがCLIサブコマンドを宣言的に追加するための定義。
PluginManifest の cli_commands フィールドにモジュールパスを指定し、
各モジュールが get_cli_commands() 関数で CLICommand リストを返す。

使用例:
    # services/plugins/abaqus/cli.py
    from services.sdk.cli_extension import CLICommand

    def get_cli_commands() -> list[CLICommand]:
        return [
            CLICommand(
                name="submit",
                help="Abaqusジョブを投入する",
                handler=handle_submit,
                add_arguments=add_submit_args,
                parent="root",
            ),
        ]

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CLICommand:
    """プラグインが提供するCLIサブコマンド定義

    Attributes:
        name: コマンド名（例: "submit"）
        help: ヘルプ文字列
        handler: 実行関数。(app: JJApp, args: argparse.Namespace) -> int を想定
        add_arguments: argparse.ArgumentParser に引数を追加する関数（オプション）
        parent: 親コマンド（"root" でトップレベル、サブコマンドグループ名も指定可能）
        aliases: コマンドエイリアス（オプション）
        metadata: 追加メタデータ
    """

    name: str
    help: str
    handler: Callable[..., int | None]
    add_arguments: Callable[..., None] | None = None
    parent: str = "root"
    aliases: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


def collect_cli_commands(module_paths: list[str]) -> list[CLICommand]:
    """指定モジュールパスからCLICommandを収集する

    各モジュールの get_cli_commands() 関数を呼び出し、
    返された CLICommand リストを集約する。

    Args:
        module_paths: CLICommand定義モジュールのパスリスト

    Returns:
        収集された CLICommand のリスト
    """
    import importlib
    import logging

    logger = logging.getLogger(__name__)
    commands: list[CLICommand] = []

    for path in module_paths:
        try:
            mod = importlib.import_module(path)
            getter = getattr(mod, "get_cli_commands", None)
            if getter is not None and callable(getter):
                result = getter()
                if isinstance(result, list):
                    commands.extend(result)
                else:
                    logger.warning(f"get_cli_commands() がリストを返さなかった: {path}")
            else:
                logger.debug(f"get_cli_commands() が見つからない: {path}")
        except ImportError as e:
            logger.debug(f"CLIコマンドモジュールのインポートをスキップ: {path}: {e}")
        except Exception as e:
            logger.warning(f"CLIコマンドの収集に失敗: {path}: {e}")

    return commands
