from io import StringIO
from typing import List, Optional

import pandas as pd

from ..misc.decorators import TimeitMeta
from ..read_inp import read_inp
from .grandpa import BaseGrandpaComponent
from .mesh import Mesher


def mesher(
    inp_filepath: Optional[str | List[str]],
    verbose: bool = True,
    timeit_cutoff: float | None = None,
) -> Mesher:
    if timeit_cutoff:

        class DebugMesher(Mesher, metaclass=TimeitMeta): ...

        instance = DebugMesher()
        setattr(instance, "timeit_cutoff", timeit_cutoff)
    else:
        instance = Mesher()

    mesh_data = read_inp(inp_filepath=inp_filepath, verbose=verbose)
    for mesh_data_i, key in zip(
        (mesh_data.nodes, mesh_data.elements, mesh_data.nsets, mesh_data.elsets),
        ("nodes_data", "elements_data", "nset_data", "elset_data"),
    ):
        granpa = getattr(instance, key)
        granpa: BaseGrandpaComponent
        for k, parent_data in mesh_data_i.items():
            if key in ["nset_data", "elset_data"] and any(
                [isinstance(i, str) for i in parent_data.data]
            ):
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

            granpa[k] = granpa.parent_class.from_array(
                arr=parent_data.data, options=parent_data.options
            )
    for _, surface_component in mesh_data.surfaces.items():
        instance.additional_string += "*SURFACE"
        for k, v in surface_component.options.items():
            instance.additional_string += f", {k}={v}"
        instance.additional_string += "\n"
        # print(surface_component.data)
        df = pd.DataFrame(surface_component.data)
        df[list(df.columns)[0]] = " " + df[list(df.columns)[0]].astype(str)
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


def concat(mesh_list: List[Mesher]) -> Mesher:
    mesh = Mesher()
    for mesh_i in mesh_list:
        for parent in mesh_i.iter_all_parents():
            mesh.add_parent_auto(parent=parent, merge=True)
    return mesh
