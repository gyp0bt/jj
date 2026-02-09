import json
import os
from collections import defaultdict
from typing import Any, Generator, Optional

import numpy as np
import pandas as pd

# Field = dict[int, float | NDArray]
Field = pd.DataFrame


class Frame:
    def __init__(
        self,
        fields: Optional[dict[str, pd.DataFrame]] = None,
        description: Optional[str] = None,
    ):
        if fields is None:
            fields = {}
        if description is None:
            description = ""
        # self.fields = defaultdict(dict)
        self.fields = defaultdict(pd.DataFrame)
        self.fields.update(fields)
        self.description = description

    def __repr__(self) -> str:
        text = ""
        for field_key, field in self.fields.items():
            text += f"\t\t- {field_key}\n"
        return text


# pd.DataFrame = dict[str, NDArray]


class History:
    def __init__(self, histories: Optional[dict[int, dict[str, pd.DataFrame]]] = None):
        if histories is None:
            histories = {}
        self.histories = defaultdict(dict)
        self.histories.update(histories)

    def __repr__(self) -> str:
        text = ""
        for node_number, node_history in self.histories.items():
            for history_key, history_data in node_history.items():
                text += f"\t\t- ({node_number}){history_key}\n"
        return text


class Step:
    """Stepデータ格納クラス"""

    def __init__(
        self, frames: dict[str, Frame] = None, histories: dict[str, History] = None
    ):
        if frames is None:
            frames = {}
        if histories is None:
            histories = {}
        self.frames = defaultdict(Frame)
        self.histories = defaultdict(History)
        self.frames.update(frames)
        self.histories.update(histories)

    def __repr__(self) -> str:
        text = ""
        for frame_name, frame in self.frames.items():
            text += f"\t- {frame_name}\n"
            text += str(frame)
        for refnode_key, history in self.histories.items():
            text += f"\t- {refnode_key}\n"
            text += str(history)
        return text

    def get_frame(self, index: int) -> Frame:
        if isinstance(index, int):
            if index <= -2:
                raise ValueError(f"index must be larger than -2")
            elif index == -1:
                index = len(self.frames) - 1
            return list(self.frames.values())[index]
        else:
            raise ValueError(f"index must be int (not {index})")

    def get_history(self, refnode: str, node_number: int) -> pd.DataFrame:
        if refnode not in self.histories:
            raise ValueError(
                f"refnode '{refnode}' not in steps.histories (maybe in {list(self.histories.keys())})"
            )
        history = self.histories[refnode]
        if node_number not in history.histories:
            raise ValueError(
                f"node_number '{node_number}' not in history.histories (maybe in {list(history.histories.keys())})"
            )
        node_history = history.histories[node_number]
        return node_history

    def iter_frames(self) -> Generator[tuple[int, Frame], None, None]:
        yield from self.frames.items()


