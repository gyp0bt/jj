"""Job Monitorダッシュボードページ (T5-8)

リモートジョブの状態をリアルタイムで表示するダッシュボードコネクター。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.connectors import DashboardPageConnector

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


class JobMonitorPageConnector(DashboardPageConnector):
    """ジョブモニターページ

    投入済みジョブの状態一覧、ステータス別集計、詳細表示を提供する。
    """

    page_label = "Job Monitor"
    connector_key = "job_monitor"

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """ジョブストレージが存在する場合に利用可能"""
        from pathlib import Path

        project_root = Path.cwd()
        jobs_dir = project_root / ".j2" / "storage" / "jobs"
        return jobs_dir.exists() and any(jobs_dir.glob("job-*.yaml"))

    def render(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        """ジョブモニターページを描画"""
        _ = view  # ジョブ一覧はリアルタイム、view configを参照しない
        import streamlit as st

        from services.job.models import JobStatus
        from services.job.service import JobService

        st.header("Job Monitor")

        service = JobService()
        all_jobs = service.list_jobs()

        if not all_jobs:
            st.info("投入済みジョブはありません。")
            return

        # ステータス別集計
        status_counts: dict[str, int] = {}
        for job in all_jobs:
            status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1

        cols = st.columns(len(status_counts))
        for col, (status, count) in zip(cols, status_counts.items(), strict=False):
            col.metric(label=status.upper(), value=count)

        st.divider()

        # フィルタ
        filter_options = ["すべて"] + [s.value for s in JobStatus]
        selected = st.selectbox("ステータスフィルタ", filter_options, index=0)

        if selected != "すべて":
            filtered = [j for j in all_jobs if j.status.value == selected]
        else:
            filtered = all_jobs

        # ジョブテーブル
        if filtered:
            table_data = []
            for job in filtered:
                submitted = job.submitted_at[:19] if job.submitted_at else ""
                table_data.append(
                    {
                        "Job ID": job.job_id,
                        "Status": job.status.value,
                        "Host": job.remote_host,
                        "Command": job.command[:50] + ("..." if len(job.command) > 50 else ""),
                        "Submitted": submitted,
                    }
                )
            st.dataframe(table_data, width="stretch")
        else:
            st.info("該当するジョブがありません。")

        st.divider()

        # ジョブ詳細
        job_ids = [j.job_id for j in all_jobs]
        if job_ids:
            selected_job_id = st.selectbox("ジョブ詳細を表示", ["(選択してください)", *job_ids])
            if selected_job_id != "(選択してください)":
                job = service.get_job(selected_job_id)
                if job:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**ステータス:** `{job.status.value}`")
                        st.markdown(f"**ホスト:** {job.remote_host}")
                        st.markdown(f"**リモートDir:** `{job.remote_dir}`")
                        st.markdown(f"**ローカルDir:** `{job.local_dir}`")
                    with col2:
                        st.markdown(f"**コマンド:** `{job.command}`")
                        st.markdown(f"**投入日時:** {job.submitted_at}")
                        if job.completed_at:
                            st.markdown(f"**完了日時:** {job.completed_at}")
                        if job.collected_at:
                            st.markdown(f"**回収日時:** {job.collected_at}")

                    if job.input_files:
                        st.markdown(f"**入力ファイル:** {', '.join(job.input_files)}")
                    if job.output_files:
                        st.markdown(f"**出力ファイル:** {', '.join(job.output_files)}")
                    if job.properties:
                        st.json(job.properties)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """ジョブモニターのHTML断片を生成"""
        from services.job.service import JobService

        service = JobService()
        all_jobs = service.list_jobs()

        if not all_jobs:
            return "<p>投入済みジョブはありません。</p>"

        rows = []
        for job in all_jobs:
            submitted = job.submitted_at[:19] if job.submitted_at else ""
            status_color = {
                "submitted": "#1f77b4",
                "running": "#ff7f0e",
                "completed": "#2ca02c",
                "collected": "#7f7f7f",
                "failed": "#d62728",
            }.get(job.status.value, "#333")
            rows.append(
                f"<tr>"
                f"<td>{job.job_id}</td>"
                f'<td style="color:{status_color};font-weight:bold">{job.status.value}</td>'
                f"<td>{job.remote_host}</td>"
                f"<td>{submitted}</td>"
                f"</tr>"
            )

        return (
            "<h2>Job Monitor</h2>"
            '<table border="1" cellpadding="4" cellspacing="0">'
            "<tr><th>Job ID</th><th>Status</th><th>Host</th><th>Submitted</th></tr>"
            + "".join(rows)
            + f"</table><p>合計: {len(all_jobs)}件</p>"
        )
