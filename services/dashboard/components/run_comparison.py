"""Run比較ダッシュボードコンポーネント

RunQueryServiceを利用してRunノードの一覧・比較・トレーサビリティを
ダッシュボード上で操作するページコンポーネント。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class RunComparisonViewConfig(ViewConfig):
    """Run比較ビュー設定コンポーネント"""

    view_type = "run_comparison"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}


class RunComparisonPage(PageComponent[RunComparisonViewConfig]):
    """Run比較ダッシュボードページ"""

    page_key = "run_comparison"
    page_label = "Run比較"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.run.query import RunQueryService

        st.header("Run比較ダッシュボード")

        graph = provider.graph
        query_svc = RunQueryService(graph)

        all_runs = query_svc.get_runs()
        if not all_runs:
            st.info("Runノードが見つかりません。")
            return

        # フィルタ: run_type
        run_types = sorted({r.properties.get("run_type", "") for r in all_runs})
        selected_type = st.selectbox(
            "Run タイプ",
            ["(すべて)", *run_types],
            key="_run_cmp_type",
        )
        if selected_type != "(すべて)":
            all_runs = [r for r in all_runs if r.properties.get("run_type") == selected_type]

        # Run一覧テーブル
        st.subheader(f"Run一覧 ({len(all_runs)}件)")
        _render_run_table(all_runs)

        # Run選択（比較用）
        run_names = [f"{r.name} (id={r.id})" for r in all_runs]
        if len(all_runs) >= 2:
            st.subheader("Run比較")
            col1, col2 = st.columns(2)
            with col1:
                sel_a = st.selectbox("Run A", run_names, key="_run_cmp_a")
            with col2:
                sel_b = st.selectbox("Run B", run_names, index=min(1, len(run_names) - 1), key="_run_cmp_b")

            idx_a = run_names.index(sel_a)
            idx_b = run_names.index(sel_b)

            if idx_a != idx_b:
                _render_run_diff(query_svc, all_runs[idx_a], all_runs[idx_b])
            else:
                st.warning("異なるRunを選択してください。")

        # 選択Runの比較グループ
        if all_runs:
            st.subheader("比較グループ探索")
            sel_run_name = st.selectbox("基準Run", run_names, key="_run_cmp_base")
            base_run = all_runs[run_names.index(sel_run_name)]
            groups = query_svc.find_comparable_runs(base_run)
            if groups:
                for g in groups:
                    st.markdown(f"**軸: {g.axis.value}** — {len(g.runs)}件")
                    st.caption(f"共通: {g.common_aspects}, 差異: {g.varying_aspects}")
            else:
                st.caption("比較可能なRunが見つかりません。")

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        self.render_page(provider, dashboard_config, **kwargs)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.run.query import RunQueryService

        graph = provider.graph
        query_svc = RunQueryService(graph)
        all_runs = query_svc.get_runs()

        if not all_runs:
            return "<p>Runノードが見つかりません。</p>"

        return _generate_run_comparison_html(all_runs, query_svc)


# ====================================================================
# 描画ヘルパー
# ====================================================================


def _render_run_table(runs: list[Any]) -> None:
    """Run一覧をテーブル表示"""
    import streamlit as st

    table_data: list[dict[str, Any]] = []
    for r in runs:
        table_data.append(
            {
                "ID": r.id,
                "名前": r.name,
                "タイプ": r.properties.get("run_type", ""),
                "ステータス": r.properties.get("run_status", ""),
                "検出": r.properties.get("discovery", ""),
                "開始": r.properties.get("started_at", ""),
                "実行時間(秒)": r.properties.get("duration_seconds", ""),
                "コマンド": r.properties.get("command", ""),
            }
        )
    if table_data:
        import pandas as pd

        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)


def _render_run_diff(query_svc: Any, run_a: Any, run_b: Any) -> None:
    """2つのRunの差分を表示"""
    import streamlit as st

    diff = query_svc.diff_runs(run_a, run_b)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Run A**: {run_a.name}")
        st.caption(
            f"入力: {len(diff.common_inputs) + len(diff.diff_inputs[0])}件, "
            f"出力: {len(diff.common_outputs) + len(diff.diff_outputs[0])}件"
        )
    with col2:
        st.markdown(f"**Run B**: {run_b.name}")
        st.caption(
            f"入力: {len(diff.common_inputs) + len(diff.diff_inputs[1])}件, "
            f"出力: {len(diff.common_outputs) + len(diff.diff_outputs[1])}件"
        )

    # 共通ノード
    if diff.common_inputs:
        st.markdown(f"**共通入力**: {', '.join(n.name for n in diff.common_inputs)}")
    if diff.common_media:
        st.markdown(f"**共通メディア**: {', '.join(n.name for n in diff.common_media)}")

    # 差分ノード
    if diff.diff_inputs[0] or diff.diff_inputs[1]:
        st.markdown("**入力差分**")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            for n in diff.diff_inputs[0]:
                st.markdown(f"- A のみ: `{n.name}`")
        with dcol2:
            for n in diff.diff_inputs[1]:
                st.markdown(f"- B のみ: `{n.name}`")

    # プロパティ差分
    if diff.property_diffs:
        st.markdown("**プロパティ差分**")
        import pandas as pd

        prop_rows: list[dict[str, Any]] = []
        for key, (va, vb) in sorted(diff.property_diffs.items()):
            prop_rows.append({"プロパティ": key, "Run A": va, "Run B": vb})
        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True, hide_index=True)


# ====================================================================
# HTML生成
# ====================================================================


def _generate_run_comparison_html(runs: list[Any], query_svc: Any) -> str:
    """Run比較のスタティックHTML生成"""
    parts: list[str] = []
    parts.append("<h2>Run比較ダッシュボード</h2>")
    parts.append(f"<p>{len(runs)}件のRunが登録されています。</p>")

    # Run一覧テーブル
    parts.append('<table style="border-collapse:collapse;width:100%;margin-bottom:16px;">')
    parts.append("<thead><tr>")
    for h in ["ID", "名前", "タイプ", "ステータス", "検出", "開始", "実行時間(秒)"]:
        parts.append(f'<th style="border:1px solid #d1d5db;padding:6px 10px;text-align:left;">{h}</th>')
    parts.append("</tr></thead><tbody>")

    for r in runs:
        parts.append("<tr>")
        for val in [
            r.id,
            r.name,
            r.properties.get("run_type", ""),
            r.properties.get("run_status", ""),
            r.properties.get("discovery", ""),
            r.properties.get("started_at", ""),
            r.properties.get("duration_seconds", ""),
        ]:
            parts.append(f'<td style="border:1px solid #d1d5db;padding:4px 8px;">{val}</td>')
        parts.append("</tr>")

    parts.append("</tbody></table>")
    return "\n".join(parts)
