"""ダッシュボード HTMLエクスポート

保存済みビューをスタンドアロンHTMLファイルに変換するロジック。
plotlyのインラインHTML化とpandas to_html()によるテーブル変換を行い、
1つのHTMLファイルにまとめる。

Streamlit非依存の純粋関数群。描画層（app.py）から分離して
テスト容易性と将来のパッケージ分離を実現する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.dashboard.widgets import build_axis_range, get_plotly_template
from services.graph.query import (
    apply_saved_view_filters,
    select_table_columns,
)

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


def generate_saved_views_html(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    views: list[Any],
    vocab: dict[str, str] | None = None,
) -> str:
    """保存済みビュー一覧をスタンドアロンHTMLに変換

    Args:
        provider: DashboardDataProvider
        project_root: プロジェクトルート
        dashboard_config: DashboardConfig
        views: SavedViewConfigのリスト
        vocab: vocabマッピング

    Returns:
        完全なHTMLドキュメント文字列
    """
    sections: list[str] = []

    for view in views:
        section_html = generate_view_html(provider, project_root, dashboard_config, view, vocab)
        if section_html:
            sections.append(
                f'<div class="view-section">'
                f"<h2>{view.name}</h2>"
                f'<p class="view-type">タイプ: {view.view_type}</p>'
                f"{section_html}"
                f"</div>"
            )

    # コネクターページのHTML断片を追加
    from services.dashboard.connectors import generate_connector_pages_html

    connector_sections = generate_connector_pages_html(provider, dashboard_config)
    for label, html in connector_sections:
        sections.append(
            f'<div class="view-section"><h2>{label}</h2><p class="view-type">タイプ: コネクターページ</p>{html}</div>'
        )

    body = "\n<hr>\n".join(sections)
    project_name = project_root.name if project_root else "jj"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>jj Dashboard - {project_name}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0; padding: 20px;
    background: #f8f9fa; color: #333;
}}
h1 {{ color: #1f2937; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
h2 {{ color: #374151; margin-top: 24px; }}
.view-section {{ background: #fff; padding: 20px; margin: 16px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.view-type {{ color: #6b7280; font-size: 0.9em; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.9em; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }}
th {{ background: #f3f4f6; font-weight: 600; }}
tr:nth-child(even) {{ background: #f9fafb; }}
.caption {{ color: #6b7280; font-size: 0.85em; margin: 4px 0; }}
.plotly-graph {{ margin: 12px 0; }}
.grid-container {{ display: grid; gap: 12px; }}
hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 24px 0; }}
</style>
</head>
<body>
<h1>jj Dashboard - {project_name}</h1>
<p class="caption">生成日時: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
{body}
</body>
</html>"""
    return html


def generate_view_html(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
    view: Any,
    vocab: dict[str, str] | None = None,
) -> str:
    """個別ビューのHTML断片を生成

    PageComponentレジストリまたはコネクターレジストリを使用して
    ビュータイプに応じたHTML生成をディスパッチする。

    Args:
        provider: DashboardDataProvider
        project_root: プロジェクトルート
        dashboard_config: DashboardConfig
        view: SavedViewConfig
        vocab: vocabマッピング

    Returns:
        HTML断片文字列
    """
    # コネクタービューの場合はコネクターレジストリからディスパッチ
    if getattr(view, "is_connector_view", False):
        from services.dashboard.connectors import generate_connector_saved_view_html

        return generate_connector_saved_view_html(
            view.connector_page_label,
            provider,
            view,
            dashboard_config,
        )

    from services.dashboard.components import get_page_component

    component = get_page_component(view.view_type)
    if component is not None:
        return component.generate_html(
            provider,
            view,
            dashboard_config,
            vocab=vocab,
            project_root=project_root,
        )
    return ""