class OdbData:
    """ODBデータ格納クラス

    Args:
        *steps (dict[str, Step]): ステップid(Step-1,Step-2,,) - Step
            *Step.frames (dict[str, Frame]): フレーム番号(**str**) - Frame
                Frame.fields (dict[str, pd.DataFrame]) : フィールド名 - 要素または節点フィールド
            *Step.histories (dict[str, History]): 参照NSET名 - History
                History.histories (dict[int, dict[str, pd.DataFrame]]) : 参照NSET内id - フィールド名 - ステップタイムと値の2D配列
    """

    def __init__(self, steps: dict[str, Step] = None):
        if steps is None:
            steps = {}
        self.steps = defaultdict(Step)
        self.steps.update(steps)
        self.steps = {k: self.steps[k] for k in sorted(self.steps)}

    def __repr__(self) -> str:
        text = ""
        for step_name, step in self.steps.items():
            text += f"- {step_name}\n"
            text += str(step)
        return text

    @classmethod
    def load(cls, json_filepath: str) -> "OdbData":
        return load_odb_json(json_filepath)

    def get_step(self, index: int | str) -> Step:
        """
        Returns:
            *Stepデータ (Step)

        Memo:
            *Step.frames (dict[str, Frame]): フレーム番号(**str**) - Frame
                * Frame.fields (dict[str, pd.DataFrame]) : フィールド名-要素または節点フィールド
            *Step.histories (dict[str, History]): 参照NSET名-History
                * History.histories (dict[int, dict[str, pd.DataFrame]]) : 参照NSET内id - フィールド名 - ステップタイムと値の2D配列
        """
        if isinstance(index, int):
            if index <= -2:
                raise ValueError(f"index must be larger than -2")
            elif index == -1:
                index = len(self.steps) - 1
            return list(self.steps.values())[index]
        else:
            if index not in self.steps:
                raise ValueError(
                    f"step index '{index}' not in odb.steps (maybe in {list(self.steps.keys())})"
                )
            return self.steps[index]

    def get_frame(self, frame_index: int, step_index: str | int = "Step-1") -> Frame:
        """
        Returns:
            *Frameデータ (Frame)

        Memo:
            *Frame.fields (dict[str, pd.DataFrame]) : フィールド名-要素または節点フィールドデータ
        """
        step = self.get_step(step_index)
        return step.get_frame(frame_index)

    def get_history(
        self, step_id: int | str, refnode: str, node_number: int = 0
    ) -> pd.DataFrame:
        """
        Returns:
            *Historyデータ (pd.DataFrame)

        Memo:
            *Step.histories (dict[str, History]): 参照NSET名-History
                * History.histories (dict[int, dict[str, pd.DataFrame]]) : 参照NSET内id - フィールド名 - 値の2D配列 (step time - value)
        """
        step = self.get_step(index=step_id)
        history = step.get_history(refnode=refnode, node_number=node_number)
        return history

    def iter_frames(
        self, step_index_list: Optional[list[str] | list[int]] = None
    ) -> Generator[tuple[int, Frame], None, None]:
        if step_index_list is None:
            step_index_list = list(self.steps.keys())
        for step_index in step_index_list:
            step = self.get_step(step_index)
            yield from step.iter_frames()


def load_odb_json(json_filepath: str) -> OdbData:
    try:
        with open(json_filepath, "r") as f:
            data = json.load(f)
        steps = dict()

        for step_name, step in data.items():
            frames = {}
            histories = {}

            for frame_key, field in step["frames"].items():
                description = field.get("description", "")
                field = {
                    k: pd.DataFrame(v) for k, v in field.items() if k != "description"
                }
                new_field = {}
                for k, v in field.items():
                    df = pd.DataFrame(v)
                    df[0] = df[0].astype(int)
                    new_field[k] = df
                frames[frame_key] = Frame(fields=new_field, description=description)
            for refnode_key, history in step["histories"].items():
                histories[refnode_key] = History(
                    histories={
                        int(k): {str(kk): pd.DataFrame(vv) for kk, vv in v.items()}
                        for k, v in history.items()
                    }
                )

            frames = dict(sorted(frames.items(), key=lambda x: int(x[0])))
            histories = {k: histories[k] for k in sorted(histories)}
            steps[step_name] = Step(frames=frames, histories=histories)

        odb_data = OdbData(steps=steps)
        return odb_data
    except Exception as e:
        raise e
        raise RuntimeError(
            f"Error: Failed to read odb-json {json_filepath} ({e})"
        ) from e
        return None


# seriarize_odb_filepath = (
# "/".join(os.path.abspath(__file__).split("/")[:-1]) + "/bin/seriarize_odb.py"
# )
# print(__file__)
# seriarize_odb_filepath = (
# "/".join(os.path.abspath(__file__).split("/")[:-1]) + "/bin/seriarize_odb.py"
# )
seriarize_odb_filepath = (
    "\\".join(os.path.abspath(__file__).split("\\")[:-1]) + "\\bin\\seriarize_odb.py"
)
# seriarize_odb_filepath = "./" + seriarize_odb_filepath.replace(
# os.path.abspath(os.getcwd()) + "/", ""
# )
# print(seriarize_odb_filepath)
# seriarize_odb_filepath = "shared/services/pymesh/misc/bin/seriarize_odb.py"
# seriarize_odb_filepath_windows = seriarize_odb_filepath.replace(
# "/mnt/c/", "C:/"
# ).replace("/", "\\\\")
seriarize_odb_filepath_windows = seriarize_odb_filepath

# module_name = seriarize_odb_filepath.split("/")[-4]
module_name = seriarize_odb_filepath.split("\\")[-4]


