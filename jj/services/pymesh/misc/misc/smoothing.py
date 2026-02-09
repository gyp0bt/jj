from typing import List
import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree


def laplacian_smoothing(
    points: np.ndarray,
    k: int = 5,
    alpha: float = 0.5,
    fixed_indices: NDArray[np.bool_] = None,
    n_iter: int = 1,
) -> np.ndarray:
    """
    ラプラシアンフィルタを用いた点群データのスムージング。

    Args:
        points (np.ndarray): (N, 2) 形式の点群データ（xy平面上のN個の点）
        k (int): 近傍点の数（k近傍）
        alpha (float): スムージング係数（0 < alpha < 1）

    Returns:
        np.ndarray: スムージングされた点群データ
    """

    fixed_indices = np.where(fixed_indices)[0].tolist()

    for _ in range(n_iter):

        # KDTreeを使って近傍探索を高速化
        tree = cKDTree(points)

        smoothed_points = np.copy(points)

        for i, point in enumerate(points):
            if i in fixed_indices:
                continue

            # k+1個の近傍を取得（自身を含むため）
            distances, indices = tree.query(point, k=k + 1)

            # 自分自身を除いた近傍点のインデックスを取得
            neighbor_indices = indices[1:]

            # 近傍点の座標を取得して平均を計算
            neighbor_points = points[neighbor_indices]
            mean_neighbor = np.mean(neighbor_points, axis=0)

            # ラプラシアン更新: (1 - alpha) * 元の点 + alpha * 近傍の平均
            smoothed_points[i] = (1 - alpha) * point + alpha * mean_neighbor

        points = smoothed_points

    return smoothed_points
