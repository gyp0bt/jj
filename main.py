# =========================
# CLI (docker寄り) + 旧CLI互換
# =========================
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config import VocabConfig, load_ssh_config, load_vocab_config
from services.run import RunService
from services.ssh import ssh
import yaml

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
TOOL_DIRPATH = Path(__file__).parents[0]


# =========
# 既存関数群（ここはあなたの現状のまま置いてOK）
# - run_ps1
# - write_standard_jcf / write_explicit_jcf / write_jcf
# - get_abq_job_name
# - execute / write_jcf_and_execute
# - get_index_and_version
# - get_properties_by_inp_filepath
# - get_properties_by_inp_parameter
# - update_go_base
# - update_frontmatter_props
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


def get_index_and_version(inp_filepath: str) -> tuple[str, str]:
    if os.path.isdir(inp_filepath):
        return "", ""
    if inp_filepath.endswith(".py"):
        return "", ""

    inp_filepath, ext = get_basename_with_ext(inp_filepath)
    head = inp_filepath.split("_")[0]
    inp_filepath = inp_filepath[len(head) + 1 :]

    # idx
    if inp_filepath.startswith("idx"):
        idx = inp_filepath.split(".")[0].split("_")[0].replace("idx", "")
    else:
        idx = ""

    # ver
    basename = inp_filepath.replace(ext, "")
    if basename.split(".")[-1].startswith("v"):
        version = basename.split(".")[-1].replace("v", "")
    else:
        version = ""

    return idx, version


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


def update_go_base(go_base: Path, keys: list[str]) -> None:
    with go_base.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    order: list[str] = data["views"][0].get("order", [])
    default_order = [
        "file.name",
        "idx",
        "ver",
        "success",
        "active",
        "description",
        "file.links",
    ]
    order = [i for i in default_order if i in order]
    ignore_keys = ["includes"]

    def reorder_keys(keys: list[str]) -> list[str]:
        front = [
            k for k in ("file.name", "idx", "ver", "success", "active") if k in keys
        ]
        back = [k for k in ("description", "file.links") if k in keys]
        middle = [k for k in keys if k not in set(front + back)]
        return front + middle + back

    keys = [i for i in keys if i not in default_order]
    order = order + keys
    order = [i for i in order if i not in ignore_keys]
    order = list(set(order))

    data["views"][0]["order"] = reorder_keys(order)
    with go_base.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def write_frontmatter_props(
    md_path: Path,
    base_name: str,
    all_basename_list: list[str],
    props: dict[str, str],
    includes: list[str] | None = None,
) -> None:
    """mdファイルを完全上書きで生成する。

    - props は frontmatter にそのまま出力する。
    - includes は frontmatter の list として出力する（[[...]] 形式）。
    - 本文は true_filepath へのリンクのみを置く（必要なら増やす）。
    """
    includes = [] if includes is None else list(includes)

    ver = props.get("ver", "")
    basename = md_path.name.removesuffix(".md")
    basename, ext = get_basename_with_ext(basename)
    # print(basename, ext)
    basename = basename + ext

    # base_name の補正（既存ロジック踏襲）
    if base_name == "go.base" and ver:
        base_name = basename.replace(f".v{ver}", "") + ".base"
        # base_name = ".".join(basename.replace("v" + ver, "").split(".")[:-1]) + ".base"

    # 親 include を決める（既存ロジック踏襲 + 安定化）
    try:
        if ver == "" or int(ver) == 1:
            parent = base_name
        else:
            parent_path_list = [
                basename.replace("v" + ver, "v" + str(int(ver) - 1)),
                basename.replace("v" + ver, ""),
            ]
            all_basename_list_i = [i for i in all_basename_list if i != basename]
            parent = base_name
            for parent_path in parent_path_list:
                if parent_path in all_basename_list_i:
                    parent = parent_path
                    break
    except Exception:
        # verが1-2とかふざけた名前をしていたらよける
        parent = base_name

    # includes の先頭に parent を入れる（重複排除しつつ順序維持）
    merged_includes: list[str] = []
    seen: set[str] = set()

    def _add_include(name: str) -> None:
        if name and name not in seen:
            merged_includes.append(name)
            seen.add(name)

    _add_include(parent)
    for inc in includes:
        _add_include(inc)

    # true filepath の生成（既存ロジック踏襲）

    true_filepath = (
        "_".join(basename.split("_")[:-1]) + "_" + basename.split("_")[-1]
        if "_" in basename
        else basename
    )
    match base_name:
        case "tools.base":
            true_filepath = "tools/" + true_filepath
        case "reports.base":
            true_filepath = "reports/" + true_filepath
        case "docs.base":
            true_filepath = "docs/" + true_filepath

    # frontmatter（完全上書き）
    fm_lines: list[str] = ["---"]
    fm_lines.extend([f"{k}: {v}" for k, v in props.items()])

    # includes を frontmatter の list で正規化して出す
    if merged_includes:
        fm_lines.append("includes:")
        for inc in merged_includes:
            fm_lines.append(f"  - [[{inc}]]")

    fm_lines.append("---")
    if merged_includes:
        for inc in merged_includes:
            fm_lines.append(f"- [[{inc}]]")

    # 本文：リンクだけ置く（あなたの既存の意図を尊重）
    body_lines: list[str] = [f"- [[{true_filepath}]]", ""]

    text = "\n".join(fm_lines) + "\n" + "\n".join(body_lines)
    md_path.write_text(text, encoding="utf-8")


