from __future__ import annotations

from dataclasses import dataclass
import numpy as np


# ============================================================
# Q4 kinematics (2x2 Gauss)
# ============================================================

_G = 1.0 / np.sqrt(3.0)
_GAUSS_PTS_2x2: list[tuple[float, float]] = [
    (-_G, -_G),
    (+_G, -_G),
    (+_G, +_G),
    (-_G, +_G),
]


def q4_dN_dxi_eta(xi: float, eta: float) -> tuple[np.ndarray, np.ndarray]:
    """Q4 dN/dxi, dN/deta at (xi,eta). Node order:
    0:(-1,-1), 1:(+1,-1), 2:(+1,+1), 3:(-1,+1)
    """
    dN_dxi = 0.25 * np.array(
        [-(1 - eta), +(1 - eta), +(1 + eta), -(1 + eta)], dtype=np.float64
    )
    dN_deta = 0.25 * np.array(
        [-(1 - xi), -(1 + xi), +(1 + xi), +(1 - xi)], dtype=np.float64
    )
    return dN_dxi, dN_deta


def quad_signed_area_and_grad(p: np.ndarray) -> tuple[float, np.ndarray]:
    """Signed area A and dA/dp for quad. p:(4,2) -> dA:(4,2)."""
    x = p[:, 0]
    y = p[:, 1]
    x1 = np.roll(x, -1)
    y1 = np.roll(y, -1)
    A = 0.5 * float(np.sum(x * y1 - y * x1))

    dA = np.zeros((4, 2), dtype=np.float64)
    for k in range(4):
        kp1 = (k + 1) % 4
        km1 = (k - 1) % 4
        d = p[kp1] - p[km1]
        dA[k, 0] = 0.5 * d[1]
        dA[k, 1] = -0.5 * d[0]
    return A, dA


# ============================================================
# Boundary extraction + loop ordering (for non-analytic contour)
# ============================================================


def extract_boundary_edges_quads(quads: np.ndarray) -> np.ndarray:
    """quadメッシュの境界エッジ(undirected)を抽出して (E,2) index配列で返す."""
    q = np.asarray(quads, dtype=np.int64)
    edges = np.vstack([q[:, [0, 1]], q[:, [1, 2]], q[:, [2, 3]], q[:, [3, 0]]])

    a = np.minimum(edges[:, 0], edges[:, 1])
    b = np.maximum(edges[:, 0], edges[:, 1])
    key = a.astype(np.int64) * (q.max() + 2) + b.astype(np.int64)

    order = np.argsort(key)
    key_s = key[order]
    edges_s = np.stack([a[order], b[order]], axis=1)

    uniq, idx, counts = np.unique(key_s, return_index=True, return_counts=True)
    bnd_edges = edges_s[idx[counts == 1]]
    return bnd_edges


