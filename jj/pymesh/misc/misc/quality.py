from typing import Literal, Dict, List, Any, Optional, Union
import numpy as np


def get_tetrahedron_volume_batch(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray
) -> np.ndarray:
    """
    複数の四面体の体積をバッチ計算する関数。

    Args:
        p1, p2, p3, p4: それぞれの頂点の座標 (複数の四面体の座標を含む np.ndarray)

    Returns:
        np.ndarray: 各四面体の体積の配列
    """
    return np.abs(np.einsum("ij,ij->i", np.cross(p2 - p1, p3 - p1), p4 - p1)) / 6.0


def get_pyramid_volume_batch(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray, apex: np.ndarray
) -> np.ndarray:
    """
    複数のピラミッド型要素の体積をバッチ計算する関数。

    Args:
        p1, p2, p3, p4: 底面の4つの頂点の座標（複数のピラミッドの座標を含む np.ndarray）
        apex: ピラミッドの頂点の座標（複数のピラミッドの座標を含む np.ndarray）

    Returns:
        np.ndarray: 各ピラミッドの体積の配列
    """
    # 底面を二つの三角形に分割してそれぞれ四面体として計算
    volume1 = np.abs(np.einsum("ij,ij->i", np.cross(p2 - p1, p3 - p1), apex - p1)) / 6.0
    volume2 = np.abs(np.einsum("ij,ij->i", np.cross(p4 - p1, p3 - p1), apex - p1)) / 6.0

    # 2つの四面体の体積を足してピラミッドの体積とする
    return volume1 + volume2


def get_prism_volume_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    複数の6節点三角柱要素の体積を一度に計算する関数。

    Args:
        element_node_coord_array: (n, 6, 3) の形をした要素集合の配列 (n は要素数、6 は各要素の頂点数)

    Returns:
        np.ndarray: 各要素の体積の配列
    """
    assert element_node_coord_array.shape[1:] == (
        6,
        3,
    ), "三角柱要素は6つの頂点と3次元座標で構成される必要があります"

    vol = np.zeros(element_node_coord_array.shape[0])
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 0],
        element_node_coord_array[:, 1],
        element_node_coord_array[:, 2],
        element_node_coord_array[:, 4],
    )
    vol += get_pyramid_volume_batch(
        element_node_coord_array[:, 0],
        element_node_coord_array[:, 2],
        element_node_coord_array[:, 3],
        element_node_coord_array[:, 5],
        element_node_coord_array[:, 4],
    )

    return vol


def get_hexahedron_volume_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    複数の8節点8面体要素の体積を一度に計算する関数。

    Args:
        element_node_coord_array: (n, 8, 3) の形をした要素集合の配列 (n は要素数、8 は各要素の頂点数)

    Returns:
        np.ndarray: 各要素の体積の配列
    """
    assert element_node_coord_array.shape[1:] == (
        8,
        3,
    ), "8面体要素は8つの頂点と3次元座標で構成される必要があります"

    vol = np.zeros(element_node_coord_array.shape[0])
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 0],
        element_node_coord_array[:, 1],
        element_node_coord_array[:, 3],
        element_node_coord_array[:, 4],
    )
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 1],
        element_node_coord_array[:, 2],
        element_node_coord_array[:, 3],
        element_node_coord_array[:, 5],
    )
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 4],
        element_node_coord_array[:, 5],
        element_node_coord_array[:, 6],
        element_node_coord_array[:, 3],
    )
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 5],
        element_node_coord_array[:, 7],
        element_node_coord_array[:, 6],
        element_node_coord_array[:, 3],
    )
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 1],
        element_node_coord_array[:, 5],
        element_node_coord_array[:, 3],
        element_node_coord_array[:, 4],
    )
    vol += get_tetrahedron_volume_batch(
        element_node_coord_array[:, 4],
        element_node_coord_array[:, 5],
        element_node_coord_array[:, 6],
        element_node_coord_array[:, 3],
    )

    return vol


