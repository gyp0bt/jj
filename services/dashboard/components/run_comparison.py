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

        # Run DAG可視化
        st.subheader("Run DAG")
        _render_run_dag(all_runs, query_svc)

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

        html = _generate_run_comparison_html(all_runs, query_svc)
        html += _generate_run_dag_html(all_runs, query_svc)
        return html


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

        st.dataframe(pd.DataFrame(table_data), width="stretch", hide_index=True)


def _render_run_dag(runs: list[Any], query_svc: Any) -> None:
    """Run間のデータフローをDAGとして可視化

    各Runの入力/出力を解析し、Run A の出力が Run B の入力に含まれる場合に
    A → B のデータフローエッジを描画する。
    """
    import streamlit as st

    if not runs:
        st.info("表示するRunがありません。")
        return

    # Run間のデータ依存関係を構築
    run_io_map: dict[int, Any] = {}
    output_to_run: dict[int, int] = {}  # output_node_id → run_id

    for run in runs:
        io = query_svc.get_run_io(run)
        run_io_map[run.id] = io
        for out_node in io.outputs:
            output_to_run[out_node.id] = run.id

    # Run間エッジ: Run A の出力 → Run B の入力
    dag_edges: list[tuple[int, int, list[str]]] = []  # (src_run_id, dst_run_id, shared_node_names)
    for run in runs:
        io = run_io_map[run.id]
        # 各入力ノードを生成したRunを探す
        predecessors: dict[int, list[str]] = {}  # src_run_id → [node_names]
        for in_node in io.inputs:
            src_run_id = output_to_run.get(in_node.id)
            if src_run_id is not None and src_run_id != run.id:
                predecessors.setdefault(src_run_id, []).append(in_node.name)
        for src_id, names in predecessors.items():
            dag_edges.append((src_id, run.id, names))

    # streamlit-agraphを試行
    if _try_render_run_dag_agraph(runs, run_io_map, dag_edges):
        return

    # フォールバック: graphviz
    if _try_render_run_dag_graphviz(runs, run_io_map, dag_edges):
        return

    st.info(
        "DAG表示にはstreamlit-agraphまたはgraphvizが必要です。\n"
        "`pip install streamlit-agraph` でインストールしてください。"
    )


def _try_render_run_dag_agraph(
    runs: list[Any],
    run_io_map: dict[int, Any],
    dag_edges: list[tuple[int, int, list[str]]],
) -> bool:
    """streamlit-agraphでRun DAGを描画。成功時True"""
    try:
        from streamlit_agraph import Config, Edge, Node, agraph
    except ImportError:
        return False

    status_colors = {
        "completed": "#10b981",
        "failed": "#ef4444",
        "running": "#f59e0b",
        "latent": "#8b5cf6",
    }

    nodes: list[Node] = []
    edges: list[Edge] = []
    run_by_id = {r.id: r for r in runs}

    for run in runs:
        status = run.properties.get("run_status", "unknown")
        color = status_colors.get(status, "#6b7280")
        run_type = run.properties.get("run_type", "run")
        duration = run.properties.get("duration_seconds", "")
        label = f"{run.name}\n[{run_type}]"
        if duration:
            label += f"\n{duration}s"

        nodes.append(
            Node(
                id=f"run_{run.id}",
                label=label,
                size=30,
                color=color,
                font={"size": 11},
                shape="box",
            )
        )

    # I/Oノード（共有ノードのみ表示 — 複数Runに関わるノード）
    # 全Runの入出力ノードIDを収集
    node_run_count: dict[int, int] = {}
    all_io_nodes: dict[int, Any] = {}
    for run in runs:
        io = run_io_map[run.id]
        for n in [*io.inputs, *io.outputs, *io.media]:
            node_run_count[n.id] = node_run_count.get(n.id, 0) + 1
            all_io_nodes[n.id] = n
    shared_node_ids = {nid for nid, count in node_run_count.items() if count > 1}

    # 共有ノードを小さいノードとして追加
    for nid in shared_node_ids:
        n = all_io_nodes[nid]
        nodes.append(
            Node(
                id=f"file_{nid}",
                label=n.name,
                size=15,
                color="#dbeafe",
                font={"size": 9},
                shape="ellipse",
            )
        )

    # Run → I/O エッジ（共有ノードのみ）
    for run in runs:
        io = run_io_map[run.id]
        for in_node in io.inputs:
            if in_node.id in shared_node_ids:
                edges.append(Edge(source=f"file_{in_node.id}", target=f"run_{run.id}", color="#93c5fd"))
        for out_node in io.outputs:
            if out_node.id in shared_node_ids:
                edges.append(Edge(source=f"run_{run.id}", target=f"file_{out_node.id}", color="#86efac"))
        for media_node in io.media:
            if media_node.id in shared_node_ids:
                edges.append(
                    Edge(
                        source=f"file_{media_node.id}",
                        target=f"run_{run.id}",
                        color="#c4b5fd",
                        dashes=True,
                    )
                )

    # Run間の直接エッジ（共有ノードがない場合のフォールバック）
    if not shared_node_ids:
        for src_id, dst_id, names in dag_edges:
            if src_id in run_by_id and dst_id in run_by_id:
                label = ", ".join(names[:2])
                if len(names) > 2:
                    label += f" +{len(names) - 2}"
                edges.append(
                    Edge(
                        source=f"run_{src_id}",
                        target=f"run_{dst_id}",
                        label=label,
                        color="#93c5fd",
                    )
                )

    config = Config(
        width=800,
        height=500,
        directed=True,
        physics=True,
        hierarchical=True,
    )

    agraph(nodes=nodes, edges=edges, config=config)
    return True


