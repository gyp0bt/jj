# =========================
# CLI (jjコアコマンド)
# main.py から委譲されるCLI本体
#
# CLI層の責務: argparse解析 + 出力整形のみ。ビジネスロジックは services/service/ に集約する。
# サブコマンドの定義は services/cli/commands.py の COMMANDS レジストリが唯一の地図。
#
# === アクティブコマンド ===
# - jj init/parse/show/export/info/diff/credential/config
#
# [READMEへ戻る](../../README.md)
# =========================
import argparse
from pathlib import Path

from services.cli.commands import COMMANDS, add_commands, run_command

__all__: list[str] = []

# =========
# 定数
# =========
TOOL_DIRPATH = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    """COMMANDS レジストリから jj のトップレベルパーサーを構築する。"""
    p = argparse.ArgumentParser(prog="jj")
    sub = p.add_subparsers(dest="cmd")
    add_commands(sub)
    return p


def _print_help() -> None:
    """コマンド未指定時のヘルプ（COMMANDS から自動生成）。"""
    print("使用方法: jj <command>")
    print()
    print("コマンド:")
    for cmd in COMMANDS:
        print(f"  {cmd.name:<12} {cmd.help}")


def dispatch(args: argparse.Namespace) -> int:
    cmd = getattr(args, "cmd", None)
    if cmd is None:
        _print_help()
        return 0
    return run_command(cmd, args)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
