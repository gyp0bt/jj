"""同期状態モデル

push/cloneのライフサイクルを管理するデータモデル。
.j2/storage/sync/sync-{id}.yaml に永続化される。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """同期の状態遷移: pending → in_progress → completed / failed"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncDirection(str, Enum):
    """同期の方向"""

    PUSH = "push"
    CLONE = "clone"


class SyncState(BaseModel):
    """同期状態ファイルのデータモデル

    1同期操作 = 1 YAML ファイルとして .j2/storage/sync/ に保存される。
    """

    sync_id: str = Field(description="同期操作の識別子")
    direction: SyncDirection = Field(description="push or clone")
    status: SyncStatus = Field(default=SyncStatus.PENDING)
    backend: str = Field(description="使用バックエンド名 (shared_folder, gitlab)")

    source_path: str = Field(description="同期元パス")
    destination_path: str = Field(description="同期先パス")

    started_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)

    files_transferred: int = Field(default=0, description="転送済みファイル数")
    files_skipped: int = Field(default=0, description="スキップ（差分なし）ファイル数")
    bytes_transferred: int = Field(default=0, description="転送済みバイト数")

    exclude_patterns: list[str] = Field(default_factory=list, description="除外パターン")
    errors: list[str] = Field(default_factory=list, description="発生エラー")
    properties: dict[str, Any] = Field(default_factory=dict, description="追加メタデータ")

    def mark_in_progress(self) -> None:
        self.status = SyncStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self) -> None:
        self.status = SyncStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, reason: str = "") -> None:
        self.status = SyncStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        if reason:
            self.errors.append(reason)
