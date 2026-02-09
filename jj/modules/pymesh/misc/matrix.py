import numpy as np


def shape_function_derivatives(xi: float, eta: float, zeta: float) -> np.ndarray:
    """
    8節点ヘキサ要素の形状関数の局所座標に対する導関数を計算する。

    Args:
        xi, eta, zeta: 局所座標 (−1 <= xi, eta, zeta <= 1)

    Returns:
        np.ndarray: 形状関数の導関数の配列 (8, 3)
    """
    dN_dxi = np.array(
        [
            [
                -0.125 * (1 - eta) * (1 - zeta),
                -0.125 * (1 - xi) * (1 - zeta),
                -0.125 * (1 - xi) * (1 - eta),
            ],
            [
                0.125 * (1 - eta) * (1 - zeta),
                -0.125 * (1 + xi) * (1 - zeta),
                -0.125 * (1 + xi) * (1 - eta),
            ],
            [
                0.125 * (1 + eta) * (1 - zeta),
                0.125 * (1 + xi) * (1 - zeta),
                -0.125 * (1 + xi) * (1 + eta),
            ],
            [
                -0.125 * (1 + eta) * (1 - zeta),
                0.125 * (1 - xi) * (1 - zeta),
                -0.125 * (1 - xi) * (1 + eta),
            ],
            [
                -0.125 * (1 - eta) * (1 + zeta),
                -0.125 * (1 - xi) * (1 + zeta),
                0.125 * (1 - xi) * (1 - eta),
            ],
            [
                0.125 * (1 - eta) * (1 + zeta),
                -0.125 * (1 + xi) * (1 + zeta),
                0.125 * (1 + xi) * (1 - eta),
            ],
            [
                0.125 * (1 + eta) * (1 + zeta),
                0.125 * (1 + xi) * (1 + zeta),
                0.125 * (1 + xi) * (1 + eta),
            ],
            [
                -0.125 * (1 + eta) * (1 + zeta),
                0.125 * (1 - xi) * (1 + zeta),
                0.125 * (1 - xi) * (1 + eta),
            ],
        ]
    )
    return dN_dxi


def get_jacobian(
    element_node_coord: np.ndarray, xi: float, eta: float, zeta: float
) -> np.ndarray:
    """
    8節点ヘキサ要素のヤコビアン行列を計算する。

    Args:
        element_node_coord: (8, 3) の形状を持つ要素の節点座標
        xi, eta, zeta: 局所座標 (-1 <= xi, eta, zeta <= 1)

    Returns:
        np.ndarray: ヤコビアン行列 (3, 3)
    """
    # 形状関数の導関数を計算
    dN_dxi = shape_function_derivatives(xi, eta, zeta)

    # ヤコビアン行列の計算
    J = np.dot(dN_dxi.T, element_node_coord)

    return J
