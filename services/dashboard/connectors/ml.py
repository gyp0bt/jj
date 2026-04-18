"""MLダッシュボードコネクター

ML/実験/最適化タスクのダッシュボードページを提供する。
Phase 5（M6）: MLOverview、モデルレジストリ、最適化ビュー、三層データフロー図。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.connectors import DashboardPageConnector
from services.dashboard.connectors.ml_query import (
    get_dataflow_graph_data,
    get_dataset_table,
    get_experiment_comparison_data,
    get_experiment_metric_keys,
    get_experiment_table,
    get_ml_relations,
    get_ml_summary,
    get_model_table,
    get_optimization_table,
    get_script_table,
    has_ml_nodes,
)

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


# ====================================================================
# Layer色定義
# ====================================================================

LAYER_COLORS = {
    1: "#4A90D9",  # CAE: 青
    2: "#50C878",  # ML: 緑
    3: "#FF8C00",  # Optimization: 橙
}

LAYER_LABELS = {
    1: "Layer 1: CAE",
    2: "Layer 2: ML/実験",
    3: "Layer 3: 最適化",
}

NODE_TYPE_LABELS = {
    "dataset": "データセット",
    "model_checkpoint": "チェックポイント",
    "serialized_model": "シリアライズモデル",
    "training_script": "学習スクリプト",
    "experiment_config": "実験設定",
    "experiment_metrics": "実験メトリクス",
    "optimization_study": "最適化スタディ",
    "optimization_config": "最適化設定",
    "trial_history": "試行履歴",
    "calculation_input": "CAE入力",
    "result": "CAE結果",
    "mesh": "メッシュ",
    "output": "出力",
    "asset": "アセット",
}


class MLOverviewPageConnector(DashboardPageConnector):
    """ML概要ページ: ML実験一覧・メトリクス比較・モデルレジストリ"""

    page_label = "ML概要"
    connector_key = "ml"

    def is_available(self, provider: DashboardDataProvider) -> bool:
        return has_ml_nodes(provider)

    def render(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        import streamlit as st

        cc = view.connector_config if hasattr(view, "connector_config") else {}
        tab = cc.get("tab", "")

        if not tab:
            # デフォルト: 全タブを表示
            st.header("ML概要")
            summary = get_ml_summary(provider)
            cols = st.columns(6)
            labels = [
                ("データセット", summary["datasets"]),
                ("モデル", summary["models"]),
                ("スクリプト", summary["scripts"]),
                ("設定", summary["configs"]),
                ("メトリクス", summary["metrics"]),
                ("最適化", summary["optimizations"]),
            ]
            for col, (label, count) in zip(cols, labels, strict=True):
                col.metric(label, count)
            st.markdown("---")
            tabs = st.tabs(["実験メトリクス", "データセット", "モデル", "スクリプト", "最適化", "リレーション"])
            with tabs[0]:
                _render_experiment_tab(provider)
            with tabs[1]:
                _render_dataset_tab(provider)
            with tabs[2]:
                _render_model_tab(provider)
            with tabs[3]:
                _render_script_tab(provider)
            with tabs[4]:
                _render_optimization_tab(provider)
            with tabs[5]:
                _render_relations_tab(provider)
            return

        # tabが指定されていれば対応タブのみ表示
        metric_keys_str = cc.get("metric_keys", "")
        experiment_ids_str = cc.get("experiment_ids", "")
        metric_keys = [k.strip() for k in metric_keys_str.split(",") if k.strip()] if metric_keys_str else None
        experiment_ids = [e.strip() for e in experiment_ids_str.split(",") if e.strip()] if experiment_ids_str else None

        st.header(f"ML概要 — {view.name}")
        tab_map = {
            "experiment": lambda: _render_experiment_tab(provider),
            "dataset": lambda: _render_dataset_tab(provider),
            "model": lambda: _render_model_tab(provider),
            "script": lambda: _render_script_tab(provider),
            "optimization": lambda: _render_optimization_tab(provider),
            "relation": lambda: _render_relations_tab(provider),
            "comparison": lambda: _render_metrics_comparison(provider, metric_keys, experiment_ids),
        }
        renderer = tab_map.get(tab)
        if renderer:
            renderer()
        else:
            st.warning(f"不明なタブ: {tab}")

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        return _generate_overview_html(provider)

    def generate_saved_view_html(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> str:
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        tab = cc.get("tab", "")
        metric_keys_str = cc.get("metric_keys", "")
        experiment_ids_str = cc.get("experiment_ids", "")

        if tab == "comparison":
            metric_keys = [k.strip() for k in metric_keys_str.split(",") if k.strip()] if metric_keys_str else None
            experiment_ids = (
                [e.strip() for e in experiment_ids_str.split(",") if e.strip()] if experiment_ids_str else None
            )
            return _generate_comparison_html(provider, metric_keys, experiment_ids)

        return self.generate_html(provider, dashboard_config)

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        return [
            {
                "key": "tab",
                "label": "表示タブ",
                "type": "text",
                "help": "experiment/dataset/model/script/optimization/relation/comparison",
            },
            {
                "key": "metric_keys",
                "label": "比較メトリクス（カンマ区切り）",
                "type": "text",
                "help": "例: best_val_accuracy,best_val_loss",
            },
            {
                "key": "experiment_ids",
                "label": "実験ID（カンマ区切り）",
                "type": "text",
                "help": "空欄で全実験を比較",
            },
        ]


class MLDataFlowPageConnector(DashboardPageConnector):
    """三層データフロー図: CAE/ML/最適化のデータフロー可視化"""

    page_label = "MLデータフロー"
    connector_key = "ml_dataflow"

    def is_available(self, provider: DashboardDataProvider) -> bool:
        return has_ml_nodes(provider)

    def render(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        import streamlit as st

        cc = view.connector_config if hasattr(view, "connector_config") else {}
        layer_filter = cc.get("layer_filter", "")

        graph_data = get_dataflow_graph_data(provider)

        # レイヤー統計
        lc = graph_data["layer_counts"]
        cols = st.columns(3)
        for col, (layer_id, label) in zip(cols, LAYER_LABELS.items(), strict=True):
            col.metric(label, lc.get(layer_id, 0))

        st.markdown("---")

        # レイヤーフィルタ適用
        if layer_filter:
            try:
                layers = {int(x.strip()) for x in layer_filter.split(",") if x.strip()}
                graph_data["nodes"] = [n for n in graph_data["nodes"] if n["layer"] in layers]
                filtered_ids = {n["id"] for n in graph_data["nodes"]}
                graph_data["edges"] = [
                    e for e in graph_data["edges"] if e["source"] in filtered_ids and e["target"] in filtered_ids
                ]
            except ValueError:
                st.warning(f"不正なレイヤーフィルタ: {layer_filter}")

        _render_dataflow_graph(provider, graph_data)

        if not layer_filter:
            st.markdown("---")
            st.subheader("層間リレーション")
            cross_edges = [e for e in graph_data["edges"] if e["cross_layer"]]
            if cross_edges:
                _render_edge_table(provider, cross_edges)
            else:
                st.info("層間リレーションはありません。")

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        return _generate_dataflow_html(provider)

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        return [
            {
                "key": "layer_filter",
                "label": "表示レイヤー（カンマ区切り）",
                "type": "text",
                "help": "1=CAE, 2=ML, 3=最適化。空欄で全レイヤー表示",
            },
        ]


# ====================================================================
# タブ描画関数
# ====================================================================


def _render_experiment_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_experiment_table(provider)
    if not rows:
        st.info("実験メトリクスノードがありません。")
        return
    st.subheader(f"実験メトリクス ({len(rows)}件)")
    _render_dataframe(rows)

    # メトリクス比較プロット
    if len(rows) >= 2:
        _render_metrics_comparison(provider)


def _render_dataset_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_dataset_table(provider)
    if not rows:
        st.info("データセットノードがありません。")
        return
    st.subheader(f"データセット ({len(rows)}件)")
    _render_dataframe(rows)


def _render_model_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_model_table(provider)
    if not rows:
        st.info("モデルノードがありません。")
        return
    st.subheader(f"モデル ({len(rows)}件)")
    _render_dataframe(rows)


def _render_script_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_script_table(provider)
    if not rows:
        st.info("学習スクリプトノードがありません。")
        return
    st.subheader(f"学習スクリプト ({len(rows)}件)")
    _render_dataframe(rows)


def _render_optimization_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_optimization_table(provider)
    if not rows:
        st.info("最適化関連ノードがありません。")
        return
    st.subheader(f"最適化 ({len(rows)}件)")
    _render_dataframe(rows)


def _render_relations_tab(provider: DashboardDataProvider) -> None:
    import streamlit as st

    rows = get_ml_relations(provider)
    if not rows:
        st.info("ML関連リレーションがありません。")
        return
    st.subheader(f"MLリレーション ({len(rows)}件)")
    _render_dataframe(rows)


# ====================================================================
# メトリクス比較プロット
# ====================================================================


def _render_metrics_comparison(
    provider: DashboardDataProvider,
    metric_keys: list[str] | None = None,
    experiment_ids: list[str] | None = None,
) -> None:
    """実験間メトリクス比較プロットを描画"""
    import streamlit as st

    st.markdown("---")
    st.subheader("メトリクス比較")

    available_keys = get_experiment_metric_keys(provider)
    if not available_keys:
        st.info("比較可能なメトリクスがありません。")
        return

    # メトリクス選択UI（ビュー保存指定がなければインタラクティブ選択）
    if metric_keys is None:
        selected_keys = st.multiselect(
            "比較するメトリクス",
            available_keys,
            default=available_keys[:3],
            key="ml_comparison_metrics",
        )
    else:
        selected_keys = [k for k in metric_keys if k in available_keys]

    if not selected_keys:
        return

    comp_data = get_experiment_comparison_data(provider, metric_keys=selected_keys, experiment_ids=experiment_ids)
    experiments = comp_data["experiments"]
    if len(experiments) < 2:
        st.info("比較に必要な実験数（2以上）がありません。")
        return

    _render_comparison_chart(experiments, selected_keys)


def _render_comparison_chart(
    experiments: list[dict[str, Any]],
    metric_keys: list[str],
) -> None:
    """メトリクス比較チャートを描画（plotly優先、フォールバック: テーブル）"""
    import streamlit as st

    exp_labels = [e.get("id") or e.get("dir") or e["name"] for e in experiments]

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        for key in metric_keys:
            values = [e.get(key) for e in experiments]
            fig.add_trace(
                go.Bar(
                    name=key,
                    x=exp_labels,
                    y=values,
                    text=[f"{v:.4g}" if isinstance(v, float) else str(v) for v in values],
                    textposition="auto",
                )
            )

        fig.update_layout(
            barmode="group",
            xaxis_title="実験",
            yaxis_title="メトリクス値",
            legend_title="メトリクス",
            height=400,
        )
        st.plotly_chart(fig, width="stretch")

    except ImportError:
        # plotly未使用時: テーブル形式で比較
        rows: list[dict[str, Any]] = []
        for exp, label in zip(experiments, exp_labels, strict=True):
            row: dict[str, Any] = {"実験": label}
            for key in metric_keys:
                row[key] = exp.get(key, "")
            rows.append(row)
        _render_dataframe(rows)


# ====================================================================
# データフローグラフ描画
# ====================================================================


def _render_dataflow_graph(
    provider: DashboardDataProvider,
    graph_data: dict[str, Any],
) -> None:
    """三層データフローをstreamlit-agraphで描画（フォールバック: テーブル表示）"""
    import streamlit as st

    nodes_data = graph_data["nodes"]
    edges_data = graph_data["edges"]

    if not nodes_data:
        st.info("データフローノードがありません。")
        return

    # streamlit-agraphが利用可能か確認
    try:
        from streamlit_agraph import Config, Edge, Node, agraph

        agraph_nodes = []
        for n in nodes_data:
            layer = n["layer"]
            color = LAYER_COLORS.get(layer, "#999999")
            type_label = NODE_TYPE_LABELS.get(n["type"], n["type"])
            agraph_nodes.append(
                Node(
                    id=str(n["id"]),
                    label=f"{n['name']}\n({type_label})",
                    color=color,
                    size=20,
                    shape="dot",
                )
            )

        agraph_edges = []
        for e in edges_data:
            agraph_edges.append(
                Edge(
                    source=str(e["source"]),
                    target=str(e["target"]),
                    label=e["label"],
                    color="#FF4444" if e["cross_layer"] else "#666666",
                    dashes=e["cross_layer"],
                )
            )

        config = Config(
            width=900,
            height=500,
            directed=True,
            physics=True,
            hierarchical=True,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
        )

        agraph(nodes=agraph_nodes, edges=agraph_edges, config=config)

    except ImportError:
        # agraph未インストール: テーブル表示にフォールバック
        st.warning("streamlit-agraph が未インストールのため、テーブル形式で表示します。")
        _render_dataflow_as_table(nodes_data, edges_data)


def _render_dataflow_as_table(
    nodes_data: list[dict[str, Any]],
    edges_data: list[dict[str, Any]],
) -> None:
    """データフローをテーブル形式で表示（agraph未使用時のフォールバック）"""
    import streamlit as st

    # レイヤー別ノード表示
    for layer_id, label in LAYER_LABELS.items():
        layer_nodes = [n for n in nodes_data if n["layer"] == layer_id]
        if not layer_nodes:
            continue
        st.markdown(f"#### {label} ({len(layer_nodes)}件)")
        rows = []
        for n in layer_nodes:
            type_label = NODE_TYPE_LABELS.get(n["type"], n["type"])
            rows.append(
                {
                    "名前": n["name"],
                    "タイプ": type_label,
                    "パス": n.get("path", ""),
                }
            )
        _render_dataframe(rows)


def _render_edge_table(
    provider: DashboardDataProvider,
    edges: list[dict[str, Any]],
) -> None:
    """エッジテーブルの表示"""
    node_map = {n.id: n for n in provider.graph.nodes}
    rows: list[dict[str, Any]] = []
    for e in edges:
        src = node_map.get(e["source"])
        tgt = node_map.get(e["target"])
        if src is None or tgt is None:
            continue
        rows.append(
            {
                "リレーション": e["label"],
                "始点": src.name,
                "始点タイプ": NODE_TYPE_LABELS.get(src.type, src.type),
                "終点": tgt.name,
                "終点タイプ": NODE_TYPE_LABELS.get(tgt.type, tgt.type),
            }
        )
    if rows:
        _render_dataframe(rows)


# ====================================================================
# 共通ヘルパー
# ====================================================================


def _render_dataframe(rows: list[dict[str, Any]]) -> None:
    """DataFrameを表示（pandas利用可能時はst.dataframe, 不可時はst.table）"""
    import streamlit as st

    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
    except ImportError:
        st.table(rows)


# ====================================================================
# HTMLエクスポート
# ====================================================================


def _generate_overview_html(provider: DashboardDataProvider) -> str:
    """ML概要のHTML断片を生成"""
    summary = get_ml_summary(provider)
    parts: list[str] = ['<div class="ml-overview">']
    parts.append("<h2>ML概要</h2>")

    # サマリー
    parts.append('<div class="ml-summary" style="display:flex;gap:2em;margin:1em 0;">')
    labels = [
        ("データセット", summary["datasets"]),
        ("モデル", summary["models"]),
        ("スクリプト", summary["scripts"]),
        ("設定", summary["configs"]),
        ("メトリクス", summary["metrics"]),
        ("最適化", summary["optimizations"]),
    ]
    for label, count in labels:
        parts.append(f'<div><strong>{label}</strong><br><span style="font-size:1.5em;">{count}</span></div>')
    parts.append("</div>")

    # 実験テーブル
    exp_rows = get_experiment_table(provider)
    if exp_rows:
        parts.append(f"<h3>実験メトリクス ({len(exp_rows)}件)</h3>")
        parts.append(_rows_to_html_table(exp_rows))

    # モデルテーブル
    model_rows = get_model_table(provider)
    if model_rows:
        parts.append(f"<h3>モデル ({len(model_rows)}件)</h3>")
        parts.append(_rows_to_html_table(model_rows))

    # データセットテーブル
    ds_rows = get_dataset_table(provider)
    if ds_rows:
        parts.append(f"<h3>データセット ({len(ds_rows)}件)</h3>")
        parts.append(_rows_to_html_table(ds_rows))

    parts.append("</div>")
    return "\n".join(parts)


def _generate_dataflow_html(provider: DashboardDataProvider) -> str:
    """三層データフローのHTML断片を生成"""
    graph_data = get_dataflow_graph_data(provider)
    parts: list[str] = ['<div class="ml-dataflow">']
    parts.append("<h2>三層データフロー</h2>")

    lc = graph_data["layer_counts"]
    parts.append('<div style="display:flex;gap:2em;margin:1em 0;">')
    for layer_id, label in LAYER_LABELS.items():
        color = LAYER_COLORS[layer_id]
        count = lc.get(layer_id, 0)
        parts.append(
            f'<div style="border-left:4px solid {color};padding-left:0.5em;">'
            f"<strong>{label}</strong><br>{count}件</div>"
        )
    parts.append("</div>")

    # ノードテーブル（レイヤー別）
    for layer_id, label in LAYER_LABELS.items():
        layer_nodes = [n for n in graph_data["nodes"] if n["layer"] == layer_id]
        if not layer_nodes:
            continue
        parts.append(f"<h3>{label} ({len(layer_nodes)}件)</h3>")
        rows = [
            {
                "名前": n["name"],
                "タイプ": NODE_TYPE_LABELS.get(n["type"], n["type"]),
                "パス": n.get("path", ""),
            }
            for n in layer_nodes
        ]
        parts.append(_rows_to_html_table(rows))

    # 層間リレーション
    cross_edges = [e for e in graph_data["edges"] if e["cross_layer"]]
    if cross_edges:
        node_map = {n.id: n for n in provider.graph.nodes}
        parts.append(f"<h3>層間リレーション ({len(cross_edges)}件)</h3>")
        rows = []
        for e in cross_edges:
            src = node_map.get(e["source"])
            tgt = node_map.get(e["target"])
            if src and tgt:
                rows.append(
                    {
                        "リレーション": e["label"],
                        "始点": src.name,
                        "終点": tgt.name,
                    }
                )
        if rows:
            parts.append(_rows_to_html_table(rows))

    parts.append("</div>")
    return "\n".join(parts)


def _generate_comparison_html(
    provider: DashboardDataProvider,
    metric_keys: list[str] | None = None,
    experiment_ids: list[str] | None = None,
) -> str:
    """メトリクス比較のHTML断片を生成"""
    comp_data = get_experiment_comparison_data(provider, metric_keys, experiment_ids)
    experiments = comp_data["experiments"]
    keys = comp_data["metric_keys"]

    parts: list[str] = ['<div class="ml-comparison">']
    parts.append("<h2>メトリクス比較</h2>")

    if not experiments or not keys:
        parts.append("<p>比較データがありません。</p>")
        parts.append("</div>")
        return "\n".join(parts)

    rows: list[dict[str, Any]] = []
    for exp in experiments:
        row: dict[str, Any] = {"実験": exp.get("id") or exp.get("dir") or exp["name"]}
        for key in keys:
            val = exp.get(key, "")
            row[key] = f"{val:.4g}" if isinstance(val, float) else str(val)
        rows.append(row)

    parts.append(_rows_to_html_table(rows))
    parts.append("</div>")
    return "\n".join(parts)


def _rows_to_html_table(rows: list[dict[str, Any]]) -> str:
    """辞書リストからHTMLテーブルを生成"""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    parts = ['<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;margin:0.5em 0;">']
    parts.append("<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>")
    for row in rows:
        cells = "".join(f"<td>{row.get(h, '')}</td>" for h in headers)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</table>")
    return "\n".join(parts)
