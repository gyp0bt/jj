from typing import Dict, Optional, Any, List, Tuple, Literal, Callable
import numpy as np
from collections import defaultdict
from ..mesh import mesher, Mesher

from typing import Dict, Literal
import numpy as np
from scipy.spatial import KDTree


def get_space_averaged_field_value(
    mesh: "Mesher",
    field: Dict[int, np.ndarray],
    r: float,
    name: Optional[str | List[str]] = None,
    mode: Literal["elem", "node"] = "elem",
) -> Dict[int, np.ndarray]:
    """要素または節点フィールドの空間平均を KDTree で取る.

    半径 r の近傍内にある要素/節点のフィールド値を単純平均する。

    Args:
        mesh (Mesher): メッシュ
        field (Dict[int, np.ndarray]): 要素または節点ラベルと
            フィールド(配列)の辞書。値はスカラーでもベクトルでもよい。
        r (float): 近傍半径
        name (Optional[str|List[str]]): ElementsまたはNodesの名前
        mode (Literal["elem", "node"]): フィールドが要素か節点か

    Returns:
        Dict[int, np.ndarray]: 各ラベルに対する空間平均済みフィールド

    Raises:
        ValueError: r < 0 または mode が不正な場合
    """
    if r < 0:
        raise ValueError("r must be non-negative")

    # --- 座標配列取得 ---
    match mode:
        case "elem":
            coord_raw = mesh.get_element_coord_array(
                name=name
            )  # label, x, y, z を持つ想定
        case "node":
            coord_raw = mesh.get_node_coord_array(name=name)
        case _:
            raise ValueError("mode must be 'elem' or 'node'")

    # (N, 4) = [label, x, y, z]
    coord_arr = np.array(
        [coord_raw["label"], coord_raw["x"], coord_raw["y"], coord_raw["z"]]
    ).T

    labels = coord_arr[:, 0].astype(int)  # (N,)
    coords = coord_arr[:, 1:4].astype(float)  # (N, 3)

    # --- field dict -> (N, m) に並べ替え ---
    fields = np.array([field[int(lbl)] for lbl in labels])
    if fields.ndim == 1:
        fields = fields.reshape(-1, 1)  # スカラーフィールドを (N, 1) に

    n_points, n_comp = fields.shape

    # --- KDTree 構築 ---
    tree = KDTree(coords)

    averaged: Dict[int, np.ndarray] = {}

    # 各点の近傍 index を取得して平均
    # query_ball_point は 1 点ずつでもベクトル化してもよいが、
    # 実装単純さ優先でループで回す
    for i in range(n_points):
        # r 半径内の近傍のインデックス (自身も含む)
        idx_neigh = tree.query_ball_point(coords[i], r)

        # 念のためガード（r=0 等でも自身は入るはずだが）
        if not idx_neigh:
            # 近傍なしなら自身の値をそのまま入れておく
            avg_val = fields[i]
        else:
            avg_val = fields[idx_neigh].mean(axis=0)

        averaged[int(labels[i])] = avg_val

    return averaged