def update_frontmatter_props(
    md_path: Path,
    props: dict[str, str],
    includes: list[str] | None = None,
    include_key: str = "includes",
) -> None:
    """frontmatterを更新する。

    - props は既存キーも含めて上書きする。
    - includes が与えられた場合、frontmatter の includes(list) に [[...]] 形式で追記する。
      既存順序は維持しつつ、新規だけ末尾に追加し、重複は排除する。
    """
    text = md_path.read_text(encoding="utf-8", errors="ignore")

    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        return

    fm_body = m.group(1)
    fm: dict[str, str] = {}

    include_links_existing: list[str] = []
    include_links_set: set[str] = set()
    include_key_present_as_list = False

    # 既存frontmatterを素朴にパース（方針維持）
    lines = fm_body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue

        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        fm[k] = v

        # includes:
        #   - [[...]]
        if includes is not None and k == include_key and v == "":
            include_key_present_as_list = True
            j = i + 1
            while j < len(lines):
                t = lines[j].rstrip()
                if not t.startswith("  - "):
                    break
                item = t[4:].strip()
                if item and item not in include_links_set:
                    include_links_existing.append(item)
                    include_links_set.add(item)
                j += 1
            i = j
            continue

        # includes: [[...]] みたいな単行を拾いたいなら（素朴に対応）
        if includes is not None and k == include_key and v:
            # そのまま1要素として扱う（必要ならここで厳密化）
            if v not in include_links_set:
                include_links_existing.append(v)
                include_links_set.add(v)

        i += 1

    updated = False

    # props は常に上書き
    for k, v in props.items():
        if fm.get(k) != v:
            fm[k] = v
            updated = True

    # includes 追加（順序維持 + 新規末尾追記）
    include_links_new: list[str] = []
    if includes:
        for inc in includes:
            md_name = f"{inc}.md" if not inc.lower().endswith(".md") else inc
            link = f"[[{md_name}]]"
            if link not in include_links_set:
                include_links_new.append(link)
                include_links_set.add(link)

        if include_links_new:
            updated = True

    if not updated:
        return

    # 再構築：includes は末尾に list で出す
    out_lines: list[str] = ["---"]

    for k, v in fm.items():
        if includes is not None and k == include_key:
            continue
        out_lines.append(f"{k}: {v}")

    if includes is not None:
        merged = include_links_existing + include_links_new
        # 元々 list だった / 何か要素がある / 単行だったものを正規化、のいずれかで出す
        if include_key_present_as_list or merged:
            out_lines.append(f"{include_key}:")
            for item in merged:
                out_lines.append(f"  - {item}")

    out_lines.append("---")

    new_fm = "\n".join(out_lines) + "\n"
    new_text = new_fm + text[m.end() :]
    md_path.write_text(new_text, encoding="utf-8")


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
    p.add_argument(
        "--make-index-md-files", "-make", action="store_true", help="notes生成"
    )
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

    # notes
    # pn = sub.add_parser("notes", help="Obsidian notes生成/更新")
    pn = sub.add_parser("n", help="Obsidian notes生成/更新")
    _add_target_args(pn)
    pn.add_argument("--root", default="notes", help="notesルート（default: notes）")
    pn.add_argument("--base-path", default="", help="未指定なら <root>/bases を使う")
    pn.add_argument("--notes-dir", default="", help="未指定なら <root>/props を使う")
    pn.add_argument(
        "--allow-duplicated", action="store_true", help="ファイル名の重複を許す"
    )
    pn.add_argument(
        "--overwrite-props", action="store_false", help="既存のpropsを削除する"
    )
    pn.add_argument(
        "--overwrite-bases", action="store_false", help="既存のbasesを削除する"
    )

    pnsub = pn.add_subparsers(dest="subcmd")
    pni = pnsub.add_parser("init", help="notesツリーとbaseテンプレ生成")
    pni.add_argument("--root", default="notes")

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

    return p


