# =========================
# CLI (docker寄り) + 旧CLI互換
# main.py から委譲されるCLI本体
#
# CLI層の責務: argparse解析 + 出力整形のみ。
# ビジネスロジックはservices/service/に集約する。
# service以外から直接ロジックをインポートすること、
# 中でロジックを実装することを禁止する。
#
# === 凍結ステータス ===
# submit/list/check/files(f)/旧互換フラグ: 凍結
#   - これらはPhase 3(runコマンド層リモート統合・fileコマンド層)着手まで凍結
#   - graphコマンド系（jj init/parse/show/export/info/diff/credential）が現在のアクティブCLI
#   - runコマンド（jj r）はアクティブ（RunCommandService経由）
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
from services.service.submit import JobListItem, SubmitService, WarningItem

__all__ = [
    "JobListItem",
]

# =========
# 定数
# =========
TOOL_DIRPATH = Path(__file__).resolve().parents[2]


# =========
# SubmitService 遅延初期化
# =========
_submit_service: SubmitService | None = None


def _get_submit_service() -> SubmitService:
    """SubmitServiceを遅延初期化して返す。

    SSH設定ファイルの読み込みをモジュールインポート時ではなく、
    submit系コマンドの実行時に遅延させる。
    これにより、graph系コマンドやrunコマンドなどSSH不要なコマンドが
    SSH設定未構成の環境でも実行可能になる。
    FastAPI等の他エントリポイントからも独立してサービスを構成可能。
    """
    global _submit_service
    if _submit_service is not None:
        return _submit_service

    from config import load_ssh_config

    ssh_config = load_ssh_config()
    ssh_config.require("linux_local_basedirpath")
    base_dirpath = ssh_config.linux_local_basedirpath
    if base_dirpath is None:
        raise ValueError("LINUX_LOCAL_BASEDIRPATHを'.pyssh.yaml'で指定してください。")

    remote_abq_path = ssh_config.remote_abq_path
    if remote_abq_path is None:
        raise ValueError("REMOTE_ABQ_PATHを'.pyssh.yaml'で指定してください。")

    _submit_service = SubmitService(
        base_dirpath=base_dirpath,
        remote_abq_path=remote_abq_path,
        tool_dirpath=TOOL_DIRPATH,
    )
    return _submit_service


# =========
# 新CLI定義
# =========
def _add_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--inp-files", "-fn", nargs="+", help="実行ファイルリストを指定")
    p.add_argument("--index", "-id", nargs="+", help="実行ファイルリストをindex指定")
    p.add_argument("--inp-files-versions", "-v", nargs="+", help="version指定")
    p.add_argument("--all-files", "-all", action="store_true", help="全ファイル選択", default=False)
    p.add_argument(
        "--subdirectory-depth",
        "-subdir",
        type=int,
        default=1,
        help="サブフォルダを考慮する階層 (allオプション有効時のみ有効)",
    )
    p.add_argument(
        "--old-files",
        "-old",
        action="store_true",
        help="バージョンが古いファイルを選択",
    )


