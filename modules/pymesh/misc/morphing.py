import numpy as np


def map_square01_to_disk_concentric(
    node_coord_arr: np.ndarray,
    *,
    center_xy: tuple[float, float] = (0.5, 0.5),
    radius: float = 0.5,
) -> np.ndarray:
    """[0,1]^2 の正方形座標を、面積（測度）保存な写像で円盤へ写す（Concentric map）.

    入力:
        node_coord_arr: 構造化 ndarray。dtype に "label","x","y","z" を含むこと。
            x,y は [0,1] を想定（範囲外でも動くが円盤外へ行きうる）。

    出力:
        入力と同じ dtype/shape の構造化 ndarray を返す。
        label はそのまま、z もそのまま、x,y だけ円盤へ写像される。

    Args:
        center_xy: 円盤の中心 (cx, cy)
        radius: 円盤の半径（デフォルト 0.5 は正方形に内接する円）

    Notes:
        - Shirley–Chiu "concentric mapping" は正方形一様分布を円盤一様分布へ送る写像として広く使われる。
        - 境界線・軸上など一部で分岐（非解析的）だが、中心収束（極座標型の特異点）を避けられる。
    """
    required = ("label", "x", "y", "z")
    for name in required:
        if name not in node_coord_arr.dtype.names:
            raise ValueError(f'node_coord_arr.dtype に "{name}" フィールドが必要です。')

    out = node_coord_arr.copy()

    cx, cy = center_xy

    # [0,1] -> [-1,1] へ（中心 0、辺が ±1）
    a = (out["x"].astype(np.float64) - 0.5) * 2.0
    b = (out["y"].astype(np.float64) - 0.5) * 2.0

    ax = np.abs(a)
    by = np.abs(b)

    # 出力（単位円盤）用
    r = np.zeros_like(a, dtype=np.float64)
    theta = np.zeros_like(a, dtype=np.float64)

    # 原点（a=b=0）はそのまま
    nonzero = (a != 0.0) | (b != 0.0)

    # |a| > |b| の領域
    mask1 = nonzero & (ax > by)
    # r = |a|
    r[mask1] = ax[mask1]
    # theta の分岐（a>0 / a<0）
    a1 = a[mask1]
    b1 = b[mask1]
    # a>0: theta = (pi/4)*(b/a)
    # a<0: theta = pi + (pi/4)*(b/a)
    theta1 = (np.pi / 4.0) * (b1 / a1)
    theta[mask1] = np.where(a1 > 0.0, theta1, np.pi + theta1)

    # |b| >= |a| の領域（mask1以外の非zero）
    mask2 = nonzero & (~mask1)
    r[mask2] = by[mask2]
    a2 = a[mask2]
    b2 = b[mask2]
    # b>0: theta = pi/2 - (pi/4)*(a/b)
    # b<0: theta = 3pi/2 - (pi/4)*(a/b)
    theta2 = (np.pi / 2.0) - (np.pi / 4.0) * (a2 / b2)
    theta[mask2] = np.where(b2 > 0.0, theta2, (3.0 * np.pi / 2.0) - (np.pi / 4.0) * (a2 / b2))

    # 単位円盤 -> 任意中心・半径へ
    x_new = cx + radius * r * np.cos(theta)
    y_new = cy + radius * r * np.sin(theta)

    out["x"] = x_new.astype(out["x"].dtype, copy=False)
    out["y"] = y_new.astype(out["y"].dtype, copy=False)
    # out["z"] はそのまま
    return out
