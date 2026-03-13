"""同期サービス

jj push / jj clone のビジネスロジック。
CLI層から呼び出され、バックエンドに委譲する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from config import IgnoreConfig

from .backends import AbstractSyncBackend

# バックエンド実装をインポートして自動登録
from .backends import shared_folder as _sf  # noqa: F401
from .exclude import build_exclude_config
from .models import SyncState, SyncStatus
from .storage import SyncStorage


class SyncService:
    """同期操作サービス"""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.storage = SyncStorage()

    def push(
        self,
        backend_name: str = "shared_folder",
        target_dir: str | None = None,
        destination: str | None = None,
        extra_exclude: list[str] | None = None,
        dry_run: bool = False,
        force: bool = False,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """プロジェクトを同期先にプッシュ

        Args:
            backend_name: 使用バックエンド名
            target_dir: pushするディレクトリ（デフォルト: project_root）
            destination: 同期先パス（Noneの場合folder_mappingsから解決）
            extra_exclude: 追加除外パターン
            dry_run: Trueの場合、転送対象一覧を返すのみ
            force: Trueの場合、差分チェックをスキップして全コピー
            on_progress: 進捗コールバック

        Returns:
            SyncState
        """
        source = Path(target_dir) if target_dir else self.project_root

        # 同期先パスの解決
        if destination is None:
            destination = self._resolve_destination(backend_name, str(source))

        # 除外パターンの構築
        exclude = self._build_exclude(extra_exclude)

        if dry_run:
            return self._dry_run_push(source, destination, exclude, backend_name)

        # バックエンドに委譲
        backend = AbstractSyncBackend.get_backend(backend_name)
        state = backend.push(
            source=source,
            destination=destination,
            exclude=exclude,
            on_progress=on_progress,
        )

        # sync_idを付与して永続化
        state.sync_id = self.storage.generate_sync_id("push")
        self.storage.save(self.project_root, state)

        return state

    def clone(
        self,
        source: str,
        backend_name: str = "shared_folder",
        destination: Path | None = None,
        extra_exclude: list[str] | None = None,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> SyncState:
        """同期元からローカルにクローン

        Args:
            source: 同期元パス
            backend_name: 使用バックエンド名
            destination: クローン先ディレクトリ（Noneの場合folder_mappingsから解決）
            extra_exclude: 追加除外パターン
            on_progress: 進捗コールバック

        Returns:
            SyncState
        """
        if destination is None:
            resolved = self._resolve_local_destination(backend_name, source)
            destination = Path(resolved)

        exclude = self._build_exclude(extra_exclude)

        backend = AbstractSyncBackend.get_backend(backend_name)
        state = backend.clone(
            source=source,
            destination=destination,
            exclude=exclude,
            on_progress=on_progress,
        )

        state.sync_id = self.storage.generate_sync_id("clone")
        self.storage.save(self.project_root, state)

        return state

    def status(
        self,
        sync_id: str | None = None,
        status_filter: SyncStatus | None = None,
    ) -> list[SyncState]:
        """同期状態を取得"""
        if sync_id:
            state = self.storage.load(self.project_root, sync_id)
            return [state] if state else []
        return self.storage.list_syncs(self.project_root, status_filter=status_filter)

    def get_sync(self, sync_id: str) -> SyncState | None:
        """指定IDの同期状態を取得"""
        return self.storage.load(self.project_root, sync_id)

    def _build_exclude(self, extra_patterns: list[str] | None = None) -> IgnoreConfig:
        """config.yaml + CLI追加パターンから除外設定を構築"""
        try:
            from config import load_sync_config

            sync_config = load_sync_config(self.project_root)
            return build_exclude_config(sync_config.exclude, extra_patterns)
        except Exception:
            return build_exclude_config(None, extra_patterns)

    def _resolve_destination(self, backend_name: str, local_path: str) -> str:
        """folder_mappingsからpush先を解決"""
        if backend_name == "shared_folder":
            try:
                from config import load_sync_config

                sync_config = load_sync_config(self.project_root)
                resolved = sync_config.resolve_shared_path(local_path)
                if resolved:
                    return resolved
            except Exception:
                pass
        raise ValueError(
            "同期先パスを解決できません。--destination を指定するか、"
            "config.yamlのsync.shared_folder.folder_mappingsを設定してください。"
        )

    def _resolve_local_destination(self, backend_name: str, remote_path: str) -> str:
        """folder_mappingsからclone先を解決"""
        if backend_name == "shared_folder":
            try:
                from config import load_sync_config

                sync_config = load_sync_config(self.project_root)
                resolved = sync_config.resolve_local_path(remote_path)
                if resolved:
                    return resolved
            except Exception:
                pass
        raise ValueError(
            "クローン先パスを解決できません。--dest を指定するか、"
            "config.yamlのsync.shared_folder.folder_mappingsを設定してください。"
        )

    def _dry_run_push(
        self,
        source: Path,
        destination: str,
        exclude: IgnoreConfig,
        backend_name: str,
    ) -> SyncState:
        """ドライラン: 転送対象ファイルの一覧を返す"""
        state = SyncState(
            sync_id="dry_run",
            direction="push",
            status=SyncStatus.COMPLETED,
            backend=backend_name,
            source_path=str(source),
            destination_path=destination,
            exclude_patterns=exclude.patterns,
        )

        files: list[str] = []
        self._collect_files(source, source, exclude, files)
        state.properties["target_files"] = files
        state.files_transferred = len(files)

        return state

    def _collect_files(
        self,
        root: Path,
        current: Path,
        exclude: IgnoreConfig,
        files: list[str],
    ) -> None:
        """転送対象ファイルを再帰的に収集"""
        if not current.exists():
            return
        for item in sorted(current.iterdir()):
            rel = str(item.relative_to(root))
            if exclude.should_ignore(rel) or exclude.should_ignore(item.name):
                continue
            if item.is_dir():
                self._collect_files(root, item, exclude, files)
            elif item.is_file():
                files.append(rel)
