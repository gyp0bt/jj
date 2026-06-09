"""画像ギャラリーページ（旧 plot image page）

go_ ノードの出力画像（``has_output`` 関係）またはプロパティに埋め込まれた
画像パスを収集し、ファイル名のパラメータ（result_key, vmax, step ...）で
グルーピングしてサムネイル表示する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from jj.services.dashboard.data_provider import DashboardDataProvider
from jj.services.dashboard.images import group_images_by_composite_key
from jj.services.graph import GraphService


@st.cache_resource
def load_provider() -> DashboardDataProvider:
    svc = GraphService()
    gm = svc.load(resolve_externalized=True)
    return DashboardDataProvider(graph=gm, project_root=Path("./"))


def main() -> None:
    st.set_page_config(page_title="画像", page_icon="🖼️", layout="wide")
    st.title("🖼️ 画像ギャラリー")

    provider = load_provider()
    project_root = Path("./").resolve()

    source = st.sidebar.radio("ソース", ["出力画像 (has_output)", "プロパティ画像"])
    cols_per_row = st.sidebar.slider("列数", min_value=1, max_value=8, value=4)

    if source.startswith("出力"):
        images = provider.get_output_images()
    else:
        images = provider.get_property_images()

    if not images:
        st.info("画像が見つかりませんでした。")
        return

    groups = group_images_by_composite_key(images)
    st.caption(f"{len(images)} 枚 / {len(groups)} グループ")

    for group_key, imgs in groups.items():
        st.subheader(group_key)
        cols = st.columns(cols_per_row)
        for i, img in enumerate(imgs):
            path = img.get("image_path", "")
            p = Path(path)
            if not p.is_absolute():
                p = project_root / p
            caption = img.get("display_name") or img.get("go_node_name") or p.name
            with cols[i % cols_per_row]:
                if p.exists():
                    st.image(str(p), caption=caption, use_container_width=True)
                else:
                    st.caption(f"⚠️ 見つかりません: {path}")


if __name__ == "__main__":
    main()
