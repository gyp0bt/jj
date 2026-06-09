# =========================
# CLI (jjコアコマンド)
# main.py から委譲されるCLI本体
#
# CLI層の責務: argparse解析 + 出力整形のみ。
# ビジネスロジックはservices/service/に集約する。
#
# === アクティブコマンド ===
# - jj init/parse/show/export/info/diff/credential/config: グラフ系
#
# [READMEへ戻る](../../README.md)
# =========================
import argparse
from pathlib import Path

from services.cli.graph import (
    add_graph_parser,
    add_top_level_graph_commands,
    run_graph_command,
    run_top_level_graph_command,
)

__all__: list[str] = []

# =========
# 定数
# =========
TOOL_DIRPATH = Path(__file__).resolve().parents[2]


# =========
# 新CLI定義
# =========
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jj")

    sub = p.add_subparsers(dest="cmd")

    # graph (jj g) — 互換性維持
    add_graph_parser(sub)

    # トップレベルのグラフコマンド (jj init, jj parse, jj show, jj export, jj info)
    add_top_level_graph_commands(sub)

    return p


def normalize_compat(args: argparse.Namespace) -> argparse.Namespace:
    """旧フラグ → 新cmd/subcmdへ写像（以後は args.cmd/args.subcmd だけ見れば良い）"""
    if args.cmd == "g":
        args.cmd = "graph"
    return args


# =========
# 各コマンド実行（CLI層：出力整形のみ）
# =========
def dispatch(args: argparse.Namespace) -> int:
    cmd = getattr(args, "cmd", None)

    # グラフ系コマンド
    if cmd == "graph":
        return run_graph_command(args)
    if cmd in (
        "init",
        "parse",
        "show",
        "export",
        "info",
        "diff",
        "credential",
        "config",
    ):
        return run_top_level_graph_command(cmd, args)

    # 未指定時はヘルプ表示
    print("使用方法: jj <command>")
    print()
    print("コマンド:")
    print("  init        プロジェクト初期化")
    print("  parse       グラフ生成")
    print("  show        グラフ表示")
    print("  export      エクスポート")
    print("  info        ファイル詳細")
    print("  diff        INP差分比較")
    print("  config      設定管理")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args = normalize_compat(args)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