def get_volume_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    三角柱要素、四面体要素、または8面体要素の体積を計算する関数。

    Args:
        element_node_coord_array: (n, m, 3) の形をした要素集合の配列 (n は要素数、m は各要素の頂点数)

    Returns:
        np.ndarray: 各要素の体積の配列
    """
    if element_node_coord_array.shape[1] == 6:
        return get_prism_volume_batch(element_node_coord_array)
    elif element_node_coord_array.shape[1] == 4:
        return get_tetrahedron_volume_batch(
            element_node_coord_array[:, 0],
            element_node_coord_array[:, 1],
            element_node_coord_array[:, 2],
            element_node_coord_array[:, 3],
        )
    elif element_node_coord_array.shape[1] == 5:
        return get_pyramid_volume_batch(
            element_node_coord_array[:, 0],
            element_node_coord_array[:, 1],
            element_node_coord_array[:, 2],
            element_node_coord_array[:, 3],
            element_node_coord_array[:, 4],
        )
    elif element_node_coord_array.shape[1] == 8:
        return get_hexahedron_volume_batch(element_node_coord_array)
    else:
        raise ValueError(
            "サポートされていない要素形式です。四面体 (4頂点)、三角柱 (6頂点) または8面体 (8頂点) が必要です。"
        )


def get_tetrahedron_detJ_batch(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray
) -> np.ndarray:
    """
    複数の四面体要素のdetJ（ヤコビ行列の行列式）をバッチ計算する関数。

    Args:
        p1, p2, p3, p4: 四面体の各頂点の座標 (複数の四面体の座標を含む np.ndarray)

    Returns:
        np.ndarray: 各四面体の detJ の配列
    """
    jacobian = np.stack([p2 - p1, p3 - p1, p4 - p1], axis=-1)
    return np.linalg.det(jacobian)


def get_prism_detJ_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    複数の6節点三角柱要素のdetJをバッチ計算する関数。

    Args:
        element_node_coord_array: (n, 6, 3) の形をした配列

    Returns:
        np.ndarray: 各三角柱要素の detJ の配列
    """
    assert element_node_coord_array.shape[1:] == (
        6,
        3,
    ), "三角柱要素は6つの頂点と3次元座標で構成される必要があります"

    jacobians = np.zeros((element_node_coord_array.shape[0], 3, 3))

    for i in range(3):
        jacobians[:, :, i] = (
            element_node_coord_array[:, i + 3] - element_node_coord_array[:, i]
        )

    return np.linalg.det(jacobians)


def get_hexahedron_detJ_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    複数の8節点8面体要素のdetJをバッチ計算する関数。

    Args:
        element_node_coord_array: (n, 8, 3) の形をした配列

    Returns:
        np.ndarray: 各8面体要素の detJ の配列
    """
    assert element_node_coord_array.shape[1:] == (
        8,
        3,
    ), "8面体要素は8つの頂点と3次元座標で構成される必要があります"

    jacobians = np.zeros((element_node_coord_array.shape[0], 3, 3))

    jacobians[:, :, 0] = element_node_coord_array[:, 1] - element_node_coord_array[:, 0]
    jacobians[:, :, 1] = element_node_coord_array[:, 3] - element_node_coord_array[:, 0]
    jacobians[:, :, 2] = element_node_coord_array[:, 4] - element_node_coord_array[:, 0]

    return np.linalg.det(jacobians)


def get_detJ_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    四面体、三角柱、または8面体のdetJをバッチ計算する関数。

    Args:
        element_node_coord_array: (n, m, 3) の形をした配列

    Returns:
        np.ndarray: 各要素の detJ の配列
    """
    if element_node_coord_array.shape[1] == 4:
        return get_tetrahedron_detJ_batch(
            element_node_coord_array[:, 0],
            element_node_coord_array[:, 1],
            element_node_coord_array[:, 2],
            element_node_coord_array[:, 3],
        )
    elif element_node_coord_array.shape[1] == 6:
        return get_prism_detJ_batch(element_node_coord_array)
    elif element_node_coord_array.shape[1] == 8:
        return get_hexahedron_detJ_batch(element_node_coord_array)
    else:
        raise ValueError(
            "サポートされていない要素形式です。四面体 (4頂点)、三角柱 (6頂点) または8面体 (8頂点) が必要です。"
        )


