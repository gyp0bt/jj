"""ジョブ管理サービス

jj job submit / jj job watch / jj job collect / jj job status のビジネスロジック。
CLI層から呼び出され、SSHClientを使ってリモート操作を行う。
"""

from __future__ import annotations

import glob
import re
import time
from collections.abc import Callable
from pathlib import Path

from .models import JobState, JobStatus
from .storage import JobStorage


def expand_targets(patterns: list[str], cwd: Path | None = None) -> list[str]:
    """ターゲットパターンを展開

    以下の展開をサポート:
    - ブレース展開: go_sample_{1..5} → go_sample_1, ..., go_sample_5
    - glob展開: *.inp → マッチするファイル群
    - そのまま: 展開パターンなしの場合はそのまま返す

    Args:
        patterns: 展開するパターンのリスト
        cwd: glob展開の基準ディレクトリ

    Returns:
        展開されたターゲットのリスト（重複除去、ソート済み）
    """
    expanded: list[str] = []
    base_dir = cwd or Path.cwd()

    for pattern in patterns:
        # ブレース展開: {start..end} パターン
        brace_results = _expand_braces(pattern)
        if brace_results is not None:
            expanded.extend(brace_results)
            continue

        # glob展開: *, ? を含む場合
        if any(c in pattern for c in ("*", "?", "[")):
            matches = sorted(glob.glob(str(base_dir / pattern)))
            if matches:
                # base_dirからの相対パスで返す
                for m in matches:
                    try:
                        expanded.append(str(Path(m).relative_to(base_dir)))
                    except ValueError:
                        expanded.append(m)
                continue

        # そのまま
        expanded.append(pattern)

    # 重複除去（順序保持）
    seen: set[str] = set()
    unique: list[str] = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _expand_braces(pattern: str) -> list[str] | None:
    """ブレース展開: {start..end} → 数値範囲展開

    例: go_sample_{1..5}.inp → [go_sample_1.inp, ..., go_sample_5.inp]
    例: test_{a,b,c}.inp → [test_a.inp, test_b.inp, test_c.inp]
    """
    # 数値範囲: {start..end}
    match = re.search(r"\{(\d+)\.\.(\d+)\}", pattern)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        prefix = pattern[: match.start()]
        suffix = pattern[match.end() :]
        step = 1 if start <= end else -1
        return [f"{prefix}{i}{suffix}" for i in range(start, end + step, step)]

    # カンマ区切り: {a,b,c}
    match = re.search(r"\{([^}]+)\}", pattern)
    if match:
        items = match.group(1).split(",")
        if len(items) > 1:
            prefix = pattern[: match.start()]
            suffix = pattern[match.end() :]
            return [f"{prefix}{item.strip()}{suffix}" for item in items]

    return None


