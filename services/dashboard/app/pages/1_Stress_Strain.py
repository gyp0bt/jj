"""応力–ひずみ曲線ページ

go_ ノード（ABQ inp）のテーブルを AgGrid で表示し、フィルタ/選択された
ケースについて配列プロパティ（RF.U3-REFJIG vs RF.RF3-REFJIG）を
公称応力–ひずみ曲線に換算してプロットする。

断面積 S は半径 ``radius`` [mm] から ``S = π·(radius/2·1e-3)²`` で求め、
反力を ``y = RF3 / S · 2`` として応力に換算する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from jj.services.dashboard.data_provider import DashboardDataProvider
from jj.services.dashboard.widgets import try_render_aggrid
from jj.services.graph import GraphService

X_KEY = "RF.U3-REFJIG"
Y_KEY = "RF.RF3-REFJIG"
DISPLAY_COLUMNS = ["id", "name", "idx", "v", "radius"]


@st.cache_resource
def load_provider() -> DashboardDataProvider:
    svc = GraphService()
    gm = svc.load(resolve_externalized=True)
    return DashboardDataProvider(graph=gm, project_root=Path("./"))


def build_go_table(provider: DashboardDataProvider) -> pd.DataFrame:
    """ABQ inp の go_ ノードをプロパティ展開した DataFrame に変換"""
    rows = provider.get_go_table(filters={"type": "ABQ inp"})
    all_cols: set[str] = set()
    for r in rows:
        all_cols.update(r)
    data: dict[str, list] = defaultdict(list)
    for r in rows:
        for k in all_cols:
            data[k].append(r.get(k))
    return pd.DataFrame(data)


def main() -> None:
    st.set_page_config(page_title="応力-ひずみ", page_icon="📈", layout="wide")
    st.title("📈 応力–ひずみ曲線")

    provider = load_provider()
    df = build_go_table(provider)
    if df.empty:
        st.warning("ABQ inp ノードが見つかりません。`jj parse` を実行してください。")
        return

    df.index = df["id"].to_numpy()
    present = [c for c in DISPLAY_COLUMNS if c in df.columns]
    table_df = df.loc[:, present]

    # テーブル表示（AgGrid。未インストール時は通常テーブルにフォールバック）
    if not try_render_aggrid(table_df):
        st.info("streamlit-aggrid が未インストールのため通常テーブルで表示します。")
        st.dataframe(table_df)
        st.session_state["filtered_df"] = table_df

    df_filtered = st.session_state.get("filtered_df")
    if df_filtered is None or df_filtered.empty:
        st.info("表示する行がありません。")
        return
    if "radius" not in df_filtered.columns or "id" not in df_filtered.columns:
        st.error("プロット元データに 'id' / 'radius' 列がありません。")
        return

    df_filtered = df_filtered.copy()
    df_filtered.index = df_filtered["id"].to_numpy()
    df_filtered["radius"] = df_filtered["radius"].astype("float32")
    # 断面積 S [m^2]
    df_filtered["S"] = np.pi * ((df_filtered["radius"] / 2.0 * 1e-3) ** 2)

    fig = go.Figure()
    for node_id, row in df_filtered.iterrows():
        xy = provider.get_array_plot_data(node_id=int(node_id), x_key=X_KEY, y_keys=[Y_KEY])
        if xy is None:
            continue
        series = xy["series"][0]
        y_values = np.array(series["values"], dtype=float) / row["S"] * 2.0
        fig.add_trace(go.Scatter(x=xy["x_values"], y=y_values, name=xy["name"], mode="lines"))

    fig.update_layout(xaxis_title=X_KEY, yaxis_title=f"{Y_KEY} / S × 2")
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
