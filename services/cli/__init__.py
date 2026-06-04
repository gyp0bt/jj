# =========================
# CLI (jjコアコマンド)
# main.py から委譲されるCLI本体
#
# CLI層の責務: argparse解析 + 出力整形のみ。
# ビジネスロジックはservices/service/に集約する。
#
# === アクティブコマンド ===
# - jj init/parse/show/export/info/diff/credential/dashboard/config: グラフ系
# - jj run (jj r): コマンド実行+ログ
#
# [READMEへ戻る](../../README.md)
# =========================
import argparse
import sys
from pathlib import Path

from services.cli.graph import (
    add_graph_parser,
    add_top_level_graph_commands,
    run_graph_command,
    run_top_level_graph_command,
)
from services.service.run_command import RunCommandService

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

    # run (jj r) — コマンド実行+ログ
    pr = sub.add_parser("r", aliases=["run"], help="コマンド実行とログ記録")
    pr.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "script", "job"],
        help="実行モード（autoで自動判定）",
    )
    pr.add_argument("--cwd", default=".", help="実行ディレクトリ")
    pr.add_argument(
        "--no-parse",
        action="store_true",
        default=False,
        help="実行後のparse自動実行をスキップ",
    )
    pr.add_argument(
        "--show-properties",
        action="store_true",
        default=False,
        help="コマンドのプロパティを実行せずに表示（dry-run）",
    )
    pr.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="実行コマンド（--は不要。例: jj r python script.py arg1）",
    )

    # graph (jj g) — 互換性維持
    add_graph_parser(sub)

    # トップレベルのグラフコマンド (jj init, jj parse, jj show, jj export, jj info)
    add_top_level_graph_commands(sub)

    return p


def normalize_compat(args: argparse.Namespace) -> argparse.Namespace:
    """旧フラグ → 新cmd/subcmdへ写像（以後は args.cmd/args.subcmd だけ見れば良い）"""
    if args.cmd == "r":
        args.cmd = "run"
    if args.cmd == "g":
        args.cmd = "graph"
    return args


# =========
# 各コマンド実行（CLI層：出力整形のみ）
# =========
def run_run(args: argparse.Namespace) -> int:
    """runコマンド: RunCommandServiceに委譲し、結果を出力する"""
    command = list(getattr(args, "command", []) or [])
    mode = getattr(args, "mode", "auto")
    cwd = getattr(args, "cwd", ".")
    no_parse = getattr(args, "no_parse", False)
    show_properties = getattr(args, "show_properties", False)

    service = RunCommandService()

    # --show-properties: プロパティ抽出のみ（実行しない）
    if show_properties:
        from pathlib import Path

        from services.run import RunService

        rs = RunService()
        props = rs.show_properties(command, cwd=Path(cwd))
        if props:
            print("properties:")
            for key, value in props.items():
                print(f"  - {key}: {value}")
        else:
            print("プロパティが見つかりません。")
        return 0

    try:
        result = service.execute(command=command, cwd=cwd, mode=mode, no_parse=no_parse)
    except ValueError as e:
        print(str(e))
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    log_path = str(result.log_path) if result.log_path else "なし"
    print(
        "[jj run]"
        f" exit_code={result.exit_code}"
        f" mode={result.mode}"
        f" duration={result.duration_seconds:.2f}s"
        f" user={result.user}"
        f" host={result.host}"
        f" log={log_path}"
    )
    if result.script_path:
        print(f"script_path: {result.script_path}")
    if result.trace_files:
        print("trace_files:")
        for path in result.trace_files:
            print(f"  - {path}")
    if result.properties:
        print("properties:")
        for key, value in result.properties.items():
            print(f"  - {key}: {value}")

    return result.exit_code


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
        "jobs",
        "credential",
        "config",
    ):
        return run_top_level_graph_command(cmd, args)

    # runコマンド
    if cmd == "run":
        return run_run(args)

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
    print("  jobs        ジョブ（RUN）一覧")
    print("  run (r)     コマンド実行+ログ")
    print("  config      設定管理")
    return 0


def main() -> int:
    parser = build_parser()
    args, remaining = parser.parse_known_args()
    # run コマンドの場合: 未認識引数をコマンドに追加（-- 不要化）
    if getattr(args, "cmd", "") in ("r", "run") and remaining:
        existing_cmd = list(getattr(args, "command", []) or [])
        args.command = existing_cmd + remaining
    args = normalize_compat(args)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
