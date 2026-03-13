"""同期ストレージのテスト"""

from services.sync.models import SyncDirection, SyncState, SyncStatus
from services.sync.storage import SyncStorage


class TestSyncStorage:
    def test_save_and_load(self, tmp_path):
        storage = SyncStorage()
        state = SyncState(
            sync_id="push_20260313T100000Z",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/local/project",
            destination_path="\\\\server\\share\\project",
        )
        path = storage.save(tmp_path, state)
        assert path.exists()
        assert "sync-push_20260313T100000Z.yaml" in path.name

        loaded = storage.load(tmp_path, "push_20260313T100000Z")
        assert loaded is not None
        assert loaded.sync_id == state.sync_id
        assert loaded.direction == SyncDirection.PUSH
        assert loaded.backend == "shared_folder"

    def test_load_nonexistent(self, tmp_path):
        storage = SyncStorage()
        result = storage.load(tmp_path, "nonexistent")
        assert result is None

    def test_list_syncs(self, tmp_path):
        storage = SyncStorage()
        for i in range(3):
            state = SyncState(
                sync_id=f"sync_{i}",
                direction=SyncDirection.PUSH,
                backend="shared_folder",
                source_path="/src",
                destination_path="/dst",
                status=SyncStatus.COMPLETED if i < 2 else SyncStatus.FAILED,
            )
            storage.save(tmp_path, state)

        all_syncs = storage.list_syncs(tmp_path)
        assert len(all_syncs) == 3

        completed = storage.list_syncs(tmp_path, status_filter=SyncStatus.COMPLETED)
        assert len(completed) == 2

        failed = storage.list_syncs(tmp_path, status_filter=SyncStatus.FAILED)
        assert len(failed) == 1

    def test_delete(self, tmp_path):
        storage = SyncStorage()
        state = SyncState(
            sync_id="to_delete",
            direction=SyncDirection.CLONE,
            backend="gitlab",
            source_path="/remote",
            destination_path="/local",
        )
        storage.save(tmp_path, state)
        assert storage.load(tmp_path, "to_delete") is not None

        deleted = storage.delete(tmp_path, "to_delete")
        assert deleted is True
        assert storage.load(tmp_path, "to_delete") is None

    def test_delete_nonexistent(self, tmp_path):
        storage = SyncStorage()
        assert storage.delete(tmp_path, "ghost") is False

    def test_generate_sync_id(self):
        storage = SyncStorage()
        sid = storage.generate_sync_id("push")
        assert sid.startswith("push_")
        assert "T" in sid
        assert sid.endswith("Z")

    def test_save_with_state_transitions(self, tmp_path):
        storage = SyncStorage()
        state = SyncState(
            sync_id="transition_test",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/src",
            destination_path="/dst",
        )
        storage.save(tmp_path, state)

        state.mark_in_progress()
        state.files_transferred = 10
        state.bytes_transferred = 1024
        storage.save(tmp_path, state)

        loaded = storage.load(tmp_path, "transition_test")
        assert loaded is not None
        assert loaded.status == SyncStatus.IN_PROGRESS
        assert loaded.files_transferred == 10
        assert loaded.bytes_transferred == 1024
