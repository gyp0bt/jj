"""バッチラン俯瞰ビューコンポーネント

同一indexのバージョン違いをブロック図+スタイルドテキストで俯瞰表示する。
バッチラン（パラメータスタディ等）の差分を視覚的に把握するためのページ。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class BatchOverviewViewConfig(ViewConfig):
    """バッチ俯瞰ビュー設定コンポーネント"""

    view_type = "batch_overview"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {}


class BatchOverviewPage(PageComponent[BatchOverviewViewConfig]):
    """バッチラン俯瞰ビューページコンポーネント"""

    page_key = "batch_overview"
    page_label = "バッチ俯瞰"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.widgets import get_active_filters, render_shared_filters

        st.header("バッチラン俯瞰")

        rows = provider.get_go_table()
        render_shared_filters(rows)
        active_filters = get_active_filters()

        if active_filters:
            rows = provider.get_go_table(filters=active_filters)

        if not rows:
            st.info("go_ ファイルが見つかりません。")
            return

        self._render_batch_overview(provider, rows, kwargs.get("vocab") or {})

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        from services.dashboard.query import apply_saved_view_filters

        rows = provider.get_go_table()
        if view.filters:
            rows = apply_saved_view_filters(rows, view.filters)

        if not rows:
            st.info("条件に一致するデータがありません。")
            return

        self._render_batch_overview(provider, rows, kwargs.get("vocab") or {})

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        from services.dashboard.query import apply_saved_view_filters

        rows = provider.get_go_table()
        if view.filters:
            rows = apply_saved_view_filters(rows, view.filters)

        if not rows:
            return "<p>データがありません。</p>"

        return _generate_batch_html(rows, provider)

    def _render_batch_overview(
        self,
        provider: DashboardDataProvider,
        rows: list[dict[str, Any]],
        vocab: dict[str, str],
    ) -> None:
        """バッチ俯瞰のメイン描画"""
        import streamlit as st

        vn_key = provider._verbose_name_key
        index_key = provider._index_key
        version_key = provider._version_key

        # indexでグルーピング
        groups = _group_by_index(rows, index_key)

        if not groups:
            st.info("indexプロパティを持つノードがありません。")
            return

        # 表示モード選択
        view_mode = st.radio(
            "表示モード",
            ["グリッド俯瞰", "詳細ブロック図"],
            horizontal=True,
            key="_batch_view_mode",
        )

        # index選択フィルタ
        all_indices = list(groups.keys())
        selected_indices = st.multiselect(
            "index選択（空=全表示）",
            all_indices,
            key="_batch_index_filter",
        )
        if selected_indices:
            groups = OrderedDict((k, v) for k, v in groups.items() if k in selected_indices)

        st.caption(f"{len(groups)} グループ / {sum(len(v) for v in groups.values())} ノード")

        if view_mode == "グリッド俯瞰":
            _render_grid_overview(groups, vn_key, version_key, index_key, provider)
        else:
            _render_block_diagram(groups, vn_key, version_key, index_key, provider)


# ====================================================================
# グルーピング
# ====================================================================


def _group_by_index(
    rows: list[dict[str, Any]],
    index_key: str,
) -> OrderedDict[str, list[dict[str, Any]]]:
    """indexプロパティでグルーピングし、indexの昇順で返す"""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        idx = row.get(index_key)
        if idx is None or idx == "":
            idx = "(なし)"
        groups.setdefault(str(idx), []).append(row)

    # indexを自然順でソート
    def _sort_key(k: str) -> tuple[int, str]:
        try:
            return (0, str(int(k)).zfill(10))
        except (ValueError, TypeError):
            return (1, k)

    return OrderedDict(sorted(groups.items(), key=lambda x: _sort_key(x[0])))


# ====================================================================
# グリッド俯瞰（コンパクト表示）
# ====================================================================


def _render_grid_overview(
    groups: OrderedDict[str, list[dict[str, Any]]],
    vn_key: str,
    version_key: str,
    index_key: str,
    provider: DashboardDataProvider,
) -> None:
    """全indexをグリッドで俯瞰表示"""
    import streamlit as st

    # 全バージョン列の収集
    all_versions: list[str] = []
    seen: set[str] = set()
    for group_rows in groups.values():
        for row in group_rows:
            v = str(row.get(version_key, "(default)") or "(default)")
            if v not in seen:
                seen.add(v)
                all_versions.append(v)

    if not all_versions:
        all_versions = ["(default)"]

    # 差分比較で注目するプロパティキーを取得
    diff_keys = _find_varying_keys(groups, version_key, index_key, vn_key)

    # ヘッダー表示
    header_cols = st.columns([2] + [1] * len(all_versions))
    with header_cols[0]:
        st.markdown("**index**")
    for ci, ver in enumerate(all_versions):
        with header_cols[ci + 1]:
            st.markdown(f"**{ver}**")

    st.markdown("---")

    # 各index行
    for idx_name, group_rows in groups.items():
        version_map: dict[str, dict[str, Any]] = {}
        for row in group_rows:
            v = str(row.get(version_key, "(default)") or "(default)")
            version_map[v] = row

        row_cols = st.columns([2] + [1] * len(all_versions))
        with row_cols[0]:
            display = group_rows[0].get(vn_key, idx_name)
            st.markdown(f"**{idx_name}**")
            if display != idx_name:
                st.caption(display)

        for ci, ver in enumerate(all_versions):
            with row_cols[ci + 1]:
                row_data = version_map.get(ver)
                if row_data is None:
                    st.markdown(
                        '<div style="padding:8px;border:1px dashed #d1d5db;'
                        'border-radius:6px;text-align:center;color:#9ca3af;">'
                        "—</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    _render_status_block(row_data, diff_keys)


def _render_status_block(row: dict[str, Any], diff_keys: list[str]) -> None:
    """1ノードのステータスブロック（コンパクト）"""
    import streamlit as st

    status = row.get("analysis_status", "unknown")
    color_map = {
        "completed": ("#10b981", "#ecfdf5"),
        "failed": ("#ef4444", "#fef2f2"),
    }
    border_color, bg_color = color_map.get(status, ("#6b7280", "#f9fafb"))

    # 差分プロパティの要約
    diff_lines: list[str] = []
    for k in diff_keys[:4]:
        val = row.get(k)
        if val is not None:
            val_str = str(val)
            if len(val_str) > 20:
                val_str = val_str[:17] + "..."
            diff_lines.append(f"<span style='color:#6b7280;font-size:0.75em;'>{k}: {val_str}</span>")

    diff_html = "<br>".join(diff_lines) if diff_lines else ""

    html = (
        f'<div style="padding:8px;border:2px solid {border_color};'
        f'background:{bg_color};border-radius:6px;">'
        f"<div style='font-size:0.85em;font-weight:600;'>{status}</div>"
        f"{diff_html}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ====================================================================
# 詳細ブロック図
# ====================================================================


def _render_block_diagram(
    groups: OrderedDict[str, list[dict[str, Any]]],
    vn_key: str,
    version_key: str,
    index_key: str,
    provider: DashboardDataProvider,
) -> None:
    """各indexのブロック図+差分テーブルを詳細表示"""
    import streamlit as st

    for idx_name, group_rows in groups.items():
        st.markdown("---")
        display = group_rows[0].get(vn_key, idx_name)
        st.subheader(f"index: {idx_name}")
        if display != idx_name:
            st.caption(display)

        if len(group_rows) == 1:
            # 単一バージョン: ブロック図のみ
            _render_single_block(group_rows[0], version_key, vn_key)
        else:
            # 複数バージョン: ブロック図 + 差分テーブル
            _render_version_blocks(group_rows, version_key, vn_key, index_key)
            _render_diff_table(group_rows, version_key, index_key, vn_key)


def _render_single_block(row: dict[str, Any], version_key: str, vn_key: str) -> None:
    """単一バージョンのブロック表示"""
    import streamlit as st

    version = row.get(version_key, "(default)")
    status = row.get("analysis_status", "unknown")
    name = row.get(vn_key, row.get("name", ""))

    color_map = {
        "completed": ("#10b981", "#ecfdf5", "#065f46"),
        "failed": ("#ef4444", "#fef2f2", "#991b1b"),
    }
    border, bg, text = color_map.get(status, ("#6b7280", "#f9fafb", "#374151"))

    html = (
        f'<div style="display:inline-block;padding:12px 20px;border:2px solid {border};'
        f'background:{bg};border-radius:8px;min-width:200px;">'
        f'<div style="font-weight:700;color:{text};font-size:1em;">{name}</div>'
        f'<div style="color:#6b7280;font-size:0.8em;">version: {version}</div>'
        f'<div style="color:{text};font-size:0.85em;margin-top:4px;">{status}</div>'
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_version_blocks(
    group_rows: list[dict[str, Any]],
    version_key: str,
    vn_key: str,
    index_key: str,
) -> None:
    """複数バージョンを横並びブロックで表示"""
    import streamlit as st

    cols = st.columns(min(len(group_rows), 4))
    for i, row in enumerate(group_rows):
        with cols[i % len(cols)]:
            version = row.get(version_key, "(default)")
            status = row.get("analysis_status", "unknown")
            name = row.get(vn_key, row.get("name", ""))

            color_map = {
                "completed": ("#10b981", "#ecfdf5", "#065f46"),
                "failed": ("#ef4444", "#fef2f2", "#991b1b"),
            }
            border, bg, text = color_map.get(status, ("#6b7280", "#f9fafb", "#374151"))

            html = (
                f'<div style="padding:12px;border:2px solid {border};'
                f'background:{bg};border-radius:8px;">'
                f'<div style="font-weight:700;color:{text};font-size:0.95em;">{name}</div>'
                f'<div style="color:#6b7280;font-size:0.8em;">version: {version}</div>'
                f'<div style="color:{text};font-size:0.85em;margin-top:4px;">{status}</div>'
                f"</div>"
            )
            st.markdown(html, unsafe_allow_html=True)


def _render_diff_table(
    group_rows: list[dict[str, Any]],
    version_key: str,
    index_key: str,
    vn_key: str,
) -> None:
    """バージョン間の差分をテーブル表示"""
    import streamlit as st

    # 差分のあるプロパティを抽出
    skip_keys = {"id", "name", "type", "format", "related_files", vn_key, index_key}
    all_keys: set[str] = set()
    for row in group_rows:
        all_keys.update(row.keys())
    all_keys -= skip_keys

    diff_props: dict[str, list[Any]] = {}
    for key in sorted(all_keys):
        values = [row.get(key) for row in group_rows]
        # 全て同値でないプロパティのみ表示
        unique = set()
        for v in values:
            if isinstance(v, (list, dict)):
                unique.add(str(v))
            else:
                unique.add(v)
        if len(unique) > 1:
            diff_props[key] = values

    if not diff_props:
        st.caption("バージョン間の差分なし")
        return

    st.markdown("**差分プロパティ**")

    # テーブル構築
    import pandas as pd

    versions = [str(r.get(version_key, "(default)") or "(default)") for r in group_rows]
    table_data: dict[str, list[Any]] = {"プロパティ": []}
    for ver in versions:
        table_data[f"v:{ver}"] = []

    for key, values in diff_props.items():
        table_data["プロパティ"].append(key)
        for vi, ver in enumerate(versions):
            val = values[vi]
            if isinstance(val, (list, dict)):
                val = str(val)
            table_data[f"v:{ver}"].append(val)

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ====================================================================
# HTML生成
# ====================================================================


def _generate_batch_html(
    rows: list[dict[str, Any]],
    provider: DashboardDataProvider,
) -> str:
    """バッチ俯瞰のスタティックHTML生成"""
    index_key = provider._index_key
    version_key = provider._version_key
    vn_key = provider._verbose_name_key

    groups = _group_by_index(rows, index_key)
    if not groups:
        return "<p>indexプロパティを持つノードがありません。</p>"

    parts: list[str] = []
    parts.append("<h2>バッチラン俯瞰</h2>")
    parts.append(f"<p>{len(groups)} グループ / {sum(len(v) for v in groups.values())} ノード</p>")

    for idx_name, group_rows in groups.items():
        parts.append(f"<h3>index: {idx_name}</h3>")
        parts.append('<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">')

        for row in group_rows:
            version = row.get(version_key, "(default)")
            status = row.get("analysis_status", "unknown")
            name = row.get(vn_key, row.get("name", ""))

            color_map = {
                "completed": ("#10b981", "#ecfdf5", "#065f46"),
                "failed": ("#ef4444", "#fef2f2", "#991b1b"),
            }
            border, bg, text = color_map.get(status, ("#6b7280", "#f9fafb", "#374151"))

            parts.append(
                f'<div style="padding:12px;border:2px solid {border};'
                f'background:{bg};border-radius:8px;min-width:180px;">'
                f'<div style="font-weight:700;color:{text};">{name}</div>'
                f'<div style="color:#6b7280;font-size:0.8em;">version: {version}</div>'
                f'<div style="color:{text};font-size:0.85em;margin-top:4px;">{status}</div>'
                f"</div>"
            )

        parts.append("</div>")

    return "\n".join(parts)


# ====================================================================
# ユーティリティ
# ====================================================================


def _find_varying_keys(
    groups: OrderedDict[str, list[dict[str, Any]]],
    version_key: str,
    index_key: str,
    vn_key: str,
) -> list[str]:
    """グループ間で値が変動するプロパティキーを抽出"""
    skip_keys = {"id", "name", "type", "format", "related_files", vn_key, index_key, version_key}
    all_keys: set[str] = set()
    for group_rows in groups.values():
        for row in group_rows:
            all_keys.update(row.keys())
    all_keys -= skip_keys

    varying: list[str] = []
    for key in sorted(all_keys):
        values: set[str] = set()
        for group_rows in groups.values():
            for row in group_rows:
                v = row.get(key)
                values.add(str(v) if v is not None else "")
        if len(values) > 1:
            varying.append(key)

    return varying
