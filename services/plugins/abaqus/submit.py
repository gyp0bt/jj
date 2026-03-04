"""SubmitService: Abaqusジョブ投入・ターゲット解決・ファイル操作のビジネスロジック

CLIのsubmit/list/check/filesコマンドで使用されるビジネスロジックを集約。
CLI層はargparse解析と出力整形のみに責務を限定する。

status-088でservices/service/submit.pyからAbaqusプラグインに移動。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import glob
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from services.parse import get_basename, get_index_and_version


@dataclass
class WarningItem:
    target: str
    message: str


@dataclass
class JobListItem:
    """ジョブ一覧の1行分のデータ"""

    target: str
    job_name: str


class SubmitService:
    """ジョブ投入およびターゲット解決のビジネスロジック

    CLI層から分離されたビジネスロジックを提供する。
    configに依存するロジック（ファイル名パターン等）はconfigを通じて取得する。
    """

    def __init__(
        self,
        base_dirpath: str,
        remote_abq_path: str,
        tool_dirpath: Path,
    ) -> None:
        self.base_dirpath = base_dirpath
        self.remote_abq_path = remote_abq_path
        self.tool_dirpath = tool_dirpath

    # =========
    # ターゲット解決
    # =========

    def resolve_targets(
        self,
        *,
        inp_files: list[str] | None = None,
        index: list[str] | None = None,
        inp_files_versions: list[str] | None = None,
        all_files: bool = False,
        subdirectory_depth: int = 1,
        old_files: bool = False,
    ) -> list[str]:
        """CLI引数からターゲットファイルリストを解決する

        Args:
            inp_files: 明示指定されたファイルリスト
            index: インデックス指定（例: ["1", "2"], ["0..5"]）
            inp_files_versions: バージョン指定（例: ["1", "2"]）
            all_files: 全ファイル選択フラグ
            subdirectory_depth: サブフォルダ探索の深さ
            old_files: 旧バージョン選択フラグ

        Returns:
            解決されたターゲットファイルのリスト（重複なし、順序維持）
        """
        inp_filepath_list: list[str] = []

        # old_files
        if old_files:
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
            inp_filepath_list = [i for i in list(glob.glob("./go*.inp")) if i not in latest_inp_files]
        else:
            # 明示指定がなければ go*.inp
            if inp_files is None and index is None and inp_files_versions is None:
                inp_filepath_list = list(glob.glob("./go*.inp"))
            else:
                inp_filepath_list = list(inp_files or [])

        # index指定
        if index:
            for idx in index:
                if ".." in idx:
                    s, e = idx.split("..")
                    s_i, e_i = int(s), int(e)
                    for idx_i in range(s_i, e_i + 1):
                        inp_i = list(glob.glob(f"go_idx{idx_i}*.inp"))
                        inp_filepath_list += inp_i
                else:
                    inp_i = list(glob.glob(f"go_idx{idx}*.inp"))
                    inp_filepath_list += inp_i

        # version指定
        if inp_files_versions:
            if inp_filepath_list:
                inp_filepath_list = [i for i in inp_filepath_list if any([f"v{j}" in i for j in inp_files_versions])]
            else:
                for ver in inp_files_versions:
                    inp_filepath_list += list(glob.glob(f"go_*.v{ver}.inp"))
        elif not old_files:
            # 最新バージョンだけ選ぶ
            inp_filepath_list = self._filter_latest_versions(inp_filepath_list)

        # all_files + depth
        if all_files:
            inp_filepath_list = []
            cwd = "./"
            for _ in range(int(subdirectory_depth) + 1):
                inp_filepath_list += glob.glob(f"{cwd}go*.inp")
                cwd += "**/"

        # 正規化（basenameだけに寄せる）
        inp_filepath_list = [get_basename(i) + ".inp" for i in inp_filepath_list]
        inp_filepath_list = [i.replace("./", "") for i in inp_filepath_list]

        # unique（順序維持）
        return self._unique_ordered(inp_filepath_list)

    def _filter_latest_versions(self, inp_filepath_list: list[str]) -> list[str]:
        """ファイルリストから最新バージョンのみを抽出"""
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
                    basename_i = get_basename(i)
            old_version, _ = version_data.get(basename_i, (0, ""))
            if old_version < version_i:
                version_data[basename_i] = (version_i, i)
        return [i[1] for i in version_data.values()]

    @staticmethod
    def _unique_ordered(items: list[str]) -> list[str]:
        """重複を除去しつつ順序を維持"""
        done: set[str] = set()
        out: list[str] = []
        for i in items:
            if i not in done:
                done.add(i)
                out.append(i)
        return out

    # =========
    # ジョブ名生成
    # =========

    def get_abq_job_name(self, inp_filepath: str | None = None) -> str:
        """Abaqusジョブ名を生成する

        ディレクトリパスからジョブ名のベースを生成し、
        ファイル指定がある場合はidx/versionを付加する。
        """
        from modules.pyssh import ssh

        dirpath = ssh.get_local_linux_filepath(os.getcwd())
        dirpath = (
            dirpath.replace(self.base_dirpath, "")
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

    def list_jobs(self, targets: list[str]) -> list[JobListItem]:
        """ターゲットファイルのジョブ名一覧を返す

        Args:
            targets: ターゲットファイルリスト

        Returns:
            ジョブ一覧（ターゲット名とジョブ名のペア）
        """
        return [JobListItem(target=t, job_name=self.get_abq_job_name(t)) for t in targets]

    # =========
    # JCFファイル生成
    # =========

    @staticmethod
    def write_standard_jcf(
        inp_filepath_list: list[str],
        jcf_filepath: str,
        job_name: str,
        abq_class: str,
        ncpu: int,
        abq_command_path: str,
    ) -> None:
        """GPU利用時の標準JCFファイルを生成"""
        if not isinstance(inp_filepath_list, list):
            inp_filepath_list = [inp_filepath_list]
        with open(jcf_filepath, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"#PBS -q {abq_class}\n")
            f.write(f"#PBS -l select=1:ncpus={ncpu}:mpiprocs={ncpu}:ngpus=1:abaqus=1\n")
            f.write(f"#PBS -N {job_name}\n")
            f.write("#PBS -j oe\n")
            f.write("#PBS -m ae\n")
            f.write("\n")
            f.write(f"CPU={ncpu}\n")
            for i, ii in enumerate(inp_filepath_list):
                f.write(f'DATA[{i}]="{ii}"\n')
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

    @staticmethod
    def write_explicit_jcf(
        inp_filepath_list: list[str],
        jcf_filepath: str,
        job_name: str,
        abq_class: str,
        ncpu: int,
        abq_command_path: str,
    ) -> None:
        """非GPU時のJCFファイルを生成"""
        if not isinstance(inp_filepath_list, list):
            inp_filepath_list = [inp_filepath_list]
        with open(jcf_filepath, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"#PBS -q {abq_class}\n")
            f.write(f"#PBS -l select=1:ncpus={ncpu}:mpiprocs={ncpu}:abaqus=1\n")
            f.write(f"#PBS -N {job_name}\n")
            f.write("#PBS -j oe\n")
            f.write("#PBS -m ae\n")
            f.write("\n")
            f.write(f"CPU={ncpu}\n")
            for i, ii in enumerate(inp_filepath_list):
                f.write(f'DATA[{i}]="{ii}"\n')
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

    @classmethod
    def write_jcf(
        cls,
        use_gpu: bool,
        inp_filepath_list: list[str],
        jcf_filepath: str,
        job_name: str,
        abq_class: str,
        ncpu: int,
        abq_command_path: str,
    ) -> None:
        """GPU有無に応じてJCFファイルを書き出す"""
        if use_gpu:
            cls.write_standard_jcf(
                inp_filepath_list,
                jcf_filepath,
                job_name,
                abq_class,
                ncpu,
                abq_command_path,
            )
        else:
            cls.write_explicit_jcf(
                inp_filepath_list,
                jcf_filepath,
                job_name,
                abq_class,
                ncpu,
                abq_command_path,
            )

    @staticmethod
    def execute(command: str, jcf_filepath: str, hostname: str | None = None) -> None:
        """JCFをリモートに転送して実行"""
        from modules.pyssh import ssh

        os.system(f"dos2unix {jcf_filepath}")
        client = ssh.SSHClient([jcf_filepath], setting=ssh.SSH_SETTING(_hostname=hostname))
        client.put()
        client.execute_command(command, cd=True)

    def write_jcf_and_execute(
        self,
        use_gpu: bool,
        inp_filepath_list: list[str],
        jcf_filepath: str,
        job_name: str,
        abq_class: str,
        ncpu: int,
        command: str,
        abq_command_path: str,
        host_name: str,
    ) -> None:
        """JCFを書き出してリモート実行する"""
        self.write_jcf(
            use_gpu,
            inp_filepath_list,
            jcf_filepath,
            job_name,
            abq_class,
            ncpu,
            abq_command_path,
        )
        self.execute(command, jcf_filepath, host_name)

    def submit(
        self,
        targets: list[str],
        *,
        use_gpu: bool = False,
        no_background: bool = False,
        jcf: str = "abq.jcf",
        abq_version: str | None = None,
        ss_class: bool = False,
        s_class: bool = False,
        ncpu: int | None = None,
        job_name: str | None = None,
        separate: bool = False,
        host_name: str = "",
    ) -> tuple[int, list[WarningItem]]:
        """ジョブを投入する

        Returns:
            (終了コード, 警告リスト)
        """
        warnings: list[WarningItem] = []

        # command
        if no_background:
            command = f"qsub -Wblock=true {jcf}"
        else:
            command = f"qsub {jcf}"

        # class / ncpu
        if ss_class:
            abq_class = "ABQSS"
            resolved_ncpu = 1
        elif s_class:
            abq_class = "ABQS"
            resolved_ncpu = 4
        else:
            abq_class = "ABQ"
            resolved_ncpu = 8
        if ncpu is not None:
            resolved_ncpu = int(ncpu)

        # abq_command_path
        if abq_version is None:
            abq_command_path = self.remote_abq_path
        else:
            abq_command_path = f"/usr1/abaqus/Commands/abq{abq_version}"

        # separate or batch
        try:
            if separate:
                for inp in targets:
                    try:
                        resolved_name = job_name if job_name else self.get_abq_job_name(inp)
                        self.write_jcf_and_execute(
                            use_gpu=use_gpu,
                            inp_filepath_list=[inp],
                            jcf_filepath=jcf,
                            job_name=resolved_name,
                            abq_class=abq_class,
                            ncpu=resolved_ncpu,
                            command=command,
                            abq_command_path=abq_command_path,
                            host_name=host_name,
                        )
                    except Exception as e:
                        warnings.append(WarningItem(inp, repr(e)))
            else:
                if len(targets) == 1:
                    resolved_name = job_name if job_name else self.get_abq_job_name(targets[0])
                else:
                    resolved_name = job_name if job_name else self.get_abq_job_name()
                self.write_jcf_and_execute(
                    use_gpu=use_gpu,
                    inp_filepath_list=targets,
                    jcf_filepath=jcf,
                    job_name=resolved_name,
                    abq_class=abq_class,
                    ncpu=resolved_ncpu,
                    command=command,
                    abq_command_path=abq_command_path,
                    host_name=host_name,
                )
        except Exception as e:
            warnings.append(WarningItem("(submit)", repr(e)))

        return (0 if not warnings else 1, warnings)

    # =========
    # ファイル操作
    # =========

    def run_files_get(self, targets: list[str], host_name: str) -> tuple[int, list[WarningItem]]:
        """ファイルをリモートから取得する"""
        warnings: list[WarningItem] = []
        script = str(self.tool_dirpath / "sget-single.ps1")
        for i in targets:
            try:
                script_args = ["-BaseName", i[:-4]]
                if host_name:
                    script_args += ["-HostName", f"{host_name}"]
                self.run_ps1(script, *script_args)
            except Exception as e:
                warnings.append(WarningItem(i, repr(e)))
        return (0 if not warnings else 1, warnings)

    def run_files_put(self, targets: list[str], host_name: str) -> tuple[int, list[WarningItem]]:
        """ファイルをリモートに送信する"""
        warnings: list[WarningItem] = []
        script = str(self.tool_dirpath / "put.ps1")
        try:
            script_args = [i for i in targets]
            if host_name:
                script_args += [host_name]
            self.run_ps1(script, *script_args)
        except Exception as e:
            warnings.append(WarningItem("(batch)", repr(e)))
        return (0 if not warnings else 1, warnings)

    @staticmethod
    def run_files_move(targets: list[str]) -> tuple[int, list[WarningItem]]:
        """ファイルをoldディレクトリに移動する"""
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
        return (0 if not warnings else 1, warnings)

    def run_check_syntax(self, targets: list[str]) -> tuple[int, list[WarningItem]]:
        """Abaqus inpのsyntaxチェックを実行する"""
        warnings: list[WarningItem] = []
        for i in targets:
            try:
                self.run_ps1(str(self.tool_dirpath / "syn.ps1"), i)
            except Exception as e:
                warnings.append(WarningItem(i, repr(e)))
        return (0 if not warnings else 1, warnings)

    @staticmethod
    def run_ps1(path: str, *args: str, capture: bool = False) -> str | None:
        """PowerShellスクリプトを実行する"""
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
