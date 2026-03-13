"""Windows共有フォルダ同期バックエンド

shutil.copy2によるファイル単位コピー。
UNCパス（\\\\server\\share\\path）をネイティブサポート。
差分同期: mtime + size 比較で変更ファイルのみ転送。
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

from config import IgnoreConfig

from ..models import SyncDirection, SyncState
from . import AbstractSyncBackend


class SharedFolderBackend(AbstractSyncBackend):
    """Windows共有フォルダ同期バックエンド"""

    backend_name = "shared_folder"

    def push(
        self,
        source: Path,
        destination: str,
        exclude: IgnoreConfig,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """ローカルから共有フォルダへプッシュ（差分同期）"""
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
            dest_path = Path(destination)
            dest_path.mkdir(parents=True, exist_ok=True)

            self._sync_directory(
                source=source,
                destination=dest_path,
                exclude=exclude,
                state=state,
                on_progress=on_progress,
            )
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
        """共有フォルダからローカルへクローン（差分同期）"""
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
            source_path = Path(source)
            if not source_path.exists():
                raise FileNotFoundError(f"ソースパスが見つかりません: {source}")

            destination.mkdir(parents=True, exist_ok=True)

            self._sync_directory(
                source=source_path,
                destination=destination,
                exclude=exclude,
                state=state,
                on_progress=on_progress,
            )
            state.mark_completed()
        except Exception as e:
            state.mark_failed(str(e))

        return state

    def _sync_directory(
        self,
        source: Path,
        destination: Path,
        exclude: IgnoreConfig,
        state: SyncState,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> None:
        """ディレクトリを再帰的に差分同期"""
        for item in sorted(source.iterdir()):
            rel_path = str(item.relative_to(source))

            if exclude.should_ignore(rel_path) or exclude.should_ignore(item.name):
                state.files_skipped += 1
                continue

            dest_item = destination / item.name

            if item.is_dir():
                dest_item.mkdir(parents=True, exist_ok=True)
                self._sync_directory(
                    source=item,
                    destination=dest_item,
                    exclude=exclude,
                    state=state,
                    on_progress=on_progress,
                )
            elif item.is_file():
                if self._needs_update(item, dest_item):
                    shutil.copy2(str(item), str(dest_item))
                    file_size = item.stat().st_size
                    state.files_transferred += 1
                    state.bytes_transferred += file_size
                    if on_progress:
                        on_progress(rel_path, file_size)
                else:
                    state.files_skipped += 1

    @staticmethod
    def _needs_update(source_file: Path, dest_file: Path) -> bool:
        """差分チェック: mtime + size 比較"""
        if not dest_file.exists():
            return True
        src_stat = source_file.stat()
        dst_stat = dest_file.stat()
        if src_stat.st_size != dst_stat.st_size:
            return True
        return os.path.getmtime(source_file) > os.path.getmtime(dest_file)