def generate_table_html(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    view: Any,
    vocab: dict[str, str] | None = None,
) -> str:
    """テーブルビューのHTML断片"""
    import pandas as pd

    rows = provider.get_go_table()
    if not rows:
        return "<p>go_ファイルが見つかりません。</p>"

    filtered = apply_saved_view_filters(rows, view.filters)
    if not filtered:
        return "<p>条件に一致するデータがありません。</p>"

    display_rows = []
    for r in filtered:
        row = {k: v for k, v in r.items() if k != "related_files"}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                row[k] = str(v)
        display_rows.append(row)

    df = pd.DataFrame(display_rows)
    table_columns = getattr(dashboard_config, "table_columns", None)
    selected_cols = select_table_columns(list(df.columns), table_columns, vocab=vocab or {})
    if selected_cols:
        df = df[[c for c in selected_cols if c in df.columns]]

    # カラムヘッダーにvocab変換を適用（表示時のみ）
    if vocab:
        from modules.vocab_display import translate_key

        df = df.rename(columns={c: translate_key(c, vocab) for c in df.columns})

    caption = f'<p class="caption">{len(filtered)} / {len(rows)} 件</p>'
    return caption + df.to_html(index=False, classes="dataframe")


def generate_plot_html(
    provider: DashboardDataProvider,
    view: Any,
    dashboard_config: Any = None,
    vocab: dict[str, str] | None = None,
) -> str:
    """プロットビューのHTML断片（plotly inlineHTML）"""
    plot_config = view.plot
    x_key = plot_config.get("x")
    y_key = plot_config.get("y")
    color = plot_config.get("color")
    chart_type = plot_config.get("chart_type", "散布図")

    if not x_key or not y_key:
        return "<p>プロット設定にx/yが指定されていません。</p>"

    # グループ結線キーをextra_keysに含める
    group_line_key = getattr(dashboard_config, "group_line_key", None) if dashboard_config else None
    extra_keys: list[str] = []
    if group_line_key:
        extra_keys.append(group_line_key)
    # コンタープロット用Z軸キーもextra_keysに含める
    z_key_for_extra = plot_config.get("z")
    if z_key_for_extra:
        extra_keys.append(z_key_for_extra)

    # colorが未設定の場合、デフォルトで表示名を使用
    vn_key = provider._verbose_name_key
    if not color:
        color = vn_key

    data = provider.get_plot_data(x_key, y_key, color_key=color, extra_keys=extra_keys)
    if view.filters:
        all_rows = provider.get_go_table()
        filtered_rows = apply_saved_view_filters(all_rows, view.filters)
        filtered_names = {r["name"] for r in filtered_rows}
        data = [d for d in data if d.get("name") in filtered_names]

    if not data:
        return f"<p>'{x_key}' と '{y_key}' の両方が数値であるデータが見つかりません。</p>"

    # plot_style: ビュー設定 > DashboardConfig > デフォルト
    plot_style = _resolve_plot_style(plot_config.get("plot_style"), dashboard_config)

    # axis_range: ビュー設定から読み取り
    axis_range = plot_config.get("axis_range", {})

    # コンタープロット用: z_keyとcolor_range
    z_key = plot_config.get("z")
    color_range = plot_config.get("color_range", {})

    try:
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame(data)
        fig = _create_plot_figure(
            px,
            df,
            x_key,
            y_key,
            color,
            chart_type,
            hover_name_col=vn_key,
            plot_style=plot_style,
            z_key=z_key,
            color_range=color_range,
            vocab=vocab,
        )
        ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []
        if ng_regions:
            _add_ng_regions_to_fig(fig, ng_regions)
        if group_line_key and group_line_key in df.columns:
            _add_group_lines_to_fig(fig, df, x_key, y_key, group_line_key)

        # 軸範囲の適用
        if axis_range:
            _apply_axis_range(fig, axis_range)

        plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
        caption = f'<p class="caption">データ点数: {len(data)}</p>'
        return f'<div class="plotly-graph">{plot_html}</div>{caption}'
    except ImportError:
        return "<p>plotlyが必要です。</p>"


