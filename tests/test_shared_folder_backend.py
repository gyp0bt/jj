"""共有フォルダバックエンドのテスト"""

import os
import time

from config import IgnoreConfig
from services.sync.backends import AbstractSyncBackend
from services.sync.backends.shared_folder import SharedFolderBackend
from services.sync.models import SyncDirection, SyncStatus


class TestSharedFolderBackendRegistration:
    def test_backend_registered(self):
        assert "shared_folder" in AbstractSyncBackend._registry
        assert AbstractSyncBackend._registry["shared_folder"] is SharedFolderBackend

    def test_get_backend(self):
        backend = AbstractSyncBackend.get_backend("shared_folder")
        assert isinstance(backend, SharedFolderBackend)

    def test_available_backends(self):
        backends = AbstractSyncBackend.available_backends()
        assert "shared_folder" in backends


class TestSharedFolderPush:
    def _make_source(self, tmp_path):
        """テスト用ソースディレクトリを作成"""
        src = tmp_path / "source"
        src.mkdir()
        (src / "input.inp").write_text("input data")
        (src / "config.yaml").write_text("config: true")
        sub = src / "subdir"
        sub.mkdir()
        (sub / "mesh.cdb").write_text("mesh data")
        return src

    def test_push_basic(self, tmp_path):
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        state = backend.push(src, str(dst), exclude)

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.PUSH
        assert state.files_transferred == 3
        assert state.bytes_transferred > 0
        assert (dst / "input.inp").exists()
        assert (dst / "config.yaml").exists()
        assert (dst / "subdir" / "mesh.cdb").exists()

    def test_push_with_exclude(self, tmp_path):
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list(["*.cdb"])
        backend = SharedFolderBackend()

        state = backend.push(src, str(dst), exclude)

        assert state.status == SyncStatus.COMPLETED
        assert state.files_transferred == 2
        assert state.files_skipped >= 1
        assert (dst / "input.inp").exists()
        assert not (dst / "subdir" / "mesh.cdb").exists()

    def test_push_with_directory_exclude(self, tmp_path):
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list(["subdir"])
        backend = SharedFolderBackend()

        state = backend.push(src, str(dst), exclude)

        assert state.status == SyncStatus.COMPLETED
        assert state.files_transferred == 2

    def test_push_incremental(self, tmp_path):
        """差分同期: 2回目は変更ファイルのみコピー"""
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        # 1回目: 全ファイルコピー
        state1 = backend.push(src, str(dst), exclude)
        assert state1.files_transferred == 3

        # 2回目: 変更なし → スキップ
        state2 = backend.push(src, str(dst), exclude)
        assert state2.files_transferred == 0
        assert state2.files_skipped == 3

    def test_push_incremental_after_modification(self, tmp_path):
        """差分同期: ファイル変更後は再コピー"""
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        # 1回目
        backend.push(src, str(dst), exclude)

        # ファイルを変更（mtimeが確実に変わるようにsleep）
        time.sleep(0.1)
        (src / "input.inp").write_text("modified input data")

        # 2回目: 変更されたファイルのみ
        state2 = backend.push(src, str(dst), exclude)
        assert state2.files_transferred == 1

    def test_push_progress_callback(self, tmp_path):
        src = self._make_source(tmp_path)
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()
        progress_log: list[tuple[str, int]] = []

        backend.push(src, str(dst), exclude, on_progress=lambda f, s: progress_log.append((f, s)))

        assert len(progress_log) == 3

    def test_push_nonexistent_source(self, tmp_path):
        src = tmp_path / "nonexistent"
        dst = tmp_path / "dest"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        state = backend.push(src, str(dst), exclude)
        assert state.status == SyncStatus.FAILED
        assert len(state.errors) > 0


class TestSharedFolderClone:
    def test_clone_basic(self, tmp_path):
        # 共有フォルダ側を模擬
        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "input.inp").write_text("shared input")
        sub = shared / "data"
        sub.mkdir()
        (sub / "result.csv").write_text("a,b,c")

        local = tmp_path / "local"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        state = backend.clone(str(shared), local, exclude)

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.CLONE
        assert state.files_transferred == 2
        assert (local / "input.inp").exists()
        assert (local / "data" / "result.csv").exists()

    def test_clone_with_exclude(self, tmp_path):
        shared = tmp_path / "shared"
        shared.mkdir()
        (shared / "input.inp").write_text("input")
        (shared / "result.odb").write_text("heavy binary")

        local = tmp_path / "local"
        exclude = IgnoreConfig.from_list(["*.odb"])
        backend = SharedFolderBackend()

        state = backend.clone(str(shared), local, exclude)

        assert state.files_transferred == 1
        assert (local / "input.inp").exists()
        assert not (local / "result.odb").exists()

    def test_clone_nonexistent_source(self, tmp_path):
        local = tmp_path / "local"
        exclude = IgnoreConfig.from_list([])
        backend = SharedFolderBackend()

        state = backend.clone(str(tmp_path / "ghost"), local, exclude)
        assert state.status == SyncStatus.FAILED


class TestNeedsUpdate:
    def test_new_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        dst = tmp_path / "dst.txt"
        assert SharedFolderBackend._needs_update(src, dst) is True

    def test_same_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        dst = tmp_path / "dst.txt"
        dst.write_text("hello")
        # mtimeを揃える
        os.utime(dst, (os.path.getatime(src), os.path.getmtime(src)))
        assert SharedFolderBackend._needs_update(src, dst) is False

    def test_different_size(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello world")
        dst = tmp_path / "dst.txt"
        dst.write_text("hi")
        assert SharedFolderBackend._needs_update(src, dst) is True

    def test_newer_source(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        dst.write_text("old")
        time.sleep(0.05)
        src.write_text("new")
        assert SharedFolderBackend._needs_update(src, dst) is True