def normalize_compat(args: argparse.Namespace) -> argparse.Namespace:
    """旧フラグ → 新cmd/subcmdへ写像（以後は args.cmd/args.subcmd だけ見れば良い）"""
    if args.cmd == "n":
        args.cmd = "notes"
    if args.cmd == "f":
        args.cmd = "files"
    if args.cmd == "r":
        args.cmd = "run"
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
    if getattr(args, "make_index_md_files", False):
        args.cmd = "notes"
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


# ---------- baseテンプレ生成 ----------
def _base_template(
    folder: Path,
    ver: bool = True,
    idx: bool = True,
    active: bool = True,
    show_only_active: bool = True,
    additional_filters: Optional[list[str]] = None,
) -> dict:
    order = ["file.name", "idx", "ver", "success", "description", "file.links"]
    if not ver:
        order = [i for i in order if i != "ver"]
    if not idx:
        order = [i for i in order if i != "idx"]
    if not active:
        order.append("active")

    if additional_filters is None:
        additional_filters = []
    filters = [
        f'file.folder == "{str(folder).replace("\\", "/")}"',
        'file.fullname.endsWith(".md")',
    ]
    if show_only_active:
        filters += ["active == true"]
    filters += additional_filters

    template = {
        "views": [
            {
                "type": "table",
                "name": "Table",
                "filters": {"and": filters},
                "order": order,
                "sort": [
                    {"property": "tmp", "direction": "ASC"},
                    {"property": "idx", "direction": "ASC"},
                    {"property": "ver", "direction": "ASC"},
                ],
            }
        ]
    }
    return template