def generate_array_plot_html(
    provider: DashboardDataProvider,
    dashboard_config: Any,
    view: Any,
    vocab: dict[str, str] | None = None,
) -> str:
    """配列プロットビューのHTML断片"""
    from modules.vocab_display import translate_key
    from services.graph.query.filters import saved_view_filters_to_provider_filters

    v = vocab or {}

    ap_config = getattr(view, "array_plot", {})
    prefix = ap_config.get("prefix", "")
    x_key = ap_config.get("x", "")
    y_keys = ap_config.get("y", [])

    if not x_key:
        array_keys = provider.get_array_property_keys()
        if prefix:
            prefix_keys = [k for k in array_keys if k.startswith(prefix + ".")]
        else:
            prefix_keys = array_keys
        if not prefix_keys:
            return "<p>配列プロパティが見つかりません。</p>"
        x_key = prefix_keys[0]
        if not y_keys:
            y_keys = [k for k in prefix_keys if k != x_key]

    if isinstance(y_keys, str):
        y_keys = [y_keys]
    if not y_keys:
        return "<p>Y軸の配列キーが指定されていません。</p>"

    filters = getattr(view, "filters", {}) or {}
    filter_dict = saved_view_filters_to_provider_filters(filters) if filters else None
    ng_regions = getattr(dashboard_config, "ng_regions", []) if dashboard_config else []

    # plot_style: ビュー設定 > DashboardConfig > デフォルト
    plot_style = _resolve_plot_style(ap_config.get("plot_style"), dashboard_config)

    # axis_range: ビュー設定から読み取り
    axis_range = ap_config.get("axis_range", {})

    mode = ap_config.get("mode", "overlay")
    parts: list[str] = []

    try:
        import plotly.graph_objects as go

        for y_key in y_keys:
            grid_data = provider.get_array_grid_data(x_key, y_key, filters=filter_dict)
            if not grid_data:
                continue
            grid_data.sort(key=lambda d: (d.get("index", ""), d.get("version", "")))

            x_label = translate_key(x_key, v)
            y_label = translate_key(y_key, v)
            parts.append(f"<h3>{y_label} vs {x_label}</h3>")

            if mode == "overlay":
                # 全条件比較: 1グラフに全条件を凡例付きで重ね書き
                fig = go.Figure()
                for item in grid_data:
                    idx_str = item.get("index", "")
                    ver_str = item.get("version", "")
                    label = item.get("display_name", item["name"])
                    if idx_str:
                        label += f" (idx{idx_str}"
                        if ver_str:
                            label += f",v{ver_str}"
                        label += ")"
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
                _apply_default_layout(
                    fig,
                    title=f"{y_label} vs {x_label}（全条件比較）",
                    x_title=translate_key(x_key.split(".")[-1], v),
                    y_title=translate_key(y_key.split(".")[-1], v),
                    height=600,
                    showlegend=True,
                    plot_style=plot_style,
                )
                if axis_range:
                    _apply_axis_range(fig, axis_range)
                plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
                parts.append(f'<div class="plotly-graph">{plot_html}</div>')
            else:
                # グリッド比較: 条件ごとに個別グラフ
                gd = getattr(dashboard_config, "gallery_defaults", None) if dashboard_config else None
                cols_per_row = gd.columns if gd is not None else 4
                parts.append(
                    f'<div class="grid-container" style="grid-template-columns: repeat({cols_per_row}, 1fr);">'
                )

                for item in grid_data:
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=item["x_values"],
                            y=item["y_values"],
                            mode="lines+markers",
                            name=translate_key(y_key, v),
                        )
                    )
                    if ng_regions:
                        _add_ng_regions_to_fig(fig, ng_regions)
                    title = item.get("display_name", item["name"])
                    idx_str = item.get("index", "")
                    if idx_str:
                        title += f" (idx{idx_str})"
                    _apply_default_layout(
                        fig,
                        title=title,
                        x_title=translate_key(x_key.split(".")[-1], v),
                        y_title=translate_key(y_key.split(".")[-1], v),
                        height=300,
                        showlegend=False,
                        plot_style=plot_style,
                        margin=dict(l=20, r=20, t=40, b=20),
                    )
                    if axis_range:
                        _apply_axis_range(fig, axis_range)
                    plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
                    parts.append(f'<div class="plotly-graph">{plot_html}</div>')

                parts.append("</div>")

            parts.append(f'<p class="caption">データ数: {len(grid_data)}</p>')

    except ImportError:
        return "<p>plotlyが必要です。</p>"

    return "\n".join(parts)


