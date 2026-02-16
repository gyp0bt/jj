"""
押し出しメッシュを作成する
"""

from typing import (
    Literal,
)

import numpy as np
from numpy import ndarray as NDArray
from plotly import graph_objects as go

from ..etypes import (
    ElementType,
    beam_element_type_list,
    element_type_dict,
    shell_element_type_list,
)
from ..mesh.mesh import Mesher
from ..mesh.parent import Elements, Nodes
from ..typing import (
    name_to_name_list,
)


def get_n_from_points_and_mesh_size(p1: list[float], p2: list[float], mesh_size: float) -> int:
    """
    2点間の距離っを計算し、メッシュサイズ分の分割数を返す
    Args:
        p1: 1点目
        p2: 2点目
        mesh_size: メッシュサイズ
    Returns:
        int: 分割数
    """
    d = np.linalg.norm(np.array(p1) - np.array(p2))
    if d < mesh_size:
        return 2
    return int(d / mesh_size) + 1


def get_n_from_angle_radius_mesh_size(angle: float, r: float, mesh_size: float) -> int:
    """
    回転押し出し用のメッシュサイズ分の分割数を返す
    Args:
        angle: 回転押し出しの角度(radian)
        r: 押し出し半径
        mesh_size: メッシュサイズ
    Returns:
        int: 分割数
    """
    arc_length = r * angle
    if arc_length < mesh_size:
        return 1
    return int(arc_length / mesh_size) + 1


def get_n_from_vector_array_mesh_size(vector_array: NDArray, mesh_size: float) -> int:
    """
    arrayのベクトルの長さの平均を計算し、メッシュサイズ分の分割数を返す
    Args:
        vector_array: ベクトルの集合
        mesh_size: メッシュサイズ
    Returns:
        int: 分割数
    """
    avg_length = np.linalg.norm(vector_array, axis=1).mean()
    if avg_length < mesh_size:
        return 2
    return int(avg_length / mesh_size) + 1


def get_line(p1: list[float], p2: list[float], n: int = 10) -> NDArray:
    """
    点間の直線を返す
    Args:
        p1: start point
        p2: end point
        n: number of points
    Returns:
        NDArray[np.float64]: line
    """
    line = np.array(
        [
            np.linspace(p1[0], p2[0], n),
            np.linspace(p1[1], p2[1], n),
        ]
    ).T
    return line


def get_line_with_fillet(
    angle: float,
    r: float,
    mesh_size: float,
    xlim: float,
    shift: NDArray = np.array([0, 0]),
) -> list[NDArray]:
    """
    x軸に対してangleの角度でrの円弧を描き、直線と滑らかにつなげる
    Args:
        angle: 角度(radian)
        r: 半径
        mesh_size: メッシュサイズ
        xlim: x軸の範囲
        shift: シフト量
    Returns:
        list[NDArray[np.float64]]: line
    """
    a0 = angle / 2

    cx = r / np.tan(a0)
    ip1 = [cx * np.cos(angle), cx * np.sin(angle)]
    ip2 = [cx, 0]

    p1 = [-xlim, -xlim * np.tan(angle)]
    p2 = [xlim, 0.0]

    line0 = get_line(p1, ip1, get_n_from_points_and_mesh_size(p1, ip1, mesh_size))
    # line0 = get_line(p1, [0,0], n)

    x, y = [], []
    # r + r sin(theta) = cx * sin(angle)
    # theta = arcsin(cx*sin(angle)/r-1)
    if angle > np.pi / 2:
        a1 = np.pi - np.arcsin(cx * np.sin(angle) / r - 1)
    else:
        a1 = np.arcsin(cx * np.sin(angle) / r - 1)
    dtheta = 2 * np.pi * 3 / 4 - a1
    ni = get_n_from_angle_radius_mesh_size(dtheta, r, mesh_size)
    for i in range(ni):
        theta_i = dtheta * i / (ni - 1) + a1
        x.append(r * np.cos(theta_i) + cx)
        y.append(r * np.sin(theta_i) + r)
    line1 = np.array([x, y]).T

    line2 = get_line(ip2, p2, get_n_from_points_and_mesh_size(ip2, p2, mesh_size))
    # line2 = get_line([0,0], p2, n)

    line0 += shift
    line1 += shift
    line2 += shift

    if 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=line0[:, 0], y=line0[:, 1], mode="lines"))
        fig.add_trace(go.Scatter(x=line1[:, 0], y=line1[:, 1], mode="lines"))
        fig.add_trace(go.Scatter(x=line2[:, 0], y=line2[:, 1], mode="lines"))
        fig.show()

    return [line0, line1, line2]


