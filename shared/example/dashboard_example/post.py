import sys
import os

sys.path.append(os.getcwd())

import glob
import io

import numpy as np
import plotly.express as px
from plotly import graph_objects as go
import pandas as pd
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

import streamlit as st
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder


def _f(s) -> str:
    name = (
        s.replace("go_", "")
        .replace("_sk1amp", "")
        .replace("idx", "条件")
        .replace("iL", "端末間距離")
        .replace("L", "電線長")
        .replace("D", "変位")
        .replace("rxfm", "固定端側角度-")
        .replace("rxf", "固定端側角度")
        .replace("deg", "度")
        .replace("rxmm", "可動端側角度-")
        .replace("rxm", "可動端側角度")
        .replace("rzmm", "L字方向角度-")
        .replace("rzm", "L字方向角度")
        .replace("dxm", "奥行オフセット-")
        .replace("dx", "奥行オフセット")
        .replace("acc", "加速度")
    )
    return name


def parse(s: str) -> dict:
    name = _f(s)
    index = name.split("_")[0].replace("条件", "")
    length = name.split("_")[1].replace("電線長", "").replace("mm", "")
    displacement = name.split("_")[2].replace("変位", "").replace("mm", "")
    distance = name.split("_")[3].replace("端末間距離", "").replace("mm", "")
    rxf = name.split("_")[4].replace("固定端側角度", "").replace("度", "")
    rxm = name.split("_")[5].replace("可動端側角度", "").replace("度", "")
    rzm = name.split("_")[6].replace("L字方向角度", "").replace("度", "")
    offset = name.split("_")[7].replace("奥行オフセット", "").replace("mm", "")
    acceleration = name.split("_")[8].replace("加速度", "").replace("G", "")
    data = dict(
        name=name,
        index=index,
        length=length,
        displacement=displacement,
        distance=distance,
        rxf=rxf,
        rxm=rxm,
        rzm=rzm,
        offset=offset,
        acceleration=acceleration,
        filename=s,
    )
    data = {
        k: (
            float(v)
            if k not in ["name", "filename", "index", "type", "parsed_name"]
            else v
        )
        for k, v in data.items()
    }
    data["extra_length_ratio"] = (
        # (data["length"] - data["distance"]) / data["length"] * 100.0
        (data["length"] - data["distance"]) / data["distance"] * 100.0
    )
    omega = np.sqrt((data["acceleration"] * 9.8) / data["displacement"] / 1.0e-3)
    data["frequency"] = float(f"{omega / 2 / np.pi:.2e}")
    if data["rxf"] >= 90.0 and data["rxm"] <= -90.0:
        type = "U字"
    elif data["rxf"] >= 45.0 and data["rxm"] <= -45.0:
        type = "半U字"
    elif (np.abs(data["rxf"]) - 45.0) * (np.abs(data["rxm"]) - 45.0) <= 0:
        type = "片U字"
    elif np.abs(data["rzm"]) > 0.0:
        type = "L字"
    elif np.abs(data["offset"]) > 0.0:
        type = "オフセット"
    else:
        type = "通常/その他"

    parsed_name = (
        f"{index}, 電線長:{length}mm, 端末間距離:{distance}mm, 変位量:{displacement}mm"
    )
    data["type"] = type
    data["parsed_name"] = parsed_name
    data["jp_dict"] = {
        "name": "名前",
        "type": "型名",
        "parsed_name": "表示名",
        "index": "条件",
        "first": "報告親番号",
        "second": "報告子番号",
        "length": "電線長[mm]",
        "displacement": "変位量[mm]",
        "distance": "端末間距離[mm]",
        "rxf": "固定端角度[deg.]",
        "rxm": "可動端角度[deg.]",
        "rzm": "L字方向角度[deg.]",
        "offset": "オフセット[mm]",
        "extra_length_ratio": "余長率[%]",
        "acceleration": "加速度[G]",
        "frequency": "周波数[Hz]",
        "full_index": "通し番号",
        "filename": "ファイル名",
        "max": "曲率変化量(最大値)[-]",
        "fix": "曲率変化量(固定端部)[-]",
        "center": "曲率変化量(端部以外)[-]",
        "move": "曲率変化量(可動端部)[-]",
        "num_displacement": "加振回数[-]",
        "cumulative_damage_degree": "累積損傷度[-]",
    }
    data["jp_to_arg_dict"] = {v: k for k, v in data["jp_dict"].items()}
    return data


