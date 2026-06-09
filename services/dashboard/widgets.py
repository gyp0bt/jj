"""ダッシュボード共有ウィジェット（Streamlit UIヘルパー）

`streamlit` / `streamlit-aggrid` への依存は関数内の遅延importに閉じ込めてあり、
本モジュール自体はコア依存のみでimportできる（UIが無い環境でも壊れない）。

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


def estimate_column_width(col_name: str) -> int:
    """列名の文字幅からAgGrid列幅（px）を推定

    日本語（全角）文字は2文字分、英数字は1文字分として計算。
    1文字あたり約10pxとし、パディング30pxを加算。最小幅は80px。
    """
    char_width = 0
    for ch in col_name:
        char_width += 2 if ord(ch) > 0x7F else 1
    return max(80, char_width * 10 + 30)


def try_render_aggrid(
    df: pd.DataFrame,
    *,
    grid_key: str | None = None,
    session_key: str = "filtered_df",
) -> bool:
    """AgGridでDataFrameを表示し、フィルタ/ソート/選択後の行を共有する。

    - 列幅は列名の文字数に基づいて初期設定する（日本語=2文字, 英数字=1文字）。
    - 数値列には ``agNumberColumnFilter``、それ以外には ``agTextColumnFilter`` を設定。
    - チェックボックスで行選択された場合は **選択行のみ**、未選択の場合は
      **フィルタ/ソート通過行全体** を ``st.session_state[session_key]`` に格納する。
      これにより plot 等の後続ビューがテーブルの絞り込み結果を共有できる。

    Args:
        df: 表示するDataFrame
        grid_key: AgGridのStreamlitキー（複数グリッド描画時の衝突回避用）
        session_key: フィルタ後DataFrameを格納する session_state のキー

    Returns:
        True: AgGridで描画成功、False: streamlit-aggrid 未インストール
    """
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return False

    import pandas as pd
    import streamlit as st

    gb = GridOptionsBuilder.from_dataframe(df)
    # editable=False: editable=True だと response.data が「編集後の全行」になり
    # data_return_mode=FILTERED_AND_SORTED が効かなくなるため。
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        groupable=True,
        value=True,
        enableRowGroup=True,
        aggFunc="sum",
        editable=False,
    )
    for col_name in df.columns:
        width = estimate_column_width(str(col_name))
        col_config: dict[str, Any] = {"minWidth": width, "initialWidth": width}
        if df[col_name].dtype in ("int64", "float64", "int32", "float32"):
            col_config["filter"] = "agNumberColumnFilter"
        else:
            col_config["filter"] = "agTextColumnFilter"
        gb.configure_column(col_name, **col_config)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()

    grid_options = gb.build()

    # 既存のグリッド状態（フィルタ/ソート/列）をinitialStateで復元
    saved_state = st.session_state.get("_aggrid_grid_state")
    if saved_state:
        grid_options["initialState"] = saved_state

    response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme="streamlit",
        key=grid_key,
    )

    # グリッド状態（フィルタ含む）を保存して次回描画時に復元する
    grid_state = getattr(response, "grid_state", None)
    if grid_state:
        st.session_state["_aggrid_grid_state"] = grid_state

    # 選択行があれば選択行のみ、無ければフィルタ/ソート通過行全体を共有
    selected = getattr(response, "selected_rows", None)
    if selected is not None and len(selected) > 0:
        result = pd.DataFrame(selected)
    else:
        result = pd.DataFrame(response.data)
    st.session_state[session_key] = result

    return True
