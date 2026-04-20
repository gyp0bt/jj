"""配列プロットビューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig
from services.dashboard.widgets import get_plotly_template

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class ArrayPlotViewConfig(ViewConfig):
    """配列プロットビュー設定コンポーネント"""

    view_type = "array_plot"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        import streamlit as st

        st.markdown("**配列プロット設定**")
        array_keys = provider.get_array_property_keys()
        if not array_keys:
            return {"array_plot": {}}
        prefixes = sorted({k.split(".")[0] for k in array_keys})
        ac1, ac2 = st.columns(2)
        with ac1:
            ap_prefix = st.selectbox("プレフィックス", prefixes, key="_add_view_ap_prefix")
        with ac2:
            ap_mode = st.selectbox("モード", ["overlay", "single"], key="_add_view_ap_mode")
        prefix_keys = [k for k in array_keys if k.startswith(ap_prefix + ".")]
        ap_x = st.selectbox("X軸", prefix_keys, key="_add_view_ap_x") if prefix_keys else ""
        ap_y_options = [k for k in prefix_keys if k != ap_x]
        ap_y = st.multiselect("Y軸", ap_y_options, key="_add_view_ap_y")
        return {
            "array_plot": {
                "prefix": ap_prefix,
                "x": ap_x,
                "y": ap_y,
                "mode": ap_mode,
            }
        }


class ArrayPlotPage(PageComponent[ArrayPlotViewConfig]):
    """配列プロットビューページコンポーネント"""

    page_key = "array_plot"
    page_label = "配列プロット"

    def render(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        """配列プロットページを対話UIで描画する

        ``view`` は enabled-pages 上の識別子兼ウィジェットキー分離用として用い、
        軸・モード・スタイル等は対話ウィジェットで選択する（旧 render_page 相当）。
        """
        import streamlit as st

        from services.dashboard.widgets import (
            build_axis_range,
            build_style_config,
            get_active_filters,
            render_shared_filters,
        )

        st.header("配列プロットビュー")

        array_keys = provider.get_array_property_keys()
        if not array_keys:
            st.info(
                "配列プロパティが見つかりません。CSVファイルがhas_output関係でGOファイルに紐付いている必要があります。"
            )
            return

        # 共有フィルタ（サイドバー描画 + 適用）
        rows = provider.get_go_table()
        render_shared_filters(rows)

        # ウィジェットキー接頭辞（同一ページ種別を複数enabled_pagesに入れても衝突しない）
        wkey = f"_ap_{view.name}"

        # configデフォルト（ビュー編集フォーム等で設定された値を初期表示に反映）
        ap_config = getattr(view, "array_plot", {}) or {}
        cfg_prefix = ap_config.get("prefix", "")
        cfg_x = ap_config.get("x", "")
        cfg_y = ap_config.get("y", [])
        cfg_mode = ap_config.get("mode", "overlay")
        if isinstance(cfg_y, str):
            cfg_y = [cfg_y]

        # 接頭辞グループの抽出（例: RF, stress）
        prefixes = sorted({k.split(".")[0] for k in array_keys})
        prefix_default_idx = prefixes.index(cfg_prefix) if cfg_prefix in prefixes else 0

        # UI: 接頭辞選択 → X/Y軸選択
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_prefix = st.selectbox(
                "データグループ",
                prefixes,
                index=prefix_default_idx,
                key=f"{wkey}_prefix",
            )

        # 選択された接頭辞のキーのみ
        prefix_keys = [k for k in array_keys if k.startswith(selected_prefix + ".")]

        with col2:
            x_default_idx = prefix_keys.index(cfg_x) if cfg_x in prefix_keys else min(1, len(prefix_keys) - 1)
            x_default_idx = max(0, x_default_idx)
            x_key = st.selectbox("X軸", prefix_keys, index=x_default_idx, key=f"{wkey}_x") if prefix_keys else ""
        with col3:
            y_options = [k for k in prefix_keys if k != x_key]
            if not y_options:
                st.warning("Y軸に使用できるキーがありません。")
                return
            y_defaults = [k for k in cfg_y if k in y_options]
            if not y_defaults:
                y_defaults = [y_options[min(len(y_options) - 1, 0)]]
            y_keys = st.multiselect("Y軸", y_options, default=y_defaults, key=f"{wkey}_y")

        if not y_keys:
            st.info("Y軸を選択してください。")
            return

        # 表示モード: 全条件比較 or 個別ノード
        mode_options = ["全条件比較", "個別ノード"]
        mode_default_idx = 1 if cfg_mode == "single" else 0
        view_mode = st.radio(
            "表示モード",
            mode_options,
            index=mode_default_idx,
            horizontal=True,
            key=f"{wkey}_mode",
        )

        # 軸範囲設定（number_input）
        with st.expander("軸範囲設定", expanded=False):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                ax_x_min = st.number_input("X最小", value=None, key=f"{wkey}_x_min", format="%g")
            with rc2:
                ax_x_max = st.number_input("X最大", value=None, key=f"{wkey}_x_max", format="%g")
            with rc3:
                ax_y_min = st.number_input("Y最小", value=0.0, key=f"{wkey}_y_min", format="%g")
            with rc4:
                ax_y_max = st.number_input("Y最大", value=100, key=f"{wkey}_y_max", format="%g")

        # スタイル設定
        with st.expander("スタイル設定", expanded=False):
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                ap_marker_size = st.number_input(
                    "マーカーサイズ",
                    value=None,
                    min_value=1,
                    max_value=50,
                    key=f"{wkey}_marker_size",
                )
            with sc2:
                ap_line_width = st.number_input("線幅", value=None, min_value=1, max_value=20, key=f"{wkey}_line_width")
            with sc3:
                ap_font_size = st.number_input(
                    "フォントサイズ",
                    value=None,
                    min_value=6,
                    max_value=48,
                    key=f"{wkey}_font_size",
                )

        ap_x_range = build_axis_range(ax_x_min, ax_x_max)
        ap_y_range = build_axis_range(ax_y_min, ax_y_max)
        ap_style = build_style_config(ap_marker_size, ap_line_width, ap_font_size)

        # 共有フィルタをprovider用のフィルタ辞書に変換
        active_filters = get_active_filters()

        # NG領域設定
        ng_regions = getattr(dashboard_config, "ng_regions", [])

        if view_mode == "全条件比較":
            _render_array_overlay(
                provider,
                x_key,
                y_keys,
                filters=active_filters,
                ng_regions=ng_regions,
                x_range=ap_x_range,
                y_range=ap_y_range,
                style=ap_style,
            )
        else:
            _render_array_single(
                provider,
                x_key,
                y_keys,
                filters=active_filters,
                ng_regions=ng_regions,
                x_range=ap_x_range,
                y_range=ap_y_range,
                style=ap_style,
                widget_key_prefix=wkey,
            )

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.html_export import generate_array_plot_html

        return generate_array_plot_html(provider, dashboard_config, view)


# ====================================================================
# 配列プロット内部描画関数
# ====================================================================


def _render_array_overlay(
    provider: DashboardDataProvider,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    style: dict[str, int] | None = None,
) -> None:
    """全条件の配列データを凡例付きで同一グラフに重ね書き"""
    import streamlit as st

    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

    for y_key in y_keys:
        st.subheader(f"{y_key} vs {x_key}")
        grid_data = provider.get_array_grid_data(x_key, y_key, filters=filters)
        if not grid_data:
            st.info(f"'{x_key}' と '{y_key}' のデータがありません。")
            continue

        grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            for item in grid_data:
                # display_nameがあれば優先使用
                label = item.get("display_name", item["name"])
                fig.add_trace(
                    go.Scatter(
                        x=item["x_values"],
                        y=item["y_values"],
                        mode="lines+markers",
                        name=label,
                    )
                )
            if ng_regions:
                _add_ng_regions_to_fig(fig, ng_regions)
            fig.update_layout(
                title=dict(
                    text=f"{y_key} vs {x_key}（全条件比較）",
                    font=dict(size=24),
                ),
                xaxis=dict(
                    title=dict(
                        text=x_key.split(".")[-1],
                        font=dict(size=20),
                    ),
                    tickfont=dict(size=20),
                ),
                yaxis=dict(
                    title=dict(
                        text=y_key.split(".")[-1],
                        font=dict(size=20),
                    ),
                    tickfont=dict(size=20),
                ),
                legend=dict(font=dict(size=16)),
                height=600,
                showlegend=True,
                template=get_plotly_template(),
            )
            if x_range:
                fig.update_xaxes(range=x_range)
            if y_range:
                fig.update_yaxes(range=y_range)
            if style:
                apply_style_to_fig(fig, style)
            st.plotly_chart(fig, width="stretch")

        except ImportError:
            st.warning("plotlyが必要です: pip install plotly")

        st.caption(f"データ数: {len(grid_data)}")


def _render_array_single(
    provider: DashboardDataProvider,
    x_key: str,
    y_keys: list[str],
    filters: dict[str, Any] | None = None,
    ng_regions: list[dict[str, Any]] | None = None,
    x_range: list[float] | None = None,
    y_range: list[float] | None = None,
    style: dict[str, int] | None = None,
    widget_key_prefix: str = "_ap",
) -> None:
    """配列データの個別ノード表示（複数Y軸重ね書き）"""
    import streamlit as st

    from services.dashboard.html_export import _add_ng_regions_to_fig
    from services.dashboard.widgets import apply_style_to_fig

    rows = provider.get_go_table()
    if not rows:
        st.info("go_ファイルが見つかりません。")
        return

    # フィルタ適用
    if filters:
        rows = [r for r in rows if provider._matches_filters(r, filters)]

    # verbose_nameキー
    vn_key = provider._verbose_name_key

    # 配列データを持つノードのみ（表示名を使用）
    items_with_array = []
    for r in rows:
        nid = r["id"]
        node = provider._node_by_id.get(nid)
        if node and isinstance(node.properties.get(x_key), list):
            items_with_array.append(
                {
                    "id": nid,
                    "display_name": r.get(vn_key, r["name"]),
                }
            )

    if not items_with_array:
        st.info(f"'{x_key}' データを持つノードがありません。")
        return

    display_names = [item["display_name"] for item in items_with_array]
    selected = st.selectbox("ノード選択", display_names, key=f"{widget_key_prefix}_node_select")
    if not selected:
        return

    # 選択ノードのIDを取得
    node_id = next(
        (item["id"] for item in items_with_array if item["display_name"] == selected),
        None,
    )
    if node_id is None:
        return

    plot_data = provider.get_array_plot_data(node_id, x_key, y_keys)
    if plot_data is None:
        st.warning("配列データの取得に失敗しました。")
        return

    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        for s in plot_data["series"]:
            fig.add_trace(
                go.Scatter(
                    x=plot_data["x_values"],
                    y=s["values"],
                    mode="lines+markers",
                    name=s["key"].split(".")[-1],
                )
            )
        # NG領域塗りつぶし
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)

        # 軸ラベル・軸数値・凡例のフォントサイズ設定（色はテンプレートに委譲）
        fig.update_layout(
            title=dict(
                text=f"{selected}",
                font=dict(size=24),
            ),
            xaxis=dict(
                title=dict(
                    text=x_key.split(".")[-1],
                    font=dict(size=20),
                ),
                tickfont=dict(size=20),
            ),
            yaxis=dict(
                title=dict(
                    text="値",
                    font=dict(size=20),
                ),
                tickfont=dict(size=20),
            ),
            legend=dict(font=dict(size=16)),
            height=500,
            template=get_plotly_template(),
        )
        if x_range:
            fig.update_xaxes(range=x_range)
        if y_range:
            fig.update_yaxes(range=y_range)
        if style:
            apply_style_to_fig(fig, style)
        st.plotly_chart(fig, width="stretch")
    except ImportError:
        st.warning("plotlyが必要です: pip install plotly")


# ====================================================================
# ヘルパー関数
# ====================================================================


def _get_array_plot_defaults(dashboard_config: DashboardConfig | None) -> dict[str, Any]:
    """DashboardConfigからarray_plotデフォルト設定を取得"""
    if not dashboard_config:
        return {}
    ap_config = getattr(dashboard_config, "array_plot_defaults", None)
    if not ap_config or not isinstance(ap_config, dict):
        return {}
    return ap_config


def _find_key_index(keys: list[str], target: str | None) -> int:
    """キーリスト内でtargetのインデックスを返す。見つからなければ0"""
    if not target or not keys:
        return 0
    try:
        return keys.index(target)
    except ValueError:
        return 0


def _get_default_y_keys(y_options: list[str], config_y: str | list[str] | None) -> list[str]:
    """configからデフォルトY軸キーを取得"""
    if not config_y:
        return []
    if isinstance(config_y, str):
        config_y = [config_y]
    return [k for k in config_y if k in y_options]
