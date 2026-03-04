from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import KDTree


def laplacian_smoothing(
    points: np.ndarray,
    fixed_indices: NDArray[np.bool_],
    k: int = 5,
    alpha: float = 0.5,
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
        tree = KDTree(points)

        smoothed_points = np.copy(points)

        for i, point in enumerate(points):
            if i in fixed_indices:
                continue

            # k+1個の近傍を取得（自身を含むため）
            _distances, indices = tree.query(point, k=k + 1)

            # 自分自身を除いた近傍点のインデックスを取得
            neighbor_indices = indices[1:]

            # 近傍点の座標を取得して平均を計算
            neighbor_points = points[neighbor_indices]
            mean_neighbor = np.mean(neighbor_points, axis=0)

            # ラプラシアン更新: (1 - alpha) * 元の点 + alpha * 近傍の平均
            smoothed_points[i] = (1 - alpha) * point + alpha * mean_neighbor

        points = smoothed_points

    return smoothed_points


def build_quads_from_labels(
    node_coord_arr: np.ndarray,
    elem_arr: np.ndarray,
    *,
    node_label_field: str = "label",
    elem_has_elem_label: bool = False,
) -> np.ndarray:
    """要素の節点label配列を、node_coord_arr内のindex接続（quads）に変換する。

    Args:
        node_coord_arr:
            構造化ndarray。少なくとも node_label_field（既定 "label"）を含むこと。
            例: dtype=[("label",i4),("x",f8),("y",f8),("z",f8)]
        elem_arr:
            (n_elem, 4) もしくは (n_elem, 5) などの配列。
            - elem_has_elem_label=False の場合: (n_elem,4) が「節点label」
            - elem_has_elem_label=True  の場合: 先頭列が「要素label」で、残り4列が「節点label」
        node_label_field:
            node_coord_arrの節点ラベル列名
        elem_has_elem_label:
            elem_arrの先頭列に要素ラベルがあるかどうか

    Returns:
        quads: (n_elem,4) の int64 ndarray（node_coord_arr内index）

    Raises:
        ValueError: label重複、未知label参照、要素が4節点でない等
    """
    if node_label_field not in node_coord_arr.dtype.names:
        raise ValueError(f'node_coord_arr に "{node_label_field}" フィールドがありません。')

    node_labels = np.asarray(node_coord_arr[node_label_field])
    if node_labels.ndim != 1:
        raise ValueError("node_coord_arr['label'] は1次元である必要があります。")

    elem_arr = np.asarray(elem_arr)
    if elem_arr.ndim != 2:
        raise ValueError("elem_arr は2次元配列である必要があります。")

    # 要素ラベル列の有無で節点ラベル部を切り出し
    if elem_has_elem_label:
        if elem_arr.shape[1] < 5:
            raise ValueError("elem_has_elem_label=True の場合、elem_arr は少なくとも5列（elem + 4 nodes）が必要です。")
        elem_node_labels = elem_arr[:, 1:5]
    else:
        if elem_arr.shape[1] < 4:
            raise ValueError("elem_arr は少なくとも4列（4節点label）が必要です。")
        elem_node_labels = elem_arr[:, :4]

    # 型は整数へ（labelが文字列等だと壊れるのでここで落とす）
    try:
        node_labels_i = node_labels.astype(np.int64, copy=False)
        elem_node_labels_i = elem_node_labels.astype(np.int64, copy=False)
    except Exception as e:
        raise ValueError("label は整数に変換可能である必要があります。") from e

    # 節点labelの重複チェック（重複があると逆引きが一意でなくなる）
    order = np.argsort(node_labels_i)
    node_labels_sorted = node_labels_i[order]
    if np.any(node_labels_sorted[1:] == node_labels_sorted[:-1]):
        dup = node_labels_sorted[1:][node_labels_sorted[1:] == node_labels_sorted[:-1]][0]
        raise ValueError(f"node label が重複しています: {int(dup)}")

    # searchsortedで一括マッピング
    # idx_in_sorted: (n_elem,4)
    idx_in_sorted = np.searchsorted(node_labels_sorted, elem_node_labels_i)

    # 範囲外チェック
    if np.any(idx_in_sorted < 0) or np.any(idx_in_sorted >= node_labels_sorted.size):
        raise ValueError("elem_arr が node_coord_arr に存在しない節点labelを参照しています（範囲外）。")

    # 一致チェック（searchsortedは“挿入位置”なので、実際に一致するか確認が必要）
    mapped_labels = node_labels_sorted[idx_in_sorted]
    bad = mapped_labels != elem_node_labels_i
    if np.any(bad):
        # 最初の不一致を1つだけ提示
        e_idx, a_idx = np.argwhere(bad)[0]
        missing = int(elem_node_labels_i[e_idx, a_idx])
        raise ValueError(f"elem_arr が未知の節点labelを参照しています: {missing}")

    # ソート順のindex -> 元のnode_coord_arr indexへ戻す
    quads = order[idx_in_sorted].astype(np.int64, copy=False)
    return quads


def area_preserving_laplacian_smoothing_quads(
    points: np.ndarray,
    quads: np.ndarray,
    fixed_mask: np.ndarray,
    *,
    target_area: float | None = None,
    w_area: float = 1.0,
    w_lap: float = 0.05,
    w_barrier: float = 0.05,
    barrier_area_frac: float = 0.2,
    step: float = 0.05,
    n_iter: int = 200,
    backtrack: int = 20,
    circle_center: tuple[float, float] | None = None,
    circle_radius: float | None = None,
) -> np.ndarray:
    """QUAD4メッシュの面積を均しつつ、ラプラシアンで滑らかにする（反転回避付き）。

    目的関数（概念）:
        E = w_area * Σ_e (A_e - A0)^2
          + w_lap  * Σ_i ||p_i - mean(nei(i))||^2
          + w_barrier * Σ_e barrier(A_e)

    barrierは A_e が小さい/負になると急激に罰が増える形（反転を強く忌避）。

    Args:
        points: (N,2) 節点座標
        quads: (M,4) 各要素の節点index（周回順を推奨。混ざると反転検出が不安定）
        fixed_mask: (N,) bool Trueならその節点は動かさない
        target_area: 目標面積 A0。Noneなら「総面積/要素数」ではなく、
            現状の平均面積を採用（形を保ちつつ均す用途向け）
        w_area: 面積均しの重み
        w_lap: ラプラシアン平滑化の重み
        w_barrier: 反転回避バリアの重み
        barrier_area_frac: バリア開始面積の閾値（A_thr = frac * A0）
        step: 初期ステップ幅（大きいと反転しやすい）
        n_iter: 反復回数
        backtrack: 反転/悪化時にステップを半減する回数上限
        circle_center, circle_radius:
            指定すると、fixed_mask=Trueの節点を毎回円周へ投影（円形境界維持用）

    Returns:
        (N,2) 更新後座標
    """
    pts = np.asarray(points, dtype=np.float64).copy()
    quads = np.asarray(quads, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points は (N,2) が必要です。")
    if quads.ndim != 2 or quads.shape[1] != 4:
        raise ValueError("quads は (M,4) が必要です（QUAD4）。")
    if fixed_mask.shape != (pts.shape[0],):
        raise ValueError("fixed_mask は (N,) が必要です。")

    # 近傍（ラプラシアン用）: 要素辺から隣接グラフを作る（KDTree不要、こちらの方がメッシュに正しい）
    nbrs: list[list[int]] = [[] for _ in range(pts.shape[0])]
    for e in range(quads.shape[0]):
        ids = quads[e]
        for a in range(4):
            i0 = int(ids[a])
            i1 = int(ids[(a + 1) % 4])
            if i1 not in nbrs[i0]:
                nbrs[i0].append(i1)
            if i0 not in nbrs[i1]:
                nbrs[i1].append(i0)

    # 符号付き面積（shoelace）と勾配
    def quad_signed_area_and_grad(p: np.ndarray) -> tuple[float, np.ndarray]:
        # p: (4,2)
        x = p[:, 0]
        y = p[:, 1]
        x1 = np.roll(x, -1)
        y1 = np.roll(y, -1)
        A = 0.5 * float(np.sum(x * y1 - y * x1))  # signed

        # dA/dp_k = 0.5 * perp(p_{k+1} - p_{k-1})
        g = np.zeros((4, 2), dtype=np.float64)
        for k in range(4):
            kp1 = (k + 1) % 4
            km1 = (k - 1) % 4
            d = p[kp1] - p[km1]
            g[k, 0] = 0.5 * d[1]
            g[k, 1] = -0.5 * d[0]
        return A, g

    # エネルギーと勾配
    def energy_and_grad(p_all: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        grad = np.zeros_like(p_all)

        # 面積の目標
        signed_areas = np.zeros(quads.shape[0], dtype=np.float64)
        for e in range(quads.shape[0]):
            ids = quads[e]
            A, _ = quad_signed_area_and_grad(p_all[ids])
            signed_areas[e] = A

        # 目標面積A0（符号は現状の平均符号に合わせる）
        if target_area is None:
            A0 = float(np.mean(signed_areas))
        else:
            # 与えられた値は「正の面積」を想定し、符号は現状に合わせる
            sgn = 1.0 if np.mean(signed_areas) >= 0.0 else -1.0
            A0 = sgn * float(target_area)

        Athr = barrier_area_frac * A0  # A0の符号込みで閾値を置く
        # Athr が符号逆転すると困るので、閾値は符号付きで統一
        # 例: A0<0なら Athr<0。AがAthrより「小さい（より負）」と危険、という扱いになる。

        E = 0.0

        # 面積項 + 反転バリア
        for e in range(quads.shape[0]):
            ids = quads[e]
            p = p_all[ids]
            A, dA = quad_signed_area_and_grad(p)

            # 面積均し（AがA0に近づく）
            ea = A - A0
            E += w_area * (ea * ea)
            grad[ids] += (2.0 * w_area * ea) * dA

            # 反転/極小面積バリア：A が Athr に近づくと発散
            # barrier = -log((A - Athr)/|A0|) ただし A > Athr が必要
            # A <= Athr なら巨大ペナルティ（戻す方向へ）
            denom_scale = max(1e-12, abs(A0))
            if (A - Athr) > 1e-12:
                b = -np.log((A - Athr) / denom_scale)
                E += w_barrier * b
                # db/dA = -1/(A - Athr)
                grad[ids] += (w_barrier * (-1.0 / (A - Athr))) * dA
            else:
                # 既に危険域（反転含む）：強烈に押し戻す
                # ここは実務優先のヒューリスティック
                E += w_barrier * 1e6
                grad[ids] += (w_barrier * (-1e6)) * dA

        # ラプラシアン項
        for i in range(p_all.shape[0]):
            if fixed_mask[i]:
                continue
            nb = nbrs[i]
            if not nb:
                continue
            mean_nb = np.mean(p_all[nb], axis=0)
            d = p_all[i] - mean_nb
            E += w_lap * float(d @ d)
            # grad: 2*w_lap*(p_i - mean_nb)
            grad[i] += 2.0 * w_lap * d

        return E, grad, signed_areas

    # 円形境界を維持したい場合：固定点を円へ投影
    def project_fixed_to_circle(p_all: np.ndarray) -> None:
        if circle_center is None or circle_radius is None:
            return
        cx, cy = circle_center
        rr = float(circle_radius)
        idx = np.where(fixed_mask)[0]
        if idx.size == 0:
            return
        v = p_all[idx] - np.array([cx, cy], dtype=np.float64)
        n = np.linalg.norm(v, axis=1)
        n = np.maximum(n, 1e-15)
        p_all[idx] = np.array([cx, cy], dtype=np.float64) + rr * (v / n[:, None])

    # 初期の投影
    project_fixed_to_circle(pts)

    # 反転チェック
    def has_inversion(signed_areas: np.ndarray) -> bool:
        # どれか符号が平均符号と逆になったら反転扱い
        sgn = 1.0 if np.mean(signed_areas) >= 0.0 else -1.0
        return np.any(sgn * signed_areas <= 0.0)

    # 最適化ループ（バックトラッキング付き）
    E, g, _areas = energy_and_grad(pts)
    step_now = step
    for _ in range(n_iter):
        if np.allclose(g[~fixed_mask], 0.0):
            break

        # step_now = step
        step_now *= 2.0
        accepted = False

        for _bt in range(backtrack):
            cand = pts.copy()
            cand[~fixed_mask] -= step_now * g[~fixed_mask]

            # 固定境界は円周へ
            project_fixed_to_circle(cand)

            E2, g2, areas2 = energy_and_grad(cand)

            # 反転が起きたら却下
            if has_inversion(areas2):
                step_now *= 0.5
                continue

            # エネルギーが下がれば採用
            if E2 < E:
                pts = cand
                E, g, _areas = E2, g2, areas2
                accepted = True
                break

            step_now *= 0.5

        print(f"Iter:{_} | bt:{_bt} E:{E2} step{step_now:.2e}")
        if not accepted:
            # これ以上は詰み：ステップが小さすぎるか、重みが悪い
            break

    return pts


def quad_signed_area_and_grad(p: np.ndarray) -> tuple[float, np.ndarray]:
    """QUAD(4,2)の符号付き面積Aと dA/dp (4,2)."""
    x = p[:, 0]
    y = p[:, 1]
    x1 = np.roll(x, -1)
    y1 = np.roll(y, -1)
    A = 0.5 * float(np.sum(x * y1 - y * x1))  # signed

    g = np.zeros((4, 2), dtype=np.float64)
    for k in range(4):
        kp1 = (k + 1) % 4
        km1 = (k - 1) % 4
        d = p[kp1] - p[km1]
        # perp(d) = [d_y, -d_x]
        g[k, 0] = 0.5 * d[1]
        g[k, 1] = -0.5 * d[0]
    return A, g


def project_to_circle_tangent_update(
    xy_new: np.ndarray,
    xy_old: np.ndarray,
    bnd_mask: np.ndarray,
    *,
    center: tuple[float, float],
    radius: float,
) -> np.ndarray:
    """境界ノードは「接線方向の移動だけ許可」して円周上に保つ."""
    if not np.any(bnd_mask):
        return xy_new

    cx, cy = center
    c = np.array([cx, cy], dtype=np.float64)

    v_old = xy_old[bnd_mask] - c
    n = np.linalg.norm(v_old, axis=1)
    n = np.maximum(n, 1e-15)
    rhat = v_old / n[:, None]  # 半径方向単位
    that = np.stack([-rhat[:, 1], rhat[:, 0]], axis=1)  # 接線方向単位

    # 提案移動を接線方向へ射影
    d = xy_new[bnd_mask] - xy_old[bnd_mask]
    dt = np.sum(d * that, axis=1)[:, None]
    xy_tan = xy_old[bnd_mask] + dt * that

    # 円周へ投影（半径を厳密固定）
    v = xy_tan - c
    nn = np.linalg.norm(v, axis=1)
    nn = np.maximum(nn, 1e-15)
    xy_new[bnd_mask] = c + radius * (v / nn[:, None])
    return xy_new


def smooth_minimize_area_error_quads(
    points: np.ndarray,
    quads: np.ndarray,
    *,
    bnd_mask: np.ndarray | None = None,
    fixed_mask: np.ndarray | None = None,
    center_xy: tuple[float, float] = (0.5, 0.5),
    radius: float = 0.5,
    target_area: float | None = None,
    w_barrier: float = 0.2,
    barrier_frac: float = 0.25,
    step: float = 0.05,
    n_iter: int = 400,
    backtrack: int = 25,
    stop_max_rel: float = 0.01,
    allow_boundary_tangent: bool = True,
    print_every: int = 20,
    verbose: bool = True,
) -> tuple[np.ndarray, dict[str, float]]:
    """面積誤差の最小化に全振りしたメッシュスムージング（反転バリア付）.

    Args:
        points: (N,2) 節点座標
        quads:  (M,4) 各要素の節点index（周回順が望ましい）
        bnd_mask:
            (N,) bool 境界ノード。Noneなら全て内部扱い。
            円形を維持したい場合に使用。
        fixed_mask:
            (N,) bool 完全固定ノード（動かさない）。Noneなら全False。
        center_xy, radius:
            円境界の定義（bnd_maskがある場合に使用）
        target_area:
            目標面積A0。Noneなら「現在の平均|A|」を採用（総面積が合ってなくても均しやすい）
        w_barrier:
            反転/極小面積バリアの強さ
        barrier_frac:
            バリア開始閾値 Athr = frac * A0（AがAthrに近づくと急激に罰）
        step:
            初期ステップ
        n_iter:
            反復回数
        backtrack:
            ステップ半減回数上限
        stop_max_rel:
            max相対誤差がこれ以下になったら終了（例: 0.01=1%）
        allow_boundary_tangent:
            Trueなら境界ノードは接線方向のみ移動可能（面積誤差を下げやすい）
            Falseなら境界ノードは固定（最初に円周へ投影するだけ）

    Returns:
        points_new: (N,2)
        stats: 面積誤差など
    """
    pts = np.asarray(points, dtype=np.float64).copy()
    quads = np.asarray(quads, dtype=np.int64)

    n = pts.shape[0]
    if bnd_mask is None:
        bnd_mask = np.zeros(n, dtype=bool)
    else:
        bnd_mask = np.asarray(bnd_mask, dtype=bool)

    if fixed_mask is None:
        fixed_mask = np.zeros(n, dtype=bool)
    else:
        fixed_mask = np.asarray(fixed_mask, dtype=bool)

    # 固定は優先
    move_mask = ~(fixed_mask)

    # 初期：境界を円周へ
    if np.any(bnd_mask):
        cx, cy = center_xy
        c = np.array([cx, cy], dtype=np.float64)
        v = pts[bnd_mask] - c
        nn = np.linalg.norm(v, axis=1)
        nn = np.maximum(nn, 1e-15)
        pts[bnd_mask] = c + radius * (v / nn[:, None])

    # 面積の符号基準（反転検出用）
    def signed_areas(p_all: np.ndarray) -> np.ndarray:
        A = np.empty(quads.shape[0], dtype=np.float64)
        for e in range(quads.shape[0]):
            ids = quads[e]
            Ae, _ = quad_signed_area_and_grad(p_all[ids])
            A[e] = Ae
        return A

    A_init = signed_areas(pts)
    sgn0 = 1.0 if np.mean(A_init) >= 0.0 else -1.0

    def has_inversion(A: np.ndarray) -> bool:
        # 初期の平均符号と逆（あるいはゼロ近傍）を反転扱い
        return np.any(sgn0 * A <= 1e-15)

    # 目的関数と勾配：面積誤差 + バリア
    def energy_and_grad(
        p_all: np.ndarray,
    ) -> tuple[float, np.ndarray, np.ndarray, float]:
        grad = np.zeros_like(p_all)
        A = signed_areas(p_all)

        # 目標面積（絶対値基準で均すのが安定）
        Aabs = np.abs(A)
        if target_area is None:
            A0 = float(np.mean(Aabs))
        else:
            A0 = float(target_area)

        # バリア閾値（正の面積で扱う）
        Athr = barrier_frac * A0

        E = 0.0

        for e in range(quads.shape[0]):
            ids = quads[e]
            p = p_all[ids]
            Ae, dAe = quad_signed_area_and_grad(p)

            # absの微分：符号を使う（ここが大事。absを雑にすると潰れやすい）
            sign = 1.0 if Ae >= 0.0 else -1.0
            Aae = abs(Ae)

            # 相対誤差（Aabsベース）
            er = (Aae - A0) / A0
            E += er * er

            # d(er^2)/dA = 2*er*(1/A0)*d|A|/dA = 2*er*(1/A0)*sign
            coef = (2.0 * er / A0) * sign
            grad[ids] += coef * dAe

            # バリア：Aabs が Athr 以下へ近づくと急激に増大（反転/潰れ抑制）
            # barrier = -log((Aabs - Athr)/A0)  (Aabs > Athr が必要)
            if (Aae - Athr) > 1e-12:
                b = -np.log((Aae - Athr) / A0)
                E += w_barrier * b
                # db/d|A| = -1/(|A|-Athr), d|A|/dA = sign
                grad[ids] += (w_barrier * (-1.0 / (Aae - Athr)) * sign) * dAe
            else:
                # 危険域は強烈に押し返す
                E += w_barrier * 1e6
                grad[ids] += (w_barrier * (-1e6) * sign) * dAe

        # 固定ノードは動かさない
        grad[~move_mask] = 0.0
        return E, grad, Aabs, A0

    # 初期評価
    E, g, Aabs, A0 = energy_and_grad(pts)

    best_max_rel = np.inf

    for it in range(1, n_iter + 1):
        rel = (Aabs - A0) / A0
        max_rel = float(np.max(np.abs(rel)))
        rms_rel = float(np.sqrt(np.mean(rel * rel)))

        if max_rel < best_max_rel:
            best_max_rel = max_rel
            improved = True
        else:
            improved = False

        if verbose and (it % print_every == 0 or improved):
            print(f"iter {it:5d} | max_rel={max_rel * 100:6.2f}% | rms={rms_rel * 100:6.2f}% | step={step:.4g}")

        if max_rel <= stop_max_rel:
            if verbose:
                print(f"iter {it:5d} | max_rel={max_rel * 100:6.2f}% | converged")
            break

        step_now = step
        accepted = False

        for _bt in range(backtrack):
            cand = pts - step_now * g

            if np.any(bnd_mask):
                if allow_boundary_tangent:
                    cand = project_to_circle_tangent_update(cand, pts, bnd_mask, center=center_xy, radius=radius)
                else:
                    cx, cy = center_xy
                    c = np.array([cx, cy], dtype=np.float64)
                    v = cand[bnd_mask] - c
                    nn = np.linalg.norm(v, axis=1)
                    nn = np.maximum(nn, 1e-15)
                    cand[bnd_mask] = c + radius * (v / nn[:, None])

            cand[~move_mask] = pts[~move_mask]

            E2, g2, Aabs2, A02 = energy_and_grad(cand)

            if has_inversion(signed_areas(cand)):
                step_now *= 0.5
                continue

            if E2 < E:
                pts, E, g, Aabs, A0 = cand, E2, g2, Aabs2, A02
                accepted = True
                break

            step_now *= 0.5

        if not accepted:
            if verbose:
                print(f"iter {it:5d} | stalled (step too small or barrier active)")
            break

    rel = (Aabs - A0) / A0
    stats = {
        "A0": float(A0),
        "max_rel_area_err": float(np.max(np.abs(rel))),
        "mean_rel_area_err": float(np.mean(np.abs(rel))),
        "rms_rel_area_err": float(np.sqrt(np.mean(rel * rel))),
        "n_iter": it,
    }
    return pts, stats