def dump_odb_to_json(
    odb_filepath: str,
    json_filepath: Optional[str] = None,
    field_keys: Optional[list[str] | str] = None,
    steps: Optional[list[str] | str] = None,
    frames: Optional[list[int] | int] = None,
    refnodes: Optional[list[str] | str] = None,
    refnode_numbers: Optional[list[str] | list[int]] = None,
    history_keys: Optional[list[str] | str] = None,
    silent: bool = False,
):
    if isinstance(field_keys, str):
        field_keys = [field_keys]
    if isinstance(steps, str):
        steps = [steps]
    if isinstance(frames, int):
        frames = [frames]
    if json_filepath is None:
        json_filepath = odb_filepath + ".json"
    if isinstance(refnodes, str):
        refnodes = [refnodes]
    if isinstance(refnode_numbers, str):
        refnode_numbers = [refnode_numbers]
    if isinstance(history_keys, str):
        history_keys = [history_keys]

    # command = f"/mnt/c/Windows/System32/cmd.exe /c  C:/SIMULIA/Commands/abq2023.bat python {module_name}/misc/bin/seriarize_odb.py -o {odb_filepath} -j {json_filepath}"
    # command = f"/mnt/c/Windows/System32/cmd.exe /c  C:/SIMULIA/Commands/abq2023.bat python {seriarize_odb_filepath_windows} -o {odb_filepath} -j {json_filepath}"
    # print(os.system("/mnt/c/Windows/System32/cmd.exe /c cd"))
    command = f"C:/SIMULIA/Commands/abq2023.bat python {seriarize_odb_filepath_windows} -o {odb_filepath} -j {json_filepath}"
    # command = f"C:/SIMULIA/Commands/abq2024.bat python {seriarize_odb_filepath_windows} -o {odb_filepath} -j {json_filepath}"
    # command = f"C:/SIMULIA/Commands/abq2025.bat python {seriarize_odb_filepath_windows} -o {odb_filepath} -j {json_filepath}"

    if field_keys:
        command += " -f"
        for i in field_keys:
            command += f" {i}"

    if steps:
        command += " -s"
        for i in steps:
            command += f" {i}"

    if frames:
        command += " -fr"
        for i in frames:
            command += f" {i}"

    if refnodes:
        command += " -rn"
        for i in refnodes:
            command += f" {i}"

    if refnode_numbers:
        command += " -rnn"
        for i in refnode_numbers:
            command += f" {i}"

    if history_keys:
        command += " -hk"
        for i in history_keys:
            command += f" {i}"

    if silent:
        command += f" -sil"

    if not silent:
        print(command)

    # os.system("/mnt/c/Windows/System32/cmd.exe /c cd")
    os.system(command)


def load_odb(
    odb_filepath: str,
    skip_seriarize: bool = False,
    field_keys: Optional[list[str]] = None,
    steps: Optional[list[str]] = None,
    frames: Optional[list[int]] = None,
    refnodes: Optional[list[str]] = None,
    refnode_numbers: Optional[list[str]] = None,
    history_keys: Optional[list[str]] = None,
    silent: bool = True,
) -> OdbData:
    json_filepath = odb_filepath + ".json"
    if skip_seriarize and os.path.exists(json_filepath):
        pass
    else:
        dump_odb_to_json(
            odb_filepath,
            json_filepath,
            field_keys=field_keys,
            steps=steps,
            frames=frames,
            refnodes=refnodes,
            refnode_numbers=refnode_numbers,
            history_keys=history_keys,
            silent=silent,
        )
    odb_data = load_odb_json(json_filepath)
    return odb_data


def get_size(obj: float | list[float]):
    if isinstance(obj, float):
        return 1
    elif isinstance(obj, list):
        return len(obj)
    else:
        raise NotImplementedError


def frame_to_df(frame: Frame, field_keys: list[str]) -> pd.DataFrame:
    fields = {k: v for k, v in frame.fields.items() if k in field_keys}

    df_merged = None
    for k, df_i in fields.items():
        if df_i.shape[1] == 2:
            columns = ["labels", k]
        else:
            columns = ["labels"] + [f"{k}_{i}" for i in range(df_i.shape[1] - 1)]
        df_i.columns = columns
        if df_merged is None:
            df_merged = df_i
        else:
            df_merged = pd.merge(df_merged, df_i, on="labels", how="outer")

    if df_merged is None:
        raise ValueError

    return df_merged


def get_field_df(
    odb: OdbData,
    field_keys: list[str],
    frame_index: int,
    step_index: str | int = "Step-1",
) -> pd.DataFrame:
    frame = odb.get_frame(frame_index, step_index)
    df = frame_to_df(frame, field_keys)
    return df