def _add_host_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host-name", "-host", default="", type=str, help="グリッド名")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="job")

    # 旧CLI互換フラグ（凍結: Phase 3着手まで変更禁止）
    p.add_argument("--use-gpu", "-g", action="store_true", help="GPUを使用")
    p.add_argument("--no-background", "-nbg", action="store_true", help="wblockを有効化")
    p.add_argument("--jcf", default="abq.jcf", type=str, help="jcfファイル名を指定")
    p.add_argument("--abq-version", "-abqv", default="2023", help="abaqusのversionを指定")
    p.add_argument("--ss-class", "-ss", action="store_true", help="SSクラス")
    p.add_argument("--s-class", "-s", action="store_true", help="Sクラス")
    p.add_argument("--ncpu", "-N", type=int, help="cpu数")
    p.add_argument("--job-name", "-n", type=str, help="ジョブ名")
    p.add_argument("--separate", "-sep", action="store_true", help="別々で実行するか")
    p.add_argument("--job-list", "-ls", action="store_true", help="実行予定一覧表示")
    p.add_argument("--syntax", "-syn", action="store_true", help="syntaxチェック")
    p.add_argument("--get-files", "-get", action="store_true", help="getコマンド")
    p.add_argument("--move-files", "-move", action="store_true", help="moveコマンド")
    p.add_argument("--put-files", "-put", action="store_true", help="putコマンド")
    _add_target_args(p)
    _add_host_args(p)

    sub = p.add_subparsers(dest="cmd")

    # submit（凍結: Phase 3着手まで変更禁止）
    ps = sub.add_parser("submit", help="投入")
    _add_target_args(ps)
    _add_host_args(ps)
    ps.add_argument("--use-gpu", "-g", action="store_true")
    ps.add_argument("--no-background", "-nbg", action="store_true")
    ps.add_argument("--jcf", default="abq.jcf", type=str)
    ps.add_argument("--abq-version", "-abqv", default="2023")
    ps.add_argument("--ss-class", "-ss", action="store_true")
    ps.add_argument("--s-class", "-s", action="store_true")
    ps.add_argument("--ncpu", "-N", type=int)
    ps.add_argument("--job-name", "-n", type=str)
    ps.add_argument("--separate", "-sep", action="store_true")

    # list（凍結: Phase 3着手まで変更禁止）
    pl = sub.add_parser("list", help="予定一覧（dry-run）")
    _add_target_args(pl)

    # check syntax（凍結: Phase 3着手まで変更禁止）
    pc = sub.add_parser("check", help="検査")
    pcsub = pc.add_subparsers(dest="subcmd")
    pcs = pcsub.add_parser("syntax", help="Abaqus inp syntax check")
    _add_target_args(pcs)

    # files（凍結: Phase 3着手まで変更禁止）
    pf = sub.add_parser("f", help="ファイル操作")
    pfsub = pf.add_subparsers(dest="subcmd")
    pfg = pfsub.add_parser("get", help="get")
    _add_target_args(pfg)
    _add_host_args(pfg)
    pfp = pfsub.add_parser("put", help="put")
    _add_target_args(pfp)
    _add_host_args(pfp)
    pfm = pfsub.add_parser("move", help="move to ./old")
    _add_target_args(pfm)

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
        help="実行コマンド（-- 以降に指定）",
    )

    # graph (jj g) — 互換性維持
    add_graph_parser(sub)

    # トップレベルのグラフコマンド (jj init, jj parse, jj show, jj export, jj info)
    add_top_level_graph_commands(sub)

    return p


def normalize_compat(args: argparse.Namespace) -> argparse.Namespace:
    """旧フラグ → 新cmd/subcmdへ写像（以後は args.cmd/args.subcmd だけ見れば良い）"""
    if args.cmd == "f":
        args.cmd = "files"
    if args.cmd == "r":
        args.cmd = "run"
    if args.cmd == "g":
        args.cmd = "graph"
    # トップレベルのグラフコマンド（jj init/parse/show/export/info/credential）
    if args.cmd in (
        "init",
        "parse",
        "show",
        "export",
        "info",
        "diff",
        "credential",
        "dashboard",
        "serve",
    ):
        return args
    if getattr(args, "cmd", None):
        return args

    if getattr(args, "job_list", False):
        args.cmd = "list"
        return args
    if getattr(args, "syntax", False):
        args.cmd = "check"
        args.subcmd = "syntax"
        return args
    if getattr(args, "get_files", False):
        args.cmd = "files"
        args.subcmd = "get"
        return args
    if getattr(args, "put_files", False):
        args.cmd = "files"
        args.subcmd = "put"
        return args
    if getattr(args, "move_files", False):
        args.cmd = "files"
        args.subcmd = "move"
        return args

    # 互換的に「何も指定されなければsubmit」
    args.cmd = "submit"

    return args


