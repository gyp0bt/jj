"""T5: リモートジョブ管理のテスト

JobState / JobStorage / JobService のユニットテスト。
SSH接続を必要としないモデル・ストレージ層のテスト。
"""

from __future__ import annotations

from pathlib import Path

from services.job.models import JobState, JobStatus
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
