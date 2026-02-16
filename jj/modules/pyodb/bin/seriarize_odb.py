# -*- coding: mbcs -*-
# Do not delete the follswing import lines
import argparse
import json
import os
import time
from collections import defaultdict
from functools import wraps
from typing import ClassVar

import numpy as np
from abaqusConstants import *  # noqa: F403
from odbAccess import HistoryPoint, openOdb


class ConstantsAPI:
    ON = ON  # noqa: F405
    OFF = OFF  # noqa: F405

    class SESSIONSTEP:
        NAME = "Session Step"
        TIME = TIME  # noqa: F405

    class FEATURE_OPTIONS:
        FEATURE = FEATURE  # noqa: F405
        FREE = FREE  # noqa: F405
        NONE = NONE  # noqa: F405
        ALL = ALL  # noqa: F405

    class CONTOUR_OPTIONS:
        CONTOURS_ON_DEF = CONTOURS_ON_DEF  # noqa: F405
        INTEGRATION_POINT = INTEGRATION_POINT  # noqa: F405
        COMPONENT = COMPONENT  # noqa: F405

    class ANIMETION_OPTIONS:
        TIME_HISTORY = TIME_HISTORY  # noqa: F405
        UNLIMITED = UNLIMITED  # noqa: F405
        AVI = AVI  # noqa: F405

    class FIELD_OPTIONS:
        MAX_PRINCIPAL = MAX_PRINCIPAL  # noqa: F405
        MIN_PRINCIPAL = MIN_PRINCIPAL  # noqa: F405
        MISES = MISES  # noqa: F405


C = ConstantsAPI


class MathAPI:
    def sqrt(self, value):
        return sqrt(value)  # noqa: F405

    def power(self, value, n):
        return power(value, n)  # noqa: F405


math = MathAPI()


