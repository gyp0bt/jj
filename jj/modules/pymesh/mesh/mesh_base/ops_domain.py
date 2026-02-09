# pymesh/mesh/mesh_base/ops_domain.py
from __future__ import annotations

from typing import Optional, Dict, List, Tuple
from typing import Literal, TYPE_CHECKING, Any, Iterator, Iterable, Callable

import numpy as np
from numpy.typing import NDArray

from scipy.spatial import KDTree
from .. import utils
from ..grandpa import (
    BaseParentComponent,
    BaseGrandpaComponent,
    BaseChildComponent,
    ElementsDict,
    NodesDict,
    Nodes,
    Elements,
    Elset,
    Nset,
    NsetDict,
    ElsetDict,
    ElementField,
    Element,
    Node,
)
from ...etypes import ElementType

from ...misc.quality import get_element_quality
from ...typing import NodeCoordArray, node_coord_array_dtype
from .protocol import MesherCoreProtocol

if TYPE_CHECKING:
    # 型チェック時のみ self の型に使う
    from ..mesh import Mesher


class DomainOpsMixin:
    """ドメイン特化 Mesher 操作群.

    MesherCoreProtocol の public API のみを利用すること。
    """

    def update_node_coord_with_odb_U(
        self: MesherCoreProtocol,
        u1: dict[str, float] | None = None,
        u2: dict[str, float] | None = None,
        u3: dict[str, float] | None = None,
    ):
        if u1 is not None:
            labels = u1.keys()
        elif u2 is not None:
            labels = u2.keys()
        elif u3 is not None:
            labels = u3.keys()
        else:
            raise ValueError(f"you must specify at least one of u1, u2, u3")

        node_coord = self.get_node_coord()
        for label in labels:
            intlabel = int(label)
            try:
                if u1 is not None:
                    node_coord[intlabel][0] += u1[label]
                if u2 is not None:
                    node_coord[intlabel][1] += u2[label]
                if u3 is not None:
                    node_coord[intlabel][2] += u3[label]
            except:
                pass
        self.update_node_coord(node_coord=node_coord)

    def update_node_coord_with_odb_COORD(
        self: MesherCoreProtocol, node_coord: dict[str, dict[str, float]]
    ):
        node_coord_modif = {
            int(k): np.array([v["0"], v["1"], v["2"]]) for k, v in node_coord.items()
        }
        self.update_node_coord(node_coord=node_coord_modif)

    def drop_overranged_elements(
        self: MesherCoreProtocol,
        element_coord_range: tuple[tuple[float | None, float | None], ...] = (
            (None, None),
            (None, None),
            (None, None),
        ),
    ):
        element_coord_arr = self.get_element_coord_array()
        if element_coord_arr is None:
            raise ValueError(f"elementデータが不正")
        over_ranged_element_labels = []

        def _drop(labels: list, arr: NDArray, axis: str, index: int = 0) -> NDArray:
            vmin = arr[axis].min()
            vmax = arr[axis].max()
            if element_coord_range[index][0] is not None:
                target_vmin = (vmax - vmin) * element_coord_range[index][0] + vmin
                indices = arr[axis] >= target_vmin
                labels += list(arr[~indices]["label"])
                arr = arr[indices]

            if element_coord_range[index][1] is not None:
                target_vmax = (vmax - vmin) * element_coord_range[index][1] + vmin
                indices = arr[axis] <= target_vmax
                labels += list(arr[~indices]["label"])
                arr = arr[indices]

            return arr

        for index, axis in enumerate(["x", "y", "z"]):
            element_coord_arr = _drop(
                labels=over_ranged_element_labels,
                arr=element_coord_arr,
                axis=axis,
                index=index,
            )

        self.drop_elements_with_labels(labels=over_ranged_element_labels)
        self.drop_unreferenced_nodes()

    @staticmethod
    def get_neighbors_with_coord_array(
        arr1: NodeCoordArray,
        arr2: NodeCoordArray,
        dmax: float = 1.0e-3,
        dmin: float | None = None,
        arr_is_structured: bool = True,
    ) -> list[tuple[int, int]]:
        if arr_is_structured:
            points1 = np.array([[i["x"], i["y"], i["z"]] for i in arr1])
        else:
            points1 = arr1.copy()[:, 1:]
            arr1 = np.array(
                [(i[0], i[1], i[2], i[3]) for i in arr1], dtype=node_coord_array_dtype
            )
            arr2 = np.array(
                [(i[0], i[1], i[2], i[3]) for i in arr2], dtype=node_coord_array_dtype
            )

        tree = KDTree(data=points1)
        pairs = []

        for i in arr2:
            if indices := tree.query_ball_point(x=[i["x"], i["y"], i["z"]], r=dmax):
                if dmin is not None:
                    exception = tree.query_ball_point(
                        x=[i["x"], i["y"], i["z"]], r=dmin
                    )
                    indices = [i for i in indices if i not in exception]
                for index in indices:
                    pairs.append((i["label"], arr1[index]["label"]))

        return pairs

    def merge_meshes(self: MesherCoreProtocol, other: MesherCoreProtocol):
        def add_parent_auto(parent: BaseParentComponent):
            if not isinstance(parent, BaseParentComponent):
                raise ValueError(
                    f"Argument parent is not BaseParentComponent, but {parent}"
                )

            elif isinstance(parent, Nodes):
                key = parent.name
                data = self.nodes_data
            elif isinstance(parent, Elements):
                key = f"{parent.name},type={parent.options['type']}"
                data = self.elements_data
            elif isinstance(parent, Nset):
                key = parent.name
                data = self.nset_data
            elif isinstance(parent, Elset):
                key = parent.name
                data = self.elset_data
            else:
                raise ValueError(f"oops! something happened in {parent}!")

            org_parent = data.data.get(key, None)
            if org_parent is not None:
                org_parent.append_array(parent.data)
                parent = org_parent

            data[key] = parent

        for parent in iter_all_parents(other):
            add_parent_auto(parent)
        return self

    def set_slope_along_axis(
        self: MesherCoreProtocol,
        scale: tuple[float, float],
        vminmax: tuple[float, float],
        elset_name: Optional[str | list[str]] = None,
        axis: Literal["x", "y", "z"] = "z",
        scale_overranged: bool = True,
    ):
        node_coord_array = self.get_node_coord_array_with_element(name=elset_name)
        if vminmax[0] is None:
            vminmax = (node_coord_array[axis].min(), vminmax[1])
        if vminmax[1] is None:
            vminmax = (vminmax[0], node_coord_array[axis].min())
        if vminmax[0] >= vminmax[1]:
            raise ValueError
        columns = [i for i in ["x", "y", "z"] if i != axis]
        r = np.sqrt(
            node_coord_array[columns[0]] ** 2 + node_coord_array[columns[1]] ** 2
        )
        t = np.arctan2(node_coord_array[columns[0]], node_coord_array[columns[1]])

        amp = vminmax[1] - vminmax[0]
        indices = (node_coord_array[axis] >= vminmax[0]) & (
            node_coord_array[axis] <= vminmax[1]
        )

        slope = scale[1] - scale[0]
        local_v = (node_coord_array[axis][indices] - vminmax[0]) / amp

        scale_array = local_v * slope + scale[0]
        r[indices] *= scale_array

        if scale_overranged:
            r[node_coord_array[axis] < vminmax[0]] *= scale[0]
            r[node_coord_array[axis] > vminmax[1]] *= scale[1]

        node_coord_array[columns[0]] = r * np.sin(t)
        node_coord_array[columns[1]] = r * np.cos(t)

        self.update_node_coord_with_array(node_coord_array=node_coord_array)

    def update_element_types(self: MesherCoreProtocol, type_mapping: dict[str, str]):
        for org, new in type_mapping.items():
            for org_key, elements_i in self.elements_data.items():
                if org == elements_i.type:
                    elements_i.options["type"] = new
                    new_key = self.get_elset_key_from_elset_and_type(
                        elset=elements_i.name, type=new
                    )
                    self.elements_data.drop_names(org_key.split(",")[0])
                    self.elements_data[new_key] = elements_i

    def square_to_circle(
        self: MesherCoreProtocol,
        l: float,
        r: float,
        plane: Literal["xy", "yz", "zx"] = "xy",
        name: Optional[str | list[str]] = None,
    ):
        if plane != "xy":
            raise NotImplementedError

        node_coord_array = self.get_node_coord_array(name=name)
        if node_coord_array is None:
            raise ValueError(f"節点データ({name})が不正")

        radius_array = np.sqrt(node_coord_array["x"] ** 2 + node_coord_array["y"] ** 2)
        theta_array = np.arctan2(node_coord_array["y"], node_coord_array["x"])

        org_theta_array = theta_array.copy()

        for _ in range(3):
            theta_array[theta_array > np.pi / 2.0] -= np.pi / 2.0
        theta_array[theta_array > np.pi / 4.0] = (
            np.pi / 2.0 - theta_array[theta_array > np.pi / 4.0]
        )
        square_radius_array = np.sqrt(l**2 / (1 - np.sin(theta_array) ** 2))
        scale = r / square_radius_array

        radius_array *= scale
        # indices = theta_array > np.pi / 4.0 * (0.97)
        # radius_array[indices] += (r - radius_array[indices]) * 0.05

        node_coord_array["x"] = radius_array * np.cos(org_theta_array)
        node_coord_array["y"] = radius_array * np.sin(org_theta_array)

        self.update_node_coord_with_array(node_coord_array=node_coord_array)

    def set_refnode(
        self: MesherCoreProtocol,
        elset_name: Optional[str | list[str]],
        refnode_name: Optional[str] = None,
    ):

        if refnode_name is None:
            if isinstance(elset_name, str):
                refnode_name = "ref" + elset_name[1:]
            else:
                raise ValueError(f"elset_name or refnode_name must be defined")

        if isinstance(elset_name, str):
            elset_name = [elset_name]

        elem_coord_arr = self.get_element_coord_array(name=elset_name)
        if elem_coord_arr is None:
            raise ValueError(f"elset({elset_name})が不正")

        init_node_label = self.get_max_labels().node

        center_of_roll = np.array(
            [
                elem_coord_arr["x"].mean(),
                elem_coord_arr["y"].mean(),
                elem_coord_arr["z"].mean(),
            ]
        )

        self.add_nodes(
            name=refnode_name,
            arr=np.array(
                [
                    [
                        init_node_label + 1,
                        center_of_roll[0],
                        center_of_roll[1],
                        center_of_roll[2],
                    ]
                ]
            ),
        )

        # points = np.array([[i["x"], i["y"], i["z"]] for i in elem_coord_arr])
        # pca = PCA(n_components=3)
        # pca.fit(points)

        # normal = pca.components_[-1]
        # x1, y1, z1 = center_of_roll
        # dx, dy, dz = normal
        # x2, y2, z2 = x1 + dx, y1 + dy, z1 + dz
        # transform_text += f"""\
        # **
        # *transform, nset={refnode}, type=C
        #  {x1:.3f}, {y1:.3f}, {z1:.3f}, {x2:.3f}, {y2:.3f}, {z2:.3f}
        # **
        # """
        #     return transform_text

    def cluster_elements_by_shared_nodes(
        self: MesherCoreProtocol,
        name: Optional[str | list[str]] = None,
        invalid_node: int | None = 0,
    ) -> tuple[NDArray[np.int64], dict[int, NDArray[np.int64]]]:
        """節点共有による要素クラスタリング（連結成分分解）.

        elements の各行:
            [elem_label, node1, node2, node3, node4, ...]
        と解釈し、少なくとも1つの節点を共有する要素同士を
        同一クラスタとみなしてクラスタIDを振る。

        Args:
            name: Elset名(strでもlist[str]でも可)
            invalid_node: 無効節点値（パディング用など）。
                例: 4角形用の配列を3角形でも使っていて、余りを0や-1で埋めている場合に
                その値を指定する。None の場合はすべて有効節点として扱う。

        Returns:
            cluster_ids:
                shape (n_elems,) の配列。各行(要素)に対応するクラスタID (0,1,2,...)。
            clusters:
                dict[cluster_id, elem_labels] という辞書。
                各クラスタIDに属する要素「ラベル」の配列を返す。

        """
        elements = self.get_element_array(name=name)
        n_elems = elements.shape[0]
        if n_elems == 0:
            return np.array([], dtype=np.int64), {}

        elem_labels = elements[:, 0]
        node_cols = elements[:, 1:]

        # ----------------------------
        # 節点 → その節点を持つ要素インデックス一覧 の辞書を作成
        # ----------------------------
        node_to_elems: dict[int, list[int]] = {}

        for ei in range(n_elems):
            for node in node_cols[ei]:
                # 無効節点はスキップ
                if invalid_node is not None and node == invalid_node:
                    continue
                node_to_elems.setdefault(int(node), []).append(ei)

        # ----------------------------
        # BFS で連結成分（クラスタ）を抽出
        # ----------------------------
        cluster_ids = np.full(n_elems, -1, dtype=np.int64)
        current_cluster = 0

        for start in range(n_elems):
            # すでにクラスタ割り当て済みならスキップ
            if cluster_ids[start] != -1:
                continue

            # 新しいクラスタ開始
            queue: deque[int] = deque([start])
            cluster_ids[start] = current_cluster

            while queue:
                ei = queue.popleft()

                # この要素が持つ節点から隣接要素をたどる
                for node in node_cols[ei]:
                    if invalid_node is not None and node == invalid_node:
                        continue

                    neighbors = node_to_elems.get(int(node), [])
                    for nj in neighbors:
                        if cluster_ids[nj] == -1:
                            cluster_ids[nj] = current_cluster
                            queue.append(nj)

            current_cluster += 1

        # ----------------------------
        # クラスタID → 要素ラベル配列 の辞書を作成
        # ----------------------------
        clusters: dict[int, NDArray[np.int64]] = {}
        for cid in range(current_cluster):
            indices = np.where(cluster_ids == cid)[0]
            clusters[cid] = elem_labels[indices]

        return cluster_ids, clusters

    def extrude_between_topology_matched_shell_clusters(
        self: MesherCoreProtocol,
        element_labels1: list[int],
        element_labels2: list[int],
        target_elset_name: str,
        n_div: int,
        node_tol: float = 1.0,
        invalid_node: int = 0,
    ):
        elem_arr1 = self.get_element_array_with_labels(
            labels=element_labels1, allow_polymorphism=True, invalid_node=invalid_node
        )
        elem_arr2 = self.get_element_array_with_labels(
            labels=element_labels2, allow_polymorphism=True, invalid_node=invalid_node
        )
        # print(elem_arr1.shape, elem_arr2.shape)
        node_arr1 = self.get_node_coord_array_with_element_labels(
            labels=element_labels1
        )
        node_arr2 = self.get_node_coord_array_with_element_labels(
            labels=element_labels2
        )
        # print(elem_arr1)
        # print(node_arr1)
        # print(node_arr1.shape, node_arr2.shape)
        elems_arr2_matched, _ = utils.match_shell_clusters_by_geometory(
            elems_bottom=elem_arr1,
            nodes_bottom=node_arr1,
            elems_top=elem_arr2,
            nodes_top=node_arr2,
            node_tol=node_tol,
        )

        start_label = self.get_max_labels(increment=1)
        # print(start_node_label, start_elem_label)

        new_nodes, solid_elems = utils.extrude_between_topology_matched_shell_clusters(
            elems_bottom=elem_arr1,
            nodes_bottom=node_arr1,
            elems_top=elems_arr2_matched,
            nodes_top=node_arr2,
            n_div=n_div,
            start_elem_label=start_label.elem,
            start_node_label=start_label.node,
        )

        prism_arr, hex_arr = utils.split_prism_and_hex(solid_elems, invalid_node=0)

        # print(new_nodes)
        self.add_nodes(name="global", arr=new_nodes)
        if prism_arr is not None:
            self.add_elements(
                name=target_elset_name, arr=prism_arr, type=ElementType.C3D6.name
            )
        if hex_arr is not None:
            self.add_elements(
                name=target_elset_name, arr=hex_arr, type=ElementType.C3D8R.name
            )

    def create_intermediate_shell_between_topology_matched_shell_clusters(
        self: MesherCoreProtocol,
        element_labels1: list[int],
        element_labels2: list[int],
        target_elset_name: str,
        target_element_type: Optional[dict[int, str]] = None,
        node_tol: float = 1.0,
        invalid_node: int = 0,
        n: int = 1,
    ):
        if target_element_type is None:
            target_element_type = {4: ElementType.S4.name, 3: ElementType.S3R.name}
        elem_arr1 = self.get_element_array_with_labels(
            labels=element_labels1, allow_polymorphism=True, invalid_node=invalid_node
        )
        elem_arr2 = self.get_element_array_with_labels(
            labels=element_labels2, allow_polymorphism=True, invalid_node=invalid_node
        )
        node_arr1 = self.get_node_coord_array_with_element_labels(
            labels=element_labels1
        )
        node_arr2 = self.get_node_coord_array_with_element_labels(
            labels=element_labels2
        )
        elems_arr2_matched, bottom_to_top_nodes = (
            utils.match_shell_clusters_by_geometory(
                elems_bottom=elem_arr1,
                nodes_bottom=node_arr1,
                elems_top=elem_arr2,
                nodes_top=node_arr2,
                node_tol=node_tol,
            )
        )

        matched_node_labels2 = [bottom_to_top_nodes[i] for i in node_arr1["label"]]
        matched_node_arr2 = self.get_node_coord_array_with_labels(matched_node_labels2)
        for i in range(n):
            start_label = self.get_max_labels(increment=1)
            scale = (i + 1) / n
            # print(scale)
            new_node_arr = np.array(
                [
                    np.arange(
                        start_label.node, start_label.node + matched_node_arr2.shape[0]
                    ),
                    node_arr1["x"] + (matched_node_arr2["x"] - node_arr1["x"]) * scale,
                    node_arr1["y"] + (matched_node_arr2["y"] - node_arr1["y"]) * scale,
                    node_arr1["z"] + (matched_node_arr2["z"] - node_arr1["z"]) * scale,
                ]
            ).T
            self.add_nodes(name="global", arr=new_node_arr)

            node_labels1_to_new_node_labels = {
                i: j for i, j in zip(node_arr1["label"], new_node_arr[:, 0])
            }
            new_elem_labels = np.arange(
                start_label.elem, start_label.elem + elem_arr2.shape[0]
            ).reshape(-1, 1)
            new_elem_node_arr = np.vectorize(
                lambda x: node_labels1_to_new_node_labels.get(x, None)
            )(elem_arr1[:, 1:])
            new_elem_arr = np.hstack([new_elem_labels, new_elem_node_arr])

            tri_indices = np.isnan(new_elem_arr[:, 1:]).any(axis=1)
            if np.any(tri_indices):
                new_quads_elem = new_elem_arr[~tri_indices]
                new_tri_elem = new_elem_arr[tri_indices][:, :-1]
            else:
                if new_elem_arr[:, 1:].shape[1] == 3:
                    new_tri_elem = new_elem_arr
                    new_quads_elem = None
                else:
                    new_quads_elem = new_elem_arr
                    new_tri_elem = None

            if new_tri_elem is not None:
                self.add_elements(
                    name=target_elset_name,
                    arr=new_tri_elem,
                    type=target_element_type[3],
                )

            if new_quads_elem is not None:
                self.add_elements(
                    name=target_elset_name,
                    arr=new_quads_elem,
                    type=target_element_type[4],
                )

    def experimental_mirror_element_xy(
        self: MesherCoreProtocol, name: Optional[str | list[str]] = None
    ):
        if isinstance(name, str):
            name = [name]

        for elements in self.elements_data.values():

            if elements.options["elset"] not in name:
                continue

            node_label_array = elements.data[:, 1:]
            if node_label_array.shape[1] == 8:
                indices = [0, 3, 2, 1, 4, 7, 6, 5]
                new_node_label_array = node_label_array[:, indices]
            elif node_label_array.shape[1] == 6 and False:
                indices = [1, 0, 2, 4, 3, 5]
                new_node_label_array = node_label_array[:, indices]
            else:
                raise ValueError()
            elements.data[:, 1:] = new_node_label_array

    def get_element_volume(
        self: MesherCoreProtocol,
        name: Optional[str | list[str]] = None,
        mode: Literal["elements", "elset"] = "elements",
    ) -> float:

        if mode == "elements":
            element_node_coord_array = self.get_element_node_coord_array(name=name)
            if element_node_coord_array is None:
                return 0.0
            element_node_coord_array_list = [element_node_coord_array]
        elif mode == "elset":
            element_node_coord_array_dict = self.get_node_coord_array_dict_with_elset(
                name=name
            )
            if all([i.size == 0 for i in element_node_coord_array_dict.values()]):
                return 0.0
            element_node_coord_array_list = list(element_node_coord_array_dict.values())

        volume = 0.0

        for i in element_node_coord_array_list:
            if i.size == 0:
                continue

            volume_i = np.sum(
                get_element_quality(element_node_coord_array=i, mode="volume")["volume"]
            )
            volume += volume_i

        return volume

    def get_element_area(
        self: MesherCoreProtocol,
        name: Optional[str | list[str]] = None,
        mode: Literal["elements", "elset"] = "elements",
    ) -> float:
        """
        三角形・四角形要素の合計面積を返す関数。

        Args:
            name (str | list[str] | None): 要素セット名または要素ラベルのリスト
            mode (Literal["elements", "elset"]): name が要素IDか elset 名かを指定

        Returns:
            float: 総面積
        """
        if mode == "elements":
            element_node_coord_array = self.get_element_node_coord_array(name=name)
            if element_node_coord_array is None:
                return 0.0
            element_node_coord_array_list = [element_node_coord_array]
        elif mode == "elset":
            element_node_coord_array_dict = self.get_node_coord_array_dict_with_elset(
                name=name
            )
            if all([i.size == 0 for i in element_node_coord_array_dict.values()]):
                return 0.0
            element_node_coord_array_list = list(element_node_coord_array_dict.values())
        else:
            raise ValueError(f"不正なmode指定: {mode}")

        area = 0.0

        for i in element_node_coord_array_list:
            if i.size == 0:
                continue
            area_i = np.sum(
                get_element_quality(element_node_coord_array=i, mode="area")["area"]
            )
            area += area_i

        return area

    def drop_collapsed_elements(
        self: MesherCoreProtocol,
        name: Optional[str | list[str]] = None,
        cutoff: dict[str, float | None] = dict(volume=None, detJ=None),
    ) -> list[int] | None:
        if "detJ" not in cutoff.keys() or cutoff["detJ"] is None:
            cutoff["detJ"] = 0.0
        if "volume" not in cutoff.keys() or cutoff["volume"] is None:
            cutoff["detJ"] = 0.0

        element_node_coord_array = self.get_element_node_coord_array(name=name)
        if element_node_coord_array is None:
            raise ValueError(f"elset({name})が不正")

        quality = get_element_quality(
            element_node_coord_array=element_node_coord_array, mode=["volume", "detJ"]
        )
        element_array = self.get_element_array(name=name)
        if element_array is None:
            raise ValueError(f"elset({name})が不正")

        zero_volume_element_labels = element_array[:, 0][
            (quality["volume"] < cutoff["volume"]) | (quality["detJ"] < cutoff["detJ"])
        ].tolist()
        self.drop_elements_with_labels(labels=zero_volume_element_labels)
        self.drop_unreferenced_nodes()

        return zero_volume_element_labels

    def reverse_elements_nodes_indices(
        self: MesherCoreProtocol, name: Optional[str | list[str]] = None
    ):
        if name is not None and not isinstance(name, list):
            name = [name]
        for elements in self.elements_data.values():
            if name is not None and elements.options["elset"] not in name:
                continue
            elements.data[:, 1:] = elements.data[:, 1:][:, ::-1]

    def scale_coord(
        self: MesherCoreProtocol, scale: tuple[float, float, float] = (1, 1, 1)
    ):
        for nodes in self.nodes_data.get_parents_list():
            nodes.data["x"] *= scale[0]
            nodes.data["y"] *= scale[1]
            nodes.data["z"] *= scale[2]

    def mirror_node_coord(
        self: MesherCoreProtocol, plane: Literal["xy", "yz", "zx"], hexa: bool = True
    ):
        if not hexa:
            raise NotImplementedError(f"Mirrors not Hexa meshes is not implemented")

        warnings.warn(
            "This feature is extremely experimental, something wrong must happen..."
        )

        match plane:
            case "xy":
                self.scale_coord(scale=(1, 1, -1))
                new_indices = [4, 5, 6, 7, 0, 1, 2, 3]
            case "yz":
                self.scale_coord(scale=(-1, 1, 1))
                new_indices = [3, 2, 1, 0, 7, 6, 5, 4]
            case "zx":
                self.scale_coord(scale=(1, -1, 1))
                new_indices = [1, 0, 3, 2, 5, 4, 7, 6]
            case _:
                raise ValueError(f"Plane must be one of xy, yz, zx")

        for elements in self.elements_data.values():
            elements.data[:, 1:] = elements.data[:, 1:][:, new_indices]
