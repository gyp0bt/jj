"""ダッシュボード共有ウィジェット

app.pyとコネクター双方が使用するStreamlit UIヘルパー関数を提供する。
コネクターからapp.pyへの逆依存を排除するための共有モジュール。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def estimate_column_width(col_name: str) -> int:
    """列名の文字幅からAgGrid列幅（px）を推定

    日本語（全角）文字は2文字分、英数字は1文字分として計算。
    1文字あたり約10pxとし、パディング30pxを加算。
    最小幅は80px。

    Args:
        col_name: 列名

    Returns:
        推定列幅（ピクセル）
    """
    char_width = 0
    for ch in col_name:
        if ord(ch) > 0x7F:
            char_width += 2
        else:
            char_width += 1
    return max(80, char_width * 10 + 30)


def try_render_aggrid(df: pd.DataFrame) -> bool:
    """AgGridでDataFrameを表示。失敗時はFalseを返す。

    列幅は列名の文字数に基づいて初期設定する。
    日本語は2文字分、英数字は1文字分として計算し、
    最低限列名が見える幅を確保する。

    Returns:
        True: AgGridで描画成功、False: インポート不可
    """
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return False

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
    )
    # 各列の幅を列名の文字幅に基づいて設定
    for col_name in df.columns:
        width = estimate_column_width(col_name)
        gb.configure_column(col_name, minWidth=width, initialWidth=width)
    gb.configure_selection(
        selection_mode="multiple",
        use_checkbox=True,
    )
    gb.configure_pagination(paginationAutoPageSize=True)
    grid_options = gb.build()

    AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=False,
        theme="streamlit",
    )
    return True