class Debug:
    @staticmethod
    def show_error(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                print("SomethingError: error in " + f.__name__)
                print(e)
                raise e

        return wrapper

    @staticmethod
    def show_error_method(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except Exception as e:
                print("SomethingError: error in " + self.__class__.__name__ + "." + f.__name__)
                print(e)
                raise e

        return wrapper


class DecorateMethods(type):
    def __new__(cls, name, bases, dct):
        for attr_name, attr_value in dct.items():
            if isinstance(attr_value, staticmethod):
                # staticmethodの場合はdecorator1を適用
                unwrapped_func = attr_value.__func__
                dct[attr_name] = staticmethod(Debug.show_error(unwrapped_func))
            elif callable(attr_value):
                # 通常のメソッドにはdecorator2を適用
                dct[attr_name] = Debug.show_error_method(attr_value)
        return super().__new__(cls, name, bases, dct)


class OdbWrapper:
    # __metaclass__ = DecorateMethods

    def __init__(self, odb_filepath):
        self.odb_filepath = odb_filepath

        self.odb = openOdb(odb_filepath)

    def __str__(self):
        return self.odb_filepath

    def get_or_create_scratch_odb(self):
        return self.odb

    def get_step(self, step=1):
        step_name = OdbWrapper.get_step_name(step, self.odb_filepath)
        if step_name in self.odb.steps:
            return self.odb.steps[step_name]
        elif step_name in self.get_or_create_scratch_odb().steps:
            return self.get_or_create_scratch_odb().steps[step_name]

    def iter_steps(self):
        yield from self.odb.steps.items()

    def get_session_step(self, step=C.SESSIONSTEP.NAME):
        scratch_odb = self.get_or_create_scratch_odb()
        return scratch_odb.steps[step]

    @staticmethod
    def get_step_name(step=1, odb_filepath=None):
        step_name = step
        if isinstance(step, int):
            if step < 0:
                odb = OdbWrapper(odb_filepath)
                step_name = [i for i in odb.odb.steps][step]
            else:
                step_name = "Step-" + str(step)
        return step_name

    def get_frame(self, step=1, frame_index=0):
        step = self.get_step(step=step)
        frame = step.frames[frame_index]
        return frame

    def get_session_frame(self, step=C.SESSIONSTEP.NAME, frame_index=0):
        step = self.get_session_step(step=step)
        frame = self.get_or_create_session_frame(frame_index=frame_index)
        return frame

    def get_or_create_session_frame(self, step=C.SESSIONSTEP.NAME, frame_index=0):
        step = self.get_session_step(step=step)
        if frame_index > len(step.frames):
            message = (
                "Frame index must be serialized, current size: "
                + str(len(step.frames))
                + ", specified index: "
                + str(int(frame_index))
            )
            raise ValueError(message)
        elif frame_index == len(step.frames):
            frame = self.create_session_frame(frame_index=frame_index)
        else:
            frame = step.frames[frame_index]
        return frame

    def create_session_frame(self, frame_index=0):
        session_step = self.get_or_create_session_step()
        session_frame = session_step.Frame(
            frameId=frame_index,
            frameValue=float(frame_index),
            description="Session Frame",
        )
        return session_frame

    def get_or_create_session_step(self):
        scratch_odb = self.get_or_create_scratch_odb()
        if C.SESSIONSTEP.NAME not in scratch_odb.steps:
            session_step = scratch_odb.Step(
                name=C.SESSIONSTEP.NAME,
                description="",
                domain=C.SESSIONSTEP.TIME,
                timePeriod=1.0,
            )
        else:
            session_step = scratch_odb.steps[C.SESSIONSTEP.NAME]
        return session_step

    def get_field_output(self, field_name, step, frame_index=0):
        frame = self.get_frame(step=step, frame_index=frame_index)
        return frame.fieldOutputs[field_name]

    def create_field_output(self, field, field_name, step=C.SESSIONSTEP.NAME, frame_index=0):
        self.get_or_create_session_step()
        frame = self.get_session_frame(step=step, frame_index=frame_index)

        if field_name in frame.fieldOutputs:
            if not globals().get("silent"):
                print(field_name + " already exists in " + step + ", passed to create field")
            return

        frame.FieldOutput(name=field_name, field=field)
        if not globals().get("silent"):
            print("Created new field '" + field_name + "' successfully !")

    def dump_field_to_json(self, field_name, step, frame_index=-1, type="element"):
        json_filepath = self.odb_filepath[:-4] + ".json"

        if os.path.exists(json_filepath):
            try:
                with open(json_filepath) as f:
                    field_dict = json.load(f)
            except Exception:
                field_dict = dict()
        else:
            field_dict = dict()

        field = self.get_field_output(field_name=field_name, step=step, frame_index=frame_index)
        step_name = self.get_step_name(step, self.odb_filepath)

        if step_name not in field_dict:
            field_dict[step_name] = dict()

        if frame_index not in field_dict[step_name]:
            field_dict[step_name][frame_index] = dict()

        if type == "element":
            field_dict[step_name][frame_index][field_name] = {i.elementLabel: i.data for i in field.values}
        elif type == "node":
            field_dict[step_name][frame_index][field_name] = {i.nodeLabel: i.data for i in field.values}

        if isinstance(field.values[0].data, np.ndarray):
            field_dict[step_name][frame_index][field_name] = {
                k: [str(i) for i in v] for k, v in field_dict[step_name][frame_index][field_name].items()
            }

        with open(json_filepath, "w") as f:
            json.dump(field_dict, f, indent=1)

    def get_history(self, refnode, key, step, node_number=0):
        endSet = self.odb.rootAssembly.instances["PART-1-1"].nodeSets[refnode]
        histPoint = HistoryPoint(node=endSet.nodes[node_number])
        tipHistories = self.odb.steps[self.get_step_name(step, self.odb_filepath)].getHistoryRegion(point=histPoint)
        values = tipHistories.historyOutputs[key].data
        return [i[0] for i in values], [i[1] for i in values]


class MimicData:
    def __init__(self, data, nodeLabel=None, elementLabel=None):
        self.data = data
        self.nodeLabel = nodeLabel
        self.elementLabel = elementLabel


class MimicField:
    def __init__(self, data, type="element"):
        self._data = data
        self.type = type

    @property
    def values(self):
        for i, v in self._data.items():
            nodeLabel, elementLabel = None, None
            if self.type == "node":
                nodeLabel = i
            elif self.type == "element":
                elementLabel = i
            else:
                raise ValueError("type cannot be " + self.type)
            data = MimicData(data=v, nodeLabel=nodeLabel, elementLabel=elementLabel)
            yield data


def average_by_id(data):
    ids = data[:, 0].astype(int)
    values = data[:, 1:]

    sort_idx = np.argsort(ids)
    ids_sorted = ids[sort_idx]
    values_sorted = values[sort_idx]

    unique_ids, start_indices, counts = np.unique(ids_sorted, return_index=True, return_counts=True)

    result = np.empty((len(unique_ids), values.shape[1] + 1))

    for i, (uid, start, count) in enumerate(zip(unique_ids, start_indices, counts, strict=False)):
        v_avg = values_sorted[start : start + count].mean(axis=0)
        result[i, 0] = uid
        result[i, 1:] = v_avg

    return result


class FieldWrapper:
    def __init__(self):
        self.field = None

    def is_element_field(self):
        for i in self.field.values:
            return getattr(i, "elementLabel", None) is not None

    def is_ndarray(self):
        for i in self.field.values:
            return isinstance(i.data, np.ndarray)

    def to_dict(self):
        if self.is_element_field():
            key = "elementLabels"
        else:
            key = "nodeLabels"

        blocks = self.field.bulkDataBlocks
        labels = getattr(blocks[0], key)
        values = blocks[0].data
        for b in [i for i in blocks][1:]:
            labels = np.append(labels, getattr(b, key))
            if b.data.shape[1] > values.shape[1]:
                pad_width = ((0, 0), (0, b.data.shape[1] - values.shape[1]))
                values = np.pad(values, pad_width, mode="constant", constant_values=np.nan)
                values = np.vstack((values, b.data))
            elif b.data.shape[1] < values.shape[1]:
                pad_width = ((0, 0), (0, values.shape[1] - b.data.shape[1]))
                data = np.pad(b.data, pad_width, mode="constant", constant_values=np.nan)
                values = np.vstack((values, data))
            else:
                values = np.vstack((values, b.data))
        values = values.reshape(-1, values.shape[1])

        labels = labels.astype(int)
        # values = np.mean(values, axis=1)

        data = np.hstack((labels.reshape(-1, 1), values))
        data = average_by_id(data)
        data = data.tolist()

        return data


def print_time(t1, t2, description):
    cutoff = 0.1
    if t2 - t1 > cutoff:
        silent = globals().get("silent", None)
        if silent is None or not silent:
            print(f"Processed in {t2 - t1:.1f} sec." + f" --- '{description}'")


def print_msg(description):
    silent = globals().get("silent", None)
    if silent is None or not silent:
        print(description)


class Frame:
    def __init__(self):
        self.fields = defaultdict(FieldWrapper)
        self.description = ""

    def to_dict(self):
        data = dict()
        data["description"] = self.description
        for field_key_i, field_i in self.fields.items():
            time.time()
            value = field_i.to_dict()
            data[field_key_i] = value
            time.time()
            # print_time(t1, t2, "Converted field to dict ({})".format(field_key_i))
        return data


class NodeHistory:
    def __init__(self):
        # Dict[history_key, data]
        self.histories = dict()


class History:
    def __init__(self):
        # Dict[refnode_number, HistoryUnit]
        self.histories = defaultdict(NodeHistory)

    def to_dict(self):
        data = dict()
        for key_i, history_i in self.histories.items():
            data[key_i] = history_i.histories
        return data


class Step:
    def __init__(self):
        self.frames = defaultdict(Frame)
        self.histories = defaultdict(History)

    def to_dict(self):
        data = dict(frames=dict(), histories=dict())
        for frame_name_i, frame_i in self.frames.items():
            frame_data_i = frame_i.to_dict()
            t1 = time.time()
            data["frames"][frame_name_i] = frame_data_i
            t2 = time.time()
            print_time(t1, t2, f"Converted frame data to dict ({frame_name_i})")

        for refnode_i, history_i in self.histories.items():
            history_unit_data_i = history_i.to_dict()
            data["histories"][refnode_i] = history_unit_data_i

        return data


class OdbData:
    def __init__(self):
        self.steps = defaultdict(Step)

    def to_dict(self):
        data = {}
        for step_name_i, step_i in self.steps.items():
            t1 = time.time()
            step_data_i = step_i.to_dict()
            data[step_name_i] = step_data_i
            t2 = time.time()
            print_time(t1, t2, f"Converted step data to dict ({step_name_i})")
        return data


class Dummy:
    historyOutputs: ClassVar[dict] = {}


class OdbSeriarizer:
    def __init__(self, odb_filepath):
        self.odb_filepath = odb_filepath
        self.odb = OdbWrapper(odb_filepath)
        self.data = OdbData()
        for step_name_i, _step_i in self.odb.iter_steps():
            self.data.steps[step_name_i] = Step()

    def get_fields(self, field_key_list=None, step_name_list=None, frame_key_list=None):

        if isinstance(field_key_list, str):
            field_key_list = [field_key_list]
        if isinstance(frame_key_list, int):
            frame_key_list = [frame_key_list]
        if isinstance(step_name_list, str):
            step_name_list = [step_name_list]

        if step_name_list is None:
            step_name_list = list(self.odb.odb.steps.keys())

        if frame_key_list is None:
            max_frame_size = 0
            for step_name in step_name_list:
                step = self.odb.odb.steps[step_name]
                if len(step.frames) > max_frame_size:
                    max_frame_size = len(step.frames)
            frame_key_list = [i for i in range(max_frame_size)]

        if field_key_list is None:
            frame = self.odb.odb.steps[step_name_list[0]].frames[0]
            field_key_list = list(frame.fieldOutputs.keys())

        for step_name in step_name_list:
            step = self.odb.odb.steps[step_name]
            for frame_index in frame_key_list:
                if len(step.frames) <= frame_index + 1:
                    continue
                frame = step.frames[frame_index]
                for field_key in field_key_list:
                    if field_key in ["maxPrincipal", "minPrincipal", "mises"]:
                        continue

                    if not globals()["silent"]:
                        print_msg("Getting value of " + str((step_name, frame_index, field_key)))

                    field = frame.fieldOutputs[field_key]
                    self.data.steps[step_name].frames[frame_index].fields[field_key.replace(" ", "")].field = field

                    for i in ["S", "LE"]:
                        if i != field_key:
                            continue

                        keys = ["maxPrincipal", "minPrincipal"]
                        if field_key == i:
                            keys.append("mises")

                        keys = [k for k in keys if k in field_key_list]

                        t1 = time.time()

                        for k in keys:
                            if k == "maxPrincipal":
                                mode = C.FIELD_OPTIONS.MAX_PRINCIPAL
                            elif k == "minPrincipal":
                                mode = C.FIELD_OPTIONS.MIN_PRINCIPAL
                            elif k == "mises":
                                mode = C.FIELD_OPTIONS.MISES
                            self.data.steps[step_name].frames[frame_index].fields[k].field = frame.fieldOutputs[
                                i
                            ].getScalarField(mode)

                        t2 = time.time()
                        print_time(t1, t2, f"Got field data '{keys}'")

    def get_histories(
        self,
        refnode_key_list=None,
        refnode_number_list=None,
        step_name_list=None,
        history_key_list=None,
    ):
        for step_name, step in self.odb.iter_steps():
            if step_name_list is not None and step_name not in step_name_list:
                continue
            for refnode_key, endSet in self.odb.odb.rootAssembly.instances["PART-1-1"].nodeSets.items():
                if refnode_key_list is not None and refnode_key not in refnode_key_list:
                    continue
                for refnode_number, refnode in enumerate(endSet.nodes):
                    if refnode_number_list is not None and refnode_number not in refnode_number_list:
                        continue
                    histPoint = HistoryPoint(node=refnode)
                    try:
                        tipHistories = step.getHistoryRegion(point=histPoint)
                    except Exception:
                        tipHistories = Dummy
                for history_key, history_data in tipHistories.historyOutputs.items():
                    if history_key_list is not None and history_key not in history_key_list:
                        continue
                    data = [[i[0], i[1]] for i in history_data.data]
                    self.data.steps[step_name].histories[refnode_key].histories[int(refnode_number)].histories[
                        history_key
                    ] = data

    def dump(self, json_filepath, mode="w"):
        t1 = time.time()
        data = self.data.to_dict()
        t2 = time.time()
        if not globals()["silent"]:
            print_time(t1, t2, "Converted all data to dict")
        with open(json_filepath, mode) as f:
            t1 = time.time()
            json.dump(data, f, indent=1)
            # json.dump(data, f, indent=None)
            t2 = time.time()
            if not globals()["silent"]:
                print_time(t1, t2, "Dumped data to json")
            # json.dump(data, f)


def convert_wsl_to_windows_filepath(filepath):
    if "/mnt/" in filepath:
        vals = filepath.split("/")[2:]
        drive_name = vals[0].upper()
        win_filepath = drive_name + ":\\\\" + "\\\\".join(vals[1:])
    else:
        win_filepath = os.path.abspath(filepath)
    return win_filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--odb_filepath", "-odb", type=str)
    parser.add_argument("--json_filepath", "-json", type=str)
    parser.add_argument("--fields", "-f", nargs="+")
    parser.add_argument("--steps", "-s", nargs="+")
    parser.add_argument("--frames", "-fr", nargs="+")
    parser.add_argument("--refnodes", "-rn", nargs="+")
    parser.add_argument("--refnode_numbers", "-rnn", nargs="+")
    parser.add_argument("--history_keys", "-hk", nargs="+")
    parser.add_argument("--silent", "-sil", action="store_true")

    args = parser.parse_args()

    args.odb_filepath = convert_wsl_to_windows_filepath(args.odb_filepath)
    args.json_filepath = convert_wsl_to_windows_filepath(args.json_filepath)

    args.frames = [int(i) for i in args.frames] if args.frames is not None else None
    args.refnode_numbers = [int(i) for i in args.refnode_numbers] if args.refnode_numbers is not None else None

    globals()["silent"] = args.silent

    o = OdbSeriarizer(odb_filepath=args.odb_filepath)
    o.get_fields(
        step_name_list=args.steps,
        field_key_list=args.fields,
        frame_key_list=args.frames,
    )
    if args.history_keys is not None or args.refnodes is not None:
        o.get_histories(
            step_name_list=args.steps,
            refnode_key_list=args.refnodes,
            refnode_number_list=args.refnode_numbers,
            history_key_list=args.history_keys,
        )
    if args.json_filepath is not None:
        o.dump(args.json_filepath)
    else:
        o.dump(args.odb_filepath + ".json")

    print_msg("dumped " + args.odb_filepath + " succeccfully")