def _write_yaml_if_missing(path: Path, data: dict, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        return
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def get_basename_with_ext(filepath: str) -> tuple[str, str]:
    org = filepath
    filepath, ext = normalize_extension_to_inp(filepath)
    if ext:
        filepath = filepath[:-4]
    filepath = filepath.split("/")[-1].split("\\")[-1]
    return filepath, ext


def get_basename(filepath: str) -> str:
    filepath, _ = get_basename_with_ext(filepath)
    return filepath


def init_notes_tree(root: Path, init_bases: bool = True) -> None:
    if init_bases:
        obsidian_config_path = Path(".obsidian")
        if not obsidian_config_path.exists():
            (Path(".obsidian")).mkdir(parents=True, exist_ok=True)
            json_filepath = str(
                Path(__file__).parent.absolute() / ".obsidian" / "*.json"
            )
            for i in glob.glob(json_filepath):
                os.system(f"cp {i} .obsidian/")
        # notes/
        (root).mkdir(parents=True, exist_ok=True)
        (root / "bases").mkdir(parents=True, exist_ok=True)
        (root / "bases" / "go").mkdir(parents=True, exist_ok=True)
        (root / "daily").mkdir(parents=True, exist_ok=True)
        (root / "canvas").mkdir(parents=True, exist_ok=True)
        (root / "props").mkdir(parents=True, exist_ok=True)
        (root / "props" / "inp").mkdir(parents=True, exist_ok=True)
        (root / "props" / "inp" / "go").mkdir(parents=True, exist_ok=True)
        (root / "props" / "inp" / "mesh").mkdir(parents=True, exist_ok=True)
        (root / "props" / "inp" / "material").mkdir(parents=True, exist_ok=True)
        (root / "props" / "inp" / "step").mkdir(parents=True, exist_ok=True)
        (root / "props" / "reports").mkdir(parents=True, exist_ok=True)
        (root / "props" / "docs").mkdir(parents=True, exist_ok=True)
        (root / "props" / "tools").mkdir(parents=True, exist_ok=True)

        # bases
        _write_yaml_if_missing(
            root / "bases" / "go.base",
            _base_template(root / "props" / "inp" / "go"),
        )
        _write_yaml_if_missing(
            root / "bases" / "mesh.base",
            _base_template(root / "props" / "inp" / "mesh"),
        )
        _write_yaml_if_missing(
            root / "bases" / "material.base",
            _base_template(root / "props" / "inp" / "material", idx=False),
        )
        _write_yaml_if_missing(
            root / "bases" / "step.base",
            _base_template(root / "props" / "inp" / "step", idx=False),
        )

        _write_yaml_if_missing(
            root / "bases" / "docs.base",
            _base_template(
                root / "props" / "docs",
                idx=False,
                ver=False,
                show_only_active=False,
                active=False,
            ),
        )
        _write_yaml_if_missing(
            root / "bases" / "reports.base",
            _base_template(root / "props" / "reports", idx=False, active=False),
        )
        _write_yaml_if_missing(
            root / "bases" / "tools.base",
            _base_template(
                root / "props" / "tools", idx=False, ver=False, active=False
            ),
        )
        _write_yaml_if_missing(
            root / "bases" / "daily.base",
            _base_template(
                root / "daily",
                idx=False,
                ver=False,
                show_only_active=False,
                active=False,
            ),
        )

    base_list = [
        "go.base",
    ]

    base_list.append("")
    go_list = list(glob.glob(str(root / "props" / "inp" / "go" / "*.md")))
    go_list = ["_".join(i.split("_")[:-1]) + "." + i.split("_")[-1] for i in go_list]
    go_list = list(set([get_basename(i) for i in go_list]))
    go_list = [i.replace(f".v{get_index_and_version(i)[1]}.", "_") for i in go_list]
    go_list = list(set([i for i in go_list]))
    go_list = list(sorted(go_list, key=lambda x: get_index_and_version(x)[0]))

    go_base_list = []
    for i in go_list:
        go_base_list.append(f"{i}.base")
        _write_yaml_if_missing(
            root / "bases" / "go" / f"{i}.base",
            _base_template(
                root / "props" / "inp" / "go",
                additional_filters=[f'file.basename.startsWith("{i}")'],
                idx=False,
                show_only_active=False,
            ),
        )
        base_list.append(f"{i}.base")

    base_list.append("")
    base_list += [
        "mesh.base",
        "material.base",
        "step.base",
        "docs.base",
        "tools.base",
        "reports.base",
        "daily.base",
    ]

    with open(str(root / "bases" / "base.md"), "w") as f:
        for i in base_list:
            if i:
                f.write(f"- [[{i}]]\n")
            else:
                f.write("\n")

    with open(str(root / "bases" / "go" / "go_index.md"), "w") as f:
        f.write("[[go.base]]\n")
        for i in go_base_list:
            f.write(f"[[{i}]]\n")


# =========================
# notes: -all で全収集（go/mesh/material/step/modfem + docs/reports/tools）
# =========================
def _notes_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    root = Path(getattr(args, "root", "notes"))
    base_path = getattr(args, "base_path", "") or str(root / "bases")
    notes_dir = getattr(args, "notes_dir", "") or str(root / "props")
    return Path(base_path), Path(notes_dir)


def _glob_prefixed_ext(
    prefix: str, depth: int, ext_list: list[str] = [".inp"]
) -> list[str]:
    out: list[str] = []
    cwd = "./"
    if prefix.startswith("./"):
        depth = 0
    for _ in range(depth + 1):
        for ext in ext_list:
            out += glob.glob(f"{cwd}{prefix}*{ext}")
        cwd += "**/"
    out = [i for i in out if "~" not in i]
    out = [i for i in out if not i.split("/")[-1].split("\\")[-1].startswith("tmp")]
    # basename化（現行と合わせる）
    # out = [os.path.basename(i).replace("./", "") for i in out]
    # unique順序維持
    seen: set[str] = set()
    uniq: list[str] = []
    for i in out:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return uniq


def _ensure_bases_exist(base_dir: Path) -> None:
    # init無しでも notes -all が動くように最低限生成
    root = base_dir.parent
    init_notes_tree(root)


def safe_rglob_files(root: Path) -> list[Path]:
    """root配下の全ファイルを収集（存在しない/途中で消えた等は握りつぶす）"""
    if not root.exists():
        return []
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            try:
                if p.is_file():
                    out.append(p)
            except FileNotFoundError:
                # 走査中に消えた等
                continue
    except FileNotFoundError:
        return []
    return out


def safe_rglob_dirs(root: Path) -> list[Path]:
    """root配下の全ディレクトリを収集（root自身は除外）。"""
    if not root.exists():
        return []
    out: list[Path] = []
    try:
        for p in root.rglob("*"):
            try:
                if p.is_dir():
                    out.append(p)
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        return []
    return out


def frontmatter_keys(md_path: Path) -> set[str]:
    """frontmatterのキー集合（消えたファイルは空で返す）"""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return set()
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not m:
        return set()
    keys: set[str] = set()
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _ = line.split(":", 1)
        k = k.strip()
        if k:
            keys.add(k)
    return keys


# run_notes の -all 部分だけ差し替え（md_groups/keys収集のところ）
def collect_keys_all() -> dict[str, set[str]]:
    base_keys: dict[str, set[str]] = {
        "docs.base": set(),
        "reports.base": set(),
        "tools.base": set(),
    }

    # reports/, tools/：フォルダ内「全ファイル」を収集（拡張子問わず）
    for p in safe_rglob_files(Path("reports")):
        if p.suffix.lower() == ".md":
            base_keys["reports.base"].update(frontmatter_keys(p))
        else:
            # 非mdはfrontmatterが無いのでスキップ（キー抽出不能）
            # 必要ならファイル名ベースで別キー体系にする
            pass

    for p in safe_rglob_files(Path("tools")):
        if p.suffix.lower() == ".md":
            base_keys["tools.base"].update(frontmatter_keys(p))
        else:
            pass

    # 制約
    base_keys["docs.base"].discard("idx")
    base_keys["docs.base"].discard("ver")
    base_keys["tools.base"].discard("idx")
    base_keys["tools.base"].discard("ver")
    base_keys["reports.base"].discard("idx")  # reportsはidxなし

    return base_keys


def parse_word_with_vocab(
    word: str, vocab: VocabConfig, category_mapping: bool = True
) -> tuple[str, str] | None:
    key, value = None, None
    if "=" in word:
        key, value = word.split("=", 1)
        key = vocab.mapping.get(key, key)
        value = vocab.mapping.get(value, value)
    elif category_mapping:
        for g, vals in vocab.categories.items():
            if word in vals:
                value = word
                key = g
                key = vocab.mapping.get(key, key)
                value = vocab.mapping.get(value, value)
    elif key is None or value is None:
        m = re.fullmatch(r"([A-Za-z]+)(\d+)", word)
        if m:
            key, value = m.group(1), m.group(2)
            key = vocab.mapping.get(key, key)
            value = vocab.mapping.get(value, value)
    if key is None or value is None:
        return None
    key = vocab.mapping.get(key, key)
    value = vocab.mapping.get(value, value)
    return key, value


def normalize_extension_to_inp(filepath: str) -> tuple[str, str]:
    if "." not in filepath:
        return filepath, ""
    target_extension_list = [
        ".cas.h5",
        ".dat.h5",
        ".aedt.batchinfo",
        ".py",
        ".xlsx",
        ".csv",
        ".pptx",
        ".yaml",
        ".md",
        ".json",
        ".sh",
        ".msh",
        ".modfem",
        ".stp",
        ".step",
        ".catPart",
        ".dxf",
        ".dwg",
        ".png",
        ".gif",
    ]
    ext = None
    for ext_i in target_extension_list:
        if filepath.endswith(ext_i):
            ext = ext_i
            break
    if ext is None:
        ext = "." + filepath.split(".")[-1]
    filepath = filepath.replace(ext, ".inp")
    return filepath, ext


def get_properties_by_filepath(
    inp_filepath: str, vocab: VocabConfig
) -> dict[str, str]:
    """ファイル名からアンダースコア区切りでプロパティ取得（prefix/idx/ver除去込み）"""

    inp_filepath, _ = normalize_extension_to_inp(inp_filepath)
    name = inp_filepath.split("/")[-1].split("\\")[-1]

    # 拡張子 .inp を剥がす
    if name.lower().endswith(".inp"):
        name = name[:-4]

    # idx / ver を外す（既存関数を尊重）
    idx, ver = get_index_and_version(inp_filepath)
    if idx:
        name = name.replace(f"idx{idx}_", "").replace(f"idx{idx}", "")
    if ver:
        name = name.replace(f".v{ver}", "")

    # 先頭prefix（go_/mesh_/material_/step_等）を剥がしたいならここで
    name = re.sub(r"^(go_|mesh_|material_|step_)", "", name, flags=re.IGNORECASE)

    props: dict[str, str] = {}
    for token in filter(None, name.split("_")):
        result = parse_word_with_vocab(token, vocab)
        if result is None:
            continue
        key, value = result
        props[key] = value

    if Path(inp_filepath).parent.name == "old":
        props["active"] = "false"
    else:
        props["active"] = "true"

    return props


def get_properties_by_inp_parameter(
    inp_filepath: str, vocab: VocabConfig
) -> dict[str, str]:
    """inp内のparameterで'**props'の記載があればパラメータとして収集"""
    props: dict[str, str] = {}
    with open(inp_filepath, encoding="utf-8", errors="ignore") as f:
        while True:
            line = f.readline()
            if not line:
                break
            s = line.strip()
            s_l = s.lower().replace(" ", "")
            if s_l.startswith("*parameter"):
                header = f.readline()
                if not header:
                    break
                header_s = header.strip().lower().replace(" ", "")
                if not header_s.startswith("**props"):
                    continue
                while True:
                    line2 = f.readline()
                    if not line2:
                        break
                    t = line2.strip()
                    if not t:
                        continue
                    if t.startswith("**"):
                        continue
                    if t.lstrip().startswith("*"):
                        break
                    u = t.replace(" ", "")
                    if "=" not in u:
                        continue
                    k, v = u.split("=", 1)
                    if k:
                        k = vocab.mapping.get(k, k)
                        v = vocab.mapping.get(v, v)
                        props[k] = v
                return props
    return props


def get_relations_by_inp_includes(inp_filepath: str) -> list[str]:
    includes: list[str] = []

    pat = re.compile(r"^\*include\s*,\s*input\s*=\s*(.+)$", re.IGNORECASE)

    with Path(inp_filepath).open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("**"):
                continue
            m = pat.match(s)
            if m:
                include_i = Path(inp_filepath).parent / m.group(1).strip()
                includes.append(str(include_i))

    if "mesh" in inp_filepath:
        includes += ["assets/" + get_basename(inp_filepath) + ".modfem"]

    return includes


def clear_notes_props(dirpath: Path) -> None:
    if not dirpath.exists():
        return
    for p in dirpath.iterdir():
        if p.is_file() or p.is_symlink():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)


