"""同期サービスのテスト"""

from services.sync.models import SyncDirection, SyncStatus
from services.sync.service import SyncService


class TestSyncServicePush:
    def _setup_project(self, tmp_path):
        """テスト用プロジェクトディレクトリを作成"""
        project = tmp_path / "project"
        project.mkdir()
        (project / "input.inp").write_text("input data")
        (project / "config.yaml").write_text("settings: true")
        (project / "result.odb").write_text("heavy binary result")
        sub = project / "subdir"
        sub.mkdir()
        (sub / "mesh.cdb").write_text("mesh data")
        return project

    def test_push_with_explicit_destination(self, tmp_path):
        project = self._setup_project(tmp_path)
        dest = tmp_path / "shared"
        service = SyncService(project_root=project)

        state = service.push(
            backend_name="shared_folder",
            destination=str(dest),
            extra_exclude=["*.odb"],
        )

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.PUSH
        assert state.files_transferred == 3  # input.inp, config.yaml, mesh.cdb
        assert (dest / "input.inp").exists()
        assert not (dest / "result.odb").exists()

    def test_push_dry_run(self, tmp_path):
        project = self._setup_project(tmp_path)
        dest = tmp_path / "shared"
        service = SyncService(project_root=project)

        state = service.push(
            backend_name="shared_folder",
            destination=str(dest),
            dry_run=True,
        )

        assert state.sync_id == "dry_run"
        assert state.status == SyncStatus.COMPLETED
        assert "target_files" in state.properties
        files = state.properties["target_files"]
        # result.odbはデフォルト除外パターンで除外される
        assert len(files) == 3
        # destにはコピーされない
        assert not dest.exists()

    def test_push_persists_state(self, tmp_path):
        project = self._setup_project(tmp_path)
        dest = tmp_path / "shared"
        service = SyncService(project_root=project)

        state = service.push(
            backend_name="shared_folder",
            destination=str(dest),
        )

        assert state.sync_id != ""
        assert state.sync_id.startswith("push_")

        # ストレージから取得できること
        loaded = service.get_sync(state.sync_id)
        assert loaded is not None
        assert loaded.status == SyncStatus.COMPLETED

    def test_push_without_destination_raises(self, tmp_path):
        project = self._setup_project(tmp_path)
        service = SyncService(project_root=project)

        import pytest

        with pytest.raises(ValueError, match="同期先パスを解決できません"):
            service.push(backend_name="shared_folder")


class TestSyncServiceClone:
    def test_clone_with_explicit_destination(self, tmp_path):
        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "input.inp").write_text("shared data")
        (shared / "heavy.odb").write_text("binary")

        local = tmp_path / "local"
        service = SyncService(project_root=tmp_path)

        state = service.clone(
            source=str(shared),
            backend_name="shared_folder",
            destination=local,
            extra_exclude=["*.odb"],
        )

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.CLONE
        assert state.files_transferred == 1
        assert (local / "input.inp").exists()
        assert not (local / "heavy.odb").exists()

    def test_clone_persists_state(self, tmp_path):
        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "file.txt").write_text("data")

        local = tmp_path / "local"
        service = SyncService(project_root=tmp_path)

        state = service.clone(
            source=str(shared),
            backend_name="shared_folder",
            destination=local,
        )

        assert state.sync_id.startswith("clone_")
        loaded = service.get_sync(state.sync_id)
        assert loaded is not None


class TestSyncServiceStatus:
    def test_status_empty(self, tmp_path):
        service = SyncService(project_root=tmp_path)
        result = service.status()
        assert result == []

    def test_status_after_push(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / "a.txt").write_text("data")
        dest = tmp_path / "dest"

        service = SyncService(project_root=project)
        service.push(backend_name="shared_folder", destination=str(dest))

        result = service.status()
        assert len(result) == 1
        assert result[0].status == SyncStatus.COMPLETED

    def test_status_by_id(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / "a.txt").write_text("data")
        dest = tmp_path / "dest"

        service = SyncService(project_root=project)
        state = service.push(backend_name="shared_folder", destination=str(dest))

        result = service.status(sync_id=state.sync_id)
        assert len(result) == 1
        assert result[0].sync_id == state.sync_id

    def test_status_nonexistent_id(self, tmp_path):
        service = SyncService(project_root=tmp_path)
        result = service.status(sync_id="nonexistent")
        assert result == []
