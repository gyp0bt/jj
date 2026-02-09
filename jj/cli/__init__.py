# =========================
# CLI (docker寄り) + 旧CLI互換
# main.py から委譲されるCLI本体
# =========================
import argparse
import glob
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from config import load_ssh_config
from services.run import RunService
from services.ssh import ssh
from services.parse import (
    get_basename,
    get_index_and_version,
)
from cli.graph import (
    add_graph_parser,
    add_top_level_graph_commands,
    run_graph_command,
    run_top_level_graph_command,
)

# =========
# Config
# =========
ssh_config = load_ssh_config()
ssh_config.require("linux_local_basedirpath")
base_dirpath = ssh_config.linux_local_basedirpath
if base_dirpath is None:
    raise ValueError("LINUX_LOCAL_BASEDIRPATHを'.pyssh.yaml'で指定してください。")

remote_abq_path = ssh_config.remote_abq_path
if remote_abq_path is None:
    raise ValueError("REMOTE_ABQ_PATHを'.pyssh.yaml'で指定してください。")
TOOL_DIRPATH = Path(__file__).resolve().parents[2]


# =========
# 既存関数群
# - run_ps1
# - write_standard_jcf / write_explicit_jcf / write_jcf
# - get_abq_job_name
# - execute / write_jcf_and_execute
# =========


def run_ps1(path: str, *args: str, capture: bool = False) -> str | None:
    if capture:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
    else:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
                *args,
            ],
            stdin=None,
            stdout=None,
            stderr=None,
        )
        return None



def get_abq_job_name(inp_filepath: str | None = None) -> str:
    dirpath = ssh.get_local_linux_filepath(os.getcwd())
    if base_dirpath is None:
        raise ValueError("LINUX_LOCAL_BASEDIRPATHを'.pyssh.yaml'で指定してください。")
    dirpath = (
        dirpath.replace(base_dirpath, "")
        .lower()
        .replace("work", "")
        .replace("idx", "")
        .replace("tests", "")
        .replace("test", "")
        .replace("0", "")
    )
    vals = [i for i in dirpath.split("/") if i != ""]
    vals = [i if len(i) <= 2 else i[:2] for i in vals]
    job_name = "".join(vals)
    if inp_filepath is not None:
        idx, version = get_index_and_version(inp_filepath)
        job_name = job_name + "_" + idx + "." + version
    return job_name