class JobService:
    """リモートジョブ管理サービス"""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.storage = JobStorage()

    def submit(
        self,
        targets: list[str],
        command_template: str = "",
        host_name: str | None = None,
        batch: bool = False,
    ) -> list[JobState]:
        """ジョブを投入（ファイル転送 + リモート実行 + ステート記録）

        Args:
            targets: 入力ファイル名のリスト
            command_template: 実行コマンドテンプレート
            host_name: リモートホスト名（SSH設定から取得）
            batch: Trueの場合、ブレース展開・glob展開を適用

        Returns:
            投入されたジョブのJobStateリスト
        """
        from config import load_ssh_config

        # バッチモード: ターゲットパターンを展開
        if batch:
            targets = expand_targets(targets, cwd=self.project_root)

        ssh_config = load_ssh_config(hostname=host_name)
        ssh_config.require("linux_local_basedirpath", "remote_basedirpath")

        jobs: list[JobState] = []
        for target in targets:
            local_dir = str(self.project_root)
            remote_dir = self._resolve_remote_dir(ssh_config, local_dir)

            job_id = self.storage.generate_job_id(Path(target).stem)
            job = JobState(
                job_id=job_id,
                remote_host=ssh_config.host or "",
                remote_dir=remote_dir,
                local_dir=local_dir,
                command=command_template.format(target=target) if command_template else "",
                input_files=[target],
            )

            # ファイル転送
            self._transfer_files(ssh_config, local_dir, remote_dir, [target])

            # リモート実行
            if job.command:
                self._execute_remote(ssh_config, remote_dir, job.command)
                job.mark_running()

            self.storage.save(self.project_root, job)
            jobs.append(job)

        return jobs

    def watch(
        self,
        job_ids: list[str] | None = None,
        interval: int = 30,
        timeout: int = 0,
        check_command: str = "",
        on_status_change: Callable[[JobState, str], None] | None = None,
    ) -> list[JobState]:
        """ジョブの完了を監視

        SSHでリモートのジョブ状態を定期的にチェックし、完了を検知する。

        Args:
            job_ids: 監視するジョブIDリスト（Noneでrunning全件）
            interval: チェック間隔（秒）
            timeout: タイムアウト秒数（0で無制限）
            check_command: ジョブ完了チェックコマンド（{job_id}をプレースホルダ）
            on_status_change: 状態変化時のコールバック

        Returns:
            監視終了時点のジョブリスト
        """
        # 監視対象ジョブを取得
        if job_ids:
            jobs = [self.storage.load(self.project_root, jid) for jid in job_ids]
            jobs = [j for j in jobs if j is not None]
        else:
            jobs = self.storage.list_jobs(self.project_root, status_filter=JobStatus.RUNNING)

        if not jobs:
            return []

        start_time = time.time()
        while True:
            all_done = True
            for job in jobs:
                if job.status not in (JobStatus.RUNNING, JobStatus.SUBMITTED):
                    continue
                all_done = False

                completed = self._check_job_completion(job, check_command)
                if completed:
                    old_status = job.status.value
                    job.mark_completed()
                    self.storage.save(self.project_root, job)
                    if on_status_change:
                        on_status_change(job, old_status)

            if all_done:
                break

            if timeout > 0 and (time.time() - start_time) >= timeout:
                break

            time.sleep(interval)

        return jobs

    def collect(
        self,
        job_ids: list[str] | None = None,
        completed_only: bool = False,
        output_patterns: list[str] | None = None,
    ) -> list[JobState]:
        """完了ジョブの結果を回収

        Args:
            job_ids: 回収するジョブIDリスト（Noneで全完了ジョブ）
            completed_only: Trueの場合、completedステータスのジョブのみ回収
            output_patterns: 出力ファイルのパターンリスト（ジョブに未設定の場合に使用）

        Returns:
            回収されたジョブのリスト
        """
        from config import load_ssh_config

        if job_ids:
            jobs = [self.storage.load(self.project_root, jid) for jid in job_ids]
            jobs = [j for j in jobs if j is not None]
        else:
            status_filter = JobStatus.COMPLETED if completed_only else None
            jobs = self.storage.list_jobs(self.project_root, status_filter=status_filter)

        if completed_only:
            jobs = [j for j in jobs if j.status == JobStatus.COMPLETED]

        collected: list[JobState] = []
        for job in jobs:
            try:
                ssh_config = load_ssh_config()

                # output_filesが未設定の場合、リモートから出力ファイルを検出
                if not job.output_files and output_patterns:
                    job.output_files = output_patterns
                elif not job.output_files:
                    detected = self._detect_output_files(ssh_config, job)
                    if detected:
                        job.output_files = detected

                self._download_outputs(ssh_config, job)
                job.mark_collected()
                self.storage.save(self.project_root, job)
                collected.append(job)
            except Exception as e:
                job.properties["collect_error"] = str(e)
                self.storage.save(self.project_root, job)

        return collected

    def list_jobs(self, status_filter: JobStatus | None = None) -> list[JobState]:
        """ジョブ一覧を取得"""
        return self.storage.list_jobs(self.project_root, status_filter=status_filter)

    def get_job(self, job_id: str) -> JobState | None:
        """指定IDのジョブを取得"""
        return self.storage.load(self.project_root, job_id)

    def _resolve_remote_dir(self, ssh_config, local_dir: str) -> str:
        """ローカルパスからリモートパスを解決"""
        # 新しいfolder_mappingsを優先
        remote = ssh_config.resolve_remote_path(local_dir)
        if remote is not None:
            return remote
        # フォールバック: 従来のbasedirpath方式
        if ssh_config.linux_local_basedirpath and ssh_config.remote_basedirpath:
            normalized = local_dir.replace("\\", "/")
            base = ssh_config.linux_local_basedirpath.replace("\\", "/")
            if normalized.startswith(base):
                relative = normalized[len(base) :]
                return ssh_config.remote_basedirpath.rstrip("/") + "/" + relative.lstrip("/")
        raise ValueError(
            f"ローカルパス '{local_dir}' に対応するリモートパスを解決できません。"
            ".pyssh.yamlのFOLDER_MAPPINGSまたはLINUX_LOCAL_BASEDIRPATH/REMOTE_BASEDIRPATHを設定してください。"
        )

    def _check_job_completion(self, job: JobState, check_command: str = "") -> bool:
        """リモートジョブの完了をチェック

        check_commandが指定されている場合はそれを実行。
        未指定の場合は、入力ファイルの拡張子から推測して完了チェック。
        """
        try:
            from modules.pyssh.ssh import execute_command

            if check_command:
                cmd = check_command.format(job_id=job.job_id)
                stdout = execute_command(cmd, remote_dirpath=job.remote_dir, cd=True, verbose=False)
                return "COMPLETED" in stdout.upper()

            # デフォルト: .lck ファイルが消えていれば完了と判定
            lock_check = "test -f *.lck && echo RUNNING || echo COMPLETED"
            stdout = execute_command(lock_check, remote_dirpath=job.remote_dir, cd=True, verbose=False)
            return "COMPLETED" in stdout
        except ImportError as e:
            raise ImportError("SSH操作にはparamikoが必要です。pip install jj[ssh] を実行してください。") from e
        except Exception:
            return False

    def _detect_output_files(self, ssh_config, job: JobState) -> list[str]:
        """リモートディレクトリから出力ファイルを検出"""
        try:
            from modules.pyssh.ssh import execute_command

            # 入力ファイル以外のファイルを出力として検出
            stdout = execute_command("ls -1", remote_dirpath=job.remote_dir, cd=True, verbose=False)
            if not stdout.strip():
                return []
            remote_files = [f.strip() for f in stdout.strip().split("\n") if f.strip()]
            input_set = set(job.input_files)
            return [f for f in remote_files if f not in input_set]
        except (ImportError, Exception):
            return []

    def _transfer_files(self, ssh_config, local_dir: str, remote_dir: str, files: list[str]) -> None:
        """ファイルをリモートに転送"""
        try:
            from modules.pyssh import SSHClient as PysshClient
            from modules.pyssh.ssh import SSH_SETTING

            setting = SSH_SETTING()
            local_paths = [str(Path(local_dir) / f) for f in files]
            remote_paths = [f"{remote_dir.rstrip('/')}/{f}" for f in files]
            client = PysshClient(
                local_filepath_list=local_paths,
                remote_filepath_list=remote_paths,
                setting=setting,
            )
            client.put()
        except ImportError as e:
            raise ImportError("SSH操作にはparamikoが必要です。pip install jj[ssh] を実行してください。") from e

    def _execute_remote(self, ssh_config, remote_dir: str, command: str) -> str:
        """リモートでコマンドを実行"""
        try:
            from modules.pyssh.ssh import execute_command

            return execute_command(command, remote_dirpath=remote_dir, cd=True)
        except ImportError as e:
            raise ImportError("SSH操作にはparamikoが必要です。pip install jj[ssh] を実行してください。") from e

    def _download_outputs(self, ssh_config, job: JobState) -> None:
        """リモートから結果ファイルをダウンロード"""
        if not job.output_files:
            return
        try:
            from modules.pyssh import SSHClient as PysshClient
            from modules.pyssh.ssh import SSH_SETTING

            setting = SSH_SETTING()
            remote_paths = [f"{job.remote_dir.rstrip('/')}/{f}" for f in job.output_files]
            local_paths = [str(Path(job.local_dir) / f) for f in job.output_files]
            client = PysshClient(
                local_filepath_list=local_paths,
                remote_filepath_list=remote_paths,
                setting=setting,
            )
            client.get()
        except ImportError as e:
            raise ImportError("SSH操作にはparamikoが必要です。pip install jj[ssh] を実行してください。") from e