def generate_status_html(
    provider: DashboardDataProvider,
) -> str:
    """ステータスビューのHTML断片"""
    import pandas as pd

    status = provider.get_status_summary()
    metrics = (
        f'<div style="display:flex;gap:24px;margin:12px 0;">'
        f"<div><strong>合計</strong>: {status['total']}</div>"
        f"<div><strong>完了</strong>: {status['completed']}</div>"
        f"<div><strong>失敗</strong>: {status['failed']}</div>"
        f"<div><strong>不明</strong>: {status['unknown']}</div>"
        f"</div>"
    )
    items = status["items"]
    if items:
        df = pd.DataFrame(items)
        return metrics + df.to_html(index=False, classes="dataframe")
    return metrics + "<p>go_ファイルが見つかりません。</p>"


def generate_card_html(
    provider: DashboardDataProvider,
    view: Any,
) -> str:
    """カードビューのHTML断片"""
    import pandas as pd

    rows = provider.get_go_table()
    if not rows:
        return "<p>go_ファイルが見つかりません。</p>"

    filtered = apply_saved_view_filters(rows, view.filters)
    if not filtered:
        return "<p>条件に一致するデータがありません。</p>"

    first_row = filtered[0]
    node_id = first_row.get("id")
    if node_id is None:
        return ""

    card = provider.get_node_card(node_id)
    if card is None:
        return ""

    props = {k: v for k, v in card["properties"].items() if k != "path"}
    props_flat = {}
    for k, v in props.items():
        if isinstance(v, (dict, list)):
            props_flat[k] = str(v)
        else:
            props_flat[k] = v

    parts = [f"<p><strong>{card['name']}</strong> ({card['type']})</p>"]
    if props_flat:
        df = pd.DataFrame([props_flat]).T
        df.columns = ["値"]
        parts.append(df.to_html(classes="dataframe"))
    return "\n".join(parts)


# ====================================================================
# plotlyヘルパー（HTMLエクスポート用・app.pyと共用）
# ====================================================================