def _try_render_run_dag_graphviz(
    runs: list[Any],
    run_io_map: dict[int, Any],
    dag_edges: list[tuple[int, int, list[str]]],
) -> bool:
    """graphvizでRun DAGを描画（フォールバック）"""
    import re

    import streamlit as st

    status_colors = {
        "completed": "#10b981",
        "failed": "#ef4444",
        "running": "#f59e0b",
        "latent": "#8b5cf6",
    }

    def _sanitize(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", str(name))

    dot_lines = [
        "digraph RunDAG {",
        "  rankdir=TB;",
        '  node [shape=box, style="rounded,filled", fontsize=10];',
        '  edge [color="#93c5fd"];',
    ]

    run_by_id = {r.id: r for r in runs}

    # Runノード
    for run in runs:
        status = run.properties.get("run_status", "unknown")
        color = status_colors.get(status, "#d1d5db")
        run_type = run.properties.get("run_type", "run")
        label = f"{run.name}\\n[{run_type}]"
        node_id = f"run_{run.id}"
        dot_lines.append(f'  {node_id} [label="{label}", fillcolor="{color}"];')

    # 共有ノード検出
    node_run_count: dict[int, int] = {}
    all_io_nodes: dict[int, Any] = {}
    for run in runs:
        io = run_io_map[run.id]
        for n in [*io.inputs, *io.outputs, *io.media]:
            node_run_count[n.id] = node_run_count.get(n.id, 0) + 1
            all_io_nodes[n.id] = n
    shared_node_ids = {nid for nid, count in node_run_count.items() if count > 1}

    # 共有ファイルノード
    for nid in shared_node_ids:
        n = all_io_nodes[nid]
        node_id = f"file_{nid}"
        label = _sanitize(n.name)
        dot_lines.append(f'  {node_id} [label="{n.name}", shape=ellipse, fillcolor="#dbeafe", color="#3b82f6"];')

    # エッジ
    for run in runs:
        io = run_io_map[run.id]
        for in_node in io.inputs:
            if in_node.id in shared_node_ids:
                dot_lines.append(f'  file_{in_node.id} -> run_{run.id} [color="#93c5fd"];')
        for out_node in io.outputs:
            if out_node.id in shared_node_ids:
                dot_lines.append(f'  run_{run.id} -> file_{out_node.id} [color="#86efac"];')
        for media_node in io.media:
            if media_node.id in shared_node_ids:
                dot_lines.append(f'  file_{media_node.id} -> run_{run.id} [style=dashed, color="#c4b5fd"];')

    # 共有ノードがない場合は直接エッジ
    if not shared_node_ids:
        for src_id, dst_id, names in dag_edges:
            if src_id in run_by_id and dst_id in run_by_id:
                label = ", ".join(names[:2])
                if len(names) > 2:
                    label += f" +{len(names) - 2}"
                dot_lines.append(f'  run_{src_id} -> run_{dst_id} [label="{label}"];')

    dot_lines.append("}")

    try:
        st.graphviz_chart("\n".join(dot_lines), width="stretch")
        return True
    except Exception:
        return False


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
        st.dataframe(pd.DataFrame(prop_rows), width="stretch", hide_index=True)


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


def _generate_run_dag_html(runs: list[Any], query_svc: Any) -> str:
    """Run DAGのスタティックHTML生成（SVGベースのDAG表現）"""
    if not runs:
        return ""

    # データ依存関係を構築
    run_io_map: dict[int, Any] = {}
    output_to_run: dict[int, int] = {}

    for run in runs:
        io = query_svc.get_run_io(run)
        run_io_map[run.id] = io
        for out_node in io.outputs:
            output_to_run[out_node.id] = run.id

    dag_edges: list[tuple[int, int, list[str]]] = []
    for run in runs:
        io = run_io_map[run.id]
        predecessors: dict[int, list[str]] = {}
        for in_node in io.inputs:
            src_run_id = output_to_run.get(in_node.id)
            if src_run_id is not None and src_run_id != run.id:
                predecessors.setdefault(src_run_id, []).append(in_node.name)
        for src_id, names in predecessors.items():
            dag_edges.append((src_id, run.id, names))

    run_by_id = {r.id: r for r in runs}
    status_colors = {
        "completed": "#10b981",
        "failed": "#ef4444",
        "running": "#f59e0b",
        "latent": "#8b5cf6",
    }

    parts: list[str] = []
    parts.append("<h3>Run DAG</h3>")

    if not dag_edges:
        # 依存関係がない場合はRun一覧のみ
        parts.append('<div style="display:flex;flex-wrap:wrap;gap:12px;margin:16px 0;">')
        for run in runs:
            status = run.properties.get("run_status", "unknown")
            color = status_colors.get(status, "#6b7280")
            run_type = run.properties.get("run_type", "run")
            parts.append(
                f'<div style="border:2px solid {color};border-radius:8px;padding:8px 16px;'
                f'background:{color}22;">'
                f"<strong>{run.name}</strong><br>"
                f'<span style="font-size:0.85em;color:#666;">[{run_type}] {status}</span>'
                f"</div>"
            )
        parts.append("</div>")
        parts.append("<p><em>Run間のデータ依存関係はありません。</em></p>")
    else:
        # 依存関係テーブル
        parts.append('<table style="border-collapse:collapse;width:100%;margin:16px 0;">')
        parts.append("<thead><tr>")
        for h in ["上流Run", "→", "下流Run", "共有ノード"]:
            parts.append(f'<th style="border:1px solid #d1d5db;padding:6px 10px;text-align:left;">{h}</th>')
        parts.append("</tr></thead><tbody>")

        for src_id, dst_id, names in dag_edges:
            src = run_by_id.get(src_id)
            dst = run_by_id.get(dst_id)
            if src and dst:
                shared = ", ".join(names[:3])
                if len(names) > 3:
                    shared += f" +{len(names) - 3}"
                parts.append("<tr>")
                parts.append(f'<td style="border:1px solid #d1d5db;padding:4px 8px;">{src.name}</td>')
                parts.append('<td style="border:1px solid #d1d5db;padding:4px 8px;text-align:center;">→</td>')
                parts.append(f'<td style="border:1px solid #d1d5db;padding:4px 8px;">{dst.name}</td>')
                parts.append(f'<td style="border:1px solid #d1d5db;padding:4px 8px;">{shared}</td>')
                parts.append("</tr>")

        parts.append("</tbody></table>")

    return "\n".join(parts)