def build_boundary_loops_from_edges(boundary_edges: np.ndarray) -> list[np.ndarray]:
    """境界エッジ集合から、順序付き境界ループ（閉曲線）を構築.

    前提:
        - 境界は1本以上の閉ループから成る
        - 典型的な2Dメッシュなら境界ノードの次数は2（ループ）
    """
    edges = np.asarray(boundary_edges, dtype=np.int64)
    if edges.size == 0:
        return []

    # adjacency
    adj: dict[int, list[int]] = {}
    for u, v in edges:
        adj.setdefault(int(u), []).append(int(v))
        adj.setdefault(int(v), []).append(int(u))

    # sanity: boundary nodes should have degree 2 in simple loops
    # (holes -> multiple loops; non-manifold boundary -> degree != 2)
    visited_edge: set[tuple[int, int]] = set()
    loops: list[np.ndarray] = []

    def mark_edge(u: int, v: int) -> None:
        visited_edge.add((u, v))
        visited_edge.add((v, u))

    for start in list(adj.keys()):
        # if all edges incident to start are visited, skip
        all_visited = True
        for nb in adj[start]:
            if (start, nb) not in visited_edge:
                all_visited = False
                break
        if all_visited:
            continue

        # walk loop
        loop = [start]
        prev = -1
        cur = start

        # pick an unvisited outgoing
        nxt = None
        for nb in adj[cur]:
            if (cur, nb) not in visited_edge:
                nxt = nb
                break
        if nxt is None:
            continue

        while True:
            mark_edge(cur, nxt)
            prev, cur = cur, nxt
            loop.append(cur)

            # reached back to start?
            if cur == start:
                break

            # choose next neighbor (degree-2 assumption: pick not prev; else pick unvisited)
            cands = adj[cur]
            if len(cands) == 0:
                break

            if len(cands) == 2:
                nxt2 = cands[0] if cands[1] == prev else cands[1]
            else:
                # non-manifold or open boundary: pick an unvisited edge if possible
                nxt2 = None
                for nb in cands:
                    if nb != prev and (cur, nb) not in visited_edge:
                        nxt2 = nb
                        break
                if nxt2 is None:
                    # fallback: pick any not prev
                    for nb in cands:
                        if nb != prev:
                            nxt2 = nb
                            break
                if nxt2 is None:
                    break
            nxt = nxt2

        # loop includes start twice (closed). Remove last duplicate.
        if len(loop) >= 2 and loop[-1] == loop[0]:
            loop = loop[:-1]
        if len(loop) >= 3:
            loops.append(np.asarray(loop, dtype=np.int64))

    return loops


# ============================================================
# Energies: quality (analytic) + soft equal-area (analytic) + boundary length (analytic)
# ============================================================