def get_element_type_list(mesh: Mesher, elset_name: str | list[str] | None, mode: Literal["2d", "3d"]) -> list[str]:
    element_type_list = set()
    elset_name_list = name_to_name_list(elset_name)
    for elset_name in elset_name_list:
        for elements in mesh.elements_data.get_parents_list(elset_name):
            elements: Elements
            if mode == "3d":
                if elements.type.upper() not in shell_element_type_list:
                    raise ValueError(
                        f"Type of base elements must be one of {shell_element_type_list}, not {elements.type}"
                    )
            elif mode == "2d" and elements.type.upper() not in beam_element_type_list:
                raise ValueError(f"Type of base elements must be one of {beam_element_type_list}, not {elements.type}")
            element_type_list.add(elements.type)

    element_type_list = list(element_type_list)
    return element_type_list


def get_target_type(element_type_list: list[str], mode: Literal["2d", "3d"]) -> str:
    target_element_type_list = set()
    for element_type in element_type_list:
        number_of_node = element_type_dict[element_type.upper()][2]
        if mode == "3d":
            if number_of_node == 3:
                target_element_type_i = ElementType.C3D6.name
            elif number_of_node == 4:
                target_element_type_i = ElementType.C3D8.name
            else:
                raise RuntimeError(
                    f"Element type must be type which contains 3 or 4 nodes. Not {element_type, element_type_dict[element_type.bigger()[2]]}"
                )
        elif mode == "2d":
            if number_of_node == 2:
                target_element_type_i = ElementType.S4.name
            else:
                raise RuntimeError(
                    f"Element type must be type which contains 2 nodes. Not {element_type, element_type_dict[element_type.bigger()[2]]}"
                )

        target_element_type_list.add(target_element_type_i)
    target_element_type_list = list(target_element_type_list)

    if len(target_element_type_list) > 1:
        raise ValueError(f"Target element types must be same through all elements, not {target_element_type_list}")
    return target_element_type_list[0]


def prepair_target_element(mesh: Mesher, target_elset_name: str, target_element_type: str) -> tuple[str, str]:
    target_elset_key = mesh.get_elset_key_from_elset_and_type(elset=target_elset_name, type=target_element_type)
    if not mesh.elements_data.isin(target_elset_key):
        mesh.elements_data[target_elset_key] = Elements(
            data=np.array([]),
            options=dict(elset=target_elset_name, type=target_element_type),
        )

    return target_elset_key, target_elset_name


def prepair_target_node(mesh: Mesher, target_nset_name: str) -> str:
    if target_nset_name not in mesh.nodes_data:
        mesh.nodes_data[target_nset_name] = Nodes(data=np.array([]), options=dict(nset=target_nset_name))
    return target_nset_name