png_filepath_list = list(glob.glob("*.png"))


st.set_page_config(layout="wide")

df = pd.read_csv("./reports/area_sk1_results.csv", encoding="shift-jis")

args = parse(df["filename"].values.tolist()[0])
df.columns = [args["jp_dict"][i] if i in args["jp_dict"] else i for i in df.columns]
xcol_list = [
    args["jp_dict"][i]
    for i in [
        "num_displacement",
        "extra_length_ratio",
        "length",
        "displacement",
        "distance",
        "rxf",
        "rxm",
        "rzm",
        "offset",
    ]
]
ycol_list = [
    args["jp_dict"][i]
    for i in ["max", "fix", "move", "center", "cumulative_damage_degree"]
]

names = df[args["jp_dict"]["name"]]
df = df[
    [
        i
        for i in df.columns
        if i
        not in [
            args["jp_dict"]["filename"],
            args["jp_dict"]["name"],
            "jp_dict",
        ]
    ]
]
df[args["jp_dict"]["name"]] = names

st.header("anonymous project")

st.subheader("結果一覧")
gb = GridOptionsBuilder.from_dataframe(df)
# gb.configure_pagination()
gb.configure_side_bar()
gb.configure_default_column(
    groupable=True, value=True, enableRowGroup=True, aggFunc="sum", editable=True
)
gb.configure_selection(selection_mode="multiple", use_checkbox=True)
gridOptions = gb.build()
response = AgGrid(df, gridOptions=gridOptions, enable_enterprise_modules=True)
df = response["data"]

grouped_elements = {
    args["jp_dict"][i]: df.groupby(args["jp_dict"][i]).groups.keys()
    for i in [
        "type",
        "first",
        "second",
        "distance",
        "displacement",
        "extra_length_ratio",
        "acceleration",
    ]
}

options_list = {k: [] for k in grouped_elements.keys()}

with st.sidebar.form(key="option_form"):
    for k, v in grouped_elements.items():
        options = st.multiselect(f"{k}", options=v, default=[])
        options_list[k] = options

    num_max_images = st.number_input("画像最大表示数を指定", value=100)
    mode = st.selectbox("形式", ["png", "gif"])
    submitted = st.form_submit_button("絞り込み")

df_display = df.copy()
if submitted:
    for k, v in options_list.items():
        if v:
            df_display = df_display[df_display[k].isin(v)]
    df_display = df_display.reset_index(drop=True)


def create_excel_with_meiryo(df: pd.DataFrame) -> bytes:
    """
    DataFrame をメモリ上で .xlsx に書き出し、全セルをメイリオフォントに設定したものを返す。

    Args:
        df (pd.DataFrame): 書き出したいデータフレーム

    Returns:
        bytes: フォント情報を含むxlsxバイナリ
    """
    # メモリ上にExcelを書き出すためのバッファ
    output = io.BytesIO()

    # ExcelWriter を openpyxl エンジンで使用し、DataFrameを書き出す
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")

        # Workbook / Worksheet オブジェクトを取得
        wb = writer.book
        ws: Worksheet = wb["Sheet1"]

        # シート全体のセルにフォント情報を適用
        for row in ws.iter_rows():
            for cell in row:
                cell.font = Font(name="メイリオ")  # フォント名を好きなものに変更可

    # BytesIOの先頭にポインタを戻す（ダウンロード時に正しく読み込めるように）
    output.seek(0)

    # getvalue() で bytes が取得できる
    return output.getvalue()


if df_display.shape[0] == 0:
    st.warning("条件が存在しません。")

