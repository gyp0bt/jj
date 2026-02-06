from collections import defaultdict
from enum import Enum
from typing import Tuple, Optional


class ElementTypeGroup(Enum):
    solid = 1
    shell = 2
    beam = 3
    truss = 4
    rigid_body = 5
    connector = 6


class ElementType(Enum):
    """要素タイプライブラリ
    (Tuple[int, ElementTypeGroup, int]): (要素タイプid, 要素分類, 節点数)
    """

    C3D4 = (1, ElementTypeGroup.solid, 4)
    C3D4T = (2, ElementTypeGroup.solid, 4)
    C3D5 = (3, ElementTypeGroup.solid, 5)
    C3D5T = (4, ElementTypeGroup.solid, 5)
    C3D8 = (5, ElementTypeGroup.solid, 8)
    C3D8T = (6, ElementTypeGroup.solid, 8)
    C3D8R = (7, ElementTypeGroup.solid, 8)
    C3D8RT = (8, ElementTypeGroup.solid, 8)
    DC3D8 = (9, ElementTypeGroup.solid, 8)
    DC3D6 = (10, ElementTypeGroup.solid, 6)
    C3D6 = (11, ElementTypeGroup.solid, 6)
    C3D10 = (12, ElementTypeGroup.solid, 10)
    C3D15 = (13, ElementTypeGroup.solid, 15)
    C3D8I = (14, ElementTypeGroup.solid, 8)

    B31 = (101, ElementTypeGroup.beam, 2)
    T3D2 = (102, ElementTypeGroup.truss, 2)
    CONN3D2 = (103, ElementTypeGroup.connector, 2)

    S3 = (201, ElementTypeGroup.shell, 3)
    S3R = (202, ElementTypeGroup.shell, 3)
    CPE3 = (203, ElementTypeGroup.shell, 3)
    CPE3R = (204, ElementTypeGroup.shell, 3)
    S4 = (205, ElementTypeGroup.shell, 4)
    S4R = (206, ElementTypeGroup.shell, 4)
    CPE4 = (207, ElementTypeGroup.shell, 4)
    CPE4R = (208, ElementTypeGroup.shell, 4)
    DS4 = (209, ElementTypeGroup.shell, 4)
    SC8R = (210, ElementTypeGroup.shell, 8)
    SC6R = (211, ElementTypeGroup.shell, 6)
    CPE6 = (212, ElementTypeGroup.shell, 6)

    CAX4 = (301, ElementTypeGroup.shell, 4)
    CAX4R = (302, ElementTypeGroup.shell, 4)
    CAX3 = (303, ElementTypeGroup.shell, 3)

    R3D3 = (401, ElementTypeGroup.rigid_body, 3)
    R3D4 = (402, ElementTypeGroup.rigid_body, 3)
    R2D2 = (403, ElementTypeGroup.rigid_body, 2)


solid_element_type_list = [
    i.name for i in ElementType if i.value[1] == ElementTypeGroup.solid
]
shell_element_type_list = [
    i.name for i in ElementType if i.value[1] == ElementTypeGroup.shell
]
beam_element_type_list = [
    i.name for i in ElementType if i.value[1] == ElementTypeGroup.beam
]
truss_element_type_list = [
    i.name for i in ElementType if i.value[1] == ElementTypeGroup.truss
]
connector_element_type_list = [
    i.name for i in ElementType if i.value[1] == ElementTypeGroup.connector
]

element_type_dict = {i.name: i.value for i in ElementType}

num_nodes_element_type_dict = defaultdict(list)
element_type_num_nodes_dict = dict()
for i in ElementType:
    num_nodes_element_type_dict[i.value[2]].append(i)
    element_type_num_nodes_dict[i.name] = i.value[2]
    element_type_num_nodes_dict[i.name.lower()] = i.value[2]


def get_element_type_info(
    type_name: str,
) -> Optional[Tuple[int, ElementTypeGroup, int]]:
    """要素タイプ名から (id, group, num_nodes) を取得する.

    大文字/小文字どちらでもOKにする。

    Args:
        type_name: "C3D8", "c3d8", "CPE4R" など

    Returns:
        (id, group, num_nodes) or None (未知タイプ)
    """
    if not type_name:
        return None

    key = type_name.upper()
    return element_type_dict.get(key)


def get_element_group(type_name: str) -> Optional[ElementTypeGroup]:
    """要素タイプ名から ElementTypeGroup を取得する."""
    info = get_element_type_info(type_name)
    if info is None:
        return None
    _, group, _ = info
    return group


def get_element_num_nodes(type_name: str) -> Optional[int]:
    """要素タイプ名から節点数を取得する."""
    info = get_element_type_info(type_name)
    if info is None:
        return None
    return info[2]