class ExtrudeLine:
    mode: Literal["2d", "3d"] = "2d"

    def __init__(
        self,
        mesh: Mesher,
        base_elset_name: str | list[str] | None,
        target_elset_name: str,
        target_nset_name: str = "global",
        return_frontier: bool = False,
        node_array_order: list[int] | None = None,
    ):
        elset_name_list = name_to_name_list(base_elset_name)
        element_type_list = get_element_type_list(mesh, base_elset_name, mode=self.mode)
        target_element_type = get_target_type(element_type_list, mode=self.mode)

        target_elset_key, target_elset_name = prepair_target_element(mesh, target_elset_name, target_element_type)
        target_nset_name = prepair_target_node(mesh, target_nset_name)
        self.return_frontier = return_frontier
        self.mesh = mesh
        self.target_elset_key = target_elset_key
        self.target_elset_name = target_elset_name
        self.target_element_type = target_element_type
        self.elset_name_list = elset_name_list
        self.target_nset_name = target_nset_name

        max_labels = mesh.get_max_labels()
        max_node_label = max_labels.node
        max_elem_label = max_labels.elem
        init_node_label, init_elem_label = max_node_label + 1, max_elem_label + 1

        base_node_coord_array = self.mesh.get_node_coord_array_with_elements(name=self.elset_name_list)

        node_label_mapping = {
            org_label: init_node_label + i for i, org_label in enumerate(base_node_coord_array["label"])
        }
        self.mesh.update_node_label_with_dict(node_label_mapping=node_label_mapping)

        base_elements_array = self.mesh.get_element_array(name=self.elset_name_list)

        base_elements_array[:, 0] = init_elem_label + np.arange(base_elements_array.shape[0]) + 1
        base_node_coord_array = self.mesh.get_node_coord_array_with_elements(name=self.elset_name_list)

        if node_array_order is not None:
            node_array_order = [node_label_mapping.get(i, 0) for i in node_array_order]
            if 0 in node_array_order:
                raise ValueError("何かおかしい")
            indices = [np.where(base_node_coord_array["label"] == i)[0].item() for i in node_array_order]
            base_node_coord_array = base_node_coord_array[indices]

        self.init_node_label = init_node_label
        self.init_elem_label = init_elem_label
        self.base_node_coord_array = base_node_coord_array
        self.base_elements_array = base_elements_array

    def get_node_coord_array_i(
        self,
        i: int,
        dx: float | NDArray | None = None,
        dy: float | NDArray | None = None,
        dz: float | NDArray | None = None,
    ) -> NDArray:
        node_coord_array_i = self.base_node_coord_array.copy()
        node_coord_array_i["label"] += self.base_node_coord_array.shape[0] * i

        dx = dx if dx is not None else 0.0
        dy = dy if dy is not None else 0.0
        dz = dz if dz is not None else 0.0

        node_coord_array_i["x"] = self.base_node_coord_array["x"] + dx
        node_coord_array_i["y"] = self.base_node_coord_array["y"] + dy
        node_coord_array_i["z"] = self.base_node_coord_array["z"] + dz

        self.mesh.add_nodes(self.target_nset_name, arr=node_coord_array_i)

        return node_coord_array_i

    def get_element_coord_array_i(self, i: int) -> NDArray:
        element_array_i = self.base_elements_array.copy()
        element_array_i[:, 0] += self.init_elem_label + element_array_i[:, 0].shape[0] * (i - 1)
        element_array_i[:, 1:] += self.base_node_coord_array.shape[0] * (i - 1)
        target_node_label_array_i = element_array_i[:, 1:] + self.base_node_coord_array.shape[0]
        element_array_i = np.hstack((element_array_i, target_node_label_array_i))
        element_array_i[:, [-2, -1]] = element_array_i[:, [-1, -2]]
        element_array_i[:, [1, 2, 3, 4]] = element_array_i[:, [4, 3, 2, 1]]

        self.mesh.add_elements(
            name=self.target_elset_name,
            arr=element_array_i,
            type=self.target_element_type,
        )

        return element_array_i

    def extrude(
        self,
        n: int,
        vector_array: NDArray,
    ):

        [self.base_node_coord_array] + [
            self.get_node_coord_array_i(
                i=i + 1,
                dx=vector_array[i, :, 0],
                dy=vector_array[i, :, 1],
                dz=vector_array[i, :, 2],
            )
            for i in range(n + 1)
        ]

        [self.get_element_coord_array_i(i=i + 1) for i in range(n + 1)]

    def extrude_until_position(
        self,
        n: int,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
        drop_base_element: bool = True,
    ):
        vector_array = np.zeros((self.base_node_coord_array.shape[0], 3))
        if x is not None:
            vector_array[:, 0] = x - self.base_node_coord_array["x"]
        if y is not None:
            vector_array[:, 1] = y - self.base_node_coord_array["y"]
        if z is not None:
            vector_array[:, 2] = z - self.base_node_coord_array["z"]
        self.extrude_with_vector_array(n=n, vector_array=vector_array, drop_base_element=drop_base_element)

    def extrude_with_vector_array(
        self,
        n: int,
        vector_array: NDArray,
        drop_base_element: bool = True,
    ):
        vector_array = vector_array[np.newaxis, :, :]
        scalars_expanded = np.linspace(0.0, 1.0, n + 2)[:, np.newaxis, np.newaxis][1:, :, :]
        vector_array = vector_array * scalars_expanded

        self.extrude(n=n, vector_array=vector_array)

        if drop_base_element:
            for i in self.elset_name_list:
                self.mesh.elements_data.drop_names(i)


