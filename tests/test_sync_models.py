"""同期モデルのテスト"""

from services.sync.models import SyncDirection, SyncState, SyncStatus


class TestSyncStatus:
    def test_enum_values(self):
        assert SyncStatus.PENDING == "pending"
        assert SyncStatus.IN_PROGRESS == "in_progress"
        assert SyncStatus.COMPLETED == "completed"
        assert SyncStatus.FAILED == "failed"


class TestSyncDirection:
    def test_enum_values(self):
        assert SyncDirection.PUSH == "push"
        assert SyncDirection.CLONE == "clone"


class TestSyncState:
    def test_create_minimal(self):
        state = SyncState(
            sync_id="test_001",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/local/project",
            destination_path="\\\\server\\share\\project",
        )
        assert state.sync_id == "test_001"
        assert state.direction == SyncDirection.PUSH
        assert state.status == SyncStatus.PENDING
        assert state.backend == "shared_folder"
        assert state.files_transferred == 0
        assert state.files_skipped == 0
        assert state.bytes_transferred == 0
        assert state.exclude_patterns == []
        assert state.errors == []
        assert state.started_at is None
        assert state.completed_at is None

    def test_mark_in_progress(self):
        state = SyncState(
            sync_id="test_002",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/a",
            destination_path="/b",
        )
        state.mark_in_progress()
        assert state.status == SyncStatus.IN_PROGRESS
        assert state.started_at is not None

    def test_mark_completed(self):
        state = SyncState(
            sync_id="test_003",
            direction=SyncDirection.CLONE,
            backend="gitlab",
            source_path="/remote",
            destination_path="/local",
        )
        state.mark_in_progress()
        state.mark_completed()
        assert state.status == SyncStatus.COMPLETED
        assert state.completed_at is not None

    def test_mark_failed(self):
        state = SyncState(
            sync_id="test_004",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/a",
            destination_path="/b",
        )
        state.mark_failed("接続失敗")
        assert state.status == SyncStatus.FAILED
        assert "接続失敗" in state.errors

    def test_model_dump_roundtrip(self):
        state = SyncState(
            sync_id="test_005",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/src",
            destination_path="\\\\srv\\dst",
            exclude_patterns=["*.odb", "*.res"],
        )
        data = state.model_dump(mode="json")
        restored = SyncState.model_validate(data)
        assert restored.sync_id == state.sync_id
        assert restored.direction == state.direction
        assert restored.exclude_patterns == ["*.odb", "*.res"]

    def test_properties_metadata(self):
        state = SyncState(
            sync_id="test_006",
            direction=SyncDirection.PUSH,
            backend="shared_folder",
            source_path="/a",
            destination_path="/b",
            properties={"last_sync_time": "2026-03-13T10:00:00Z"},
        )
        assert state.properties["last_sync_time"] == "2026-03-13T10:00:00Z"