def _create_plot_figure(
    px: Any,
    df: Any,
    x_key: str,
    y_key: str,
    color: str | None,
    chart_type: str,
    hover_name_col: str = "name",
    plot_style: dict[str, int] | None = None,
    z_key: str | None = None,
    color_range: dict[str, float] | None = None,
    vocab: dict[str, str] | None = None,
) -> Any:
    """plotlyのFigureオブジェクトを作成

    Args:
        hover_name_col: ホバー時に表示する列名（デフォルト: "name"）
        plot_style: スタイル設定辞書（marker_size, line_width, font_size）
        z_key: コンタープロット用Z軸キー（色分け変数）
        color_range: カラーバー範囲 {"vmin": float, "vmax": float}
        vocab: vocabマッピング（軸ラベル・タイトルの表示名変換用）
    """
    from modules.vocab_display import translate_key

    v = vocab or {}
    x_label = translate_key(x_key, v)
    y_label = translate_key(y_key, v)
    # hover_name列がdfに存在しなければ"name"にフォールバック
    hn = hover_name_col if hover_name_col in df.columns else "name"

    template = get_plotly_template()

    if chart_type == "散布図":
        fig = px.scatter(
            df,
            x=x_key,
            y=y_key,
            color=color,
            hover_name=hn if hn in df.columns else None,
            title=f"{y_label} vs {x_label}",
            template=template,
        )
    elif chart_type == "棒グラフ":
        fig = px.bar(
            df,
            x=hn if hn in df.columns else "name",
            y=y_key,
            color=color,
            title=f"{y_label} by name",
            template=template,
        )
    elif chart_type == "コンター":
        # コンタープロット: Z軸キーで色分けした散布図（連続カラースケール）
        contour_z = z_key if z_key and z_key in df.columns else color
        z_label = translate_key(contour_z, v) if contour_z else ""
        cr = color_range or {}
        range_color = None
        if cr.get("vmin") is not None or cr.get("vmax") is not None:
            vmin = cr.get("vmin", df[contour_z].min() if contour_z and contour_z in df.columns else 0)
            vmax = cr.get("vmax", df[contour_z].max() if contour_z and contour_z in df.columns else 1)
            range_color = [vmin, vmax]
        fig = px.scatter(
            df,
            x=x_key,
            y=y_key,
            color=contour_z if contour_z and contour_z in df.columns else None,
            hover_name=hn if hn in df.columns else None,
            title=f"{y_label} vs {x_label}" + (f" (色: {z_label})" if contour_z else ""),
            template=template,
            color_continuous_scale="Viridis",
            range_color=range_color,
        )
    elif chart_type == "等高線":
        # 等高線プロット: px.density_contourによる密度等高線
        contour_z = z_key if z_key and z_key in df.columns else None
        z_label = translate_key(contour_z, v) if contour_z else ""
        fig = px.density_contour(
            df,
            x=x_key,
            y=y_key,
            z=contour_z,
            hover_name=hn if hn in df.columns else None,
            title=f"{y_label} vs {x_label}" + (f" (Z: {z_label})" if contour_z else " (密度)"),
            template=template,
        )
        # 等高線の塗りつぶし
        cr = color_range or {}
        contours_kwargs: dict[str, Any] = {}
        if cr.get("vmin") is not None:
            contours_kwargs["start"] = cr["vmin"]
        if cr.get("vmax") is not None:
            contours_kwargs["end"] = cr["vmax"]
        fig.update_traces(
            contours_coloring="fill",
            colorscale="Viridis",
            **(
                {
                    "contours": contours_kwargs,
                }
                if contours_kwargs
                else {}
            ),
        )
    else:
        fig = px.line(
            df,
            x=x_key,
            y=y_key,
            color=color,
            hover_name=hn if hn in df.columns else None,
            title=f"{y_label} vs {x_label}",
            markers=True,
            template=template,
        )

    # マーカーサイズ: plot_styleに指定があればそちらを優先、なければデフォルト16
    # barグラフ・等高線はmarker.sizeプロパティを持たないため除外
    marker_size = (plot_style or {}).get("marker_size", 16)
    if chart_type not in ("棒グラフ", "等高線"):
        fig.update_traces(marker=dict(size=marker_size))

    # 線幅: plot_styleに指定があれば適用
    line_width = (plot_style or {}).get("line_width")
    if line_width is not None:
        fig.update_traces(line=dict(width=line_width))

    # フォントサイズ: plot_styleに指定があればそちらを優先、なければデフォルト20
    font_sz = (plot_style or {}).get("font_size", 20)
    title_font_sz = round(font_sz * 24 / 20)
    legend_font_sz = round(font_sz * 16 / 20)
    fig.update_layout(
        title_font=dict(size=title_font_sz),
        legend=dict(font=dict(size=legend_font_sz)),
    )
    fig.update_xaxes(
        title_text=x_label,
        title_font=dict(size=font_sz),
        tickfont=dict(size=font_sz),
    )
    fig.update_yaxes(
        title_text=y_label,
        title_font=dict(size=font_sz),
        tickfont=dict(size=font_sz),
    )
    return fig


def _resolve_plot_style(
    view_style: dict[str, Any] | None,
    dashboard_config: Any,
) -> dict[str, int]:
    """ビュー設定とDashboardConfigからplot_styleをマージして返す

    優先順位: ビュー設定 > DashboardConfig.plot_style > 空dict
    """
    base: dict[str, int] = {}
    if dashboard_config is not None:
        config_style = getattr(dashboard_config, "plot_style", None)
        if config_style:
            base.update(config_style)
    if view_style and isinstance(view_style, dict):
        for k in ("marker_size", "line_width", "font_size"):
            v = view_style.get(k)
            if v is not None:
                base[k] = int(v)
    return base


def _apply_axis_range(fig: Any, axis_range: dict[str, Any]) -> None:
    """軸範囲をFigureに適用

    axis_range: {"x_min": float, "x_max": float, "y_min": float, "y_max": float}
    """
    x_range = build_axis_range(axis_range.get("x_min"), axis_range.get("x_max"))
    y_range = build_axis_range(axis_range.get("y_min"), axis_range.get("y_max"))
    if x_range:
        fig.update_xaxes(range=x_range)
    if y_range:
        fig.update_yaxes(range=y_range)


