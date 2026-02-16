# pymesh/mesh/mesh_base/core.py
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import (
    Any,
    Literal,
    TypeVar,
)

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.spatial import KDTree

from ...etypes import (
    ElementType,
    beam_element_type_list,
    connector_element_type_list,
    element_type_num_nodes_dict,
    shell_element_type_list,
    solid_element_type_list,
    truss_element_type_list,
)
from ...misc.data import cut_dup_numbers
from ...typing import NodeCoordArray, node_coord_array_dtype
from ..child import BaseChildComponent, Element, Node
from ..grandpa import (
    BaseGrandpaComponent,
    ElementField,
    ElementsDict,
    ElsetDict,
    NodesDict,
    NsetDict,
)
from ..misc import is_empty_array
from ..parent import BaseParentComponent, Elements, Elset, Nodes, Nset

TChild = TypeVar("TChild", bound=BaseChildComponent)
TParent = TypeVar("TParent", bound=BaseParentComponent)
TGrandpa = TypeVar("TGrandpa", bound=BaseGrandpaComponent)


@dataclass
class MaxLabel:
    elem: int
    node: int


def _pad_cols(arr: NDArray, target_cols: int, invalid_node: int) -> NDArray:
    """arr を target_cols 列に右側ゼロ埋め（invalid_node）して返す。"""
    cur = arr.shape[1]
    if cur >= target_cols:
        return arr
    pad = np.full((arr.shape[0], target_cols - cur), invalid_node, dtype=arr.dtype)
    return np.hstack((arr, pad))