def run_notes(args: argparse.Namespace, targets: list[str]) -> int:
    warnings: list[WarningItem] = []

    base_dir, notes_dir = _notes_paths(args)
    notes_dir.mkdir(parents=True, exist_ok=True)
    base_dir.mkdir(parents=True, exist_ok=True)

    if getattr(args, "overwrite_props", True):
        clear_notes_props(notes_dir)

    if getattr(args, "overwrite_bases", True):
        clear_notes_props(base_dir)
        clear_notes_props(base_dir / "go")
        init_notes_tree(base_dir.parent)

    # -all のときは全カテゴリ収集（targetsは無視）
    if getattr(args, "all_files", False):
        _ensure_bases_exist(base_dir)

        depth = int(getattr(args, "subdirectory_depth", 1))

        # inp系（mdは notes/inp に作る）
        inp_groups: dict[str, list[str]] = {
            "go.base": _glob_prefixed_ext(
                "go", depth, ext_list=[".inp", ".cas.h5", ".aedt"]
            ),
            "mesh.base": _glob_prefixed_ext("mesh", depth, ext_list=[".inp", ".msh"]),
            "material.base": _glob_prefixed_ext("material", depth),
            "step.base": _glob_prefixed_ext("step_", depth),
            "docs.base": _glob_prefixed_ext("./docs/*", depth, ext_list=[""]),
            "reports.base": _glob_prefixed_ext("./reports/*", depth, ext_list=["*"]),
            "tools.base": _glob_prefixed_ext("./tools/*", depth, ext_list=["*"]),
        }

        # baseごとのキー集合（最終的に base の order に追記するキー）
        base_keys: dict[str, set[str]] = {
            "go.base": set(),
            "mesh.base": set(),
            "material.base": set(),
            "step.base": set(),
            "docs.base": set(),
            "reports.base": set(),
            "tools.base": set(),
        }

        # ---- inp → md 生成/追記 + キー収集
        all_basename_list = []
        for base_name, inp_list in inp_groups.items():
            all_basename_list += [i.split("\\")[-1].split("/")[-1] for i in inp_list]
        done = set()
        md_inp_dict = {}
        vocab = load_vocab_config()
        for base_name, inp_list in inp_groups.items():
            for i in inp_list:
                try:
                    idx, ver = get_index_and_version(i)
                    props: dict[str, str] = {"idx": idx, "ver": ver}
                    includes: list[str] = []

                    props.update(get_properties_by_filepath(i, vocab))

                    if i.endswith(".inp"):
                        props.update(get_properties_by_inp_parameter(i, vocab))
                        includes += get_relations_by_inp_includes(i)

                    # frontmatterが真実源なので「追記のみ」
                    if os.path.isdir(i):
                        basename = Path(i).name
                    else:
                        _basename, ext = get_basename_with_ext(i)
                        basename = (
                            # ".".join(Path(i).name.split(".")[:-1])[0:]
                            _basename + "_" + ext[1:]
                        )
                    if any([i in base_name for i in ["docs", "reports", "tools"]]):
                        md_path = notes_dir / f"{base_name.split('.')[0]}/{basename}.md"
                    else:
                        md_path = (
                            notes_dir
                            / "inp"
                            / base_name.split(".")[0]
                            / f"{basename}.md"
                        )

                    if (
                        not getattr(args, "allow_duplicated", False)
                        and md_path.name in done
                    ):
                        raise ValueError(f"""
"{md_path}" appeared twice 
- 1: {i}
- 2: {md_inp_dict[md_path.name]})
""")
                    if not md_path.exists() or True:
                        write_frontmatter_props(
                            md_path=md_path,
                            base_name=base_name,
                            all_basename_list=all_basename_list,
                            props=props,
                            includes=includes,
                        )

                    else:
                        update_frontmatter_props(md_path, props)

                    done.add(md_path.name)
                    md_inp_dict[md_path.name] = i
                    # キーは「frontmatterの実態」から取る（真実源の徹底）
                    base_keys[base_name].update(frontmatter_keys(md_path))

                except Exception as e:
                    # warnings.append(WarningItem(i, repr(e)))
                    raise e

        # ---- reports/tools：フォルダ内の md 全収集（名前一致なし）
        for p in safe_rglob_files(Path("reports")):
            if p.suffix.lower() == ".md":
                base_keys["reports.base"].update(frontmatter_keys(p))

        for p in safe_rglob_files(Path("tools")):
            if p.suffix.lower() == ".md":
                base_keys["tools.base"].update(frontmatter_keys(p))

        # ---- 制約反映
        # docs/tools: idx/ver なし
        for bn in ("docs.base", "tools.base"):
            base_keys[bn].discard("idx")
            base_keys[bn].discard("ver")
        # reports: idx なし（verは残す）
        base_keys["reports.base"].discard("idx")

        # ---- base更新（orderに無いキーだけ追記）
        try:
            for base_name, keys in base_keys.items():
                update_go_base(base_dir / base_name, sorted(keys))

                if base_name == "go.base":
                    sub_base_list = list(glob.glob(str(base_dir / "go" / "*.base")))
                    for i in sub_base_list:
                        update_go_base(Path(i), sorted(keys))

            init_notes_tree(notes_dir.parent, init_bases=False)

        except Exception as e:
            warnings.append(WarningItem(str(base_dir), repr(e)))

        _print_warnings(warnings)
        return 0 if not warnings else 1

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
    print(f"[jj run] exit_code={result.exit_code} log={log_path}")
    if result.trace_files:
        print("trace_files:")
        for path in result.trace_files:
            print(f"  - {path}")

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

    if cmd == "notes" and subcmd == "init":
        root = Path(getattr(args, "root", "notes"))
        init_notes_tree(root)
        return 0

    if cmd == "notes":
        return run_notes(args, targets)

    if cmd == "run":
        return run_run(args)

    # default: submit
    return run_submit(args, targets)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args = normalize_compat(args)
    return dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
