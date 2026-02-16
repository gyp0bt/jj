from io import StringIO
from typing import Any

import pandas as pd

from ..misc.decorators import TimeitMeta
from ..read_inp import ABQData, read_inp
from .grandpa import BaseGrandpaComponent
from .mesh import Mesher

__all__ = [
    "ABQData",
    "Mesher",
    "concat",
    "mesher",
]


def mesher(
    inp_filepath: str | list[str] | None,
    verbose: bool = True,
    timeit_cutoff: float | None = None,
    cached_abq_data: Any | None = None,
) -> Mesher:
    """Mesherインスタンスを生成する

    Args:
        inp_filepath: .inpファイルのパス
        verbose: 詳細ログを出力するか
        timeit_cutoff: タイムアウト設定
        cached_abq_data: キャッシュ済みABQData（指定時はread_inp()をスキップ）
    """
    if timeit_cutoff:

        class DebugMesher(Mesher, metaclass=TimeitMeta): ...

        instance = DebugMesher()
        instance.timeit_cutoff = timeit_cutoff
    else:
        instance = Mesher()

    if cached_abq_data is not None:
        mesh_data = cached_abq_data
    else:
        mesh_data = read_inp(inp_filepath=inp_filepath, verbose=verbose)
    for mesh_data_i, key in zip(
        (mesh_data.nodes, mesh_data.elements, mesh_data.nsets, mesh_data.elsets),
        ("nodes_data", "elements_data", "nset_data", "elset_data"),
        strict=False,
    ):
        granpa = getattr(instance, key)
        granpa: BaseGrandpaComponent
        for k, parent_data in mesh_data_i.items():
            if key in ["nset_data", "elset_data"] and any([isinstance(i, str) for i in parent_data.data]):
                labels = []
                for i in parent_data.data:
                    if isinstance(i, int):
                        labels.append(i)
                        continue
                    match key:
                        case "nset_data":
                            labels += instance.nodes_data.get_labels(name=i)
                            labels += instance.nset_data.get_labels(name=i)
                        case "elset_data":
                            labels += instance.elements_data.get_labels(name=i)
                            labels += instance.elset_data.get_labels(name=i)
                parent_data.data = labels

            granpa[k] = granpa.parent_class.from_array(arr=parent_data.data, options=parent_data.options)
    for _, surface_component in mesh_data.surfaces.items():
        instance.additional_string += "*SURFACE"
        for k, v in surface_component.options.items():
            instance.additional_string += f", {k}={v}"
        instance.additional_string += "\n"
        # print(surface_component.data)
        df = pd.DataFrame(surface_component.data)
        df[next(iter(df.columns))] = " " + df[next(iter(df.columns))].astype(str)
        csv_buffer: StringIO = StringIO()
        df.to_csv(
            csv_buffer,
            index=False,
            header=False,
            lineterminator="\n",
        )
        instance.additional_string += csv_buffer.getvalue()
    instance.additional_string = instance.additional_string.upper()

    if verbose:
        print(instance)
    return instance


def concat(mesh_list: list[Mesher]) -> Mesher:
    mesh = Mesher()
    for mesh_i in mesh_list:
        for parent in mesh_i.iter_all_parents():
            mesh.add_parent_auto(parent=parent, merge=True)
    return mesh
