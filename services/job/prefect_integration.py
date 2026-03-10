"""Prefect統合モジュール (T5-9)

jjのジョブ管理とPrefectワークフローエンジンを統合する。

## 2層アーキテクチャ

- **Layer 1**: 事後記録（report_to_prefect） — Prefect未起動でも安全にスキップ
- **Layer 2**: マネージドワーカー（JjPrefectManager） — jj prefect up/downで制御

## 使用方法

Layer 1（常時有効・fire-and-forget）::

    from services.job.prefect_integration import report_to_prefect
    report_to_prefect("submit", job_states=[job])

Layer 2（オプション・明示的起動）::

    from services.job.prefect_integration import JjPrefectManager
    manager = JjPrefectManager(project_root)
    manager.start()   # Prefect Server + Worker起動
    manager.stop()    # 停止

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.job.models import JobState

logger = logging.getLogger(__name__)


# ====================================================================
# Layer 1: 事後記録 (fire-and-forget)
# ====================================================================

_PREFECT_AVAILABLE: bool | None = None


def _check_prefect() -> bool:
    """Prefectが利用可能かチェック（結果をキャッシュ）"""
    global _PREFECT_AVAILABLE
    if _PREFECT_AVAILABLE is None:
        try:
            import prefect  # noqa: F401

            _PREFECT_AVAILABLE = True
        except ImportError:
            _PREFECT_AVAILABLE = False
    return _PREFECT_AVAILABLE


def report_to_prefect(
    action: str,
    job_states: list[JobState] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """jjコマンドの実行結果をPrefectに記録する（fire-and-forget）

    Prefectが利用不可の場合やサーバーに接続できない場合は
    静かにスキップしてFalseを返す。jjの主処理をブロックしない。

    Args:
        action: アクション名（"submit", "watch", "collect", "run"等）
        job_states: 関連するJobStateのリスト
        metadata: 追加メタデータ

    Returns:
        True: 記録成功、False: スキップまたはエラー
    """
    if not _check_prefect():
        return False

    try:
        from prefect import flow
        from prefect.artifacts import create_markdown_artifact

        @flow(name=f"jj-{action}", log_prints=True)
        def _report_flow() -> dict[str, Any]:
            result: dict[str, Any] = {
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "jobs": [],
            }

            if job_states:
                for job in job_states:
                    job_info = {
                        "job_id": job.job_id,
                        "status": job.status.value,
                        "remote_host": job.remote_host,
                        "command": job.command,
                    }
                    result["jobs"].append(job_info)

                # Markdownアーティファクト作成
                md_lines = [f"## jj {action}", ""]
                md_lines.append(f"**実行時刻**: {result['timestamp']}")
                md_lines.append(f"**ジョブ数**: {len(job_states)}")
                md_lines.append("")
                md_lines.append("| Job ID | Status | Host |")
                md_lines.append("|--------|--------|------|")
                for job in job_states:
                    md_lines.append(f"| {job.job_id} | {job.status.value} | {job.remote_host} |")

                create_markdown_artifact(
                    key=f"jj-{action}-report",
                    markdown="\n".join(md_lines),
                    description=f"jj {action} report",
                )

            if metadata:
                result["metadata"] = metadata

            return result

        _report_flow()
        return True

    except Exception as e:
        logger.debug("Prefect report skipped: %s", e)
        return False


# ====================================================================
# Layer 2: マネージドPrefectワーカー
# ====================================================================

_DEFAULT_PORT = 4200
_POLL_INTERVAL_MINUTES = 30


class JjPrefectManager:
    """jj Prefect Server/Worker ライフサイクル管理

    ユーザーがPrefectの設定やコードを書くことなく、
    `jj prefect up` で即座にフル機能のPrefectダッシュボードを利用可能にする。

    Attributes:
        project_root: プロジェクトルートパス
        port: Prefect Server ポート番号
        poll_interval: 自動ポーリング間隔（分）
    """

    def __init__(
        self,
        project_root: Path,
        port: int = _DEFAULT_PORT,
        poll_interval: int = _POLL_INTERVAL_MINUTES,
    ) -> None:
        self.project_root = project_root
        self.port = port
        self.poll_interval = poll_interval
        self._server_process: subprocess.Popen[bytes] | None = None
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pid_file = project_root / ".j2" / "storage" / "prefect-server.pid"

    @property
    def is_running(self) -> bool:
        """Prefect Serverが稼働中か"""
        if self._server_process is not None:
            return self._server_process.poll() is None
        return self._pid_file.exists()

    def start(self) -> dict[str, Any]:
        """Prefect Server + 自動ポーリングワーカーを起動

        Returns:
            起動情報を含む辞書
        """
        if not _check_prefect():
            return {
                "success": False,
                "error": "Prefectがインストールされていません。pip install jj[prefect] を実行してください。",
            }

        if self.is_running:
            return {
                "success": True,
                "message": f"Prefect Server は既に稼働中です (port: {self.port})",
                "url": f"http://localhost:{self.port}",
            }

        # Prefect APIのURLを設定
        import os

        os.environ["PREFECT_API_URL"] = f"http://127.0.0.1:{self.port}/api"

        # Server起動
        try:
            self._server_process = subprocess.Popen(
                [sys.executable, "-m", "prefect", "server", "start", "--port", str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # PIDファイル保存
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(self._server_process.pid))

            # サーバー起動待ち（最大10秒）
            _wait_for_server(self.port, timeout=10)

        except Exception as e:
            return {"success": False, "error": f"Server起動失敗: {e}"}

        # Flowテンプレート登録
        self._register_flows()

        # 自動ポーリングワーカー起動
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._poll_worker,
            daemon=True,
            name="jj-prefect-poll",
        )
        self._worker_thread.start()

        return {
            "success": True,
            "message": f"Prefect Server を起動しました (port: {self.port})",
            "url": f"http://localhost:{self.port}",
            "poll_interval": f"{self.poll_interval}分",
        }

    def stop(self) -> dict[str, Any]:
        """Prefect Server + ワーカーを停止"""
        # ワーカー停止
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)

        # Server停止
        if self._server_process is not None:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

        # PIDファイルからの停止（別プロセスで起動した場合）
        if self._pid_file.exists():
            try:
                import signal

                pid = int(self._pid_file.read_text().strip())
                import os

                os.kill(pid, signal.SIGTERM)
            except (ValueError, ProcessLookupError, OSError):
                pass
            self._pid_file.unlink(missing_ok=True)

        return {"success": True, "message": "Prefect Server を停止しました"}

    def status(self) -> dict[str, Any]:
        """Prefect Serverの状態を取得"""
        return {
            "running": self.is_running,
            "port": self.port,
            "url": f"http://localhost:{self.port}" if self.is_running else None,
            "poll_interval": f"{self.poll_interval}分" if self.is_running else None,
            "pid_file": str(self._pid_file),
        }

    def _register_flows(self) -> None:
        """jj組み込みFlowテンプレートをPrefectに登録"""
        try:
            from prefect import flow

            @flow(name="jj-poll", description="jj自動ポーリング: 完了ジョブの自動回収")
            def jj_poll_flow(project_root: str = str(self.project_root)) -> dict[str, Any]:
                from services.job.service import JobService

                svc = JobService(project_root=Path(project_root))
                completed = svc.collect(completed_only=True)
                return {
                    "collected_count": len(completed),
                    "job_ids": [j.job_id for j in completed],
                }

            @flow(name="jj-submit", description="jj ジョブ投入")
            def jj_submit_flow(
                targets: list[str],
                command_template: str = "",
                host_name: str = "",
                project_root: str = str(self.project_root),
            ) -> dict[str, Any]:
                from services.job.service import JobService

                svc = JobService(project_root=Path(project_root))
                jobs = svc.submit(
                    targets=targets,
                    command_template=command_template,
                    host_name=host_name or None,
                )
                return {
                    "submitted_count": len(jobs),
                    "job_ids": [j.job_id for j in jobs],
                }

            @flow(name="jj-collect", description="jj 結果回収")
            def jj_collect_flow(
                completed_only: bool = True,
                project_root: str = str(self.project_root),
            ) -> dict[str, Any]:
                from services.job.service import JobService

                svc = JobService(project_root=Path(project_root))
                collected = svc.collect(completed_only=completed_only)
                return {
                    "collected_count": len(collected),
                    "job_ids": [j.job_id for j in collected],
                }

            logger.info("jj Flows registered: jj-poll, jj-submit, jj-collect")

        except Exception as e:
            logger.warning("Flow registration failed: %s", e)

    def _poll_worker(self) -> None:
        """自動ポーリングワーカー（バックグラウンドスレッド）

        poll_interval分ごとに完了ジョブの自動回収を実行する。
        """
        while not self._stop_event.is_set():
            try:
                from services.job.service import JobService

                svc = JobService(project_root=self.project_root)
                collected = svc.collect(completed_only=True)
                if collected:
                    logger.info(
                        "Auto-collected %d job(s): %s",
                        len(collected),
                        [j.job_id for j in collected],
                    )
                    # Prefectに自動回収結果を記録
                    report_to_prefect("auto-collect", job_states=collected)
            except Exception as e:
                logger.debug("Auto-poll error: %s", e)

            # poll_interval分待機（1秒刻みでstop_eventをチェック）
            for _ in range(self.poll_interval * 60):
                if self._stop_event.is_set():
                    return
                time.sleep(1)


# ====================================================================
# ユーティリティ
# ====================================================================


def _wait_for_server(port: int, timeout: int = 10) -> bool:
    """Prefect Serverが応答可能になるまで待機

    Args:
        port: サーバーポート
        timeout: タイムアウト秒数

    Returns:
        True: サーバー応答確認、False: タイムアウト
    """
    import urllib.request

    url = f"http://127.0.0.1:{port}/api/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def get_prefect_status(project_root: Path) -> dict[str, Any]:
    """Prefectの状態を取得（CLIヘルパー）"""
    manager = JjPrefectManager(project_root)
    return manager.status()


def serialize_job_for_prefect(job: JobState) -> dict[str, Any]:
    """JobStateをPrefectアーティファクト用に変換"""
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "submitted_at": job.submitted_at,
        "completed_at": job.completed_at,
        "collected_at": job.collected_at,
        "remote_host": job.remote_host,
        "remote_dir": job.remote_dir,
        "command": job.command,
        "input_files": job.input_files,
        "output_files": job.output_files,
    }
