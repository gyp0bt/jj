"""Abaqusダッシュボードコネクター（描画層）

Abaqus専用のダッシュボードページを提供するコネクター群。
- 「物性一覧」: abaqus_materialノードの物性テーブル表示とカーブプロット
- 「メッシュ品質」: go_ノードおよびelsetの品質サマリー
- 「ジョブサマリー」: 解析ステータス・エラー・警告の集約

DashboardPageConnector.__init_subclass__により自動登録される。

## 責務分離（status-078）
- **描画層（本ファイル）**: Streamlit UIの構築・ユーザー操作の処理
- **クエリ層（abaqus_query.py）**: 物性データ取得・列名推定・軸設定の純粋ロジック

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import Any

from services.dashboard.connectors import DashboardPageConnector
from services.dashboard.connectors.abaqus_query import (
    get_curve_plot_axes,
    get_elset_quality_summary,
    get_job_summary,
    get_material_table,
    get_material_table_data,
    get_material_table_keys,
    get_material_usage,
    get_mesh_quality_summary,
    guess_table_column_names,
    parse_material_curve_columns,
)

if False:  # TYPE_CHECKING
    from services.dashboard.data_provider import DashboardDataProvider


def _render_material_page(
    provider: DashboardDataProvider,
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
    mcc = parse_material_curve_columns(raw_mcc)

    mat_rows = get_material_table(provider)
    if not mat_rows:
        st.info("abaqus_materialノードが見つかりません。material.inpファイルがパースされている必要があります。")
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
            col_names = guess_table_column_names(selected_key, len(data_rows[0]), mcc)
            table_df = pd.DataFrame(data_rows, columns=col_names)
            st.dataframe(table_df, use_container_width=True, hide_index=True)

    with col2:
        # ラインプロット
        data_rows = table_data["data"]
        if data_rows and len(data_rows[0]) >= 2:
            col_names = guess_table_column_names(selected_key, len(data_rows[0]), mcc)
            x_idx, y_idx = get_curve_plot_axes(selected_key, len(data_rows[0]), mcc)
            try:
                import plotly.graph_objects as go

                fig = go.Figure()
                x_vals = [row[x_idx] for row in data_rows]
                y_vals = [row[y_idx] for row in data_rows]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines+markers",
                        name=selected_key,
                    )
                )
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
    provider: DashboardDataProvider,
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
        default=mat_names_with_key[: min(5, len(mat_names_with_key))],
        key="_mat_compare_select",
    )

    if not selected_mats:
        st.info("物性を選択してください。")
        return

    # 比較データの収集（プロット + CSVエクスポート用）
    import pandas as pd

    comparison_data: list[dict[str, Any]] = []
    num_cols = 2  # デフォルト

    for mat_name in selected_mats:
        mat_id = next((r["id"] for r in mat_rows if r["name"] == mat_name), None)
        if mat_id is None:
            continue
        table_data = get_material_table_data(provider, mat_id, compare_key)
        if table_data is None:
            continue
        data_rows = table_data["data"]
        if not data_rows or len(data_rows[0]) < 2:
            continue
        num_cols = len(data_rows[0])
        x_idx, y_idx = get_curve_plot_axes(compare_key, num_cols, mcc)
        col_names = guess_table_column_names(compare_key, num_cols, mcc)
        for row in data_rows:
            entry: dict[str, Any] = {"material": mat_name}
            for ci, cn in enumerate(col_names):
                if ci < len(row):
                    entry[cn] = row[ci]
            comparison_data.append(entry)

    # 重ね書きプロット
    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        col_names = guess_table_column_names(compare_key, num_cols, mcc)
        x_idx, y_idx = get_curve_plot_axes(compare_key, num_cols, mcc)

        for mat_name in selected_mats:
            mat_id = next((r["id"] for r in mat_rows if r["name"] == mat_name), None)
            if mat_id is None:
                continue
            table_data = get_material_table_data(provider, mat_id, compare_key)
            if table_data is None:
                continue
            data_rows = table_data["data"]
            if not data_rows or len(data_rows[0]) < 2:
                continue
            x_vals = [row[x_idx] for row in data_rows]
            y_vals = [row[y_idx] for row in data_rows]
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines+markers",
                    name=mat_name,
                )
            )

        x_label = col_names[x_idx] if x_idx < len(col_names) else "X"
        y_label = col_names[y_idx] if y_idx < len(col_names) else "Y"
        fig.update_layout(
            xaxis_title=x_label,
            yaxis_title=y_label,
            title=f"物性比較: {compare_key}",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")

    # CSVエクスポートボタン
    if comparison_data:
        csv_df = pd.DataFrame(comparison_data)
        csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="比較データCSVダウンロード",
            data=csv_bytes,
            file_name=f"material_comparison_{compare_key}.csv",
            mime="text/csv",
        )


# get_material_usage は abaqus_query.py からインポート済み


def _render_material_usage(
    provider: DashboardDataProvider,
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
        rows.append(
            {
                "物性名": item["material_name"],
                "使用GOノード数": len(go_names),
                "使用GOノード": ", ".join(go_names) if go_names else "（未使用）",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _format_quality_dict(quality: dict[str, Any]) -> dict[str, str]:
    """品質辞書をフラットな表示用に変換"""
    result: dict[str, str] = {}
    for metric, stats in quality.items():
        if isinstance(stats, dict):
            min_v = stats.get("min", "")
            max_v = stats.get("max", "")
            mean_v = stats.get("mean", "")
            result[f"{metric}_min"] = f"{min_v:.4g}" if isinstance(min_v, (int, float)) else str(min_v)
            result[f"{metric}_max"] = f"{max_v:.4g}" if isinstance(max_v, (int, float)) else str(max_v)
            result[f"{metric}_mean"] = f"{mean_v:.4g}" if isinstance(mean_v, (int, float)) else str(mean_v)
    return result


def _render_mesh_quality_summary(
    provider: DashboardDataProvider,
) -> None:
    """メッシュ品質サマリーテーブルを表示"""
    import streamlit as st

    st.subheader("メッシュ品質サマリー")

    mesh_rows = get_mesh_quality_summary(provider)
    if not mesh_rows:
        st.info("メッシュ品質データがありません。")
        return

    import pandas as pd

    display_rows = []
    for r in mesh_rows:
        row: dict[str, Any] = {
            "GOノード": r["go_name"],
            "節点数": r["node_count"],
            "要素数": r["element_count"],
        }
        # 要素タイプを文字列化
        etypes = r.get("element_types", {})
        if isinstance(etypes, dict) and etypes:
            row["要素タイプ"] = ", ".join(f"{k}:{v}" for k, v in etypes.items())
        # 品質メトリクスを展開
        quality = r.get("quality", {})
        if isinstance(quality, dict):
            row.update(_format_quality_dict(quality))
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_elset_quality_summary(
    provider: DashboardDataProvider,
) -> None:
    """Elset品質サマリーテーブルを表示"""
    import streamlit as st

    st.subheader("Elset品質サマリー")

    elset_rows = get_elset_quality_summary(provider)
    if not elset_rows:
        st.info("Elset品質データがありません。")
        return

    import pandas as pd

    display_rows = []
    for r in elset_rows:
        row: dict[str, Any] = {
            "Elset名": r["elset_name"],
            "メッシュソース": r.get("mesh_source", ""),
            "要素数": r["element_count"],
            "材料": r.get("material", ""),
        }
        quality = r.get("quality", {})
        if isinstance(quality, dict):
            row.update(_format_quality_dict(quality))
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_mesh_quality_page(
    provider: DashboardDataProvider,
) -> None:
    """メッシュ品質ビュー: go_ノードおよびelsetの品質サマリーを表示"""
    import streamlit as st

    st.header("メッシュ品質")

    # メッシュ品質サマリーセクション
    _render_mesh_quality_summary(provider)

    # Elset品質サマリーセクション
    st.markdown("---")
    _render_elset_quality_summary(provider)


def _render_job_summary_page(
    provider: DashboardDataProvider,
) -> None:
    """Abaqusジョブサマリーページを表示"""
    import streamlit as st

    st.header("Abaqusジョブサマリー")

    job_rows = get_job_summary(provider)
    if not job_rows:
        st.info("ジョブサマリーデータがありません。")
        return

    import pandas as pd

    display_rows = []
    for r in job_rows:
        row: dict[str, Any] = {
            "GOノード": r["go_name"],
            "解析ステータス": r["analysis_status"],
        }
        if "cpu_time" in r:
            row["CPU時間(sec)"] = r["cpu_time"]
        if "wallclock_time" in r:
            row["経過時間(sec)"] = r["wallclock_time"]
        # エラー・警告を集約
        errors: list[str] = []
        warnings: list[str] = []
        for key in ("sta_errors", "msg_errors", "dat_errors"):
            src = key.split("_")[0]
            for e in r.get(key, []):
                errors.append(f"[{src}] {e}")
        for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
            src = key.split("_")[0]
            for w in r.get(key, []):
                warnings.append(f"[{src}] {w}")
        if errors:
            row["エラー数"] = len(errors)
        if warnings:
            row["警告数"] = len(warnings)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)

    try:
        from services.dashboard.widgets import try_render_aggrid

        if not try_render_aggrid(df):
            st.dataframe(df, use_container_width=True, hide_index=True)
    except ImportError:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.caption(f"ジョブ数: {len(job_rows)}")

    # 個別ジョブのエラー・警告詳細
    st.markdown("---")
    st.subheader("エラー・警告詳細")
    job_names = [r["go_name"] for r in job_rows]
    selected_job = st.selectbox("ジョブ選択", job_names, key="_job_detail_select")
    if selected_job:
        job = next((r for r in job_rows if r["go_name"] == selected_job), None)
        if job:
            all_errors: list[str] = []
            all_warnings: list[str] = []
            for key in ("sta_errors", "msg_errors", "dat_errors"):
                src = key.split("_")[0]
                for e in job.get(key, []):
                    all_errors.append(f"[{src}] {e}")
            for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
                src = key.split("_")[0]
                for w in job.get(key, []):
                    all_warnings.append(f"[{src}] {w}")

            if all_errors:
                st.error(f"エラー ({len(all_errors)}件)")
                for e in all_errors:
                    st.text(e)
            else:
                st.success("エラーなし")

            if all_warnings:
                st.warning(f"警告 ({len(all_warnings)}件)")
                for w in all_warnings:
                    st.text(w)
            else:
                st.info("警告なし")


# ====================================================================
# コネクター登録
# ====================================================================


class AbaqusMaterialPageConnector(DashboardPageConnector):
    """Abaqus物性一覧ページコネクター

    abaqus_materialノードが存在する場合にのみ「物性一覧」ページを提供する。

    保存済みビュー（connector_config）で利用可能なキー:
      - material_name: 表示する物性名（未指定時は全物性）
      - property_key: カーブ表示するプロパティキー（例: "plastic"）
      - compare_materials: 比較表示する物性名リスト
    """

    page_label = "物性一覧"
    connector_key = "abaqus"

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        return [
            {"key": "material_name", "label": "物性名", "type": "text", "help": "特定物性の詳細表示（空で全物性）"},
            {"key": "property_key", "label": "プロパティキー", "type": "text", "help": "カーブ表示キー（例: plastic）"},
            {
                "key": "compare_materials",
                "label": "比較物性名（カンマ区切り）",
                "type": "text",
                "help": "複数物性を比較表示",
            },
        ]

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """abaqus_materialノードが1つ以上存在するか判定"""
        return any(n.type == "abaqus_material" for n in provider.graph.nodes)

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> None:
        """物性一覧ページをレンダリング"""
        _render_material_page(provider, dashboard_config)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        """保存済みビュー: connector_configに基づいて物性カーブを表示

        connector_config:
          material_name: 特定物性のカーブを表示
          property_key: 表示するプロパティキー
          compare_materials: 比較する物性名リスト
        """
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        mat_name = cc.get("material_name", "")
        prop_key = cc.get("property_key", "")
        compare_mats = cc.get("compare_materials", [])

        if not mat_name and not compare_mats:
            # connector_config未設定: デフォルトのrender_pageに委譲
            self.render_page(provider, dashboard_config)
            return

        _render_material_saved_view(provider, dashboard_config, mat_name, prop_key, compare_mats)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """物性一覧のHTML断片を生成"""
        return _generate_material_html(provider, dashboard_config)

    def generate_saved_view_html(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> str:
        """保存済みビューのHTML断片を生成"""
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        mat_name = cc.get("material_name", "")
        prop_key = cc.get("property_key", "")
        compare_mats = cc.get("compare_materials", [])

        if not mat_name and not compare_mats:
            return self.generate_html(provider, dashboard_config)

        return _generate_material_saved_view_html(provider, dashboard_config, mat_name, prop_key, compare_mats)


class AbaqusMeshQualityPageConnector(DashboardPageConnector):
    """Abaqusメッシュ品質ページコネクター

    go_ノードにメッシュ関連データ（mesh_element_count, mesh_quality等）が
    存在する場合に「メッシュ品質」ページを提供する。

    保存済みビュー（connector_config）で利用可能なキー:
      - go_name: 特定GOノードのメッシュ品質のみ表示
      - show_elset: elset品質サマリーを表示するか（デフォルトTrue）
    """

    page_label = "メッシュ品質"
    connector_key = "abaqus"

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        return [
            {"key": "go_name", "label": "GOノード名", "type": "text", "help": "特定GOノードに絞り込み"},
            {"key": "show_elset", "label": "elset品質を表示", "type": "checkbox", "help": "elset品質サマリーの表示"},
        ]

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """メッシュ関連データが1つ以上存在するか判定"""
        for n in provider.graph.nodes:
            name_lower = n.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue
            if any(k in n.properties for k in ("mesh_quality", "mesh_element_count", "mesh_node_count")):
                return True
        # elsetノードの品質データも確認
        return any(n.type == "abaqus_elset" and "quality" in n.properties for n in provider.graph.nodes)

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> None:
        """メッシュ品質ページをレンダリング"""
        _render_mesh_quality_page(provider)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        """保存済みビュー: connector_configに基づいてメッシュ品質を表示"""
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        go_name = cc.get("go_name", "")
        show_elset = cc.get("show_elset", True)

        if not go_name and show_elset:
            self.render_page(provider, dashboard_config)
            return

        _render_mesh_quality_saved_view(provider, go_name, show_elset)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """メッシュ品質のHTML断片を生成"""
        return _generate_mesh_quality_html(provider)


class AbaqusJobSummaryPageConnector(DashboardPageConnector):
    """Abaqusジョブサマリーページコネクター

    go_ノードにジョブ関連データ（analysis_status等）が存在する場合に
    「ジョブサマリー」ページを提供する。

    保存済みビュー（connector_config）で利用可能なキー:
      - status_filter: 解析ステータスでフィルタ（例: "COMPLETED"）
      - go_name: 特定GOノードのジョブサマリーのみ表示
    """

    page_label = "ジョブサマリー"
    connector_key = "abaqus"

    @classmethod
    def get_connector_config_schema(cls) -> list[dict[str, Any]]:
        return [
            {
                "key": "status_filter",
                "label": "ステータスフィルタ",
                "type": "text",
                "help": "解析ステータスでフィルタ（例: COMPLETED）",
            },
            {"key": "go_name", "label": "GOノード名", "type": "text", "help": "特定GOノードに絞り込み"},
        ]

    def is_available(self, provider: DashboardDataProvider) -> bool:
        """ジョブ関連データが1つ以上存在するか判定"""
        for n in provider.graph.nodes:
            name_lower = n.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue
            if any(k in n.properties for k in ("analysis_status", "cpu_time", "wallclock_time")):
                return True
        return False

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> None:
        """ジョブサマリーページをレンダリング"""
        _render_job_summary_page(provider)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> None:
        """保存済みビュー: connector_configに基づいてジョブサマリーを表示"""
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        status_filter = cc.get("status_filter", "")
        go_name = cc.get("go_name", "")

        if not status_filter and not go_name:
            self.render_page(provider, dashboard_config)
            return

        _render_job_summary_saved_view(provider, status_filter, go_name)

    def generate_html(
        self,
        provider: DashboardDataProvider,
        dashboard_config: Any,
    ) -> str:
        """ジョブサマリーのHTML断片を生成"""
        return _generate_job_summary_html(provider)

    def generate_saved_view_html(
        self,
        provider: DashboardDataProvider,
        view: Any,
        dashboard_config: Any,
    ) -> str:
        """保存済みビューのHTML断片を生成"""
        cc = view.connector_config if hasattr(view, "connector_config") else {}
        status_filter = cc.get("status_filter", "")
        go_name = cc.get("go_name", "")

        if not status_filter and not go_name:
            return self.generate_html(provider, dashboard_config)

        return _generate_job_summary_saved_view_html(provider, status_filter, go_name)


# ====================================================================
# 保存済みビュー用描画関数（Streamlit依存）
# ====================================================================


def _render_material_saved_view(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    material_name: str,
    property_key: str,
    compare_materials: list[str],
) -> None:
    """物性一覧の保存済みビューをレンダリング

    connector_configで指定された物性名・プロパティに絞った表示を行う。
    compare_materialsが指定されている場合は比較表示。
    """
    import streamlit as st

    # コネクタ固有configからmaterial-curve-columns取得
    raw_mcc: dict[str, Any] = {}
    if dashboard_config is not None:
        get_fn = getattr(dashboard_config, "get_connector_config", None)
        if get_fn is not None:
            abq_cfg = get_fn("abaqus")
            raw_mcc = abq_cfg.get("material-curve-columns", {})
        else:
            raw_mcc = getattr(dashboard_config, "material_curve_columns", None) or {}
    mcc = parse_material_curve_columns(raw_mcc)

    mat_rows = get_material_table(provider)
    if not mat_rows:
        st.info("abaqus_materialノードが見つかりません。")
        return

    if compare_materials:
        # 比較モード: 指定された物性の特定プロパティカーブを重ね書き
        import pandas as pd

        if not property_key:
            st.warning("compare_materialsを使用する場合はproperty_keyの指定が必要です。")
            return

        st.subheader(f"物性比較: {property_key}")

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            num_cols = 2
            for mat_name_iter in compare_materials:
                mat_id = next((r["id"] for r in mat_rows if r["name"] == mat_name_iter), None)
                if mat_id is None:
                    continue
                table_data = get_material_table_data(provider, mat_id, property_key)
                if table_data is None:
                    continue
                data_rows = table_data["data"]
                if not data_rows or len(data_rows[0]) < 2:
                    continue
                num_cols = len(data_rows[0])
                x_idx, y_idx = get_curve_plot_axes(property_key, num_cols, mcc)
                x_vals = [row[x_idx] for row in data_rows]
                y_vals = [row[y_idx] for row in data_rows]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines+markers",
                        name=mat_name_iter,
                    )
                )

            col_names = guess_table_column_names(property_key, num_cols, mcc)
            x_idx, y_idx = get_curve_plot_axes(property_key, num_cols, mcc)
            fig.update_layout(
                xaxis_title=col_names[x_idx] if x_idx < len(col_names) else "X",
                yaxis_title=col_names[y_idx] if y_idx < len(col_names) else "Y",
                title=f"物性比較: {property_key}",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.warning("plotlyが必要です: pip install plotly")
        return

    # 単一物性モード: material_nameの詳細表示
    mat_row = next((r for r in mat_rows if r["name"] == material_name), None)
    if mat_row is None:
        st.warning(f"物性 '{material_name}' が見つかりません。")
        return

    mat_id = mat_row["id"]

    import pandas as pd

    # 物性テーブル（1行）
    st.subheader(f"物性: {material_name}")
    display_row = {}
    for k, v in mat_row.items():
        if isinstance(v, (dict, list)):
            display_row[k] = str(v)
        else:
            display_row[k] = v
    df = pd.DataFrame([display_row])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # プロパティカーブ
    if property_key:
        table_keys = [property_key]
    else:
        table_keys = get_material_table_keys(provider, mat_id)

    for tk in table_keys:
        table_data = get_material_table_data(provider, mat_id, tk)
        if table_data is None:
            continue
        data_rows = table_data["data"]
        if not data_rows or len(data_rows[0]) < 2:
            continue

        num_cols = len(data_rows[0])
        col_names = guess_table_column_names(tk, num_cols, mcc)
        x_idx, y_idx = get_curve_plot_axes(tk, num_cols, mcc)

        col1, col2 = st.columns(2)
        with col1:
            table_df = pd.DataFrame(data_rows, columns=col_names)
            st.dataframe(table_df, use_container_width=True, hide_index=True)
        with col2:
            try:
                import plotly.graph_objects as go

                fig = go.Figure()
                x_vals = [row[x_idx] for row in data_rows]
                y_vals = [row[y_idx] for row in data_rows]
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="lines+markers",
                        name=tk,
                    )
                )
                fig.update_layout(
                    xaxis_title=col_names[x_idx] if x_idx < len(col_names) else "X",
                    yaxis_title=col_names[y_idx] if y_idx < len(col_names) else "Y",
                    title=f"{material_name} - {tk}",
                    height=400,
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.warning("plotlyが必要です: pip install plotly")


def _render_mesh_quality_saved_view(
    provider: DashboardDataProvider,
    go_name: str,
    show_elset: bool,
) -> None:
    """メッシュ品質の保存済みビューをレンダリング

    go_nameフィルターとelset表示制御をサポート。
    """
    import streamlit as st

    st.header("メッシュ品質")

    # メッシュ品質サマリー（go_nameフィルタ）
    mesh_rows = get_mesh_quality_summary(provider)
    if go_name:
        mesh_rows = [r for r in mesh_rows if r["go_name"] == go_name]

    if mesh_rows:
        import pandas as pd

        st.subheader("メッシュ品質サマリー")
        display_rows = []
        for r in mesh_rows:
            row: dict[str, Any] = {
                "GOノード": r["go_name"],
                "節点数": r["node_count"],
                "要素数": r["element_count"],
            }
            etypes = r.get("element_types", {})
            if isinstance(etypes, dict) and etypes:
                row["要素タイプ"] = ", ".join(f"{k}:{v}" for k, v in etypes.items())
            quality = r.get("quality", {})
            if isinstance(quality, dict):
                row.update(_format_quality_dict(quality))
            display_rows.append(row)
        df = pd.DataFrame(display_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("メッシュ品質データがありません。")

    # Elset品質サマリー
    if show_elset:
        st.markdown("---")
        _render_elset_quality_summary(provider)


def _render_job_summary_saved_view(
    provider: DashboardDataProvider,
    status_filter: str,
    go_name: str,
) -> None:
    """ジョブサマリーの保存済みビューをレンダリング

    status_filterとgo_nameによるフィルタリングをサポート。
    """
    import streamlit as st

    st.header("Abaqusジョブサマリー")

    job_rows = get_job_summary(provider)

    # フィルタ適用
    if status_filter:
        job_rows = [r for r in job_rows if r.get("analysis_status") == status_filter]
    if go_name:
        job_rows = [r for r in job_rows if r["go_name"] == go_name]

    if not job_rows:
        st.info("条件に合致するジョブサマリーデータがありません。")
        return

    import pandas as pd

    display_rows = []
    for r in job_rows:
        row: dict[str, Any] = {
            "GOノード": r["go_name"],
            "解析ステータス": r["analysis_status"],
        }
        if "cpu_time" in r:
            row["CPU時間(sec)"] = r["cpu_time"]
        if "wallclock_time" in r:
            row["経過時間(sec)"] = r["wallclock_time"]
        errors: list[str] = []
        warnings: list[str] = []
        for key in ("sta_errors", "msg_errors", "dat_errors"):
            errors.extend(r.get(key, []))
        for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
            warnings.extend(r.get(key, []))
        if errors:
            row["エラー数"] = len(errors)
        if warnings:
            row["警告数"] = len(warnings)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"ジョブ数: {len(job_rows)}")


# ====================================================================
# HTML生成関数（Streamlit非依存）
# ====================================================================


def _generate_material_html(
    provider: DashboardDataProvider,
    dashboard_config: Any = None,
) -> str:
    """物性一覧のHTML断片を生成"""
    import pandas as pd

    mat_rows = get_material_table(provider)
    if not mat_rows:
        return "<p>abaqus_materialノードが見つかりません。</p>"

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
    sections = [
        "<h3>物性テーブル</h3>",
        f'<p class="caption">物性数: {len(mat_rows)}</p>',
        df.to_html(index=False, classes="dataframe"),
    ]

    # 物性使用関係
    usage = get_material_usage(provider)
    if usage:
        usage_rows = []
        for item in usage:
            go_names = [g["name"] for g in item["go_nodes"]]
            usage_rows.append(
                {
                    "物性名": item["material_name"],
                    "使用GOノード数": len(go_names),
                    "使用GOノード": ", ".join(go_names) if go_names else "（未使用）",
                }
            )
        usage_df = pd.DataFrame(usage_rows)
        sections.append("<h3>物性使用関係</h3>")
        sections.append(usage_df.to_html(index=False, classes="dataframe"))

    return "\n".join(sections)


def _generate_mesh_quality_html(
    provider: DashboardDataProvider,
) -> str:
    """メッシュ品質のHTML断片を生成"""
    import pandas as pd

    sections: list[str] = []

    # メッシュ品質サマリー
    mesh_rows = get_mesh_quality_summary(provider)
    if mesh_rows:
        display_rows = []
        for r in mesh_rows:
            row: dict[str, Any] = {
                "GOノード": r["go_name"],
                "節点数": r["node_count"],
                "要素数": r["element_count"],
            }
            etypes = r.get("element_types", {})
            if isinstance(etypes, dict) and etypes:
                row["要素タイプ"] = ", ".join(f"{k}:{v}" for k, v in etypes.items())
            quality = r.get("quality", {})
            if isinstance(quality, dict):
                row.update(_format_quality_dict(quality))
            display_rows.append(row)
        df = pd.DataFrame(display_rows)
        sections.append("<h3>メッシュ品質サマリー</h3>")
        sections.append(df.to_html(index=False, classes="dataframe"))

    # Elset品質サマリー
    elset_rows = get_elset_quality_summary(provider)
    if elset_rows:
        display_rows = []
        for r in elset_rows:
            row = {
                "Elset名": r["elset_name"],
                "メッシュソース": r.get("mesh_source", ""),
                "要素数": r["element_count"],
                "材料": r.get("material", ""),
            }
            quality = r.get("quality", {})
            if isinstance(quality, dict):
                row.update(_format_quality_dict(quality))
            display_rows.append(row)
        df = pd.DataFrame(display_rows)
        sections.append("<h3>Elset品質サマリー</h3>")
        sections.append(df.to_html(index=False, classes="dataframe"))

    return "\n".join(sections) if sections else ""


def _generate_job_summary_html(
    provider: DashboardDataProvider,
) -> str:
    """ジョブサマリーのHTML断片を生成"""
    import pandas as pd

    job_rows = get_job_summary(provider)
    if not job_rows:
        return "<p>ジョブサマリーデータがありません。</p>"

    display_rows = []
    for r in job_rows:
        row: dict[str, Any] = {
            "GOノード": r["go_name"],
            "解析ステータス": r["analysis_status"],
        }
        if "cpu_time" in r:
            row["CPU時間(sec)"] = r["cpu_time"]
        if "wallclock_time" in r:
            row["経過時間(sec)"] = r["wallclock_time"]
        errors: list[str] = []
        warnings: list[str] = []
        for key in ("sta_errors", "msg_errors", "dat_errors"):
            errors.extend(r.get(key, []))
        for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
            warnings.extend(r.get(key, []))
        if errors:
            row["エラー数"] = len(errors)
        if warnings:
            row["警告数"] = len(warnings)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    sections = [
        f'<p class="caption">ジョブ数: {len(job_rows)}</p>',
        df.to_html(index=False, classes="dataframe"),
    ]

    # エラー・警告詳細
    for r in job_rows:
        all_errors: list[str] = []
        all_warnings: list[str] = []
        for key in ("sta_errors", "msg_errors", "dat_errors"):
            src = key.split("_")[0]
            for e in r.get(key, []):
                all_errors.append(f"[{src}] {e}")
        for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
            src = key.split("_")[0]
            for w in r.get(key, []):
                all_warnings.append(f"[{src}] {w}")

        if all_errors or all_warnings:
            sections.append(f"<h4>{r['go_name']}</h4>")
            if all_errors:
                sections.append(f'<div style="color:#dc2626">エラー ({len(all_errors)}件):<ul>')
                for e in all_errors:
                    sections.append(f"<li>{e}</li>")
                sections.append("</ul></div>")
            if all_warnings:
                sections.append(f'<div style="color:#d97706">警告 ({len(all_warnings)}件):<ul>')
                for w in all_warnings:
                    sections.append(f"<li>{w}</li>")
                sections.append("</ul></div>")

    return "\n".join(sections)


def _generate_material_saved_view_html(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    material_name: str,
    property_key: str,
    compare_materials: list[str],
) -> str:
    """物性一覧の保存済みビューHTML断片を生成"""
    import pandas as pd

    raw_mcc: dict[str, Any] = {}
    if dashboard_config is not None:
        get_fn = getattr(dashboard_config, "get_connector_config", None)
        if get_fn is not None:
            abq_cfg = get_fn("abaqus")
            raw_mcc = abq_cfg.get("material-curve-columns", {})
        else:
            raw_mcc = getattr(dashboard_config, "material_curve_columns", None) or {}
    mcc = parse_material_curve_columns(raw_mcc)

    mat_rows = get_material_table(provider)
    if not mat_rows:
        return "<p>abaqus_materialノードが見つかりません。</p>"

    sections: list[str] = []

    if compare_materials and property_key:
        sections.append(f"<h3>物性比較: {property_key}</h3>")
        comparison_data: list[dict[str, Any]] = []
        for mat_name_iter in compare_materials:
            mat_id = next((r["id"] for r in mat_rows if r["name"] == mat_name_iter), None)
            if mat_id is None:
                continue
            table_data = get_material_table_data(provider, mat_id, property_key)
            if table_data is None:
                continue
            data_rows = table_data["data"]
            if not data_rows:
                continue
            num_cols = len(data_rows[0])
            col_names = guess_table_column_names(property_key, num_cols, mcc)
            for row in data_rows:
                entry: dict[str, Any] = {"material": mat_name_iter}
                for ci, cn in enumerate(col_names):
                    if ci < len(row):
                        entry[cn] = row[ci]
                comparison_data.append(entry)
        if comparison_data:
            csv_df = pd.DataFrame(comparison_data)
            sections.append(csv_df.to_html(index=False, classes="dataframe"))
    elif material_name:
        mat_row = next((r for r in mat_rows if r["name"] == material_name), None)
        if mat_row is None:
            return f"<p>物性 '{material_name}' が見つかりません。</p>"
        sections.append(f"<h3>物性: {material_name}</h3>")
        display_row = {k: (str(v) if isinstance(v, (dict, list)) else v) for k, v in mat_row.items()}
        df = pd.DataFrame([display_row])
        sections.append(df.to_html(index=False, classes="dataframe"))

        mat_id = mat_row["id"]
        keys_to_show = [property_key] if property_key else get_material_table_keys(provider, mat_id)
        for tk in keys_to_show:
            table_data = get_material_table_data(provider, mat_id, tk)
            if table_data is None:
                continue
            data_rows = table_data["data"]
            if not data_rows or len(data_rows[0]) < 2:
                continue
            num_cols = len(data_rows[0])
            col_names = guess_table_column_names(tk, num_cols, mcc)
            table_df = pd.DataFrame(data_rows, columns=col_names)
            sections.append(f"<h4>{tk}</h4>")
            sections.append(table_df.to_html(index=False, classes="dataframe"))

    return "\n".join(sections) if sections else ""


def _generate_job_summary_saved_view_html(
    provider: DashboardDataProvider,
    status_filter: str,
    go_name: str,
) -> str:
    """ジョブサマリーの保存済みビューHTML断片を生成"""
    import pandas as pd

    job_rows = get_job_summary(provider)
    if status_filter:
        job_rows = [r for r in job_rows if r.get("analysis_status") == status_filter]
    if go_name:
        job_rows = [r for r in job_rows if r["go_name"] == go_name]

    if not job_rows:
        return "<p>条件に合致するジョブサマリーデータがありません。</p>"

    display_rows = []
    for r in job_rows:
        row: dict[str, Any] = {
            "GOノード": r["go_name"],
            "解析ステータス": r["analysis_status"],
        }
        if "cpu_time" in r:
            row["CPU時間(sec)"] = r["cpu_time"]
        if "wallclock_time" in r:
            row["経過時間(sec)"] = r["wallclock_time"]
        errors: list[str] = []
        warnings: list[str] = []
        for key in ("sta_errors", "msg_errors", "dat_errors"):
            errors.extend(r.get(key, []))
        for key in ("sta_warnings", "msg_warnings", "dat_warnings"):
            warnings.extend(r.get(key, []))
        if errors:
            row["エラー数"] = len(errors)
        if warnings:
            row["警告数"] = len(warnings)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    return df.to_html(index=False, classes="dataframe")
