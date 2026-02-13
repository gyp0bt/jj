"""Abaqus物性一覧ダッシュボードコネクター

Abaqus専用のダッシュボードページ「物性一覧」を提供するコネクター。
abaqus_materialノードの物性テーブル表示とカーブプロットを行う。

DashboardPageConnector.__init_subclass__により自動登録される。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import Any

from jj_types import Node
from services.dashboard.connectors import DashboardPageConnector

if False:  # TYPE_CHECKING
    from services.dashboard.data_provider import DashboardDataProvider


# ====================================================================
# Abaqus物性データプロバイダー関数
# ====================================================================


def get_material_table(provider: "DashboardDataProvider") -> list[dict[str, Any]]:
    """abaqus_materialノードの物性テーブルデータ

    全abaqus_materialノードの非テーブル型プロパティを
    フラットなテーブル行として返す。テーブル型データ（list[list]）は
    列名だけを表示用に含める。

    Args:
        provider: DashboardDataProvider

    Returns:
        行データのリスト
    """
    rows: list[dict[str, Any]] = []

    for node in provider.graph.nodes:
        if node.type != "abaqus_material":
            continue

        row: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
        }

        for key, value in node.properties.items():
            if key in ("path", "include_properties", "source_file"):
                continue
            # テーブル型データ（list[list]）はサマリのみ
            if isinstance(value, list) and value and isinstance(value[0], list):
                row[key] = f"[{len(value)}行]"
            elif isinstance(value, (dict, list)):
                row[key] = str(value)
            else:
                row[key] = value

        rows.append(row)

    return rows


def get_material_table_data(
    provider: "DashboardDataProvider",
    node_id: int,
    property_key: str,
) -> dict[str, Any] | None:
    """materialノードのテーブル型プロパティデータを取得

    plastic, elastic等のテーブル型データ（list[list[float]]）を返す。

    Args:
        provider: DashboardDataProvider
        node_id: materialノードID
        property_key: プロパティキー（例: "plastic", "elastic"）

    Returns:
        {
            "name": str,
            "property_key": str,
            "data": list[list[float]],
            "keywords": list[str],
        }
        見つからない場合はNone
    """
    node = provider._node_by_id.get(node_id)
    if node is None or node.type != "abaqus_material":
        return None

    value = node.properties.get(property_key)
    if not isinstance(value, list) or not value:
        return None

    # テーブル型（list[list]）かチェック
    if not isinstance(value[0], list):
        return None

    return {
        "name": node.name,
        "property_key": property_key,
        "data": value,
        "keywords": node.properties.get("keywords", []),
    }


def get_material_table_keys(
    provider: "DashboardDataProvider",
    node_id: int,
) -> list[str]:
    """materialノードのテーブル型プロパティキーを返す

    Args:
        provider: DashboardDataProvider
        node_id: materialノードID

    Returns:
        テーブル型プロパティキーのソート済みリスト
    """
    node = provider._node_by_id.get(node_id)
    if node is None or node.type != "abaqus_material":
        return []

    keys: list[str] = []
    for key, value in node.properties.items():
        if isinstance(value, list) and value and isinstance(value[0], list):
            keys.append(key)
    return sorted(keys)


# ====================================================================
# 物性カーブヘルパー関数
# ====================================================================


def guess_table_column_names(
    property_key: str,
    num_cols: int,
    material_curve_columns: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """テーブル型プロパティの列名をconfig設定から取得

    config.dashboard.material-curve-columnsに定義された列名を使用する。
    configにマッチしない場合はcol_0, col_1, ... で補完する。

    Args:
        property_key: プロパティキー（plastic, elastic等）
        num_cols: 列数
        material_curve_columns: config.dashboard.material-curve-columns

    Returns:
        列名のリスト
    """
    names: list[str] = []
    if material_curve_columns and property_key in material_curve_columns:
        entry = material_curve_columns[property_key]
        names = list(entry.get("columns", []))
    # 不足分はcol_Nで補完
    while len(names) < num_cols:
        names.append(f"col_{len(names)}")
    return names[:num_cols]


def get_curve_plot_axes(
    property_key: str,
    num_cols: int,
    material_curve_columns: dict[str, dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """物性カーブのプロットX/Y軸インデックスをconfigから取得

    configにx/yが指定されている場合はそれを使用。
    未指定の場合はデフォルト（x=0, y=1）を返す。

    Args:
        property_key: プロパティキー
        num_cols: 列数
        material_curve_columns: config.dashboard.material-curve-columns

    Returns:
        (x_index, y_index) タプル
    """
    x_idx = 0
    y_idx = min(1, num_cols - 1)
    if material_curve_columns and property_key in material_curve_columns:
        entry = material_curve_columns[property_key]
        if "x" in entry:
            x_idx = min(int(entry["x"]), num_cols - 1)
        if "y" in entry:
            y_idx = min(int(entry["y"]), num_cols - 1)
    return x_idx, y_idx


# ====================================================================
# Abaqus物性一覧ページ レンダリング
# ====================================================================


def _parse_material_curve_columns(
    raw_mcc: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """material-curve-columns設定を正規化

    config.yamlのconnectors.abaqus.material-curve-columnsセクションを
    {property_key: {columns: [...], x: int, y: int}} 形式に正規化する。

    Args:
        raw_mcc: 生の設定辞書

    Returns:
        正規化された設定辞書
    """
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_mcc, dict):
        return result
    for key, val in raw_mcc.items():
        if isinstance(val, dict):
            entry: dict[str, Any] = {}
            cols = val.get("columns", [])
            if isinstance(cols, list):
                entry["columns"] = [str(c) for c in cols]
            else:
                entry["columns"] = []
            if "x" in val:
                entry["x"] = int(val["x"])
            if "y" in val:
                entry["y"] = int(val["y"])
            result[str(key)] = entry
        elif isinstance(val, list):
            # 簡略形式: property_key: [col1, col2]
            result[str(key)] = {
                "columns": [str(c) for c in val],
            }
    return result


def _render_material_page(
    provider: "DashboardDataProvider",
    dashboard_config: Any = None,
) -> None:
    """物性一覧ビュー: abaqus_materialノードをテーブル表示＋ラインプロット"""
    import streamlit as st

    st.header("物性一覧")
    # コネクタ固有configからmaterial-curve-columns取得
    raw_mcc: dict[str, Any] = {}
    if dashboard_config is not None:
        get_fn = getattr(dashboard_config, "get_connector_config", None)
        if get_fn is not None:
            abq_cfg = get_fn("abaqus")
            raw_mcc = abq_cfg.get("material-curve-columns", {})
        else:
            # 後方互換: 旧形式(material_curve_columns属性)
            raw_mcc = getattr(dashboard_config, "material_curve_columns", None) or {}
    mcc = _parse_material_curve_columns(raw_mcc)

    mat_rows = get_material_table(provider)
    if not mat_rows:
        st.info(
            "abaqus_materialノードが見つかりません。"
            "material.inpファイルがパースされている必要があります。"
        )
        return

    # テーブル表示
    st.subheader("物性テーブル")
    import pandas as pd

    display_rows = []
    for r in mat_rows:
        row = {}
        for k, v in r.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
            else:
                row[k] = v
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    # AgGridを試行（共有ウィジェット使用）
    try:
        from services.dashboard.widgets import try_render_aggrid

        if not try_render_aggrid(df):
            st.dataframe(df, use_container_width=True, hide_index=True)
    except ImportError:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"物性数: {len(mat_rows)}")

    # テーブル型データ（plastic, elastic等）のラインプロット
    st.markdown("---")
    st.subheader("物性カーブ")

    mat_names = [r["name"] for r in mat_rows]
    selected_mat = st.selectbox("物性選択", mat_names)
    if not selected_mat:
        return

    mat_id = next((r["id"] for r in mat_rows if r["name"] == selected_mat), None)
    if mat_id is None:
        return

    table_keys = get_material_table_keys(provider, mat_id)
    if not table_keys:
        st.info("テーブル型データ（plastic, elastic等）がありません。")
        return

    selected_key = st.selectbox("プロパティ", table_keys)
    if not selected_key:
        return

    table_data = get_material_table_data(provider, mat_id, selected_key)
    if table_data is None:
        st.warning("データの取得に失敗しました。")
        return

    # テーブルとプロットを並べて表示
    col1, col2 = st.columns(2)

    with col1:
        # テーブル表示
        data_rows = table_data["data"]
        if data_rows:
            col_names = guess_table_column_names(
                selected_key, len(data_rows[0]), mcc
            )
            table_df = pd.DataFrame(data_rows, columns=col_names)
            st.dataframe(table_df, use_container_width=True, hide_index=True)

    with col2:
        # ラインプロット
        data_rows = table_data["data"]
        if data_rows and len(data_rows[0]) >= 2:
            col_names = guess_table_column_names(
                selected_key, len(data_rows[0]), mcc
            )
            x_idx, y_idx = get_curve_plot_axes(
                selected_key, len(data_rows[0]), mcc
            )
            try:
                import plotly.graph_objects as go

                fig = go.Figure()
                x_vals = [row[x_idx] for row in data_rows]
                y_vals = [row[y_idx] for row in data_rows]
                fig.add_trace(go.Scatter(
                    x=x_vals, y=y_vals,
                    mode="lines+markers",
                    name=selected_key,
                ))
                fig.update_layout(
                    xaxis_title=col_names[x_idx] if x_idx < len(col_names) else "X",
                    yaxis_title=col_names[y_idx] if y_idx < len(col_names) else "Y",
                    title=f"{selected_mat} - {selected_key}",
                    height=400,
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning("plotlyが必要です: pip install plotly")

    # 物性比較セクション
    st.markdown("---")
    _render_material_comparison(provider, mat_rows, mcc)

    # 物性使用関係セクション
    st.markdown("---")
    _render_material_usage(provider)


def _render_material_comparison(
    provider: "DashboardDataProvider",
    mat_rows: list[dict[str, Any]],
    mcc: dict[str, dict[str, Any]],
) -> None:
    """物性比較: 複数materialの同一プロパティカーブを重ね書き"""
    import streamlit as st

    st.subheader("物性比較")

    # 全materialのテーブル型プロパティキーを収集
    all_table_keys: set[str] = set()
    for r in mat_rows:
        node_id = r["id"]
        keys = get_material_table_keys(provider, node_id)
        all_table_keys.update(keys)

    if not all_table_keys:
        st.info("比較可能なテーブル型データがありません。")
        return

    sorted_table_keys = sorted(all_table_keys)
    compare_key = st.selectbox("比較プロパティ", sorted_table_keys, key="_mat_compare_key")
    if not compare_key:
        return

    # 選択プロパティを持つmaterialをフィルタ
    mat_names_with_key = []
    for r in mat_rows:
        keys = get_material_table_keys(provider, r["id"])
        if compare_key in keys:
            mat_names_with_key.append(r["name"])

    if not mat_names_with_key:
        st.info(f"'{compare_key}' データを持つ物性がありません。")
        return

    selected_mats = st.multiselect(
        "比較する物性",
        mat_names_with_key,
        default=mat_names_with_key[:min(5, len(mat_names_with_key))],
        key="_mat_compare_select",
    )

    if not selected_mats:
        st.info("物性を選択してください。")
        return

    # 重ね書きプロット
    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        for mat_name in selected_mats:
            mat_id = next(
                (r["id"] for r in mat_rows if r["name"] == mat_name), None
            )
            if mat_id is None:
                continue
            table_data = get_material_table_data(provider, mat_id, compare_key)
            if table_data is None:
                continue
            data_rows = table_data["data"]
            if not data_rows or len(data_rows[0]) < 2:
                continue
            x_idx, y_idx = get_curve_plot_axes(
                compare_key, len(data_rows[0]), mcc
            )
            x_vals = [row[x_idx] for row in data_rows]
            y_vals = [row[y_idx] for row in data_rows]
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                mode="lines+markers",
                name=mat_name,
            ))

        col_names = guess_table_column_names(compare_key, 2, mcc)
        x_label = col_names[0] if len(col_names) > 0 else "X"
        y_label = col_names[1] if len(col_names) > 1 else "Y"
        fig.update_layout(
            xaxis_title=x_label,
            yaxis_title=y_label,
            title=f"物性比較: {compare_key}",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")


# ====================================================================
# 物性-GOノード使用関係
# ====================================================================


def get_material_usage(
    provider: "DashboardDataProvider",
) -> list[dict[str, Any]]:
    """materialノードとgo_ノードの使用関係を取得

    uses_material関係をたどり、各materialがどのgo_ノードで使われているかを返す。

    Returns:
        [{"material_name": str, "material_id": int,
          "go_nodes": [{"name": str, "id": int}, ...]}]
    """
    results: list[dict[str, Any]] = []

    for node in provider.graph.nodes:
        if node.type != "abaqus_material":
            continue

        go_nodes: list[dict[str, Any]] = []
        for rel in provider._relations_by_node.get(node.id, []):
            if rel.label != "uses_material":
                continue
            # uses_material: go_node -> material_node (node1 → node2)
            go_id = rel.node1_id if rel.node2_id == node.id else rel.node2_id
            if go_id == node.id:
                continue
            go_node = provider._node_by_id.get(go_id)
            if go_node is None:
                continue
            name_lower = go_node.name.lower()
            if name_lower.startswith("go_") or name_lower == "go":
                go_nodes.append({"name": go_node.name, "id": go_node.id})

        results.append({
            "material_name": node.name,
            "material_id": node.id,
            "go_nodes": go_nodes,
        })

    return results


def _render_material_usage(
    provider: "DashboardDataProvider",
) -> None:
    """物性-GOノード使用関係テーブルを表示"""
    import streamlit as st

    st.subheader("物性使用関係")

    usage = get_material_usage(provider)
    if not usage:
        st.info("物性使用関係データがありません。")
        return

    import pandas as pd

    rows = []
    for item in usage:
        go_names = [g["name"] for g in item["go_nodes"]]
        rows.append({
            "物性名": item["material_name"],
            "使用GOノード数": len(go_names),
            "使用GOノード": ", ".join(go_names) if go_names else "（未使用）",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ====================================================================
# コネクター登録
# ====================================================================


class AbaqusMaterialPageConnector(DashboardPageConnector):
    """Abaqus物性一覧ページコネクター

    abaqus_materialノードが存在する場合にのみ「物性一覧」ページを提供する。
    """

    page_label = "物性一覧"
    connector_key = "abaqus"

    def is_available(self, provider: "DashboardDataProvider") -> bool:
        """abaqus_materialノードが1つ以上存在するか判定"""
        return any(n.type == "abaqus_material" for n in provider.graph.nodes)

    def render_page(
        self,
        provider: "DashboardDataProvider",
        dashboard_config: Any,
    ) -> None:
        """物性一覧ページをレンダリング"""
        _render_material_page(provider, dashboard_config)