# =========
# 新CLI定義
# =========
def _add_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--inp-files", "-fn", nargs="+", help="実行ファイルリストを指定")
    p.add_argument("--index", "-id", nargs="+", help="実行ファイルリストをindex指定")
    p.add_argument("--inp-files-versions", "-v", nargs="+", help="version指定")
    p.add_argument(
        "--all-files", "-all", action="store_true", help="全ファイル選択", default=False
    )
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

    # 旧CLI互換フラグ（入口として保持）
    p.add_argument("--use-gpu", "-g", action="store_true", help="GPUを使用")
    p.add_argument(
        "--no-background", "-nbg", action="store_true", help="wblockを有効化"
    )
    p.add_argument("--jcf", default="abq.jcf", type=str, help="jcfファイル名を指定")
    p.add_argument(
        "--abq-version", "-abqv", default="2023", help="abaqusのversionを指定"
    )
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

    # submit
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

    # list
    pl = sub.add_parser("list", help="予定一覧（dry-run）")
    _add_target_args(pl)


    # check syntax
    pc = sub.add_parser("check", help="検査")
    pcsub = pc.add_subparsers(dest="subcmd")
    pcs = pcsub.add_parser("syntax", help="Abaqus inp syntax check")
    _add_target_args(pcs)

    # files
    # pf = sub.add_parser("files", help="ファイル操作")
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
    if args.cmd in ("init", "parse", "show", "export", "info", "diff", "credential"):
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
# ターゲット解決（現行ロジックを維持）
# =========
def resolve_targets(args: argparse.Namespace) -> list[str]:
    inp_filepath_list: list[str] = []

    # old_files（現行通り）
    if getattr(args, "old_files", False):
        files = list(glob.glob("./go*.inp"))
        files = [i for i in files if get_index_and_version(i)[1]]
        ver_dict = {i: int(get_index_and_version(i)[1]) for i in files}
        basename_ver_dict: dict[str, tuple[str, int]] = {}
        for filepath, ver_i in ver_dict.items():
            basename = os.path.basename(filepath)[:-4].replace(f"v{ver_i}", "")
            _, ver_b = basename_ver_dict.get(basename, ("", 0))
            if ver_i > ver_b:
                basename_ver_dict[basename] = (filepath, ver_i)
        latest_inp_files = [i[0] for i in basename_ver_dict.values()]
        inp_filepath_list = [
            i for i in list(glob.glob("./go*.inp")) if i not in latest_inp_files
        ]
    else:
        # 明示指定がなければ go*.inp
        if (
            args.inp_files is None
            and args.index is None
            and args.inp_files_versions is None
        ):
            inp_filepath_list = list(glob.glob("./go*.inp"))
        else:
            inp_filepath_list = list(args.inp_files or [])

    # index指定（現行通り）
    if args.index:
        for idx in args.index:
            if ".." in idx:
                s, e = idx.split("..")
                s_i, e_i = int(s), int(e)
                for idx_i in range(s_i, e_i + 1):
                    inp_i = list(glob.glob(f"go_idx{idx_i}*.inp"))
                    inp_filepath_list += inp_i
            else:
                inp_i = list(glob.glob(f"go_idx{idx}*.inp"))
                inp_filepath_list += inp_i

    # version指定（現行通り）
    if args.inp_files_versions:
        if inp_filepath_list:
            inp_filepath_list = [
                i
                for i in inp_filepath_list
                if any([f"v{j}" in i for j in args.inp_files_versions])
            ]
        else:
            for ver in args.inp_files_versions:
                inp_filepath_list += list(glob.glob(f"go_*.v{ver}.inp"))
    elif not getattr(args, "old_files", False):
        # 最新だけ選ぶ（現行通り）
        version_data: dict[str, tuple[int, str]] = {}
        for i in inp_filepath_list:
            vals = i.split(".")
            if len(vals) == 2:
                basename_i = vals[0]
                version_i = 1
            else:
                if vals[-2].startswith("v"):
                    try:
                        version_i = int(vals[-2][1:])
                        basename_i = ".".join(vals[:-2])[1:]
                    except Exception:
                        version_i = 1
                        basename_i = ".".join(vals[:-1])
                else:
                    version_i = 1
                    # basename_i = ".".join(vals)
                    basename_i = get_basename(i)
            old_version, _ = version_data.get(basename_i, (0, ""))
            if old_version < version_i:
                version_data[basename_i] = (version_i, i)
        inp_filepath_list = [i[1] for i in version_data.values()]

    # all_files + depth（現行通り）
    if getattr(args, "all_files", False):
        inp_filepath_list = []
        cwd = "./"
        for _ in range(int(getattr(args, "subdirectory_depth", 1)) + 1):
            inp_filepath_list += glob.glob(f"{cwd}go*.inp")
            cwd += "**/"

    # 正規化（basenameだけに寄せる：現行通り）
    inp_filepath_list = [get_basename(i) + ".inp" for i in inp_filepath_list]
    inp_filepath_list = [i.replace("./", "") for i in inp_filepath_list]

    # unique（順序維持）
    done: set[str] = set()
    out: list[str] = []
    for i in inp_filepath_list:
        if i not in done:
            done.add(i)
            out.append(i)
    return out


# =========
# 各コマンド実行（warning継続）
# =========
@dataclass
class WarningItem:
    target: str
    message: str


def _print_warnings(warnings: list[WarningItem]) -> None:
    if not warnings:
        return
    print("\n[WARNINGS]")
    for w in warnings:
        print(f"  - {w.target}: {w.message}")


def run_list(targets: list[str]) -> int:
    if targets:
        print("Jobs that will be submitted")
        for i in targets:
            print(f"\t- {i}, {get_abq_job_name(i)}")
    else:
        print("NO jobs will be submitted")
    return 0


def run_check_syntax(targets: list[str]) -> int:
    warnings: list[WarningItem] = []
    for i in targets:
        try:
            run_ps1(str(TOOL_DIRPATH / "syn.ps1"), i)
        except Exception as e:
            warnings.append(WarningItem(i, repr(e)))
    _print_warnings(warnings)
    return 0 if not warnings else 1


def run_files_get(targets: list[str], host_name: str) -> int:
    warnings: list[WarningItem] = []
    script = str(TOOL_DIRPATH / "sget-single.ps1")
    for i in targets:
        try:
            script_args = ["-BaseName", i[:-4]]
            if host_name:
                script_args += ["-HostName", f"{host_name}"]
            run_ps1(script, *script_args)
        except Exception as e:
            warnings.append(WarningItem(i, repr(e)))
    _print_warnings(warnings)
    return 0 if not warnings else 1


def run_files_put(targets: list[str], host_name: str) -> int:
    warnings: list[WarningItem] = []
    script = str(TOOL_DIRPATH / "put.ps1")
    try:
        script_args = [i for i in targets]
        if host_name:
            script_args += [host_name]
        run_ps1(script, *script_args)
    except Exception as e:
        warnings.append(WarningItem("(batch)", repr(e)))
    _print_warnings(warnings)
    return 0 if not warnings else 1