def get_tetrahedron_aspect_ratio_batch(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray
) -> np.ndarray:
    """
    四面体要素のアスペクト比をバッチで計算する関数。

    Args:
        p1, p2, p3, p4: 四面体の各頂点の座標を含む np.ndarray

    Returns:
        np.ndarray: 各四面体要素のアスペクト比の配列
    """
    edges = np.array(
        [
            np.linalg.norm(p2 - p1, axis=1),
            np.linalg.norm(p3 - p1, axis=1),
            np.linalg.norm(p4 - p1, axis=1),
            np.linalg.norm(p3 - p2, axis=1),
            np.linalg.norm(p4 - p2, axis=1),
            np.linalg.norm(p4 - p3, axis=1),
        ]
    )
    L_max = np.max(edges, axis=0)
    L_min = np.min(edges, axis=0)

    return L_max / L_min


def get_prism_aspect_ratio_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    三角柱要素のアスペクト比をバッチで計算する関数。

    Args:
        element_node_coord_array: (n, 6, 3) の形の配列

    Returns:
        np.ndarray: 各三角柱要素のアスペクト比の配列
    """
    assert element_node_coord_array.shape[1:] == (
        6,
        3,
    ), "三角柱要素は6つの頂点と3次元座標で構成される必要があります"

    edges = [
        np.linalg.norm(
            element_node_coord_array[:, i] - element_node_coord_array[:, j], axis=1
        )
        for i in range(6)
        for j in range(i + 1, 6)
    ]
    edges = np.array(edges)

    L_max = np.max(edges, axis=0)
    L_min = np.min(edges, axis=0)

    return L_max / L_min


def get_hexahedron_aspect_ratio_batch(
    element_node_coord_array: np.ndarray,
) -> np.ndarray:
    """
    8節点8面体要素のアスペクト比をバッチで計算する関数。

    Args:
        element_node_coord_array: (n, 8, 3) の形の配列

    Returns:
        np.ndarray: 各8面体要素のアスペクト比の配列
    """
    assert element_node_coord_array.shape[1:] == (
        8,
        3,
    ), "8面体要素は8つの頂点と3次元座標で構成される必要があります"

    edges = [
        np.linalg.norm(
            element_node_coord_array[:, i] - element_node_coord_array[:, j], axis=1
        )
        for i in range(8)
        for j in range(i + 1, 8)
    ]
    edges = np.array(edges)

    L_max = np.max(edges, axis=0)
    L_min = np.min(edges, axis=0)

    return L_max / L_min


def get_aspect_ratio_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    四面体、三角柱、または8面体要素のアスペクト比をバッチ計算する関数。

    Args:
        element_node_coord_array: (n, m, 3) の形の配列

    Returns:
        np.ndarray: 各要素のアスペクト比の配列
    """
    if element_node_coord_array.shape[1] == 4:
        return get_tetrahedron_aspect_ratio_batch(
            element_node_coord_array[:, 0],
            element_node_coord_array[:, 1],
            element_node_coord_array[:, 2],
            element_node_coord_array[:, 3],
        )
    elif element_node_coord_array.shape[1] == 6:
        return get_prism_aspect_ratio_batch(element_node_coord_array)
    elif element_node_coord_array.shape[1] == 8:
        return get_hexahedron_aspect_ratio_batch(element_node_coord_array)
    else:
        raise ValueError(
            "サポートされていない要素形式です。四面体 (4頂点)、三角柱 (6頂点) または8面体 (8頂点) が必要です。"
        )


