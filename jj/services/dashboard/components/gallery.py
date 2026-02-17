"""ギャラリービューコンポーネント

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.dashboard.components import PageComponent, ViewConfig

if TYPE_CHECKING:
    from config import DashboardConfig, SavedViewConfig
    from services.dashboard.data_provider import DashboardDataProvider


class GalleryViewConfig(ViewConfig):
    """ギャラリービュー設定コンポーネント"""

    view_type = "gallery"

    def render_add_form(
        self,
        provider: DashboardDataProvider,
        **kwargs: Any,
    ) -> dict[str, Any]:
        import streamlit as st

        st.markdown("**ギャラリー設定**")
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            g_source = st.selectbox("ソース", ["has_output", "property"], key="_add_view_gsrc")
        with gc2:
            g_format = st.text_input("フォーマット", key="_add_view_gfmt")
        with gc3:
            # propertyソース時のキー指定
            if g_source == "property":
                prop_images = provider.get_property_images()
                prop_keys = sorted({img["property_key"] for img in prop_images if img.get("property_key")})
                g_prop_key = st.selectbox("プロパティキー", ["（すべて）", *prop_keys], key="_add_view_gpkey")
            else:
                g_prop_key = "（すべて）"
        gallery_config: dict[str, Any] = {"source": g_source}
        if g_format:
            gallery_config["format"] = g_format
        if g_prop_key and g_prop_key != "（すべて）":
            gallery_config["property_key"] = g_prop_key
        return {"gallery": gallery_config}


class GalleryPage(PageComponent[GalleryViewConfig]):
    """ギャラリービューページコンポーネント"""

    page_key = "gallery"
    page_label = "ギャラリー"

    def render_page(
        self,
        provider: DashboardDataProvider,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        project_root = kwargs.get("project_root")
        if project_root is None:
            st.error("project_rootが指定されていません。")
            return
        project_root = Path(project_root)

        st.header("画像ギャラリー")

        # 画像ソース選択
        source_options = ["has_output関係", "プロパティ画像パス"]
        image_source = st.radio("画像ソース", source_options, horizontal=True)

        if image_source == "has_output関係":
            _render_gallery_output_images(provider, project_root, dashboard_config)
        else:
            _render_gallery_property_images(provider, project_root, dashboard_config)

    def render_saved_view(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> None:
        import streamlit as st

        project_root = kwargs.get("project_root")
        if project_root is None:
            return
        project_root = Path(project_root)

        gallery_config = view.gallery
        source = gallery_config.get("source", "has_output")
        property_key = gallery_config.get("property_key")
        format_filter = gallery_config.get("format")

        if source == "property":
            images = provider.get_property_images()
            if property_key:
                images = [img for img in images if img["property_key"] == property_key]
        else:
            images = provider.get_output_images()

        if format_filter:
            images = [img for img in images if img["image_format"] == format_filter]

        if not images:
            st.info("条件に一致する画像がありません。")
            return

        cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
        rows_per_page = getattr(dashboard_config, "gallery_rows", 4)
        max_display = cols_per_row * rows_per_page
        images = images[:max_display]

        st.caption(f"{len(images)} 件")
        _render_image_grid(
            images,
            cols_per_row,
            project_root,
            source="property" if source == "property" else "output",
        )

    def generate_html(
        self,
        provider: DashboardDataProvider,
        view: SavedViewConfig,
        dashboard_config: DashboardConfig,
        **kwargs: Any,
    ) -> str:
        # ギャラリーのHTMLエクスポートは未実装（画像はローカルパス依存のため）
        return ""


# ====================================================================
# ギャラリー内部描画関数
# ====================================================================


def _render_gallery_output_images(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """has_output関係の画像ギャラリー（NxMグリッド・グループ表示対応）"""
    import streamlit as st

    from services.dashboard.query import collect_group_keys, filter_images_by_keys

    images = provider.get_output_images()

    if not images:
        st.info(
            "画像出力が見つかりません。has_output関係で画像ファイル"
            "（PNG/GIF/JPG等）が紐付いているgo_ノードがありません。"
        )
        return

    # フィルタ: フォーマット
    formats = sorted({img["image_format"] for img in images})
    selected_format = st.sidebar.selectbox("画像フォーマット", ["すべて", *formats])
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # フィルタ: キー名リスト指定（result_keyベース）
    from services.dashboard.query import _extract_result_key_from_path

    available_result_keys = sorted({_extract_result_key_from_path(img.get("image_path", "")) for img in images} - {""})
    if available_result_keys:
        selected_keys = st.sidebar.multiselect(
            "result_keyフィルタ",
            available_result_keys,
            key="_gallery_output_key_filter",
        )
        if selected_keys:
            images = filter_images_by_keys(images, selected_keys, source="output")

    # グループ表示オプション（デフォルト: 最初の利用可能キー）
    group_keys = collect_group_keys(images, source="output")
    group_options = ["なし", *group_keys]
    default_group_idx = 1 if group_keys else 0
    group_by = st.sidebar.selectbox(
        "グループ表示",
        group_options,
        index=default_group_idx,
        key="_gallery_output_group",
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(images, cols_per_row, project_root, source="output", group_key=group_by)
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input("ページ", min_value=1, max_value=total_pages, value=1)
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx : start_idx + max_display]

    st.caption(
        f"{len(page_images)} / {total_images} 件 "
        f"（{cols_per_row}列 x {rows_per_page}行、ページ {page_num}/{total_pages}）"
    )

    if not page_images:
        st.info("条件に一致する画像がありません。")
        return

    # NxMグリッドで表示
    _render_image_grid(page_images, cols_per_row, project_root, source="output")


def _render_gallery_property_images(
    provider: DashboardDataProvider,
    project_root: Path,
    dashboard_config: Any,
) -> None:
    """プロパティ画像パスのギャラリー（キー別一覧・NxMグリッド・グループ表示対応）"""
    import streamlit as st

    from services.dashboard.query import collect_group_keys, filter_images_by_keys, normalize_group_key

    images = provider.get_property_images()

    if not images:
        st.info(
            "プロパティに画像ファイルパスが見つかりません。"
            "Obsidianのdaily noteからプロパティに画像パスを割り当てたノードがありません。"
        )
        return

    # キー名リスト指定フィルタ（multiselect、未選択時は全件表示）
    all_keys = sorted({normalize_group_key(img["property_key"]) for img in images})
    selected_keys = st.sidebar.multiselect(
        "プロパティキー",
        all_keys,
        key="_gallery_property_key_filter",
    )
    if selected_keys:
        images = filter_images_by_keys(images, selected_keys, source="property")

    # フォーマットフィルタ
    formats = sorted({img["image_format"] for img in images})
    selected_format = st.sidebar.selectbox("画像フォーマット（プロパティ）", ["すべて", *formats])
    if selected_format != "すべて":
        images = [img for img in images if img["image_format"] == selected_format]

    # グループ表示オプション（デフォルト: property_key でグループ化）
    group_keys = collect_group_keys(images, source="property")
    group_options = ["なし", *group_keys]
    # property_keyが利用可能な場合はデフォルトで選択
    default_group_idx = 0
    if "property_key" in group_keys:
        default_group_idx = group_options.index("property_key")
    elif group_keys:
        default_group_idx = 1
    group_by = st.sidebar.selectbox(
        "グループ表示（プロパティ）",
        group_options,
        index=default_group_idx,
        key="_gallery_property_group",
    )

    # NxMグリッド設定
    cols_per_row = getattr(dashboard_config, "gallery_columns", 5)
    rows_per_page = getattr(dashboard_config, "gallery_rows", 4)

    if group_by != "なし":
        st.caption(f"{len(images)} 件（グループ: {group_by}）")
        _render_gallery_grouped(images, cols_per_row, project_root, source="property", group_key=group_by)
        return

    max_display = cols_per_row * rows_per_page

    # ページネーション
    total_images = len(images)
    total_pages = max(1, (total_images + max_display - 1) // max_display)
    page_num = st.sidebar.number_input("ページ（プロパティ画像）", min_value=1, max_value=total_pages, value=1)
    start_idx = (page_num - 1) * max_display
    page_images = images[start_idx : start_idx + max_display]

    st.caption(
        f"{len(page_images)} / {total_images} 件 "
        f"（{cols_per_row}列 x {rows_per_page}行、ページ {page_num}/{total_pages}）"
    )

    if not page_images:
        st.info("条件に一致する画像がありません。")
        return

    # NxMグリッドで表示
    _render_image_grid(page_images, cols_per_row, project_root, source="property")


def _render_gallery_grouped(
    images: list[dict[str, Any]],
    cols_per_row: int,
    project_root: Path,
    source: str,
    group_key: str,
) -> None:
    """画像をグループ別に表示

    Args:
        images: 画像情報のリスト
        cols_per_row: 1行あたりの列数
        project_root: プロジェクトルート
        source: "output" or "property"
        group_key: グループ化に使用するキー
    """
    from collections import OrderedDict

    import streamlit as st

    from services.dashboard.query import extract_path_metadata, normalize_group_key

    if group_key == "result_key":
        # 画像パスからresult_keyとプロパティを抽出してグルーピング
        groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        for img in images:
            path = img.get("image_path", "")
            result_key, _props = extract_path_metadata(path)
            gk = result_key if result_key else "(その他)"
            groups.setdefault(gk, []).append(img)

        for group_name, group_images in groups.items():
            # グループ内の画像からプロパティ情報を表示
            st.subheader(f"result_key: {group_name}")
            # 代表的なプロパティを表示
            sample_path = group_images[0].get("image_path", "")
            _, sample_props = extract_path_metadata(sample_path)
            if sample_props:
                prop_str = ", ".join(f"{k}={v}" for k, v in sorted(sample_props.items()))
                st.caption(f"{len(group_images)} 件 | {prop_str}")
            else:
                st.caption(f"{len(group_images)} 件")
            _render_image_grid(group_images, cols_per_row, project_root, source=source)
        return

    groups_ord: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for img in images:
        if group_key == "property_key":
            # property_keyでグルーピング（daily:日付:キー → キー部分のみ）
            raw_key = img.get("property_key", "")
            gk = normalize_group_key(raw_key)
        else:
            # go_propertiesのキーでグルーピング
            gk = str(img.get("go_properties", {}).get(group_key, "（未設定）"))
        groups_ord.setdefault(gk, []).append(img)

    for group_name, group_images in groups_ord.items():
        st.subheader(f"{group_key}: {group_name}")
        st.caption(f"{len(group_images)} 件")
        _render_image_grid(group_images, cols_per_row, project_root, source=source)


def _render_image_grid(
    images: list[dict[str, Any]],
    cols_per_row: int,
    project_root: Path,
    source: str,
) -> None:
    """画像をNxMグリッドで描画

    Args:
        images: 画像情報のリスト
        cols_per_row: 1行あたりの列数
        project_root: プロジェクトルート
        source: "output"（has_output）または "property"（プロパティ画像パス）
    """
    import streamlit as st

    for row_start in range(0, len(images), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, img_info in enumerate(images[row_start : row_start + cols_per_row]):
            with cols[col_idx]:
                # ヘッダー情報（表示名を優先使用）
                display_name = img_info.get("display_name", img_info["go_node_name"])
                if source == "output":
                    st.markdown(f"**{display_name}**")
                    image_path_str = img_info["image_path"]
                    caption = img_info["image_name"]
                else:
                    st.markdown(f"**{display_name}**")
                    st.caption(f"key: {img_info['property_key']}")
                    image_path_str = img_info["image_path"]
                    caption = f"{img_info['property_key']}: {Path(image_path_str).name}"

                # 画像表示（プロジェクトルート基準、フォールバック: notes/daily基準）
                image_path = project_root / image_path_str
                if not image_path.exists():
                    # notes/daily基準のパスとして再試行
                    fallback = project_root / "notes" / "daily" / image_path_str
                    if fallback.exists():
                        image_path = fallback
                if image_path.exists():
                    st.image(
                        str(image_path),
                        caption=caption,
                        use_container_width=True,
                    )
                else:
                    st.warning(f"画像が見つかりません: {image_path_str}")
