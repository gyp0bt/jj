"""GitLab同期バックエンド

subprocessでgit init/add/commit/pushを実行。
除外パターンは.gitignoreに自動反映。
認証は環境変数経由のトークン。
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from config import IgnoreConfig

from ..models import SyncDirection, SyncState
from . import AbstractSyncBackend


class GitLabBackend(AbstractSyncBackend):
    """GitLab git push/pull 同期バックエンド"""

    backend_name = "gitlab"

    def push(
        self,
        source: Path,
        destination: str,
        exclude: IgnoreConfig,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """ローカルからGitLabリポジトリへpush

        Args:
            source: ローカルプロジェクトディレクトリ
            destination: GitLabリポジトリURL
            exclude: 除外パターン（.gitignoreに反映）
            on_progress: 進捗コールバック
        """
        state = SyncState(
            sync_id="",
            direction=SyncDirection.PUSH,
            backend=self.backend_name,
            source_path=str(source),
            destination_path=destination,
            exclude_patterns=exclude.patterns,
        )
        state.mark_in_progress()

        try:
            # .gitignoreを生成/更新
            self._write_gitignore(source, exclude)

            # git init（既にgitリポの場合は何もしない）
            self._run_git(source, ["init"])

            # remote設定
            remote_url = self._inject_token(destination)
            self._setup_remote(source, remote_url)

            # git add + commit
            self._run_git(source, ["add", "-A"])

            # 変更があるかチェック
            result = self._run_git(source, ["status", "--porcelain"], check=False)
            if result.stdout.strip():
                self._run_git(source, ["commit", "-m", "jj push sync"])
                if on_progress:
                    on_progress("git commit", 0)

            # git push
            self._run_git(source, ["push", "-u", "origin", "main"], check=False)
            # mainブランチが存在しない場合はmasterを試す
            self._run_git(source, ["push", "-u", "origin", "HEAD"], check=False)

            if on_progress:
                on_progress("git push", 0)

            # ファイル数を取得
            ls_result = self._run_git(source, ["ls-files"], check=False)
            if ls_result.stdout.strip():
                state.files_transferred = len(ls_result.stdout.strip().split("\n"))

            state.mark_completed()
        except Exception as e:
            state.mark_failed(str(e))

        return state

    def clone(
        self,
        source: str,
        destination: Path,
        exclude: IgnoreConfig,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """GitLabリポジトリからクローン

        Args:
            source: GitLabリポジトリURL
            destination: ローカルクローン先
            exclude: 除外パターン
            on_progress: 進捗コールバック
        """
        state = SyncState(
            sync_id="",
            direction=SyncDirection.CLONE,
            backend=self.backend_name,
            source_path=source,
            destination_path=str(destination),
            exclude_patterns=exclude.patterns,
        )
        state.mark_in_progress()

        try:
            clone_url = self._inject_token(source)

            subprocess.run(
                ["git", "clone", clone_url, str(destination)],
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
            )

            if on_progress:
                on_progress("git clone", 0)

            # クローンされたファイル数
            if destination.exists():
                file_count = sum(1 for f in destination.rglob("*") if f.is_file() and ".git" not in f.parts)
                state.files_transferred = file_count

            state.mark_completed()
        except subprocess.CalledProcessError as e:
            state.mark_failed(f"git clone failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            state.mark_failed("git clone timed out (300s)")
        except Exception as e:
            state.mark_failed(str(e))

        return state

    @staticmethod
    def _write_gitignore(project_dir: Path, exclude: IgnoreConfig) -> None:
        """除外パターンを.gitignoreに書き出す"""
        gitignore_path = project_dir / ".gitignore"
        marker_start = "# === jj sync exclude start ==="
        marker_end = "# === jj sync exclude end ==="

        existing_lines: list[str] = []
        if gitignore_path.exists():
            existing_lines = gitignore_path.read_text(encoding="utf-8").splitlines()

        # マーカー間の既存パターンを除去
        new_lines: list[str] = []
        in_marker = False
        for line in existing_lines:
            if line.strip() == marker_start:
                in_marker = True
                continue
            if line.strip() == marker_end:
                in_marker = False
                continue
            if not in_marker:
                new_lines.append(line)

        # マーカー付きで追加
        if exclude.patterns:
            new_lines.append("")
            new_lines.append(marker_start)
            for pattern in exclude.patterns:
                new_lines.append(pattern)
            new_lines.append(marker_end)

        gitignore_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    @staticmethod
    def _inject_token(url: str) -> str:
        """環境変数からGitLabトークンを取得してURLに注入"""
        token = os.environ.get("GITLAB_TOKEN", "")
        if not token:
            return url
        # https://gitlab.example.com/group/repo.git
        # → https://oauth2:TOKEN@gitlab.example.com/group/repo.git
        if url.startswith("https://"):
            return url.replace("https://", f"https://oauth2:{token}@", 1)
        return url

    @staticmethod
    def _setup_remote(project_dir: Path, remote_url: str) -> None:
        """gitリモートを設定"""
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                check=True,
            )

    @staticmethod
    def _run_git(
        project_dir: Path,
        args: list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """gitコマンドを実行"""
        return subprocess.run(
            ["git", *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            check=check,
            timeout=120,
        )