class CoreMesher:
    def __init__(self):
        self.nodes_data: NodesDict = NodesDict(data=dict())
        self.elements_data: ElementsDict = ElementsDict(data=dict())
        self.nset_data: NsetDict = NsetDict(data=dict())
        self.elset_data: ElsetDict = ElsetDict(data=dict())
        self.additional_string: str = ""

    def __repr__(self) -> str:
        text = "- Mesher\n"
        for data in [
            self.nodes_data,
            self.elements_data,
            self.nset_data,
            self.elset_data,
        ]:
            for key in data:
                text += f"\t- {data.parent_class.__name__}({key})\n"
        return text

    # ----------------------------------
    # Nodes basic
    # ----------------------------------
    def add_nodes(self, name: str, arr: NDArray | list[tuple[float, ...]]) -> Nodes:
        if self.nodes_data.isin(name=name):
            self.nodes_data[name].append_array(arr=arr)
        else:
            if arr is not None:
                nodes = Nodes.from_array(arr=arr, options=dict(nset=name))
            else:
                nodes = Nodes(options=dict(nset=name))
            self.nodes_data[name] = nodes
        return self.nodes_data[name]

    def register_nodes(self, name: str, arr: NDArray | list[tuple[float, ...]], add: bool = False) -> Nodes:
        if add:
            return self.add_nodes(name=name, arr=arr)
        else:
            nodes = Nodes.from_array(arr=arr, options=dict(nset=name))
            self.nodes_data[name] = nodes
            return nodes

    def get_nodes_list(self, name: str | list[str] | None = None) -> list[Nodes]:
        return self.nodes_data.get_parents_list(name=name)

    def iter_nodes(self, name: str | list[str] | None = None) -> Iterable[Node]:
        return self.nodes_data.iter_children(name=name)

    def get_node(self, label: int) -> Node:
        return self.nodes_data.get_child(label=label)

    def get_nodes(self, name: str | list[str] | None = None) -> dict[int, Node]:
        return self.nodes_data.get_children(name=name)

    def get_nodes_keys(self) -> list[str]:
        return list(self.nodes_data.keys())

    # ----------------------------------
    # Elements basic
    # ----------------------------------
    def add_elements(self, name: str, type: str, arr: NDArray | list[tuple[float, ...]]) -> Elements:
        elset_key = self.get_elset_key_from_elset_and_type(elset=name, type=type)
        if self.elements_data.isin(name=elset_key):
            self.elements_data[elset_key].append_array(arr=arr)
        else:
            if arr is not None:
                elements = Elements.from_array(arr=arr, options=dict(elset=name, type=type))
            else:
                elements = Elements(options=dict(elset=name, type=type))
            self.elements_data[elset_key] = elements
        return self.elements_data[elset_key]

    def replace_elements_name(self, org: str, to: str):
        new_elements_data = {}
        for k, elements in self.elements_data.items():
            elements.options["elset"] = k.replace(org, to)
            new_elements_data[k.replace(org, to)] = elements
        self.elements_data.data = new_elements_data

    def get_elset_key_from_elset_and_type(self, elset: str, type: str) -> str:
        return f"{elset},type={type}"

    def register_elements(
        self,
        name: str,
        arr: NDArray | list[tuple[float, ...]],
        type: str,
        add: bool = False,
    ) -> Elements:
        if add:
            return self.add_elements(name=name, arr=arr, type=type)
        else:
            elements = Elements.from_array(arr=arr, options=dict(elset=name, type=type))
            self.elements_data[name] = elements
            return elements

    def get_element_list(self, name: str | list[str] | None = None) -> list[Elements]:
        return self.elements_data.get_parents_list(name=name)

    def iter_elements_with_nodes(self, name: str | list[str] | None = None) -> Iterable[Element]:
        for elements in self.elements_data.get_parents_list(name=name):
            for element in elements.iter_children():
                element: Element
                element.nodes_list = [self.get_node(label=i) for i in element.node_id_list]
                yield element

    def get_element(self, label: int, with_nodes: bool = False) -> Element:
        element = self.elements_data.get_child(label=label)

        if with_nodes:
            element.nodes_list = [self.get_node(label=i) for i in element.node_id_list]

        return element

    def get_elements(self, name: str | list[str] | None = None) -> dict[int, Element]:
        return self.elements_data.get_children(name=name)

    def get_elements_dict(
        self, mode: Literal["type", "num_nodes"], name: str | list[str] | None = None
    ) -> dict[str | int, list[Elements]]:
        """
        Elementsの辞書を取得

        Args:
            * name (Optional[str|list[str]]): Elset名、typeは含まない。ワイルドカード可。
            * mode (Literal["type", "num_nodes"]): 辞書化する際のキー指定
        """
        data = defaultdict(list)

        for elements in self.elements_data.get_parents_list(name=name):
            if mode == "type":
                key = elements.type
            elif mode == "num_nodes":
                key = element_type_num_nodes_dict[elements.type]

            data[key].append(elements)

        return data

    def get_elements_keys(self) -> list[str]:
        return list(self.elements_data.keys())

    # ----------------------------------
    # Nset basic
    # ----------------------------------
    def add_nset(self, name: str, arr: ArrayLike) -> Nset:
        if self.nset_data.isin(name=name):
            self.nset_data[name].append_array(arr=arr)
        else:
            nset = Nset.from_array(arr=arr, options=dict(nset=name))
            self.nset_data[name] = nset
        return self.nset_data[name]

    def register_nset(self, name: str, arr: ArrayLike, add: bool = False) -> Nset:
        if add:
            return self.add_nset(name=name, arr=arr)
        else:
            nset = Nset.from_array(arr=arr, options=dict(nset=name))
            self.nset_data[name] = nset
            return nset

    def get_nset_list(self, name: str | list[str] | None = None) -> list[Nset]:
        return self.nset_data.get_parents_list(name=name)

    def iter_nset(self, name: str | list[str] | None = None) -> Iterable[Node]:
        return self.nset_data.iter_children(name=name)

    def get_nset_keys(self) -> list[str]:
        return list(self.nset_data.keys())

    # ----------------------------------
    # Elset basic
    # ----------------------------------
    def add_elset(self, name: str, arr: ArrayLike) -> Elset:
        if self.elset_data.isin(name=name):
            self.elset_data[name].append_array(arr=arr)
        else:
            elset = Elset.from_array(arr=arr, options=dict(elset=name))
            self.elset_data[name] = elset
        return self.elset_data[name]

    def register_elset(self, name: str, arr: ArrayLike, add: bool = False) -> Elset:
        if add:
            return self.add_elset(name=name, arr=arr)
        else:
            elset_data = Elset.from_array(arr=arr, options=dict(elset=name))
            self.elset_data[name] = elset_data
            return elset_data

    def get_elset_list(self, name: str | list[str] | None = None) -> list[Elset]:
        return self.elset_data.get_parents_list(name=name)

    def iter_elset(self, name: str | list[str] | None = None) -> Iterable[Element]:
        return self.elset_data.iter_children(name=name)

    def get_elset_keys(self) -> list[str]:
        return list(self.elset_data.keys())

    # ----------------------------------
    # get_node_labels
    # ----------------------------------
    def get_node_labels(self, name: str | list[str] | None = None) -> list[int]:
        return self.nodes_data.get_labels(name=name)

    def get_node_labels_with_nset(self, name: str | list[str] | None = None) -> list[int]:
        return self.nset_data.get_labels(name=name)

    def get_node_labels_with_elements(self, name: str | list[str] | None = None) -> list[int]:
        node_label_set = set()
        elements_list = self.elements_data.get_parents_list(name=name)
        for elements_i in elements_list:
            node_label_set.update(elements_i.data[:, 1:].flatten().tolist())
        return list(node_label_set)

    def get_node_labels_with_elset(self, name: str | list[str] | None = None) -> list[int]:
        elset_labels_set = set()
        elset_list = self.elset_data.get_parents_list(name=name)
        for elset_i in elset_list:
            elset_labels_set.update(elset_i.data.tolist())
        elset_labels = list(elset_labels_set)

        node_label_set = set()
        elements_list = self.elements_data.get_parents_list()
        for elements_i in elements_list:
            node_labels_i = elements_i.data[np.isin(elements_i.data[:, 0], elset_labels)][:, 1:].flatten().tolist()
            node_label_set.update(node_labels_i)
        return list(node_label_set)

    def get_node_labels_with_element_labels(self, labels: list[int]) -> list[int]:
        elements = self.get_element_array_with_labels(labels=labels, allow_polymorphism=True, invalid_node=0)
        node_label_list = list(set(elements[:, 1:].flatten().tolist()))
        node_label_list = [i for i in node_label_list if i != 0]
        return node_label_list

    def get_node_label_mapping_with_array(
        self, name: str | list[str] | None = None
    ) -> tuple[dict[int, int], NodeCoordArray]:
        node_coord_arr = self.get_node_coord_array(name=name)
        if node_coord_arr is None:
            raise ValueError("節点データが不正")
        node_label_mapping = {ii["label"]: i for i, ii in enumerate(node_coord_arr)}
        return node_label_mapping, node_coord_arr

    # ----------------------------------
    # update_node_label & update_element_label
    # ----------------------------------

    def update_node_label_with_dict(
        self,
        node_label_mapping: dict[int, int],
        updated_elements_name: str | list[str] | None = None,
        skip_nodes: bool = False,
        skip_nset: bool = False,
        skip_elements: bool = False,
    ):
        if not skip_nodes:
            for nodes in self.nodes_data.values():
                if nodes.data is None:
                    continue

                nodes.data["label"] = np.array([node_label_mapping.get(i, i) for i in nodes.data["label"]])

        if not skip_nset:
            for nset in self.nset_data.values():
                if nset.data is None:
                    continue

                data = [node_label_mapping.get(i, int(i)) for i in nset.data]
                nset.data = np.array(data)

        if not skip_elements:
            for elements in self.elements_data.get_parents_list(name=updated_elements_name):
                if is_empty_array(elements.data):
                    continue

                elements.data[:, 1:] = np.array(
                    [[node_label_mapping.get(i, i) for i in row] for row in elements.data[:, 1:]]
                )

    def update_element_label_with_dict(self, element_label_mapping: dict[int, int]):
        for elements in self.elements_data.values():
            labels = elements.data[:, 0]
            unique_labels = np.unique(labels)
            valid_labels = cut_dup_numbers(unique_labels, list(element_label_mapping.keys()))
            label_indices = {label: np.where(labels == label)[0] for label in valid_labels}
            for label, indices in label_indices.items():
                elements.data[:, 0][indices] = element_label_mapping[label]

        for elset in self.elset_data.values():
            if elset.data is None:
                continue

            elset.data = np.array([element_label_mapping.get(i, i) for i in elset.data])

    def update_node_and_element_labels(self, init_labels: tuple[int, int] = (1, 1)):
        node_labels = self.get_node_labels()
        node_label_mapping = {ii: i + init_labels[0] for i, ii in enumerate(node_labels)}
        self.update_node_label_with_dict(node_label_mapping=node_label_mapping)

        element_labels = self.get_element_labels()
        element_label_mapping = {ii: i + init_labels[1] for i, ii in enumerate(element_labels)}
        self.update_element_label_with_dict(element_label_mapping=element_label_mapping)

    def renumber(self, init_labels: tuple[int, int] = (1, 1)):
        return self.update_node_and_element_labels(init_labels=init_labels)

    # ----------------------------------
    # get_node_coord
    # ----------------------------------
    def get_node_coord(self, name: str | list[str] | None = None) -> dict[int, np.ndarray]:
        node_labels = self.get_node_labels(name=name)
        return self.get_node_coord_with_node_labels(node_labels=node_labels)

    def get_node_coord_with_nset(self, name: str | list[str] | None = None) -> dict[int, np.ndarray]:
        node_labels = self.nset_data.get_labels(name=name)
        return self.get_node_coord_with_node_labels(node_labels=node_labels)

    def get_node_coord_with_elements(self, name: str | list[str] | None = None) -> dict[int, np.ndarray]:
        node_labels = self.get_node_labels_with_elements(name=name)
        return self.get_node_coord_with_node_labels(node_labels=node_labels)

    def get_node_coord_with_elset(self, name: str | list[str] | None = None) -> dict[int, np.ndarray]:
        node_labels = self.get_node_labels_with_elset(name=name)
        return self.get_node_coord_with_node_labels(node_labels=node_labels)

    def get_node_coord_with_node_labels(self, node_labels: list[int]) -> dict[int, np.ndarray]:
        node_label_mapping, node_coord_arr = self.get_node_label_mapping_with_array()
        node_coord = {
            i: np.array(
                (
                    float(node_coord_arr[node_label_mapping[i]]["x"]),
                    float(node_coord_arr[node_label_mapping[i]]["y"]),
                    float(node_coord_arr[node_label_mapping[i]]["z"]),
                )
            )
            for i in node_labels
        }
        return node_coord

    def get_node_coord_with_element_labels(self, labels: list[int]) -> dict[int, np.ndarray]:
        node_coord_array = self.get_node_coord_array_with_element_labels(labels=labels)
        node_coord = {int(i["label"]): np.array((i["x"], i["y"], i["z"])) for i in node_coord_array}
        return node_coord

    # ----------------------------------
    # get_node_coord_array
    # ----------------------------------

    def get_node_coord_array(self, name: str | list[str] | None = None) -> NodeCoordArray:
        return self.nodes_data.get_array(name=name)

    def get_node_coord_array_with_labels(self, labels: list[int]) -> NodeCoordArray:
        node_label_mapping, node_coord_arr = self.get_node_label_mapping_with_array()
        node_index = [node_label_mapping[i] for i in labels]
        return node_coord_arr[node_index]

    def get_node_coord_array_with_element_labels(self, labels: list[int]) -> NodeCoordArray:
        node_label_mapping, node_coord_arr = self.get_node_label_mapping_with_array()
        node_labels = self.get_node_labels_with_element_labels(labels=labels)
        node_labels = [i for i in node_labels if i != 0]

        node_index = [node_label_mapping[i] for i in node_labels]
        node_coord_arr = node_coord_arr[node_index]

        _, unique_idx = np.unique(node_coord_arr["label"], return_index=True)
        node_coord_arr = node_coord_arr[unique_idx]
        return node_coord_arr

    def get_node_coord_array_with_elements(self, name: str | list[str] | None) -> NodeCoordArray:
        node_label_mapping, node_coord_arr = self.get_node_label_mapping_with_array()
        node_labels = self.get_node_labels_with_elements(name=name)

        node_index = [node_label_mapping[i] for i in node_labels]
        node_coord_arr = node_coord_arr[node_index]

        _, unique_idx = np.unique(node_coord_arr["label"], return_index=True)
        node_coord_arr = node_coord_arr[unique_idx]

        return node_coord_arr

    def get_node_coord_array_with_elset(self, name: str | list[str] | None) -> NodeCoordArray:
        node_label_mapping, node_coord_arr = self.get_node_label_mapping_with_array()
        node_labels = self.get_node_labels_with_elset(name=name)
        node_index = [node_label_mapping[i] for i in node_labels]
        node_coord_arr = node_coord_arr[node_index]

        _, unique_idx = np.unique(node_coord_arr["label"], return_index=True)
        node_coord_arr = node_coord_arr[unique_idx]

        return node_coord_arr

    def get_node_coord_array_with_nset(self, name: str | list[str] | None = None) -> NodeCoordArray:
        node_coord_arr = self.get_node_coord_array()
        node_labels = self.get_node_labels_with_nset(name=name)
        node_index = np.isin(node_coord_arr["label"], node_labels)
        node_coord_arr = node_coord_arr[node_index]

        _, unique_idx = np.unique(node_coord_arr["label"], return_index=True)
        node_coord_arr = node_coord_arr[unique_idx]

        return node_coord_arr

    def get_node_coord_array_dict_with_elset(
        self, name: str | list[str] | None = None
    ) -> dict[int, NDArray[np.float32]]:
        element_array = self.elset_data.get_array(name=name)
        if element_array is None:
            raise ValueError(f"elementsが不正 ({self.get_elset_keys()})")
        element_array = element_array.tolist()
        element_array_dict = self.get_element_array_dict(mode="num_nodes")

        new_element_array_dict = {k: v[np.isin(v[:, 0], element_array)] for k, v in element_array_dict.items()}
        node_coord = self.get_node_coord_with_elset(name=name)

        element_node_coord_array_dict = {}
        for k, element_array in new_element_array_dict.items():
            element_node_coord_array = []
            for element in element_array:
                # element_node_coord_i = [element[0]]
                element_node_coord_i = []
                for node_label_i in element[1:]:
                    node_coord_i = node_coord[node_label_i]
                    element_node_coord_i.append(
                        [
                            node_coord_i[0],
                            node_coord_i[1],
                            node_coord_i[2],
                        ]
                    )
                element_node_coord_array.append(element_node_coord_i)
            element_node_coord_array = np.array(element_node_coord_array)
            element_node_coord_array_dict[k] = element_node_coord_array

        return element_node_coord_array_dict

    # ----------------------------------
    # get_node_coord_matrix
    # ----------------------------------
    def get_node_coord_matrix(self, name: str | list[str] | None = None) -> np.ndarray:
        arr = self.nodes_data.get_array(name=name)
        matrix = np.array([arr["label"], arr["x"], arr["y"], arr["z"]]).T
        return matrix

    def get_node_coord_matrix_with_labels(self, labels: list[int]) -> np.ndarray:
        arr = self.get_node_coord_matrix()
        arr = arr[np.isin(arr[:, 0], labels)]
        return arr

    def get_node_coord_matrix_with_nset(self, name: str | list[str]) -> np.ndarray:
        labels = self.get_node_labels_with_nset(name=name)
        arr = self.get_node_coord_matrix_with_labels(labels=labels)
        return arr

    def get_node_coord_matrix_with_elements(self, name: str | list[str]) -> np.ndarray:
        labels = self.get_node_labels_with_elements(name=name)
        arr = self.get_node_coord_matrix_with_labels(labels=labels)
        return arr

    def get_node_coord_matrix_with_elset(self, name: str | list[str]) -> np.ndarray:
        labels = self.get_node_labels_with_elset(name=name)
        arr = self.get_node_coord_matrix_with_labels(labels=labels)
        return arr

    def get_node_coord_matrix_with_element_labels(self, labels: list[int]) -> np.ndarray:
        labels = self.get_node_labels_with_element_labels(labels=labels)
        arr = self.get_node_coord_matrix_with_labels(labels=labels)
        return arr

    # ----------------------------------
    # get_element_coord_matrix
    # ----------------------------------
    def get_element_coord_matrix(self, name: str | list[str] | None = None) -> np.ndarray:
        node_coord_arr = self.get_node_coord_matrix()
        if node_coord_arr is None:
            raise ValueError("nodeデータが不正")
        node_label_mapping = {ii[0]: i for i, ii in enumerate(node_coord_arr)}
        element_array_dict = self.get_element_array_dict(mode="num_nodes")
        element_labels = self.get_element_labels(name=name)
        element_coord_arr_with_label = None

        for element_arr_i in element_array_dict.values():
            new_element_arr_i = element_arr_i.copy()

            if not np.isin(new_element_arr_i[:, 0], element_labels).any():
                continue

            for i, arr_i in enumerate(element_arr_i):
                new_arr_i = np.array([node_label_mapping[j] for j in arr_i[1:]])
                new_element_arr_i[i, 1:] = new_arr_i

            element_coord_arr_i = node_coord_arr[:, 1:][new_element_arr_i[:, 1:]].mean(axis=1)

            element_coord_arr_with_label_i = np.zeros((element_coord_arr_i.shape[0], 4))
            element_coord_arr_with_label_i[:, 0] = element_arr_i[:, 0]
            element_coord_arr_with_label_i[:, 1] = element_coord_arr_i[:, 0]
            element_coord_arr_with_label_i[:, 2] = element_coord_arr_i[:, 1]
            element_coord_arr_with_label_i[:, 3] = element_coord_arr_i[:, 2]

            element_coord_arr_with_label_i = element_coord_arr_with_label_i[
                np.isin(element_coord_arr_with_label_i[:, 0], element_labels)
            ]

            if element_coord_arr_with_label is None:
                element_coord_arr_with_label = element_coord_arr_with_label_i
            else:
                element_coord_arr_with_label = np.append(
                    element_coord_arr_with_label, element_coord_arr_with_label_i, axis=0
                )

        if element_coord_arr_with_label is None:
            raise ValueError(f"element({name})が不正 ({self.get_element_keys()})")

        return element_coord_arr_with_label

    def get_element_coord_matrix_with_labels(self, labels: list[int]) -> np.ndarray:
        arr = self.get_element_coord_matrix()
        arr = arr[np.isin(arr[:, 0], labels)]
        return arr

    def get_element_coord_matrix_with_node_labels(self, labels: list[int]) -> np.ndarray:
        labels = self.get_element_labels_with_node_labels(labels)
        arr = self.get_element_coord_matrix_with_labels(labels=labels)
        return arr

    def get_element_coord_matrix_with_nodes(self, name: str | list[str]) -> np.ndarray:
        labels = self.get_element_labels_with_nodes(name)
        arr = self.get_element_coord_matrix_with_labels(labels)
        return arr

    def get_element_coord_matrix_with_elset(self, name: str | list[str]) -> np.ndarray:
        labels = self.get_element_labels_with_elset(name)
        arr = self.get_element_coord_matrix_with_labels(labels=labels)
        return arr

    # ----------------------------------
    # update_node_coord & update_node_coord_with_array
    # ----------------------------------
    def update_node_coord(self, node_coord: dict[int, np.ndarray]):
        data = [[k, v[0], v[1], v[2]] for k, v in node_coord.items()]
        node_coord_array = np.array([tuple(i) for i in data], dtype=node_coord_array_dtype)
        self.update_node_coord_with_array(node_coord_array)

    def update_node_coord_with_array(self, node_coord_array: NodeCoordArray):
        for nodes_i in self.nodes_data.values():
            node_coord_array_i = nodes_i.data

            # mask = np.isin(node_coord_array_i["label"], node_coord_array["label"])
            sort_org_indices = np.argsort(node_coord_array_i["label"])
            sort_new_indices = np.argsort(node_coord_array["label"])

            _common_labels, org_match_indices, new_match_indices = np.intersect1d(
                node_coord_array_i["label"][sort_org_indices],
                node_coord_array["label"][sort_new_indices],
                return_indices=True,
            )

            for axis in ["x", "y", "z"]:
                node_coord_array_i[axis][sort_org_indices[org_match_indices]] = node_coord_array[axis][
                    sort_new_indices[new_match_indices]
                ]
            nodes_i.data = node_coord_array_i

    # ----------------------------------
    # get_element_labels
    # ----------------------------------
    def get_element_labels_with_nodes(self, name: str | list[str] | None = None) -> list[int]:
        node_labels = self.get_node_labels(name)
        elem_labels = self.get_element_labels_with_node_labels(node_labels)
        return elem_labels

    def get_element_labels_with_nset(self, name: str | list[str] | None = None) -> list[int]:
        node_labels = self.get_node_labels_with_nset(name)
        elem_labels = self.get_element_labels_with_node_labels(node_labels)
        return elem_labels

    def get_element_labels_with_node_labels(
        self, node_labels: list[int], name: str | list[str] | None = None
    ) -> list[int] | None:
        element_data_arr = self.get_element_array(name=name)
        if element_data_arr is None:
            return None
        mask = np.zeros(len(element_data_arr), dtype=bool)
        for i in range(element_data_arr.shape[1] - 1):
            col = i + 1
            mask |= np.isin(element_data_arr[:, col], node_labels)
        return [int(i) for i in element_data_arr[mask][:, 0]]

    def get_element_labels_with_elset(self, name: str | list[str] | None = None) -> list[int]:
        return self.elset_data.get_labels(name=name)

    def get_element_labels(self, name: str | list[str] | None = None) -> list[int]:
        """
        要素ラベルを取得

        Args:
            * name (Optional[str|list[str]]): Elset名、typeは含まない。ワイルドカード可。
        """
        elements_dict = self.get_element_array_dict(mode="num_nodes", name=name)
        labels = []
        for _key, elements_array_i in elements_dict.items():
            if not is_empty_array(elements_array_i):
                labels += elements_array_i[:, 0].tolist()
        return labels

    # ----------------------------------
    # get_element_array
    # ----------------------------------

    def get_element_array(
        self,
        name: str | list[str] | None = None,
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray:
        return self.elements_data.get_array(
            name=name,
            allow_polymorphism=allow_polymorphism,
            invalid_node=invalid_node,
        )

    def get_element_array_with_labels(
        self,
        labels: list[int],
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray:
        """指定ラベルの要素行（[elem_label, n1, n2, ...]）を返す。"""

        element_array_dict = self.get_element_array_dict(mode="num_nodes")

        picked: list[NDArray] = []
        hit_num_nodes: list[int] = []

        # labels が大きいと isin が重いので、まず ndarray 化しておく
        labels_arr = np.asarray(labels)

        for num_nodes, arr in element_array_dict.items():
            # 1列目が要素ラベル前提
            idx = np.isin(arr[:, 0], labels_arr)
            if not idx.any():
                continue

            if hit_num_nodes and (num_nodes != hit_num_nodes[0]) and (not allow_polymorphism):
                raise UserWarning(f"異なる節点数を持つ要素を同時に取得できません ({hit_num_nodes[0]}, {num_nodes})")

            picked.append(arr[idx])  # ここで “上書き” じゃなく “蓄積”
            hit_num_nodes.append(num_nodes)

        if not picked:
            raise RuntimeError("指定 labels に該当する要素が見つかりません")

        if not allow_polymorphism or len(picked) == 1:
            return picked[0]

        # 多型：列数を最大に揃えて結合
        max_cols = max(a.shape[1] for a in picked)
        picked = [_pad_cols(a, max_cols, invalid_node) for a in picked]
        return np.vstack(picked)

    def get_element_array_with_elset(
        self,
        name: str | list[str] | None = None,
        allow_polymorphism: bool = True,
        invalid_node: int = 0,
    ) -> NDArray:
        labels = self.get_element_labels_with_elset(name=name)
        return self.get_element_array_with_labels(
            labels=labels,
            allow_polymorphism=allow_polymorphism,
            invalid_node=invalid_node,
        )

    def get_element_array_dict(
        self,
        mode: Literal["type", "num_nodes"],
        name: str | list[str] | None = None,
    ) -> dict[str | int, NDArray]:
        """
        要素配列の辞書を取得

        Args:
            * name (Optional[str|list[str]]): Elset名、typeは含まない。ワイルドカード可。
            * mode (Literal["type", "num_nodes"]): 辞書化する際のキー指定
        """
        elements_dict = self.get_elements_dict(mode=mode, name=name)

        out: dict[str | int, NDArray] = {}
        for key, elements_list_i in elements_dict.items():
            blocks: list[NDArray] = []
            for elements_i in elements_list_i:
                if elements_i.data is None or elements_i.data.size == 0:
                    continue
                blocks.append(elements_i.data)

            if blocks:
                out[key] = np.vstack(blocks)

        return out

    # ----------------------------------
    # drop_element_coord
    # ----------------------------------
    def get_element_coord(self, name: str | list[str] | None) -> dict[int, np.ndarray | tuple[float, float, float]]:
        element_coord_arr = self.get_element_coord_array(name=name)
        if element_coord_arr is None:
            raise ValueError(f"element({name})データが不正 {self.get_elements_keys()}")

        element_coord = {}
        for i in element_coord_arr:
            element_coord[i["label"]] = np.array([i["x"], i["y"], i["z"]])
        return element_coord

    # ----------------------------------
    # get_element_coord_array
    # ----------------------------------

    def get_element_coord_array_with_elset(self, name: str | list[str] | None) -> NodeCoordArray:
        elset_list = self.elset_data.get_parents_list(name=name)
        labels = set()
        for elset in elset_list:
            labels.update(elset.data)
        labels = list(labels)
        return self.get_element_coord_array_with_labels(labels=labels)

    def get_element_coord_array_with_labels(self, labels: list[int]) -> NodeCoordArray:
        elements_coord_array = self.get_element_coord_array()
        if elements_coord_array is None:
            raise ValueError("elementデータが不正")
        elements_coord_array = elements_coord_array[np.isin(elements_coord_array["label"], labels)]
        return elements_coord_array

    def get_element_coord_array(self, name: str | list[str] | None = None) -> NodeCoordArray:
        """
        節点座標から要素重心座標配列を取得

        Args:
            * name (Optional[str|list[str]]): Elset名、typeは含まない。ワイルドカード可。
        """

        node_coord_arr = self.get_node_coord_array()
        if node_coord_arr is None:
            raise ValueError("nodeデータが不正")
        node_label_mapping = {ii["label"]: i for i, ii in enumerate(node_coord_arr)}
        node_coord_arr = np.column_stack((node_coord_arr["x"], node_coord_arr["y"], node_coord_arr["z"]))
        element_array_dict = self.get_element_array_dict(mode="num_nodes")
        element_labels = self.get_element_labels(name=name)
        element_coord_arr_with_label = None

        for element_arr_i in element_array_dict.values():
            new_element_arr_i = element_arr_i.copy()

            if not np.isin(new_element_arr_i[:, 0], element_labels).any():
                continue

            for i, arr_i in enumerate(element_arr_i):
                new_arr_i = np.array([node_label_mapping[j] for j in arr_i[1:]])
                new_element_arr_i[i, 1:] = new_arr_i

            element_coord_arr_i = node_coord_arr[new_element_arr_i[:, 1:]].mean(axis=1)

            element_coord_arr_with_label_i = np.zeros(
                element_coord_arr_i.shape[0],
                dtype=node_coord_array_dtype,
            )
            element_coord_arr_with_label_i["label"] = element_arr_i[:, 0]
            element_coord_arr_with_label_i["x"] = element_coord_arr_i[:, 0]
            element_coord_arr_with_label_i["y"] = element_coord_arr_i[:, 1]
            element_coord_arr_with_label_i["z"] = element_coord_arr_i[:, 2]

            element_coord_arr_with_label_i = element_coord_arr_with_label_i[
                np.isin(element_coord_arr_with_label_i["label"], element_labels)
            ]

            if element_coord_arr_with_label is None:
                element_coord_arr_with_label = element_coord_arr_with_label_i
            else:
                element_coord_arr_with_label = np.append(
                    element_coord_arr_with_label, element_coord_arr_with_label_i, axis=0
                )

        if element_coord_arr_with_label is None:
            raise ValueError(f"element({name})が不正 {self.get_elements_keys()}")

        return element_coord_arr_with_label

    def _get_element_node_coord_array(
        self,
        element_array: np.ndarray,
        node_coord: dict[int, np.ndarray],
    ) -> NDArray[np.float32]:
        if not isinstance(node_coord, dict):
            raise ValueError(f"node coord must be dict (not {type(node_coord)})")

        element_node_coord_array: list[list[list[float]]] = []

        for element in element_array:
            # element[0] は要素ラベルなので飛ばす
            coords_i: list[list[float]] = []
            for node_label_i in element[1:]:
                # node_coord は {label: np.array([x,y,z])}
                coord = node_coord[int(node_label_i)]
                coords_i.append([float(coord[0]), float(coord[1]), float(coord[2])])

            element_node_coord_array.append(coords_i)

        # 要素ごとの節点数が揃っていれば (Ne, Nn, 3) の float32 配列になる
        return np.asarray(element_node_coord_array, dtype=np.float32)

    def get_element_node_coord_array(
        self,
        name: str | list[str] | None = None,
    ) -> NDArray[np.float32]:
        """要素ごとの節点座標配列を返す.

        Returns:
            shape (Ne, Nn, 3) 相当の ndarray を想定。
        """

        try:
            element_array = self.get_element_array(
                name=name,
                allow_polymorphism=False,
            )
        except Exception as e:
            raise UserWarning("Warning! 節点数の異なる要素を同時に取得はできません") from e
        node_coord = self.get_node_coord_with_elements(name=name)

        return self._get_element_node_coord_array(element_array=element_array, node_coord=node_coord)

    def get_element_node_coord_array_with_labels(self, labels: list[int]) -> NDArray[np.float32]:
        """要素ごとの節点座標配列を返す.

        Args:
            labels (list[int]): 要素ラベルのリスト(節点ラベルではない！)

        Returns:
            shape (Ne, Nn, 3) 相当の ndarray を想定。
        """

        try:
            element_array = self.get_element_array_with_labels(labels=labels)
        except Exception as e:
            raise UserWarning("節点数の異なる要素を同時に取得はできません") from e
        node_coord = self.get_node_coord_with_element_labels(labels=labels)

        return self._get_element_node_coord_array(element_array=element_array, node_coord=node_coord)

    # ----------------------------------
    # etc
    # ----------------------------------

    def dump(
        self,
        inp_filepath: str,
        add: bool = False,
        to_femap: bool = False,
        encoding: str = "utf-8",
    ):
        mode = "a" if add else "w"
        text = ""
        for parent in self.iter_all_parents():
            text += parent.to_str()

        text += self.additional_string

        if to_femap:
            text += "*material, name=M1\n"
            text += "*elastic\n"
            text += " 1., 0.3\n"
            for elements in self.elements_data.values():
                etype = elements.options["type"].upper()
                if etype in solid_element_type_list:
                    text += f"*solid section, elset={elements.name}, material=M1\n"
                elif etype in shell_element_type_list:
                    text += f"*shell section, elset={elements.name}, material=M1\n 1.\n"
                elif etype in beam_element_type_list:
                    text += f"*beam section, elset={elements.name}, material=M1, section=circ\n 0.,1.,0.\n 1.\n"
                elif etype in truss_element_type_list:
                    text += f"*solid section, elset={elements.name}, material=M1\n 1.\n"
                elif etype in connector_element_type_list:
                    text += f"*connector section, elset={elements.name}\n join\n"
                else:
                    raise ValueError(
                        f"Element type({elements.options['type'].upper()}) does not exist in ElementType library({[i.name for i in ElementType]})"
                    )

        with open(inp_filepath, mode, encoding=encoding) as f:
            f.write(text)

    def set_element_fields(self, fields: dict[str, dict[str | int, float]]):
        for key, field in fields.items():
            self.elements_data.fields[key] = ElementField(name=key, field_scalars={int(k): v for k, v in field.items()})

    # ----------------------------------
    # drop_nodes
    # ----------------------------------
    def drop_nodes(self, node_labels: list[int]):
        self.nodes_data.drop_labels(labels=node_labels)
        self.nset_data.drop_labels(labels=node_labels)

    def drop_nodes_except_with(self, except_node_labels: list[int]):
        self.nodes_data.drop_labels(labels=except_node_labels, except_with=True)
        self.nset_data.drop_labels(labels=except_node_labels, except_with=True)

    def drop_unreferenced_nodes(self, drop_empty: bool = True):
        referenced_node_labels = self.get_node_labels_with_elements()
        self.drop_nodes_except_with(except_node_labels=referenced_node_labels)
        self.drop_non_existent_elements_from_elset()
        self.drop_non_existent_nodes_from_nset()
        if drop_empty:
            self.drop_empty_grampa()

    def drop_nodes_with_name(
        self,
        name: str | list[str] | None = None,
        except_name: str | list[str] | None = None,
    ):
        self.nodes_data.drop_names(name=name, except_name=except_name)

    # ----------------------------------
    # drop_elements
    # ----------------------------------
    def drop_elements_with_labels(
        self,
        labels: list[int],
        drop_unreferenced_nodes: bool = False,
    ):
        self.elements_data.drop_labels(labels=labels)
        self.elset_data.drop_labels(labels=labels)
        if drop_unreferenced_nodes:
            self.drop_unreferenced_nodes()

    def drop_elements_except_with(
        self,
        except_elemnt_labels: list[int],
        drop_unreferenced_nodes: bool = False,
    ):
        self.elements_data.drop_labels(labels=except_elemnt_labels, except_with=True)
        self.elset_data.drop_labels(labels=except_elemnt_labels, except_with=True)
        if drop_unreferenced_nodes:
            self.drop_unreferenced_nodes()

    def drop_empty_grampa(self):
        empty_grampas = []
        for k, v in self.nodes_data.data.items():
            if v.data.size == 0:
                empty_grampas.append(k)
        if empty_grampas:
            self.drop_nodes_with_name(empty_grampas)

        empty_grampas = []
        for k, v in self.elements_data.data.items():
            if v.data.size == 0:
                empty_grampas.append(k)
        if empty_grampas:
            self.drop_elements_with_name(empty_grampas)

        empty_grampas = []
        for k, v in self.nset_data.data.items():
            if v.data.size == 0:
                empty_grampas.append(k)
        if empty_grampas:
            self.drop_nset_with_name(empty_grampas)

        empty_grampas = []
        for k, v in self.elset_data.data.items():
            if v.data.size == 0:
                empty_grampas.append(k)
        if empty_grampas:
            self.drop_elset_with_name(empty_grampas)

    def drop_elements_with_name(
        self,
        name: str | list[str] | None = None,
        except_name: str | list[str] | None = None,
        drop_unreferenced_nodes: bool = False,
    ):
        self.elements_data.drop_names(name=name, except_name=except_name)
        if drop_unreferenced_nodes:
            self.drop_unreferenced_nodes()

    # ----------------------------------
    #  drop_elset & drop_nset
    # ----------------------------------

    def drop_non_existent_elements_from_elset(self):
        element_labels = self.get_element_labels()
        self.elset_data.drop_labels(labels=element_labels, except_with=True)

    def drop_non_existent_nodes_from_nset(self):
        node_labels = self.get_node_labels()
        self.nset_data.drop_labels(labels=node_labels, except_with=True)

    def drop_elset_with_name(
        self,
        name: str | list[str] | None = None,
        except_name: str | list[str] | None = None,
    ):
        self.elset_data.drop_names(name=name, except_name=except_name)

    def drop_nset_with_name(
        self,
        name: str | list[str] | None = None,
        except_name: str | list[str] | None = None,
    ):
        self.nset_data.drop_names(name=name, except_name=except_name)

    def drop_duplicated_labels_nset(self, target_nset_name: str, remain_nset_name: str):
        target = self.nset_data.data[target_nset_name]
        remain_nset = self.nset_data.data[remain_nset_name]
        target.data = np.array([i for i in target.data if i not in remain_nset.data])

    # ----------------------------------
    # high-level but core
    # ----------------------------------

    def get_max_labels(self, increment: int = 0) -> MaxLabel:
        """
        節点ラベル、要素ラベルの最大値を返す

        Args:
            * increment (int): 最大値に対して足して返す値
        Returns:
            * 節点ラベルの最大値、要素ラベルの最大値 (MaxLabel)
        """
        node_labels = self.get_node_labels()
        elem_labels = self.get_element_labels()
        max_node_label, max_elem_label = 0, 0
        if node_labels:
            max_node_label = np.max(node_labels)
        if elem_labels:
            max_elem_label = np.max(elem_labels)
        max_node_label += increment
        max_elem_label += increment
        return MaxLabel(node=int(max_node_label), elem=int(max_elem_label))

    def get_number_of_nodes(self) -> int:
        return len(self.get_node_labels())

    def iter_all_parents(self, iter_keys: bool = False) -> Iterator[Any]:
        def _iter(data: Any):
            for k, v in data.items():
                if iter_keys:
                    yield k, v
                yield v

        yield from _iter(self.nodes_data)
        yield from _iter(self.elements_data)
        yield from _iter(self.nset_data)
        yield from _iter(self.elset_data)

    def increment_label(self, increment: int):
        for child in self.iter_all_parents():
            if isinstance(child, Nodes):
                child.data["label"] += increment
            else:
                child.data += increment

    def drop_duplicated_elements(self, name: str | list[str] | None | None = None) -> None:
        """ノード構成が順不同で一致する要素を重複とみなし削除する.

        0列目をラベル、1列目以降を接続ノードとする要素配列を仮定。
        同じ num_nodes ごとに処理し、同じノード構成の最初の1要素だけ残す。

        Args:
            name (Optional[str|list[str]], optional): 要素セット名のフィルタがあるなら使用。
        """
        # num_nodes ごとに要素群が返ってくる前提
        elements_dict = self.get_elements_dict(mode="num_nodes", name=name)

        dup_elem_labels: list[int] = []

        for _num_nodes, elements_list in elements_dict.items():
            if not elements_list:
                continue

            # elements_i.data: shape = (Ni, 1 + num_nodes) を想定
            elem_array = np.vstack([e.data for e in elements_list])
            if elem_array.size == 0:
                continue

            # 0列目 = 要素ラベル
            labels = elem_array[:, 0].astype(int)

            # 1列目以降をソートして順不同を吸収
            conn_sorted = np.sort(elem_array[:, 1:], axis=1)

            # conn_sorted の重複行を unique でグループ化
            # keys: 一意な行
            # idx_first: 各グループの「最初に出現した」行インデックス
            # inverse: 各行がどのグループに属するか (0..G-1)
            # counts: 各グループの要素数
            _keys, idx_first, inverse, counts = np.unique(
                conn_sorted,
                axis=0,
                return_index=True,
                return_inverse=True,
                return_counts=True,
            )

            n = labels.shape[0]
            row_idx = np.arange(n)

            # 各行について:
            # - 自分の属するグループの counts > 1 → そのグループは重複あり
            # - かつ自分の index != そのグループの idx_first → 2回目以降
            dup_mask = (counts[inverse] > 1) & (row_idx != idx_first[inverse])

            dup_elem_labels.extend(labels[dup_mask].tolist())

        if dup_elem_labels:
            self.drop_elements_with_labels(labels=dup_elem_labels)

    def drop_duplicated_nodes(self, tol: float = 1.0e-5):
        node_data_array = self.get_node_coord_array()
        if node_data_array is None:
            raise ValueError("節点データが不正")
        points = np.array([node_data_array["x"], node_data_array["y"], node_data_array["z"]]).T
        tree = KDTree(points)

        to_remove = set()
        node_label_mapping = {}

        for i, point in enumerate(points):
            if node_data_array["label"][i] in to_remove:
                continue
            neighbors = tree.query_ball_point(point, tol)
            for neighbor in neighbors:
                if neighbor > i:
                    to_remove.add(node_data_array["label"][neighbor])
                    node_label_mapping[node_data_array["label"][neighbor]] = node_data_array["label"][i]

        self.update_node_label_with_dict(node_label_mapping=node_label_mapping)
        self.nodes_data.drop_labels(labels=list(to_remove))
        self.drop_duplicated_node_labels()
        self.drop_unreferenced_nodes()
        return to_remove

    def drop_duplicated_node_labels(self):
        for nodes in self.nodes_data.values():
            # 指定した列のラベル情報を抽出
            labels = nodes.data["label"]

            # np.uniqueでラベルの一意な値とその最初の出現インデックスを取得
            _unique_labels, unique_indices = np.unique(labels, return_index=True)

            # 一意なインデックスに対応する行を取得
            nodes.data = nodes.data[np.sort(unique_indices)]

        for nset_data in self.nset_data.values():
            labels = nset_data.data.tolist()
            nset_data.data = np.array(list(set(labels)))

    def drop_duplicated_element_labels(self) -> list[int]:
        dup_labels = set()
        done = set()

        for elements in self.elements_data.values():
            for i in elements.data[:, 1]:
                if i in done:
                    dup_labels.add(i)
                done.add(i)

        return list(dup_labels)

    def copy(self) -> "CoreMesher":
        new_mesh = CoreMesher()
        new_mesh.nodes_data = self.nodes_data.copy()
        new_mesh.elements_data = self.elements_data.copy()
        new_mesh.nset_data = self.nset_data.copy()
        new_mesh.elset_data = self.elset_data.copy()
        return new_mesh

    # ----------------------------------
    # TO BE REMOVED
    # ----------------------------------
    def set_gfront(
        self,
        tol: float = 1.0e-3,
        n_each_area: int | list[int] = 10,
        n_area: int = 3,
        axis: Literal["x", "y", "z"] = "z",
        elset_key: str | list[str] | None = None,
        front_is_negative_side: bool = False,
        set_symmetory: bool = False,
        exclude_front_nodes_for_symmetory_set: bool | list[bool] | None = None,
        efn: bool | list[bool] | None = None,
    ):
        if efn is None:
            efn = [False]
        if isinstance(n_each_area, int):
            n_each_area = [n_each_area for _ in range(n_area)]

        if len(n_each_area) != n_area:
            raise ValueError(f"n_area must be equal to len(n_each_area), not '{n_area}' and '{n_each_area}'")

        if exclude_front_nodes_for_symmetory_set is None:
            exclude_front_nodes_for_symmetory_set = efn

        if not isinstance(exclude_front_nodes_for_symmetory_set, list):
            exclude_front_nodes_for_symmetory_set = [exclude_front_nodes_for_symmetory_set for i in range(n_area)]

        if len(exclude_front_nodes_for_symmetory_set) != n_area:
            exclude_front_nodes_for_symmetory_set = [exclude_front_nodes_for_symmetory_set[0] for i in range(n_area)]

        done_node = set()
        done_elem = set()

        ismin = False
        if front_is_negative_side:
            ismin = True

        front_node_list = set()
        node_coord_array = self.get_node_coord_array_with_elements(name=elset_key)
        elem_array_dict = self.get_element_array_dict(mode="num_nodes", name=elset_key)

        org_element_labels = set()
        for i in elem_array_dict.values():
            org_element_labels.update(i[:, 0].tolist())

        for i in range(n_area):
            done_node_b = done_node.copy()
            done_elem_b = done_elem.copy()

            done_node_front, _, _, _ = self.get_max_or_min_node_and_element_labels(
                tol=tol,
                axis=axis,
                n_iter=1,
                ismin=ismin,
                done_node=set(done_node_b),
                done_elem=set(done_elem_b),
                elset_key=elset_key,
                node_coord_array=node_coord_array,
                elem_array_dict=elem_array_dict,
            )

            done_node, done_elem, _, _ = self.get_max_or_min_node_and_element_labels(
                tol=tol,
                axis=axis,
                n_iter=n_each_area[i],
                ismin=ismin,
                done_node=set(done_node_b),
                done_elem=set(done_elem_b),
                elset_key=elset_key,
                node_coord_array=node_coord_array,
                elem_array_dict=elem_array_dict,
            )

            done_node_i = list(set(done_node_front) - set(done_node_b))
            done_elem_i = list(set(done_elem) - set(done_elem_b))

            if exclude_front_nodes_for_symmetory_set[i]:
                front_node_list.update(done_node_i)

            self.register_nset(name=f"gfront{i + 1}", arr=list(done_node_i), add=False)
            self.register_elset(name=f"gfront{i + 1}", arr=list(done_elem_i), add=False)

        element_labels = np.setdiff1d(np.array(list(org_element_labels)), np.array(list(done_elem))).tolist()
        self.elset_data.drop_names("gmain")
        self.add_elset("gmain", arr=element_labels)

        if set_symmetory:
            if exclude_front_nodes_for_symmetory_set:
                exclude_node_labels = list(front_node_list)
            else:
                exclude_node_labels = []

            self.set_symmetory(tol=tol, elset_key=elset_key, excluded_node_labels=exclude_node_labels)

    def set_symmetory(
        self,
        tol: float = 1.0e-3,
        elset_key: str | list[str] | None = None,
        excluded_node_labels: list[int] | None = None,
    ):
        if excluded_node_labels is None:
            excluded_node_labels = []
        node_coord_array = self.get_node_coord_array_with_elements(name=elset_key)
        elem_array_dict = self.get_element_array_dict(mode="num_nodes", name=elset_key)

        gxmin, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="x",
            n_iter=1,
            ismin=True,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )
        gxmax, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="x",
            n_iter=1,
            ismin=False,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )
        gymin, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="y",
            n_iter=1,
            ismin=True,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )
        gymax, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="y",
            n_iter=1,
            ismin=False,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )
        gzmin, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="z",
            n_iter=1,
            ismin=True,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )
        gzmax, _, _, _ = self.get_max_or_min_node_and_element_labels(
            tol=tol,
            axis="z",
            n_iter=1,
            ismin=False,
            elset_key=elset_key,
            node_coord_array=node_coord_array,
            elem_array_dict=elem_array_dict,
        )

        def f(label_list: list[int]) -> list[int]:
            return [i for i in label_list if i not in excluded_node_labels]

        gxmin = f(gxmin)
        gxmax = f(gxmax)
        gymin = f(gymin)
        gymax = f(gymax)
        gzmin = f(gzmin)
        gzmax = f(gzmax)

        self.register_nset(name="gxmin", arr=gxmin, add=False)
        self.register_nset(name="gxmax", arr=gxmax, add=False)
        self.register_nset(name="gymin", arr=gymin, add=False)
        self.register_nset(name="gymax", arr=gymax, add=False)
        self.register_nset(name="gzmin", arr=gzmin, add=False)
        self.register_nset(name="gzmax", arr=gzmax, add=False)

    def get_max_or_min_node_and_element_labels(
        self,
        tol: float = 1.0e-3,
        axis: Literal["x", "y", "z"] = "z",
        n_iter: int = 1,
        ismin: bool = False,
        done_node: set | None = None,
        done_elem: set | None = None,
        elset_key: str | list[str] | None = None,
        node_coord_array: NodeCoordArray | None = None,
        elem_array_dict: dict[str | int, NDArray] | None = None,
    ) -> tuple[list[int], list[int], NodeCoordArray, dict[str, NDArray]]:
        if done_node is None:
            done_node = set()
        if done_elem is None:
            done_elem = set()

        if isinstance(done_node, list):
            done_node = set(done_node)
        if isinstance(done_elem, list):
            done_elem = set(done_elem)

        if node_coord_array is None:
            node_coord_array = self.get_node_coord_array_with_elements(name=elset_key)
        else:
            node_coord_array = node_coord_array.copy()
        if elem_array_dict is None:
            elem_array_dict = self.get_element_array_dict(mode="num_nodes", name=elset_key)
        else:
            elem_array_dict = {k: v.copy() for k, v in elem_array_dict.items()}

        done_node = done_node.copy()
        done_elem = done_elem.copy()

        for _i in range(n_iter):
            node_coord_array = node_coord_array[~np.isin(node_coord_array["label"], list(done_node))]
            elem_array_dict = {
                k: elem_arr[~np.isin(elem_arr[:, 0], list(done_elem))] for k, elem_arr in elem_array_dict.items()
            }

            if len(node_coord_array) == 0:
                break

            if ismin:
                v = node_coord_array[axis].min()
            else:
                v = node_coord_array[axis].max()

            node_labels_i = node_coord_array[np.abs(node_coord_array[axis] - v) < tol]["label"].tolist()
            elem_labels_i = []
            for elem_arr in elem_array_dict.values():
                elem_labels_i += elem_arr[np.any(np.isin(elem_arr[:, 1:], node_labels_i), axis=1)][:, 0].tolist()

            done_node.update(node_labels_i)
            done_elem.update(elem_labels_i)

        return list(done_node), list(done_elem), node_coord_array, elem_array_dict
