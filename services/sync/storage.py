"""同期状態の永続化ストレージ

.j2/storage/sync/ 配下に同期操作ごとのYAMLファイルを管理する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import SyncState, SyncStatus


class SyncStorage:
    """同期状態ファイルのCRUD操作"""

    def __init__(self, storage_dir: str = ".j2/storage/sync") -> None:
        self.storage_dir = storage_dir

    def _sync_dir(self, project_root: Path) -> Path:
        sync_dir = project_root / self.storage_dir
        sync_dir.mkdir(parents=True, exist_ok=True)
        return sync_dir

    def _sync_path(self, project_root: Path, sync_id: str) -> Path:
        return self._sync_dir(project_root) / f"sync-{sync_id}.yaml"

    def save(self, project_root: Path, state: SyncState) -> Path:
        """同期状態をYAMLファイルに保存"""
        path = self._sync_path(project_root, state.sync_id)
        data = state.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        return path

    def load(self, project_root: Path, sync_id: str) -> SyncState | None:
        """指定IDの同期状態を読み込み"""
        path = self._sync_path(project_root, sync_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        return SyncState.model_validate(data)

    def list_syncs(
        self,
        project_root: Path,
        status_filter: SyncStatus | None = None,
    ) -> list[SyncState]:
        """全同期状態を一覧取得"""
        sync_dir = self._sync_dir(project_root)
        syncs: list[SyncState] = []
        for path in sorted(sync_dir.glob("sync-*.yaml")):
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            state = SyncState.model_validate(data)
            if status_filter is not None and state.status != status_filter:
                continue
            syncs.append(state)
        return syncs

    def delete(self, project_root: Path, sync_id: str) -> bool:
        """同期状態ファイルを削除"""
        path = self._sync_path(project_root, sync_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def generate_sync_id(self, prefix: str = "sync") -> str:
        """タイムスタンプ付き同期IDを生成"""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{prefix}_{stamp}"
