"""T5: リモートジョブ管理のテスト

JobState / JobStorage / JobService のユニットテスト。
SSH接続を必要としないモデル・ストレージ層のテスト。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from services.job.models import JobState, JobStatus
from services.job.service import JobService
from services.job.storage import JobStorage


class TestJobState:
    """JobStateモデルのテスト"""

    def test_create_job_state(self):
        job = JobState(
            job_id="test_job_001",
            remote_host="grid-server",
            remote_dir="/usr2/user/work/",
            local_dir="/home/user/work/",
            command="abaqus job=test_001 cpus=8",
            input_files=["test_001.inp"],
        )
        assert job.job_id == "test_job_001"
        assert job.status == JobStatus.SUBMITTED
        assert job.remote_host == "grid-server"
        assert job.submitted_at  # auto-generated

    def test_status_transitions(self):
        job = JobState(
            job_id="test_job_002",
            remote_host="server",
            remote_dir="/remote/",
            local_dir="/local/",
        )
        assert job.status == JobStatus.SUBMITTED

        job.mark_running()
        assert job.status == JobStatus.RUNNING

        job.mark_completed()
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None

        job.mark_collected()
        assert job.status == JobStatus.COLLECTED
        assert job.collected_at is not None

    def test_mark_failed(self):
        job = JobState(
            job_id="test_job_003",
            remote_host="server",
            remote_dir="/remote/",
            local_dir="/local/",
        )
        job.mark_failed("接続タイムアウト")
        assert job.status == JobStatus.FAILED
        assert job.properties["failure_reason"] == "接続タイムアウト"

    def test_serialization(self):
        job = JobState(
            job_id="test_job_004",
            remote_host="grid-server",
            remote_dir="/usr2/user/work/",
            local_dir="/home/user/work/",
            command="abaqus job=test cpus=4",
            input_files=["test.inp"],
            output_files=["test.odb", "test.sta"],
            properties={"abq_version": "2023"},
        )
        data = job.model_dump(mode="json")
        restored = JobState.model_validate(data)
        assert restored.job_id == job.job_id
        assert restored.status == job.status
        assert restored.input_files == job.input_files
        assert restored.output_files == job.output_files
        assert restored.properties == job.properties


class TestJobStorage:
    """JobStorageのテスト"""

    def test_save_and_load(self, tmp_path: Path):
        storage = JobStorage()
        job = JobState(
            job_id="save_test_001",
            remote_host="grid-server",
            remote_dir="/usr2/user/work/",
            local_dir=str(tmp_path),
        )
        path = storage.save(tmp_path, job)
        assert path.exists()

        loaded = storage.load(tmp_path, "save_test_001")
        assert loaded is not None
        assert loaded.job_id == "save_test_001"
        assert loaded.remote_host == "grid-server"

    def test_load_nonexistent(self, tmp_path: Path):
        storage = JobStorage()
        result = storage.load(tmp_path, "nonexistent")
        assert result is None

    def test_list_jobs(self, tmp_path: Path):
        storage = JobStorage()

        # 3つのジョブを作成
        for i in range(3):
            job = JobState(
                job_id=f"list_test_{i:03d}",
                remote_host="server",
                remote_dir="/remote/",
                local_dir="/local/",
            )
            if i == 1:
                job.mark_completed()
            if i == 2:
                job.mark_failed("error")
            storage.save(tmp_path, job)

        # 全件取得
        all_jobs = storage.list_jobs(tmp_path)
        assert len(all_jobs) == 3

        # ステータスフィルタ
        submitted = storage.list_jobs(tmp_path, status_filter=JobStatus.SUBMITTED)
        assert len(submitted) == 1
        assert submitted[0].job_id == "list_test_000"

        completed = storage.list_jobs(tmp_path, status_filter=JobStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].job_id == "list_test_001"

        failed = storage.list_jobs(tmp_path, status_filter=JobStatus.FAILED)
        assert len(failed) == 1

    def test_delete(self, tmp_path: Path):
        storage = JobStorage()
        job = JobState(
            job_id="delete_test",
            remote_host="server",
            remote_dir="/remote/",
            local_dir="/local/",
        )
        storage.save(tmp_path, job)
        assert storage.load(tmp_path, "delete_test") is not None

        assert storage.delete(tmp_path, "delete_test") is True
        assert storage.load(tmp_path, "delete_test") is None

        # 存在しないジョブの削除
        assert storage.delete(tmp_path, "nonexistent") is False

    def test_generate_job_id(self):
        storage = JobStorage()
        job_id = storage.generate_job_id("go_sample_v3")
        assert job_id.startswith("go_sample_v3_")
        assert "T" in job_id  # タイムスタンプ含む


class TestFolderMapping:
    """SSHConfig.folder_mappingsのテスト"""

    def test_from_dict_with_folder_mappings(self):
        from config import SSHConfig

        data = {
            "HOST": "grid-server",
            "PORT": "22",
            "USER": "testuser",
            "PASSWORD": "pass",
            "LINUX_LOCAL_BASEDIRPATH": "/home/user/work/",
            "REMOTE_BASEDIRPATH": "/usr2/user/work/",
            "FOLDER_MAPPINGS": [
                {"local": "F:/active/", "remote": "/usr2/user/work/"},
                {"local": "D:/archive/", "remote": "/usr2/user/archive/"},
            ],
        }
        config = SSHConfig.from_dict(data)
        assert config.folder_mappings is not None
        assert len(config.folder_mappings) == 2
        assert config.folder_mappings[0].local == "F:/active/"
        assert config.folder_mappings[0].remote == "/usr2/user/work/"

    def test_from_dict_without_folder_mappings(self):
        from config import SSHConfig

        data = {
            "HOST": "grid-server",
            "PORT": "22",
            "USER": "testuser",
            "PASSWORD": "pass",
        }
        config = SSHConfig.from_dict(data)
        assert config.folder_mappings is None

    def test_resolve_remote_path(self):
        from config import FolderMapping, SSHConfig

        config = SSHConfig(
            folder_mappings=[
                FolderMapping(local="F:/active/", remote="/usr2/user/work/"),
                FolderMapping(local="D:/archive/", remote="/usr2/user/archive/"),
            ]
        )
        result = config.resolve_remote_path("F:/active/project_a/v3/")
        assert result == "/usr2/user/work/project_a/v3/"

        result = config.resolve_remote_path("D:/archive/old_project/")
        assert result == "/usr2/user/archive/old_project/"

        result = config.resolve_remote_path("/unknown/path/")
        assert result is None

    def test_resolve_local_path(self):
        from config import FolderMapping, SSHConfig

        config = SSHConfig(
            folder_mappings=[
                FolderMapping(local="F:/active/", remote="/usr2/user/work/"),
            ]
        )
        result = config.resolve_local_path("/usr2/user/work/project_a/v3/")
        assert result == "F:/active/project_a/v3/"

        result = config.resolve_local_path("/unknown/remote/path/")
        assert result is None

    def test_resolve_remote_path_windows_backslash(self):
        from config import FolderMapping, SSHConfig

        config = SSHConfig(
            folder_mappings=[
                FolderMapping(local="F:/active/", remote="/usr2/user/work/"),
            ]
        )
        result = config.resolve_remote_path("F:\\active\\project_a\\v3\\")
        assert result == "/usr2/user/work/project_a/v3/"


class TestJobServiceSubmit:
    """T5-3: JobService.submit のテスト（SSHモック）"""

    def test_submit_creates_job_state(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        mock_ssh_config = MagicMock()
        mock_ssh_config.host = "grid-server"
        mock_ssh_config.resolve_remote_path.return_value = "/usr2/user/work/"
        mock_ssh_config.linux_local_basedirpath = "/home/user/work/"
        mock_ssh_config.remote_basedirpath = "/usr2/user/work/"

        with (
            patch("services.job.service.JobService._transfer_files") as mock_transfer,
            patch("services.job.service.JobService._execute_remote") as mock_execute,
            patch("config.load_ssh_config", return_value=mock_ssh_config),
        ):
            jobs = service.submit(
                targets=["test.inp"],
                command_template="abaqus job={target} cpus=4",
                host_name="grid-server",
            )

        assert len(jobs) == 1
        job = jobs[0]
        assert job.remote_host == "grid-server"
        assert job.remote_dir == "/usr2/user/work/"
        assert job.input_files == ["test.inp"]
        assert "abaqus job=test.inp cpus=4" in job.command
        assert job.status == JobStatus.RUNNING
        mock_transfer.assert_called_once()
        mock_execute.assert_called_once()

        # ストレージに永続化されているか
        loaded = service.storage.load(tmp_path, job.job_id)
        assert loaded is not None
        assert loaded.job_id == job.job_id

    def test_submit_without_command(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        mock_ssh_config = MagicMock()
        mock_ssh_config.host = "server"
        mock_ssh_config.resolve_remote_path.return_value = "/remote/"

        with (
            patch("services.job.service.JobService._transfer_files"),
            patch("config.load_ssh_config", return_value=mock_ssh_config),
        ):
            jobs = service.submit(targets=["data.csv"], command_template="")

        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.SUBMITTED  # コマンドなし → runningにならない
        assert jobs[0].command == ""

    def test_submit_multiple_targets(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        mock_ssh_config = MagicMock()
        mock_ssh_config.host = "server"
        mock_ssh_config.resolve_remote_path.return_value = "/remote/"

        with (
            patch("services.job.service.JobService._transfer_files"),
            patch("services.job.service.JobService._execute_remote"),
            patch("config.load_ssh_config", return_value=mock_ssh_config),
        ):
            jobs = service.submit(
                targets=["a.inp", "b.inp", "c.inp"],
                command_template="run {target}",
            )

        assert len(jobs) == 3
        assert all(j.status == JobStatus.RUNNING for j in jobs)
        job_ids = [j.job_id for j in jobs]
        assert len(set(job_ids)) == 3  # ユニークなID


class TestJobServiceWatch:
    """T5-4: JobService.watch のテスト（SSHモック）"""

    def test_watch_detects_completion(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        # runningジョブを作成
        job = JobState(
            job_id="watch_test_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
        )
        job.mark_running()
        service.storage.save(tmp_path, job)

        call_count = 0

        def mock_check(job_state, check_command=""):
            nonlocal call_count
            call_count += 1
            return True  # 即座に完了

        with patch.object(service, "_check_job_completion", side_effect=mock_check):
            result = service.watch(
                job_ids=["watch_test_001"],
                interval=1,
                timeout=10,
            )

        assert len(result) == 1
        assert result[0].status == JobStatus.COMPLETED
        assert result[0].completed_at is not None

    def test_watch_timeout(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        job = JobState(
            job_id="watch_timeout_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
        )
        job.mark_running()
        service.storage.save(tmp_path, job)

        with patch.object(service, "_check_job_completion", return_value=False):
            result = service.watch(
                job_ids=["watch_timeout_001"],
                interval=1,
                timeout=2,
            )

        assert len(result) == 1
        assert result[0].status == JobStatus.RUNNING  # タイムアウト → まだrunning

    def test_watch_no_running_jobs(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)
        result = service.watch(interval=1, timeout=1)
        assert result == []

    def test_watch_callback(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        job = JobState(
            job_id="watch_cb_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
        )
        job.mark_running()
        service.storage.save(tmp_path, job)

        callback_calls = []

        def on_change(j, old_status):
            callback_calls.append((j.job_id, old_status, j.status.value))

        with patch.object(service, "_check_job_completion", return_value=True):
            service.watch(
                job_ids=["watch_cb_001"],
                interval=1,
                timeout=10,
                on_status_change=on_change,
            )

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("watch_cb_001", "running", "completed")


class TestJobServiceCollect:
    """T5-5: JobService.collect のテスト（SSHモック）"""

    def test_collect_completed_jobs(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        job = JobState(
            job_id="collect_test_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
            output_files=["result.odb", "result.sta"],
        )
        job.mark_completed()
        service.storage.save(tmp_path, job)

        mock_ssh_config = MagicMock()

        with (
            patch("config.load_ssh_config", return_value=mock_ssh_config),
            patch.object(service, "_download_outputs"),
        ):
            collected = service.collect(
                job_ids=["collect_test_001"],
                completed_only=True,
            )

        assert len(collected) == 1
        assert collected[0].status == JobStatus.COLLECTED
        assert collected[0].collected_at is not None

    def test_collect_with_output_patterns(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        job = JobState(
            job_id="collect_pattern_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
        )
        job.mark_completed()
        service.storage.save(tmp_path, job)

        mock_ssh_config = MagicMock()

        with (
            patch("config.load_ssh_config", return_value=mock_ssh_config),
            patch.object(service, "_download_outputs"),
        ):
            collected = service.collect(
                job_ids=["collect_pattern_001"],
                output_patterns=["*.odb", "*.sta"],
            )

        assert len(collected) == 1
        assert collected[0].output_files == ["*.odb", "*.sta"]

    def test_collect_handles_error(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        job = JobState(
            job_id="collect_error_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
            output_files=["result.odb"],
        )
        job.mark_completed()
        service.storage.save(tmp_path, job)

        mock_ssh_config = MagicMock()

        with (
            patch("config.load_ssh_config", return_value=mock_ssh_config),
            patch.object(service, "_download_outputs", side_effect=Exception("接続エラー")),
        ):
            collected = service.collect(job_ids=["collect_error_001"])

        assert len(collected) == 0  # エラーで回収失敗
        # エラーがpropertiesに記録される
        saved = service.storage.load(tmp_path, "collect_error_001")
        assert saved is not None
        assert "collect_error" in saved.properties
        assert "接続エラー" in saved.properties["collect_error"]

    def test_collect_skips_non_completed(self, tmp_path: Path):
        service = JobService(project_root=tmp_path)

        # runningジョブ（completed_only=Trueでスキップされるべき）
        job = JobState(
            job_id="collect_skip_001",
            remote_host="server",
            remote_dir="/remote/",
            local_dir=str(tmp_path),
        )
        job.mark_running()
        service.storage.save(tmp_path, job)

        mock_ssh_config = MagicMock()

        with patch("config.load_ssh_config", return_value=mock_ssh_config):
            collected = service.collect(
                job_ids=["collect_skip_001"],
                completed_only=True,
            )

        assert len(collected) == 0
