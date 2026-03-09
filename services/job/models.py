"""ジョブ状態モデル

リモートジョブのライフサイクルを管理するデータモデル。
.j2/storage/jobs/job-{timestamp}.yaml に永続化される。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """ジョブの状態遷移: submitted → running → completed → collected"""

    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    COLLECTED = "collected"
    FAILED = "failed"


class JobState(BaseModel):
    """ジョブ状態ファイルのデータモデル

    1ジョブ = 1 YAML ファイルとして .j2/storage/jobs/ に保存される。
    """

    job_id: str = Field(description="ジョブ識別子（例: go_sample_v3_idx1）")
    status: JobStatus = Field(default=JobStatus.SUBMITTED)
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = Field(default=None)
    collected_at: str | None = Field(default=None)

    remote_host: str = Field(description="リモートホスト名")
    remote_dir: str = Field(description="リモートディレクトリパス")
    local_dir: str = Field(description="ローカルディレクトリパス")

    command: str = Field(default="", description="実行コマンド")
    input_files: list[str] = Field(default_factory=list, description="転送した入力ファイル")
    output_files: list[str] = Field(default_factory=list, description="期待される出力ファイル")

    properties: dict[str, Any] = Field(default_factory=dict, description="追加メタデータ")

    def mark_running(self) -> None:
        self.status = JobStatus.RUNNING

    def mark_completed(self) -> None:
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def mark_collected(self) -> None:
        self.status = JobStatus.COLLECTED
        self.collected_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, reason: str = "") -> None:
        self.status = JobStatus.FAILED
        if reason:
            self.properties["failure_reason"] = reason
