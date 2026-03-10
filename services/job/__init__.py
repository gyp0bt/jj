"""リモートジョブ管理サービス (T5)

jj submit / jj watch / jj collect / jj job status の基盤。

ジョブの状態を .j2/storage/jobs/ にYAMLファイルとして永続化し、
投入→監視→回収のライフサイクルを管理する。
Prefect統合 (T5-9) によるワークフロー記録・管理をサポート。
"""

from __future__ import annotations

from .models import JobState, JobStatus
from .storage import JobStorage

__all__ = [
    "JobState",
    "JobStatus",
    "JobStorage",
]