class ExtrudeSurface(ExtrudeLine):
    mode = "3d"

    def get_element_coord_array_i(self, i: int) -> NDArray:
        element_array_i = self.base_elements_array.copy()
        element_array_i[:, 0] += self.init_elem_label + element_array_i[:, 0].shape[0] * (i - 1)
        element_array_i[:, 1:] += self.base_node_coord_array.shape[0] * (i - 1)
        target_node_label_array_i = element_array_i[:, 1:] + self.base_node_coord_array.shape[0]
        element_array_i = np.hstack((element_array_i, target_node_label_array_i))

        self.mesh.add_elements(
            name=self.target_elset_name,
            arr=element_array_i,
            type=self.target_element_type,
        )

        return element_array_i


def create_requtangular(
    mesh: Mesher,
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    p3: tuple[float, float, float],
    p4: tuple[float, float, float],
    n: tuple[int, int],
    target_elset_name: str,
    target_nset_name: str = "global",
) -> Mesher:
    p1_arr = np.array(p1)
    p2_arr = np.array(p2)
    p3_arr = np.array(p3)
    p4_arr = np.array(p4)

    points1 = np.array([(p2_arr - p1_arr) / n[0] * i + p1_arr for i in range(n[0] + 1)])
    points2 = np.array([(p4_arr - p3_arr) / n[0] * i + p3_arr for i in range(n[0] + 1)])

    vector_array = points2 - points1

    max_labels = mesh.get_max_labels()
    init_node_label = max_labels.node
    init_elem_label = max_labels.elem

    node_labels = np.array([[i + 1 + init_node_label for i in range(n[0] + 1)]]).T
    node_data = np.concatenate((node_labels, points1), axis=1)

    mesh.add_nodes(name=target_nset_name, arr=node_data)

    elem_data = [[i + 1 + init_elem_label, node_data[i][0], node_data[i + 1][0]] for i in range(len(node_data) - 1)]

    mesh.add_elements(name="__ptmp", arr=np.array(elem_data), type=ElementType.B31.name)

    ExtrudeLine(
        mesh=mesh,
        base_elset_name="__ptmp",
        target_elset_name=target_elset_name,
        target_nset_name=target_nset_name,
        node_array_order=node_labels.flatten().tolist(),
    ).extrude_with_vector_array(n=n[1], vector_array=vector_array, drop_base_element=True)

    return mesh