def _apply_default_layout(
    fig: Any,
    title: str,
    x_title: str,
    y_title: str,
    height: int,
    showlegend: bool,
    plot_style: dict[str, int] | None = None,
    margin: dict[str, int] | None = None,
) -> None:
    """配列プロットのレイアウトにplot_styleを適用"""
    font_sz = (plot_style or {}).get("font_size", 20)
    title_font_sz = round(font_sz * 24 / 20)
    legend_font_sz = round(font_sz * 16 / 20)

    layout_kwargs: dict[str, Any] = {
        "title": dict(text=title, font=dict(size=title_font_sz)),
        "xaxis": dict(title=dict(text=x_title, font=dict(size=font_sz)), tickfont=dict(size=font_sz)),
        "yaxis": dict(title=dict(text=y_title, font=dict(size=font_sz)), tickfont=dict(size=font_sz)),
        "legend": dict(font=dict(size=legend_font_sz)),
        "height": height,
        "showlegend": showlegend,
        "template": get_plotly_template(),
    }
    if margin:
        layout_kwargs["margin"] = margin
    fig.update_layout(**layout_kwargs)

    # マーカーサイズ・線幅の適用
    if plot_style:
        if "marker_size" in plot_style:
            fig.update_traces(marker=dict(size=plot_style["marker_size"]))
        if "line_width" in plot_style:
            fig.update_traces(line=dict(width=plot_style["line_width"]))


def _add_ng_regions_to_fig(fig: Any, ng_regions: list[dict[str, Any]]) -> None:
    """プロットにNG領域（矩形/カーブ）を追加

    矩形タイプ: {"type": "rect", "x_min": float, "x_max": float,
                  "y_min": float, "y_max": float, "color": str, "label": str}
    カーブタイプ: {"type": "curve", "points": [[x,y],...],
                   "fill": "above"|"below", "color": str, "label": str}
    """
    import plotly.graph_objects as go

    for region in ng_regions:
        rtype = region.get("type", "rect")
        color = region.get("color", "rgba(255,0,0,0.1)")
        label = region.get("label", "NG")

        if rtype == "curve":
            points = region.get("points", [])
            if not points:
                continue
            x_pts = [p[0] for p in points]
            y_pts = [p[1] for p in points]
            fill_dir = region.get("fill", "above")
            fig.add_trace(
                go.Scatter(
                    x=x_pts,
                    y=y_pts,
                    mode="lines",
                    line=dict(color=color.replace("0.1", "0.6") if "rgba" in color else color, dash="dash"),
                    name=label,
                    showlegend=True,
                )
            )
            if fill_dir == "above":
                fig.add_trace(
                    go.Scatter(
                        x=x_pts,
                        y=y_pts,
                        fill="tonexty" if len(fig.data) > 1 else "tozeroy",
                        fillcolor=color,
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
            elif fill_dir == "below":
                fig.add_trace(
                    go.Scatter(
                        x=x_pts,
                        y=y_pts,
                        fill="tozeroy",
                        fillcolor=color,
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )
        else:
            x0 = region.get("x_min")
            x1 = region.get("x_max")
            y0 = region.get("y_min")
            y1 = region.get("y_max")
            fig.add_shape(
                type="rect",
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                fillcolor=color,
                line=dict(width=0),
                layer="below",
            )
            if label and x1 is not None and y1 is not None:
                fig.add_annotation(
                    x=x1,
                    y=y1,
                    text=label,
                    showarrow=False,
                    font=dict(size=10, color="red"),
                    xanchor="right",
                    yanchor="bottom",
                )


def _add_group_lines_to_fig(
    fig: Any,
    df: Any,
    x_key: str,
    y_key: str,
    group_key: str,
) -> None:
    """同一グループのデータ点を灰色点線で結線"""
    import plotly.graph_objects as go

    for _group_val, group_df in df.groupby(group_key):
        if len(group_df) < 2:
            continue
        sorted_df = group_df.sort_values(x_key)
        fig.add_trace(
            go.Scatter(
                x=sorted_df[x_key].tolist(),
                y=sorted_df[y_key].tolist(),
                mode="lines",
                line=dict(color="gray", width=1, dash="dot"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
