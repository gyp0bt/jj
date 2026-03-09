"""ジョブ状態の永続化ストレージ

.j2/storage/jobs/ 配下にジョブごとのYAMLファイルを管理する。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import JobState, JobStatus


class JobStorage:
    """ジョブ状態ファイルのCRUD操作"""

    def __init__(self, storage_dir: str = ".j2/storage/jobs") -> None:
        self.storage_dir = storage_dir

    def _jobs_dir(self, project_root: Path) -> Path:
        jobs_dir = project_root / self.storage_dir
        jobs_dir.mkdir(parents=True, exist_ok=True)
        return jobs_dir

    def _job_path(self, project_root: Path, job_id: str) -> Path:
        return self._jobs_dir(project_root) / f"job-{job_id}.yaml"

    def save(self, project_root: Path, job: JobState) -> Path:
        """ジョブ状態をYAMLファイルに保存"""
        path = self._job_path(project_root, job.job_id)
        data = job.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        return path

    def load(self, project_root: Path, job_id: str) -> JobState | None:
        """指定IDのジョブ状態を読み込み"""
        path = self._job_path(project_root, job_id)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        return JobState.model_validate(data)

    def list_jobs(
        self,
        project_root: Path,
        status_filter: JobStatus | None = None,
    ) -> list[JobState]:
        """全ジョブ状態を一覧取得（オプションでステータスフィルタ）"""
        jobs_dir = self._jobs_dir(project_root)
        jobs: list[JobState] = []
        for path in sorted(jobs_dir.glob("job-*.yaml")):
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            job = JobState.model_validate(data)
            if status_filter is not None and job.status != status_filter:
                continue
            jobs.append(job)
        return jobs

    def delete(self, project_root: Path, job_id: str) -> bool:
        """ジョブ状態ファイルを削除"""
        path = self._job_path(project_root, job_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def generate_job_id(self, base_name: str) -> str:
        """タイムスタンプ付きジョブIDを生成"""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{base_name}_{stamp}"