def __create_quater_circle1(
    mesh: Mesher,
    r: float,
    n: tuple[int, int, int],
    target_elset_name: str,
    target_nset_name: str = "global",
) -> Mesher:
    p0 = (0.0, 0.0, 0.0)
    p1 = (r * 0.5, 0.0, 0.0)
    p2 = (0.0, r * 0.5, 0.0)
    p3 = (r * 0.6, r * 0.6, 0.0)
    p4 = (r, 0.0, 0.0)
    p5 = (0.0, r, 0.0)
    p6 = (r, r, 0.0)

    create_requtangular(
        mesh=mesh,
        p1=p0,
        p2=p2,
        p3=p1,
        p4=p3,
        n=(n[0], n[1]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    create_requtangular(
        mesh=mesh,
        p1=p2,
        p2=p5,
        p3=p3,
        p4=p6,
        n=(n[2], n[1]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    create_requtangular(
        mesh=mesh,
        p1=p1,
        p2=p3,
        p3=p4,
        p4=p6,
        n=(n[0], n[2]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    mesh.square_to_circle(l=r, r=r, plane="xy", name="__ptmp")

    mesh.add_nodes(name=target_nset_name, arr=mesh.nodes_data["__ptmp"].data)
    mesh.nodes_data.drop("__ptmp")

    return mesh


def __create_quater_circle2(
    mesh: Mesher,
    r: float,
    n: tuple[int, int, int],
    target_elset_name: str,
    target_nset_name: str = "global",
) -> Mesher:
    p0 = (0.0, 0.0, 0.0)
    p1 = (r, 0.0, 0.0)
    p2 = (r * np.cos(np.pi / 4.0), r * np.sin(np.pi / 4.0), 0.0)
    p3 = (0.0, r, 0.0)

    create_requtangular(
        mesh=mesh,
        p1=p0,
        p2=p3,
        p3=p1,
        p4=p2,
        n=(n[0], n[1]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    node_coord_array = mesh.get_node_coord_array(name="__ptmp")

    theta_array = np.arctan2(node_coord_array["y"], node_coord_array["x"])
    org_theta_array = theta_array.copy()
    theta_array[theta_array > np.pi / 4.0] = np.pi / 2.0 - theta_array[theta_array > np.pi / 4.0]
    radius_array = np.sqrt(node_coord_array["x"] ** 2 + node_coord_array["y"] ** 2)

    def get_scale_array():
        a = (p2[1] - p1[1]) / (p2[0] - p1[0])
        c = r
        _x_array = (-a * c) / (np.tan(theta_array) - a)
        _y_array = a * _x_array - a * c
        radius_array = np.sqrt(_x_array**2 + _y_array**2)
        return r / radius_array

    scale_array = get_scale_array()
    radius_array *= scale_array

    node_coord_array["x"] = radius_array * np.cos(org_theta_array)
    node_coord_array["y"] = radius_array * np.sin(org_theta_array)

    mesh.update_node_coord_with_array(node_coord_array)

    mesh.add_nodes(name=target_nset_name, arr=mesh.nodes_data["__ptmp"].data)
    mesh.nodes_data.drop("__ptmp")
    return mesh


def create_quater_circle(
    mesh: Mesher,
    r: float,
    n: tuple[int, int, int],
    target_elset_name: str,
    target_nset_name: str = "global",
) -> Mesher:
    p0 = (0.0, 0.0, 0.0)
    p1 = (r * 0.6, 0.0, 0.0)
    p2 = (0.0, r * 0.6, 0.0)
    p3 = (r * 0.5, r * 0.5, 0.0)
    p4 = (r, 0.0, 0.0)
    p5 = (0.0, r, 0.0)
    p6 = (r * np.cos(np.pi / 4.0), r * np.sin(np.pi / 4.0), 0.0)

    create_requtangular(
        mesh=mesh,
        p1=p0,
        p2=p2,
        p3=p1,
        p4=p3,
        n=(n[0], n[1]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )
    create_requtangular(
        mesh=mesh,
        p1=p2,
        p2=p5,
        p3=p3,
        p4=p6,
        n=(n[2], n[1]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    create_requtangular(
        mesh=mesh,
        p1=p1,
        p2=p3,
        p3=p4,
        p4=p6,
        n=(n[0], n[2]),
        target_elset_name=target_elset_name,
        target_nset_name="__ptmp",
    )

    mesh.drop_duplicated_nodes(tol=float(r / np.mean(n) * 0.01))

    node_coord_array = mesh.get_node_coord_array(name="__ptmp")

    theta_array = np.arctan2(node_coord_array["y"], node_coord_array["x"])
    org_theta_array = theta_array.copy()
    theta_array[theta_array > np.pi / 4.0] = np.pi / 2.0 - theta_array[theta_array > np.pi / 4.0]
    radius_array = np.sqrt(node_coord_array["x"] ** 2 + node_coord_array["y"] ** 2)

    def get_scale_array():
        a = (p4[1] - p6[1]) / (p4[0] - p6[0])
        c = r
        _x_array = (-a * c) / (np.tan(theta_array) - a)
        _y_array = a * _x_array - a * c
        radius_array = np.sqrt(_x_array**2 + _y_array**2)
        return r / radius_array

    scale_array = get_scale_array()
    radius_array *= scale_array

    node_coord_array["x"] = radius_array * np.cos(org_theta_array)
    node_coord_array["y"] = radius_array * np.sin(org_theta_array)

    indices = radius_array > r * 0.99
    indices |= node_coord_array["x"] < r / np.mean(n) * 0.1
    indices |= node_coord_array["y"] < r / np.mean(n) * 0.1

    xy = np.array([[i["x"], i["y"]] for i in node_coord_array])
    # xy = laplacian_smoothing(
    # points=xy, k=10, alpha=0.3, fixed_indices=indices, n_iter=1
    # )
    node_coord_array["x"] = xy[:, 0]
    node_coord_array["y"] = xy[:, 1]

    mesh.update_node_coord_with_array(node_coord_array)

    mesh.add_nodes(name=target_nset_name, arr=mesh.nodes_data["__ptmp"].data)
    mesh.nodes_data.drop("__ptmp")
    return mesh