# =========
# ターゲット解決（SubmitServiceに委譲）
# =========
def resolve_targets(args: argparse.Namespace) -> list[str]:
    service = _get_submit_service()
    return service.resolve_targets(
        inp_files=getattr(args, "inp_files", None),
        index=getattr(args, "index", None),
        inp_files_versions=getattr(args, "inp_files_versions", None),
        all_files=getattr(args, "all_files", False),
        subdirectory_depth=getattr(args, "subdirectory_depth", 1),
        old_files=getattr(args, "old_files", False),
    )


# =========
# 各コマンド実行（CLI層：出力整形のみ）
# =========
def _print_warnings(warnings: list[WarningItem]) -> None:
    if not warnings:
        return
    print("\n[WARNINGS]")
    for w in warnings:
        print(f"  - {w.target}: {w.message}")


def run_list(targets: list[str]) -> int:
    """listコマンド: SubmitService.list_jobs()に委譲し、結果を出力する"""
    service = _get_submit_service()
    jobs = service.list_jobs(targets)

    if jobs:
        print("Jobs that will be submitted")
        for item in jobs:
            print(f"\t- {item.target}, {item.job_name}")
    else:
        print("NO jobs will be submitted")
    return 0


def run_check_syntax(targets: list[str]) -> int:
    """check syntaxコマンド: SubmitServiceに委譲し、結果を出力する"""
    service = _get_submit_service()
    exit_code, warnings = service.run_check_syntax(targets)
    _print_warnings(warnings)
    return exit_code


def run_files_get(targets: list[str], host_name: str) -> int:
    """files getコマンド: SubmitServiceに委譲し、結果を出力する"""
    service = _get_submit_service()
    exit_code, warnings = service.run_files_get(targets, host_name)
    _print_warnings(warnings)
    return exit_code


def run_files_put(targets: list[str], host_name: str) -> int:
    """files putコマンド: SubmitServiceに委譲し、結果を出力する"""
    service = _get_submit_service()
    exit_code, warnings = service.run_files_put(targets, host_name)
    _print_warnings(warnings)
    return exit_code


def run_files_move(targets: list[str]) -> int:
    """files moveコマンド: SubmitServiceに委譲し、結果を出力する"""
    exit_code, warnings = SubmitService.run_files_move(targets)
    _print_warnings(warnings)
    return exit_code


def run_submit(args: argparse.Namespace, targets: list[str]) -> int:
    """submitコマンド: SubmitServiceに委譲し、結果を出力する"""
    service = _get_submit_service()

    # 投入前のジョブ情報を表示
    print()
    print("############################################")
    if args.host_name:
        print(f"Job @{args.host_name} will be submitted")
    else:
        print("Job will be submitted")
    for i in targets:
        print(f"    - {i}")
    print("############################################")
    print()

    exit_code, warnings = service.submit(
        targets,
        use_gpu=args.use_gpu,
        no_background=args.no_background,
        jcf=args.jcf,
        abq_version=args.abq_version,
        ss_class=args.ss_class,
        s_class=args.s_class,
        ncpu=args.ncpu,
        job_name=args.job_name,
        separate=args.separate,
        host_name=args.host_name,
    )
    _print_warnings(warnings)
    return exit_code


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
    cmd = getattr(args, "cmd", "submit")
    subcmd = getattr(args, "subcmd", None)

    # グラフ系コマンド（SSH設定不要）
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
        "dashboard",
        "serve",
        "config",
    ):
        return run_top_level_graph_command(cmd, args)

    # runコマンド（SSH設定不要）
    if cmd == "run":
        return run_run(args)

    # submit系コマンド（SSH設定必要 — SubmitServiceを遅延初期化）
    targets = resolve_targets(args)

    if cmd == "list":
        return run_list(targets)

    if cmd == "check" and subcmd == "syntax":
        return run_check_syntax(targets)

    if cmd == "files" and subcmd == "get":
        return run_files_get(targets, args.host_name)

    if cmd == "files" and subcmd == "put":
        return run_files_put(targets, args.host_name)

    if cmd == "files" and subcmd == "move":
        return run_files_move(targets)

    # default: submit
    return run_submit(args, targets)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args = normalize_compat(args)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