def get_tetrahedron_skewness_batch(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray
) -> np.ndarray:
    """
    複数の四面体要素の Skewness をバッチで計算する関数。

    Args:
        p1, p2, p3, p4: 四面体の各頂点の座標を含む np.ndarray

    Returns:
        np.ndarray: 各四面体要素の Skewness の配列
    """
    edges = np.array(
        [
            np.linalg.norm(p2 - p1, axis=1),
            np.linalg.norm(p3 - p1, axis=1),
            np.linalg.norm(p4 - p1, axis=1),
            np.linalg.norm(p3 - p2, axis=1),
            np.linalg.norm(p4 - p2, axis=1),
            np.linalg.norm(p4 - p3, axis=1),
        ]
    )

    # 理想的なエッジ長の平均
    ideal_edge_length = np.mean(edges, axis=0)

    # 各四面体の Skewness 計算
    skewness = np.max(np.abs(edges - ideal_edge_length) / ideal_edge_length, axis=0)

    return skewness


def get_prism_skewness_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    三角柱要素の Skewness をバッチで計算する関数。

    Args:
        element_node_coord_array: (n, 6, 3) の形の配列

    Returns:
        np.ndarray: 各三角柱要素の Skewness の配列
    """
    assert element_node_coord_array.shape[1:] == (
        6,
        3,
    ), "三角柱要素は6つの頂点と3次元座標で構成される必要があります"

    edges = [
        np.linalg.norm(
            element_node_coord_array[:, i] - element_node_coord_array[:, j], axis=1
        )
        for i in range(6)
        for j in range(i + 1, 6)
    ]
    edges = np.array(edges)

    ideal_edge_length = np.mean(edges, axis=0)

    skewness = np.max(np.abs(edges - ideal_edge_length) / ideal_edge_length, axis=0)

    return skewness


def get_hexahedron_skewness_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    8節点8面体要素の Skewness をバッチで計算する関数。

    Args:
        element_node_coord_array: (n, 8, 3) の形の配列

    Returns:
        np.ndarray: 各8面体要素の Skewness の配列
    """
    assert element_node_coord_array.shape[1:] == (
        8,
        3,
    ), "8面体要素は8つの頂点と3次元座標で構成される必要があります"

    edges = [
        np.linalg.norm(
            element_node_coord_array[:, i] - element_node_coord_array[:, j], axis=1
        )
        for i in range(8)
        for j in range(i + 1, 8)
    ]
    edges = np.array(edges)

    ideal_edge_length = np.mean(edges, axis=0)

    skewness = np.max(np.abs(edges - ideal_edge_length) / ideal_edge_length, axis=0)

    return skewness


def get_skewness_batch(element_node_coord_array: np.ndarray) -> np.ndarray:
    """
    四面体、三角柱、または8面体要素の Skewness をバッチで計算する関数。

    Args:
        element_node_coord_array: (n, m, 3) の形の配列

    Returns:
        np.ndarray: 各要素の Skewness の配列
    """
    if element_node_coord_array.shape[1] == 4:
        return get_tetrahedron_skewness_batch(
            element_node_coord_array[:, 0],
            element_node_coord_array[:, 1],
            element_node_coord_array[:, 2],
            element_node_coord_array[:, 3],
        )
    elif element_node_coord_array.shape[1] == 6:
        return get_prism_skewness_batch(element_node_coord_array)
    elif element_node_coord_array.shape[1] == 8:
        return get_hexahedron_skewness_batch(element_node_coord_array)
    else:
        raise ValueError(
            "サポートされていない要素形式です。四面体 (4頂点)、三角柱 (6頂点) または8面体 (8頂点) が必要です。"
        )


def get_element_quality(
    element_node_coord_array: np.ndarray,
    mode: Literal["skewness", "aspect", "detJ", "volume"] | List[str] = None,
):
    quality_eval_funcs = dict(
        skewness=get_skewness_batch,
        aspect=get_aspect_ratio_batch,
        detJ=get_detJ_batch,
        volume=get_volume_batch,
    )

    if mode is None:
        mode = ["skewness", "aspect", "detJ", "volume"]

    if not isinstance(mode, list):
        mode = [mode]

    quality_eval_funcs = {k: v for k, v in quality_eval_funcs.items() if k in mode}
    results = dict()
    for mode_i, f in quality_eval_funcs.items():
        results[mode_i] = f(element_node_coord_array)

    return results
