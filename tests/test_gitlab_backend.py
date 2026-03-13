"""GitLabバックエンドのテスト"""

import subprocess
from unittest.mock import MagicMock, patch

from config import IgnoreConfig
from services.sync.backends import AbstractSyncBackend
from services.sync.backends.gitlab import GitLabBackend
from services.sync.models import SyncDirection, SyncStatus


class TestGitLabBackendRegistration:
    def test_backend_registered(self):
        assert "gitlab" in AbstractSyncBackend._registry
        assert AbstractSyncBackend._registry["gitlab"] is GitLabBackend

    def test_get_backend(self):
        backend = AbstractSyncBackend.get_backend("gitlab")
        assert isinstance(backend, GitLabBackend)


class TestGitLabWriteGitignore:
    def test_write_gitignore_new(self, tmp_path):
        exclude = IgnoreConfig.from_list(["*.odb", "*.res", ".j2"])
        GitLabBackend._write_gitignore(tmp_path, exclude)

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "# === jj sync exclude start ===" in gitignore
        assert "*.odb" in gitignore
        assert "*.res" in gitignore
        assert ".j2" in gitignore
        assert "# === jj sync exclude end ===" in gitignore

    def test_write_gitignore_preserves_existing(self, tmp_path):
        (tmp_path / ".gitignore").write_text("# existing\n*.tmp\n")
        exclude = IgnoreConfig.from_list(["*.odb"])
        GitLabBackend._write_gitignore(tmp_path, exclude)

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "# existing" in gitignore
        assert "*.tmp" in gitignore
        assert "*.odb" in gitignore

    def test_write_gitignore_updates_marker_section(self, tmp_path):
        initial = (
            "# user patterns\n*.tmp\n\n# === jj sync exclude start ===\n*.old_pattern\n# === jj sync exclude end ===\n"
        )
        (tmp_path / ".gitignore").write_text(initial)

        exclude = IgnoreConfig.from_list(["*.new_pattern"])
        GitLabBackend._write_gitignore(tmp_path, exclude)

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "*.old_pattern" not in gitignore
        assert "*.new_pattern" in gitignore
        assert "*.tmp" in gitignore

    def test_write_gitignore_empty_patterns(self, tmp_path):
        exclude = IgnoreConfig.from_list([])
        GitLabBackend._write_gitignore(tmp_path, exclude)

        gitignore = (tmp_path / ".gitignore").read_text()
        assert "# === jj sync exclude start ===" not in gitignore


class TestGitLabInjectToken:
    def test_inject_token(self):
        with patch.dict("os.environ", {"GITLAB_TOKEN": "mytoken123"}):
            url = GitLabBackend._inject_token("https://gitlab.example.com/group/repo.git")
            assert url == "https://oauth2:mytoken123@gitlab.example.com/group/repo.git"

    def test_no_token(self):
        with patch.dict("os.environ", {}, clear=True):
            url = GitLabBackend._inject_token("https://gitlab.example.com/group/repo.git")
            assert url == "https://gitlab.example.com/group/repo.git"

    def test_non_https(self):
        with patch.dict("os.environ", {"GITLAB_TOKEN": "tok"}):
            url = GitLabBackend._inject_token("git@gitlab.example.com:group/repo.git")
            assert url == "git@gitlab.example.com:group/repo.git"


class TestGitLabPush:
    @patch("services.sync.backends.gitlab.subprocess.run")
    def test_push_success(self, mock_run, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / "input.inp").write_text("data")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "input.inp\n.gitignore"
        mock_run.return_value = mock_result

        backend = GitLabBackend()
        exclude = IgnoreConfig.from_list(["*.odb"])

        state = backend.push(
            project,
            "https://gitlab.example.com/group/repo.git",
            exclude,
        )

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.PUSH
        assert state.backend == "gitlab"
        assert mock_run.called

    @patch("services.sync.backends.gitlab.subprocess.run")
    def test_push_failure(self, mock_run, tmp_path):
        project = tmp_path / "project"
        project.mkdir()

        mock_run.side_effect = subprocess.CalledProcessError(1, "git", stderr="error")

        backend = GitLabBackend()
        exclude = IgnoreConfig.from_list([])

        state = backend.push(
            project,
            "https://gitlab.example.com/group/repo.git",
            exclude,
        )

        assert state.status == SyncStatus.FAILED
        assert len(state.errors) > 0


class TestGitLabClone:
    @patch("services.sync.backends.gitlab.subprocess.run")
    def test_clone_success(self, mock_run, tmp_path):
        dest = tmp_path / "cloned"

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # 模擬的にクローン先ディレクトリを作成
        dest.mkdir()
        (dest / "file.txt").write_text("data")

        backend = GitLabBackend()
        exclude = IgnoreConfig.from_list([])

        state = backend.clone(
            "https://gitlab.example.com/group/repo.git",
            dest,
            exclude,
        )

        assert state.status == SyncStatus.COMPLETED
        assert state.direction == SyncDirection.CLONE

    @patch("services.sync.backends.gitlab.subprocess.run")
    def test_clone_failure(self, mock_run, tmp_path):
        dest = tmp_path / "cloned"
        mock_run.side_effect = subprocess.CalledProcessError(128, "git clone", stderr="not found")

        backend = GitLabBackend()
        exclude = IgnoreConfig.from_list([])

        state = backend.clone(
            "https://gitlab.example.com/group/nonexistent.git",
            dest,
            exclude,
        )

        assert state.status == SyncStatus.FAILED

    @patch("services.sync.backends.gitlab.subprocess.run")
    def test_clone_timeout(self, mock_run, tmp_path):
        dest = tmp_path / "cloned"
        mock_run.side_effect = subprocess.TimeoutExpired("git clone", 300)

        backend = GitLabBackend()
        exclude = IgnoreConfig.from_list([])

        state = backend.clone(
            "https://gitlab.example.com/group/repo.git",
            dest,
            exclude,
        )

        assert state.status == SyncStatus.FAILED
        assert "timed out" in state.errors[0]