def quality_phi_and_grad_quads(
    points: np.ndarray,
    quads: np.ndarray,
    *,
    fixed_mask: np.ndarray,
    w_var: float,
    w_barrier: float,
    detJ_eps: float,
) -> tuple[float, np.ndarray, float]:
    """Φ_quality = w_var*Σ Var_gp(log detJ) + w_barrier*Σ(-log detJ) と解析勾配.

    注意:
        - detJ<=0 の試行はラインサーチ側で reject する前提
        - detJ_eps は log/1/detJ の数値安定用（小さく）
    """
    pts = np.asarray(points, dtype=np.float64)
    quads = np.asarray(quads, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    grad = np.zeros_like(pts)
    phi = 0.0
    min_detJ = np.inf

    ng = 4
    c_var = 2.0 / ng  # dVar/dl_k = (2/ng)*(l_k-mu)

    for ids in quads:
        p = pts[ids]
        x = p[:, 0]
        y = p[:, 1]

        detJ = np.empty(ng, dtype=np.float64)
        dx_dxi = np.empty(ng, dtype=np.float64)
        dx_deta = np.empty(ng, dtype=np.float64)
        dy_dxi = np.empty(ng, dtype=np.float64)
        dy_deta = np.empty(ng, dtype=np.float64)
        dN_xi = np.empty((ng, 4), dtype=np.float64)
        dN_eta = np.empty((ng, 4), dtype=np.float64)

        for k, (xi, eta) in enumerate(_GAUSS_PTS_2x2):
            dN_dxi, dN_deta = q4_dN_dxi_eta(xi, eta)
            dN_xi[k] = dN_dxi
            dN_eta[k] = dN_deta

            dx_dxi[k] = float(np.dot(dN_dxi, x))
            dx_deta[k] = float(np.dot(dN_deta, x))
            dy_dxi[k] = float(np.dot(dN_dxi, y))
            dy_deta[k] = float(np.dot(dN_deta, y))

            detJ[k] = dx_dxi[k] * dy_deta[k] - dx_deta[k] * dy_dxi[k]

        min_detJ = float(min(min_detJ, float(np.min(detJ))))

        # stabilize for log/reciprocal (but don't clip in a way that kills physics)
        detJc = detJ + detJ_eps
        logJ = np.log(detJc)

        mu = float(np.mean(logJ))
        dev = logJ - mu
        var = float(np.mean(dev * dev))

        phi += w_var * var
        phi += w_barrier * float(-np.sum(np.log(detJc)))

        # dΦ/d(detJ_k)
        dphi_d_detJ = w_var * (c_var * dev / detJc) + w_barrier * (-1.0 / detJc)

        for a_local, a_global in enumerate(ids):
            if fixed_mask[a_global]:
                continue
            gx = 0.0
            gy = 0.0
            for k in range(ng):
                dNdxi = dN_xi[k, a_local]
                dNdeta = dN_eta[k, a_local]

                ddetJ_dx = dNdxi * dy_deta[k] - dNdeta * dy_dxi[k]
                ddetJ_dy = dx_dxi[k] * dNdeta - dx_deta[k] * dNdxi

                w = float(dphi_d_detJ[k])
                gx += w * ddetJ_dx
                gy += w * ddetJ_dy

            grad[a_global, 0] += gx
            grad[a_global, 1] += gy

    grad[fixed_mask] = 0.0
    return float(phi), grad, float(min_detJ)


def quad_angle_energy_and_grad_cos2(
    points: np.ndarray,
    quads: np.ndarray,
    *,
    fixed_mask: np.ndarray,
    w_angle: float,
    eps: float = 1e-30,
) -> tuple[float, np.ndarray]:
    """E_ang = w * Σ_e Σ_vertex cos^2(theta) と解析勾配.

    Args:
        points: (N,2)
        quads: (M,4)
        fixed_mask: (N,)
        w_angle: 重み
        eps: ゼロ割回避

    Returns:
        E, grad (N,2)
    """
    if w_angle <= 0.0:
        return 0.0, np.zeros_like(points)

    pts = np.asarray(points, dtype=np.float64)
    q = np.asarray(quads, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    g = np.zeros_like(pts)
    E = 0.0

    for ids in q:
        p = pts[ids]  # (4,2)

        # vertices 0..3, neighbors cyclic
        for i in range(4):
            im = (i - 1) % 4
            ip = (i + 1) % 4

            a = p[im] - p[i]
            b = p[ip] - p[i]
            na = float(np.linalg.norm(a))
            nb = float(np.linalg.norm(b))
            if na < eps or nb < eps:
                continue

            s = float(a @ b)
            inv = 1.0 / (na * nb)
            c = s * inv  # cos(theta)

            E += w_angle * (c * c)

            # dc/da and dc/db
            # dc/da = b/(na nb) - s/(na^3 nb) a
            # dc/db = a/(na nb) - s/(na nb^3) b
            dc_da = (b * inv) - (s * a) / (na**3 * nb)
            dc_db = (a * inv) - (s * b) / (na * nb**3)

            # d(c^2)/da = 2c dc/da
            coef = 2.0 * w_angle * c
            dE_da = coef * dc_da
            dE_db = coef * dc_db

            gi = ids[i]
            gim = ids[im]
            gip = ids[ip]

            if not fixed_mask[gim]:
                g[gim] += dE_da
            if not fixed_mask[gip]:
                g[gip] += dE_db
            if not fixed_mask[gi]:
                g[gi] -= dE_da + dE_db

    g[fixed_mask] = 0.0
    return float(E), g


def area_soft_equal_energy_and_grad_quads(
    points: np.ndarray,
    quads: np.ndarray,
    *,
    fixed_mask: np.ndarray,
    A0: float,
    mu_area: float,
    use_abs_area: bool = True,
) -> tuple[float, np.ndarray]:
    """E_area = mu * Σ ((A - A0)/A0)^2 と解析勾配."""
    if mu_area <= 0.0:
        return 0.0, np.zeros_like(points)

    pts = np.asarray(points, dtype=np.float64)
    quads = np.asarray(quads, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    grad = np.zeros_like(pts)
    E = 0.0
    invA0 = 1.0 / max(abs(A0), 1e-30)

    for ids in quads:
        A, dA = quad_signed_area_and_grad(pts[ids])
        if use_abs_area:
            s = 1.0 if A >= 0.0 else -1.0
            Aeff = abs(A)
            dAeff = s * dA
        else:
            Aeff = A
            dAeff = dA

        r = (Aeff - A0) * invA0
        E += mu_area * float(r * r)

        coef = mu_area * (2.0 * r * invA0)  # d/dp
        for a_local, a_global in enumerate(ids):
            if fixed_mask[a_global]:
                continue
            grad[a_global] += coef * dAeff[a_local]

    grad[fixed_mask] = 0.0
    return float(E), grad


def boundary_length_energy_and_grad(
    points: np.ndarray,
    boundary_loop: np.ndarray,
    *,
    fixed_mask: np.ndarray,
    w_len: float,
) -> tuple[float, np.ndarray]:
    """E_len = w * Σ (||p_{j+1}-p_j|| - mean)^2 と解析勾配."""
    if w_len <= 0.0:
        return 0.0, np.zeros_like(points)

    pts = np.asarray(points, dtype=np.float64)
    loop = np.asarray(boundary_loop, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    K = loop.size
    if K < 3:
        return 0.0, np.zeros_like(points)

    p0 = pts[loop]
    p1 = pts[np.roll(loop, -1)]
    e = p1 - p0
    L = np.linalg.norm(e, axis=1)
    Lm = float(np.mean(L))
    r = L - Lm

    E = float(w_len * np.sum(r * r))
    g = np.zeros_like(pts)

    for j in range(K):
        i0 = int(loop[j])
        i1 = int(loop[(j + 1) % K])
        if fixed_mask[i0] and fixed_mask[i1]:
            continue
        lij = float(L[j])
        if lij < 1e-30:
            continue
        u = e[j] / lij
        coef = 2.0 * w_len * float(r[j])
        if not fixed_mask[i0]:
            g[i0] += coef * (-u)
        if not fixed_mask[i1]:
            g[i1] += coef * (+u)

    g[fixed_mask] = 0.0
    return E, g


# ============================================================
# Boundary tangent projection (key trick)
# ============================================================


def project_grad_to_boundary_tangent_inplace(
    grad: np.ndarray,
    points: np.ndarray,
    boundary_loop: np.ndarray,
    *,
    fixed_mask: np.ndarray,
    eps: float = 1e-30,
) -> None:
    """境界ループ上ノードの更新ベクトルを接線方向のみに射影（in-place）."""
    pts = np.asarray(points, dtype=np.float64)
    loop = np.asarray(boundary_loop, dtype=np.int64)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    K = loop.size
    for j in range(K):
        i = int(loop[j])
        if fixed_mask[i]:
            grad[i] = 0.0
            continue

        ip = int(loop[(j + 1) % K])
        im = int(loop[(j - 1) % K])

        t = pts[ip] - pts[im]
        nt = float(np.linalg.norm(t))
        if nt < eps:
            grad[i] = 0.0
            continue
        t /= nt
        grad[i] = float(grad[i] @ t) * t  # tangent component only


# ============================================================
# Optimizer
# ============================================================


@dataclass
class PipelineConfig:
    max_iter: int = 300
    step: float = 0.05
    bt_shrink: float = 0.5
    bt_min_step: float = 1e-8
    print_every: int = 10

    # quality
    w_var: float = 1.0
    w_barrier: float = 1e-2
    detJ_eps: float = 1e-12  # log/1/detJ stability

    # soft equal area
    mu_area: float = 30.0
    mu_ramp_iters: int = 50
    use_abs_area: bool = True

    w_angle: float = 1.0

    # boundary edge-length equalization (tangential "reparameterization")
    w_bnd_len: float = 1.0

    # optional: emphasize boundary-ring elements (simple but effective)
    w_boundary_elem_mul: float = 1.0  # 1.0 means no extra weight


def elements_touching_boundary(
    quads: np.ndarray, boundary_edges: np.ndarray
) -> np.ndarray:
    """境界に接する要素（境界辺を含む要素）のmask."""
    q = np.asarray(quads, dtype=np.int64)
    bnd = np.asarray(boundary_edges, dtype=np.int64)
    if bnd.size == 0:
        return np.zeros(q.shape[0], dtype=bool)

    # build set of undirected boundary edges as keys
    a = np.minimum(bnd[:, 0], bnd[:, 1])
    b = np.maximum(bnd[:, 0], bnd[:, 1])
    n_nodes = int(np.max(q)) + 1
    key_b = a.astype(np.int64) * (n_nodes + 1) + b.astype(np.int64)
    key_set = set(map(int, key_b))

    mask = np.zeros(q.shape[0], dtype=bool)
    edges = np.stack(
        [q[:, [0, 1]], q[:, [1, 2]], q[:, [2, 3]], q[:, [3, 0]]], axis=1
    )  # (M,4,2)
    for e in range(q.shape[0]):
        for k in range(4):
            u, v = int(edges[e, k, 0]), int(edges[e, k, 1])
            aa, bb = (u, v) if u < v else (v, u)
            key = aa * (n_nodes + 1) + bb
            if key in key_set:
                mask[e] = True
                break
    return mask


def optimize_quads_soft_equal_area_with_tangent_boundary(
    points0: np.ndarray,
    quads: np.ndarray,
    *,
    fixed_mask: np.ndarray | None = None,
    cfg: PipelineConfig | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """不定形輪郭OK：境界は接線方向のみ移動（固定しなくても輪郭が暴れにくい）.

    Args:
        points0: (N,2)
        quads: (M,4) node indices
        fixed_mask: (N,) Trueなら完全固定（例: コーナーだけ固定など）
        cfg: PipelineConfig

    Returns:
        points_opt, stats
    """
    cfg = PipelineConfig() if cfg is None else cfg
    pts = np.asarray(points0, dtype=np.float64).copy()
    q = np.asarray(quads, dtype=np.int64)

    n = pts.shape[0]
    if fixed_mask is None:
        fixed_mask = np.zeros(n, dtype=bool)
    fixed_mask = np.asarray(fixed_mask, dtype=bool)

    # boundary loops
    bnd_edges = extract_boundary_edges_quads(q)
    loops = build_boundary_loops_from_edges(bnd_edges)
    if len(loops) == 0:
        # no boundary found -> treat as closed surface in plane
        loops = []

    # boundary-ring elements (optional weighting)
    bnd_elem_mask = elements_touching_boundary(q, bnd_edges)

    # target area (global equal)
    A_abs = np.array(
        [abs(quad_signed_area_and_grad(pts[ids])[0]) for ids in q], dtype=np.float64
    )
    A_tot = float(np.sum(A_abs))
    A0 = A_tot / float(q.shape[0])

    def eval_quality(pts_in: np.ndarray) -> tuple[float, np.ndarray, float]:
        # optional: boundary elements weighted heavier by simple split
        if cfg.w_boundary_elem_mul == 1.0 or not np.any(bnd_elem_mask):
            return quality_phi_and_grad_quads(
                pts_in,
                q,
                fixed_mask=fixed_mask,
                w_var=cfg.w_var,
                w_barrier=cfg.w_barrier,
                detJ_eps=cfg.detJ_eps,
            )

        # split into boundary elems and others
        q_b = q[bnd_elem_mask]
        q_i = q[~bnd_elem_mask]

        phi_i, g_i, minJ_i = quality_phi_and_grad_quads(
            pts_in,
            q_i,
            fixed_mask=fixed_mask,
            w_var=cfg.w_var,
            w_barrier=cfg.w_barrier,
            detJ_eps=cfg.detJ_eps,
        )
        phi_b, g_b, minJ_b = quality_phi_and_grad_quads(
            pts_in,
            q_b,
            fixed_mask=fixed_mask,
            w_var=cfg.w_var * cfg.w_boundary_elem_mul,
            w_barrier=cfg.w_barrier * cfg.w_boundary_elem_mul,
            detJ_eps=cfg.detJ_eps,
        )
        phi = phi_i + phi_b
        g = g_i + g_b
        return float(phi), g, float(min(minJ_i, minJ_b))

    for it in range(1, cfg.max_iter + 1):
        mu_area = cfg.mu_area * min(1.0, it / max(cfg.mu_ramp_iters, 1))

        phi_q, g_q, minJ = eval_quality(pts)
        e_area, g_area = area_soft_equal_energy_and_grad_quads(
            pts,
            q,
            fixed_mask=fixed_mask,
            A0=A0,
            mu_area=mu_area,
            use_abs_area=cfg.use_abs_area,
        )
        e_angle, g_angle = quad_angle_energy_and_grad_cos2(
            pts, q, fixed_mask=fixed_mask, w_angle=cfg.w_angle
        )

        # boundary length equalization (sum over loops)
        e_len = 0.0
        g_len = np.zeros_like(pts)
        for loop in loops:
            Ei, gi = boundary_length_energy_and_grad(
                pts,
                loop,
                fixed_mask=fixed_mask,
                w_len=cfg.w_bnd_len,
            )
            e_len += Ei
            g_len += gi

        E0 = phi_q + e_area + e_len + e_angle
        grad = g_q + g_area + g_len + g_angle
        grad[fixed_mask] = 0.0

        # boundary tangent-only update: project grad components on each loop
        for loop in loops:
            project_grad_to_boundary_tangent_inplace(
                grad,
                pts,
                loop,
                fixed_mask=fixed_mask,
            )

        # backtracking (reject if detJ <= 0 or energy not decreased)
        step = cfg.step
        accepted = False
        while step >= cfg.bt_min_step:
            trial = pts.copy()
            trial[~fixed_mask] -= step * grad[~fixed_mask]

            phi_q1, _, minJ1 = eval_quality(trial)
            if minJ1 <= 0.0:
                step *= cfg.bt_shrink
                continue

            e_a1, _ = area_soft_equal_energy_and_grad_quads(
                trial,
                q,
                fixed_mask=fixed_mask,
                A0=A0,
                mu_area=mu_area,
                use_abs_area=cfg.use_abs_area,
            )

            e_len1 = 0.0
            for loop in loops:
                Ei, _ = boundary_length_energy_and_grad(
                    trial,
                    loop,
                    fixed_mask=fixed_mask,
                    w_len=cfg.w_bnd_len,
                )
                e_len1 += Ei

            E1 = phi_q1 + e_a1 + e_len1
            if E1 <= E0:
                pts = trial
                accepted = True
                minJ = minJ1
                E0 = E1
                break

            step *= cfg.bt_shrink

        if it % cfg.print_every == 0 or it == 1:
            A_now = np.array(
                [abs(quad_signed_area_and_grad(pts[ids])[0]) for ids in q],
                dtype=np.float64,
            )
            rel = (A_now - A0) / max(A0, 1e-30)
            print(
                f"iter {it:5d} | E={E0:.6e} | acc={accepted} | "
                f"min(detJ)={minJ:.3e} | max|relA|={np.max(np.abs(rel))*100:.2f}% | "
                f"rms|relA|={np.sqrt(np.mean(rel**2))*100:.2f}% | mu={mu_area:.3g}"
            )
        if not accepted:
            break

    # stats
    A_now = np.array(
        [abs(quad_signed_area_and_grad(pts[ids])[0]) for ids in q], dtype=np.float64
    )
    rel = (A_now - A0) / max(A0, 1e-30)
    stats = {
        "A0": float(A0),
        "max_rel_area_err": float(np.max(np.abs(rel))),
        "rms_rel_area_err": float(np.sqrt(np.mean(rel**2))),
        "n_boundary_loops": int(len(loops)),
        "n_boundary_edges": int(bnd_edges.shape[0]),
    }
    return pts, stats


# ============================================================
# Example usage
# ============================================================

if __name__ == "__main__":
    # ここはあなたの環境で置き換えてください（points0, quads, fixed_mask）
    pass