def run_files_move(targets: list[str]) -> int:
    warnings: list[WarningItem] = []
    try:
        if not os.path.exists("old"):
            os.mkdir("old")
        for i in targets:
            for j in glob.glob(i[:-4] + ".*"):
                try:
                    if os.path.exists(f"old/{j}"):
                        os.system(f"rm old/{j}")
                    os.system(f"mv {j} old/{j}")
                except Exception as e:
                    warnings.append(WarningItem(j, repr(e)))
    except Exception as e:
        warnings.append(WarningItem("(move)", repr(e)))
    _print_warnings(warnings)
    return 0 if not warnings else 1


# ここはあなたの既存 submit 実装に接続する（write_jcf_and_execute等）
def write_standard_jcf(
    inp_filepath_list: list | list[str],
    jcf_filepath: str,
    job_name: str,
    abq_class: str,
    ncpu: int,
    abq_command_path: str,
) -> None:
    if not isinstance(inp_filepath_list, list):
        inp_filepath_list = [inp_filepath_list]
    with open(jcf_filepath, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("#PBS -q %s\n" % (abq_class))
        f.write(
            "#PBS -l select=1:ncpus=%s:mpiprocs=%s:ngpus=1:abaqus=1\n" % (ncpu, ncpu)
        )
        f.write("#PBS -N %s\n" % (job_name))
        f.write("#PBS -j oe\n")
        f.write("#PBS -m ae\n")
        f.write("\n")
        f.write("CPU=%s\n" % (ncpu))
        for i, ii in enumerate(inp_filepath_list):
            f.write('DATA[%s]="%s"\n' % (i, ii))
        f.write("\n")
        f.write(f'PROG="{abq_command_path}"\n')
        f.write("\n")
        f.write('GPU="/usr1/etc/tools/get_gpu.pl"\n')
        f.write('OPT="double interactive cpus=${CPU} gpus=1 usegpu=${GPU}"\n')
        f.write("\n")
        f.write("cd $PBS_O_WORKDIR\n")
        f.write('SCRATCH_DIR="/scratch/${PBS_JOBID}"\n')
        f.write("for JOB in ${DATA[@]}\n")
        f.write("do\n")
        f.write("cd $PBS_O_WORKDIR\n")
        f.write("echo JOB=[$JOB]\n")
        f.write("$PROG job=${JOB} ${OPT}\n")
        f.write("done\n")


def write_explicit_jcf(
    inp_filepath_list: list | list[str],
    jcf_filepath: str,
    job_name: str,
    abq_class: str,
    ncpu: int,
    abq_command_path: str,
) -> None:
    if not isinstance(inp_filepath_list, list):
        inp_filepath_list = [inp_filepath_list]
    with open(jcf_filepath, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("#PBS -q %s\n" % (abq_class))
        f.write("#PBS -l select=1:ncpus=%s:mpiprocs=%s:abaqus=1\n" % (ncpu, ncpu))
        f.write("#PBS -N %s\n" % (job_name))
        f.write("#PBS -j oe\n")
        f.write("#PBS -m ae\n")
        f.write("\n")
        f.write("CPU=%s\n" % (ncpu))
        for i, ii in enumerate(inp_filepath_list):
            f.write('DATA[%s]="%s"\n' % (i, ii))
        f.write("\n")
        f.write(f'PROG="{abq_command_path}"\n')
        f.write("\n")
        f.write('export MPIRUN_OPTIONS="-cpu_bind=map,v"\n')
        f.write('OPT="double interactive cpus=${CPU}"\n')
        f.write("\n")
        f.write("cd $PBS_O_WORKDIR\n")
        f.write('SCRATCH_DIR="/scratch/${PBS_JOBID}"\n')
        f.write("for JOB in ${DATA[@]}\n")
        f.write("do\n")
        f.write("cd $PBS_O_WORKDIR\n")
        f.write("echo JOB=[$JOB]\n")
        f.write("$PROG job=${JOB} ${OPT}\n")
        f.write("done\n")


def write_jcf(
    use_gpu: bool,
    inp_filepath_list: list | list[str],
    jcf_filepath: str,
    job_name: str,
    abq_class: str,
    ncpu: int,
    abq_command_path: str,
) -> None:
    if use_gpu:
        write_standard_jcf(
            inp_filepath_list, jcf_filepath, job_name, abq_class, ncpu, abq_command_path
        )
    else:
        write_explicit_jcf(
            inp_filepath_list, jcf_filepath, job_name, abq_class, ncpu, abq_command_path
        )


def execute(command: str, jcf_filepath: str, hostname: str | None = None) -> None:
    os.system(f"dos2unix {jcf_filepath}")
    client = ssh.SSHClient([jcf_filepath], setting=ssh.SSH_SETTING(_hostname=hostname))
    client.put()
    client.execute_command(command, cd=True)


def write_jcf_and_execute(
    use_gpu: bool,
    inp_filepath_list: list | list[str],
    jcf_filepath: str,
    job_name: str,
    abq_class: str,
    ncpu: int,
    command: str,
    abq_command_path: str,
    host_name: str,
) -> None:
    write_jcf(
        use_gpu,
        inp_filepath_list,
        jcf_filepath,
        job_name,
        abq_class,
        ncpu,
        abq_command_path,
    )
    print()
    print("############################################")
    if host_name:
        print(f"Job '{job_name}'@{host_name} will be submited")
    else:
        print(f"Job '{job_name}' will be submited")
    print(f"    - class:{abq_class}")
    print(f"    - version:{abq_command_path.split('/')[-1]}")
    print(f"    - ncpu:{ncpu}")
    if use_gpu:
        print("    - use-gpu: True")
    if not isinstance(inp_filepath_list, list):
        inp_filepath_list = [inp_filepath_list]
    for i in inp_filepath_list:
        print(f"    - {i}")
    print("############################################")
    print()
    execute(command, jcf_filepath, host_name)


def run_submit(args: argparse.Namespace, targets: list[str]) -> int:
    warnings: list[WarningItem] = []

    # command
    if args.no_background:
        command = f"qsub -Wblock=true {args.jcf}"
    else:
        command = f"qsub {args.jcf}"

    # class / ncpu（現行通り）
    if args.ss_class:
        abq_class = "ABQSS"
        ncpu = 1
    elif args.s_class:
        abq_class = "ABQS"
        ncpu = 4
    else:
        abq_class = "ABQ"
        ncpu = 8
    if args.ncpu is not None:
        ncpu = int(args.ncpu)

    # abq_command_path（現行通り）
    if args.abq_version is None:
        if remote_abq_path is None:
            raise ValueError("REMOTE_ABQ_PATHを'.pyssh.yaml'で指定してください。")
        abq_command_path = remote_abq_path
    else:
        abq_command_path = f"/usr1/abaqus/Commands/abq{args.abq_version}"

    # separate or batch
    try:
        if args.separate:
            for inp in targets:
                try:
                    job_name = args.job_name if args.job_name else get_abq_job_name(inp)
                    write_jcf_and_execute(
                        use_gpu=args.use_gpu,
                        inp_filepath_list=[inp],
                        jcf_filepath=args.jcf,
                        job_name=job_name,
                        abq_class=abq_class,
                        ncpu=ncpu,
                        command=command,
                        abq_command_path=abq_command_path,
                        host_name=args.host_name,
                    )
                except Exception as e:
                    warnings.append(WarningItem(inp, repr(e)))
        else:
            if len(targets) == 1:
                job_name = (
                    args.job_name if args.job_name else get_abq_job_name(targets[0])
                )
            else:
                job_name = args.job_name if args.job_name else get_abq_job_name()
            write_jcf_and_execute(
                use_gpu=args.use_gpu,
                inp_filepath_list=targets,
                jcf_filepath=args.jcf,
                job_name=job_name,
                abq_class=abq_class,
                ncpu=ncpu,
                command=command,
                abq_command_path=abq_command_path,
                host_name=args.host_name,
            )
    except Exception as e:
        warnings.append(WarningItem("(submit)", repr(e)))

    _print_warnings(warnings)
    return 0 if not warnings else 1


def run_run(args: argparse.Namespace) -> int:
    command = list(getattr(args, "command", []) or [])
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("実行コマンドを指定してください。")
        return 1

    mode = getattr(args, "mode", "auto")
    if mode == "auto":
        mode = None

    cwd = Path(getattr(args, "cwd", ".")).resolve()
    service = RunService()
    result = service.execute(command=command, cwd=cwd, mode=mode)

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
    targets = resolve_targets(args)

    cmd = getattr(args, "cmd", "submit")
    subcmd = getattr(args, "subcmd", None)

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

    if cmd == "run":
        return run_run(args)

    if cmd == "graph":
        return run_graph_command(args)

    # トップレベルのグラフコマンド
    if cmd in ("init", "parse", "show", "export", "info", "diff", "credential"):
        return run_top_level_graph_command(cmd, args)

    # default: submit
    return run_submit(args, targets)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args = normalize_compat(args)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