else:
    df_xlsx = df_display[
        [i for i in df.columns if i not in [args["jp_dict"][j] for j in ["filename"]]]
    ]
    excel_data = create_excel_with_meiryo(df_xlsx)
    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name="data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    st.subheader("曲率変化量")
    ycol = st.selectbox("y軸", ycol_list)
    fig = px.bar(
        df_display,
        x=args["jp_dict"]["parsed_name"],
        y=ycol,
        color=args["jp_dict"]["type"],
        title="曲率変化量(最大)",
    )
    st.plotly_chart(fig)

    xcol = st.selectbox("x軸", xcol_list, key="xcol-scatter1")
    ycol = st.selectbox("y軸", ycol_list, key="ycol-scatter1")

    fig = go.Figure()
    group_keys = ["length", "distance", "acceleration", "rxf", "rxm", "rzm", "offset"]
    group_keys = [args["jp_dict"][i] for i in group_keys]
    grouped_df = df_display.copy().groupby(group_keys)
    for i, df_i in grouped_df:
        fig.add_trace(
            go.Scatter(
                x=df_i[xcol],
                y=df_i[ycol],
                mode="lines",
                line=dict(color="gray", dash="dot"),
                showlegend=False,
            )
        )

    lines = px.scatter(
        df_display,
        x=xcol,
        y=ycol,
        color=args["jp_dict"]["type"],
        title="曲率変化量(最大)",
        hover_data={
            args["jp_dict"]["index"]: True,
            args["jp_dict"]["parsed_name"]: True,
        },
    )

    for trace in lines.data:
        fig.add_trace(trace)

    fig.update_layout(title=f"{xcol}-{ycol}", xaxis_title=xcol, yaxis_title=ycol)
    if xcol == args["jp_dict"]["num_displacement"]:
        fig.update_layout(xaxis_type="log")

        if ycol != args["jp_dict"]["cumulative_damage_degree"]:
            x_values = np.linspace(
                df_display[xcol].min() * 0.9, df_display[xcol].max() * 1.1, 100
            )

            def baskin(k):
                return 0.0414 * k ** (-0.11)

            y_values = [baskin(i) for i in x_values]

            ymax_values = [df_display[ycol].max() * 1.03] * len(x_values)

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=ymax_values,  # すべてのXに対してYmax
                    mode="lines",
                    line=dict(color="rgba(255,255,255,0)"),  # ラインを透明に
                    showlegend=False,
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",  # ラインのみ
                    fill="tonexty",  # X軸ゼロまで塗りつぶし
                    fillcolor="rgba(250, 30, 0, 0.3)",  # RGBAで透明度30%の青
                    line=dict(color="red"),  # ラインの色
                    name="NG領域(0.0414x^(-0.11))",
                )
            )

    st.plotly_chart(fig)


st.divider()
st.subheader("画像一覧")


if df_display.shape[0] == 0:
    st.warning("条件が存在しません。")
else:
    for i in range(min([int(df_display.shape[0] // 5) + 1, int(num_max_images // 5)])):
        cols = st.columns(5, vertical_alignment="center", border=True)
        for j in range(5):
            filename = df_display[args["jp_dict"]["name"]][i * 5 + j]
            with cols[j]:
                tmp_df = pd.DataFrame(
                    {
                        args["jp_dict"][k]: [df_display[args["jp_dict"][k]][i * 5 + j]]
                        for k in [
                            "index",
                            "length",
                            "distance",
                            "displacement",
                            "acceleration",
                            "frequency",
                            "type",
                        ]
                    }
                )
                tmp_df.index = ["値"]
                st.table(tmp_df.T)

                match mode:
                    case "png":
                        if os.path.exists("./reports/" + filename + ".merged.png"):
                            st.image("./reports/" + filename + ".merged.png")
                        else:
                            st.warning(
                                f"画像がありません(./reports/{filename}.merged.png)"
                            )
                    case "gif":
                        if os.path.exists("./reports/" + filename + ".gif"):
                            with open("./reports/" + filename + ".gif", "rb") as f:
                                gif_data = f.read()
                            st.image(gif_data)
                        else:
                            st.warning(f"画像がありません(./reports/{filename}.gif)")

            if i * 5 + j + 1 >= df_display.shape[0]:
                break
        if i * 5 + j + 1 >= df_display.shape[0]:
            break
