import numpy as np
from numpy.typing import DTypeLike, NDArray


def match_shell_clusters_by_geometory(
    elems_bottom: NDArray[np.int64],
    nodes_bottom: np.ndarray,
    elems_top: NDArray[np.int64],
    nodes_top: np.ndarray,
    node_tol: float = 1e-6,
    invalid_node: int = 0,
) -> tuple[NDArray[np.int64], dict[int, int]]:
    """幾何形状に基づき、topクラスタをbottomクラスタに揃えた要素配列を構築する（3角・4角混在可）。

    前提:
        - elems_bottom, elems_top:
            shape (n_elems, n_cols), int64
            elems[:, 0] が要素ラベル, elems[:, 1:] が節点ラベル.
            3角形は (n1, n2, n3, invalid_node, ...),
            4角形は (n1, n2, n3, n4, ...) のように混在して良い。
        - nodes_bottom, nodes_top:
            dtype に ("label","x","y","z") を持つ構造化ndarray.
        - 幾何的トポロジーは同一だが、ラベル対応はバラバラ。
        - 対応する節点同士の距離は node_tol 程度以下。

    処理の概要:
        1) bottom節点ごとに最近傍 top節点を見つけ、一意対応 bottom->top を作る。
        2) bottom要素の有効節点集合（3 or 4個）を bottom->top 対応で写像し、
           同じ節点集合を持つ top要素を探す。
        3) bottomの行順・局所節点順に揃えた elems_top_matched を返す。

    Args:
        elems_bottom: 下側クラスタの要素配列.
        nodes_bottom: 下側クラスタの節点座標.
        elems_top: 上側クラスタの要素配列（raw）。
        nodes_top: 上側クラスタの節点座標.
        node_tol: 節点マッチングの許容距離.
        invalid_node: 無効節点ラベル（パディング用）。

    Returns:
        elems_top_matched:
            shape は elems_bottom と同じ。
            0列目: top側の要素ラベル（対応する要素）
            それ以降: bottomの局所節点順に対応した top節点ラベル
                      （余りは invalid_node でパディング）。
        bottom_to_top_node:
            dict[bottom_node_label] = top_node_label

    Raises:
        ValueError: トポロジー不整合やマッチング不能な場合。
    """
    if elems_bottom.shape[1] != elems_top.shape[1]:
        raise ValueError("bottom/top の要素配列の列数が異なります。")

    n_elems_bottom, _n_cols = elems_bottom.shape
    n_elems_top, _ = elems_top.shape

    if n_elems_bottom != n_elems_top:
        raise ValueError(f"bottom/top の要素数が一致していません。({n_elems_bottom, n_elems_top})")

    # --- 座標配列の準備 ---
    bottom_labels = np.asarray(nodes_bottom["label"], dtype=np.int64)
    bottom_xyz = np.stack([nodes_bottom["x"], nodes_bottom["y"], nodes_bottom["z"]], axis=1).astype(float)

    top_labels = np.asarray(nodes_top["label"], dtype=np.int64)
    top_xyz = np.stack([nodes_top["x"], nodes_top["y"], nodes_top["z"]], axis=1).astype(float)

    # label -> index
    bottom_label_to_index: dict[int, int] = {int(lbl): int(i) for i, lbl in enumerate(bottom_labels)}

    # --- bottom節点 -> top節点 を最近傍で決める（再利用なし） ---
    bottom_to_top_node: dict[int, int] = {}
    used_top_indices: set[int] = set()

    for lbl_b, idx_b in bottom_label_to_index.items():
        pb = bottom_xyz[idx_b]  # (3,)

        diff = top_xyz - pb
        dist2 = np.sum(diff * diff, axis=1)
        order = np.argsort(dist2)

        chosen: int | None = None
        for idx_t in order:
            if int(idx_t) in used_top_indices:
                continue
            d = np.sqrt(dist2[idx_t])
            if d > node_tol:
                raise ValueError(
                    f"bottom節点 {lbl_b} に十分近い top節点がありません (最近距離={d:.3e} > tol={node_tol:.3e})."
                )
            chosen = int(idx_t)
            break

        if chosen is None:
            raise ValueError(f"bottom節点 {lbl_b} に対応可能な top節点が割り当てられません。")

        used_top_indices.add(chosen)
        bottom_to_top_node[lbl_b] = int(top_labels[chosen])

    # --- top側: 有効節点集合 -> 要素インデックス の辞書 ---
    top_node_set_to_elem_index: dict[frozenset[int], int] = {}
    for ei in range(n_elems_top):
        raw_nodes = elems_top[ei, 1:]
        valid_nodes = [int(n) for n in raw_nodes if int(n) != invalid_node]

        if len(valid_nodes) not in (3, 4):
            raise ValueError(f"top要素 {elems_top[ei, 0]} の有効節点数 {len(valid_nodes)} が 3/4 以外です。")

        key = frozenset(valid_nodes)
        if key in top_node_set_to_elem_index:
            raise ValueError("同じ節点集合を持つtop要素が複数あります。トポロジーが曖昧です。")
        top_node_set_to_elem_index[key] = ei

    # --- bottom要素ごとに対応top要素を見つけ、局所順を揃えた配列を作る ---
    elems_top_matched = np.full_like(elems_bottom, fill_value=invalid_node)

    # print(bottom_to_top_node)
    for ei in range(n_elems_bottom):
        raw_nodes = elems_bottom[ei, 1:]
        bottom_nodes = [int(n) for n in raw_nodes if int(n) != invalid_node]

        if len(bottom_nodes) not in (3, 4):
            raise ValueError(f"bottom要素 {elems_bottom[ei, 0]} の有効節点数 {len(bottom_nodes)} が 3/4 以外です。")

        mapped_top_nodes = [bottom_to_top_node[nb] for nb in bottom_nodes]
        key = frozenset(mapped_top_nodes)

        if key not in top_node_set_to_elem_index:
            raise ValueError(f"bottom要素 {elems_bottom[ei, 0]} に対応する top要素が見つかりません。")

        t_ei = top_node_set_to_elem_index[key]
        top_elem_label = elems_top[t_ei, 0]

        elems_top_matched[ei, 0] = top_elem_label
        # bottom の局所順に対応する top節点ラベルを詰める
        elems_top_matched[ei, 1 : 1 + len(mapped_top_nodes)] = np.array(mapped_top_nodes, dtype=np.int64)
        # 余りは invalid_node のまま

    return elems_top_matched, bottom_to_top_node


def extrude_between_topology_matched_shell_clusters(
    elems_bottom: NDArray[np.int64],
    nodes_bottom: np.ndarray,
    elems_top: NDArray[np.int64],
    nodes_top: np.ndarray,
    n_div: int,
    start_node_label: int,
    start_elem_label: int,
    invalid_node: int = 0,
) -> tuple[np.ndarray, NDArray[np.int64]]:
    """2つのシェルクラスタ間を押し出してソリッド要素を生成（3角/4角混在可）。

    想定:
        - elems_bottom, elems_top:
            shape (n_elems, n_cols), int64
            elems[:,0] が要素ラベル, elems[:,1:] が節点ラベル.
            3角形は (n1,n2,n3,invalid_node,...),
            4角形は (n1,n2,n3,n4,...) という混在。
            *事前に幾何マッチング済み*（行と局所順は対応済み）を想定。
        - nodes_bottom, nodes_top:
            dtype [("label","i8"),("x","f8"),("y","f8"),("z","f8")] の構造化ndarray.
        - n_div:
            厚み方向の要素分割数。節点層数は n_div+1。
        - 出力:
            * new_nodes:
                dtype は nodes_bottom と同じ。全層分の節点を格納。
            * solid_elems:
                shape (n_elems * n_div, 1 + 8) の int64.
                solid_elems[:,0] = 要素ラベル.
                solid_elems[:,1:] = ソリッド要素の節点ラベル.
                - 三角シェル要素 → 6節点プリズム:
                    [b1,b2,b3,t1,t2,t3, invalid_node, invalid_node]
                - 四角シェル要素 → 8節点ヘキサ:
                    [b1,b2,b3,b4,t1,t2,t3,t4]

    Args:
        elems_bottom: 下側シェル要素配列（matched基準）。
        nodes_bottom: 下側節点座標.
        elems_top: 上側シェル要素配列（matched）。
        nodes_top: 上側節点座標.
        n_div: 厚み方向の要素分割数.
        start_node_label: 新規節点ラベルの開始値.
        start_elem_label: 新規要素ラベルの開始値.
        invalid_node: 無効節点ラベル（パディング用）。

    Returns:
        new_nodes: 構造化ndarray (label,x,y,z), 全層分の節点。
        solid_elems: int64配列 shape (n_elems*n_div, 9).
    """
    if elems_bottom.shape != elems_top.shape:
        raise ValueError("bottom/top の要素配列 shape が一致していません。")

    if n_div <= 0:
        raise ValueError("n_div は 1 以上にしてください。")

    n_elems, n_cols = elems_bottom.shape
    n_cols - 1

    # --- 節点ラベル → 座標 ---
    bottom_label_to_coord: dict[int, np.ndarray] = {
        int(lbl): np.array([float(x), float(y), float(z)], dtype=float)
        for lbl, x, y, z in zip(
            nodes_bottom["label"],
            nodes_bottom["x"],
            nodes_bottom["y"],
            nodes_bottom["z"],
            strict=False,
        )
    }
    {
        int(lbl): np.array([float(x), float(y), float(z)], dtype=float)
        for lbl, x, y, z in zip(nodes_top["label"], nodes_top["x"], nodes_top["y"], nodes_top["z"], strict=False)
    }

    # --- bottom側で実際に使われている有効節点の集合 ---
    used_bottom_nodes: set[int] = set()
    for ei in range(n_elems):
        for n in elems_bottom[ei, 1:]:
            ni = int(n)
            if ni == invalid_node:
                continue
            used_bottom_nodes.add(ni)

    unique_bottom_nodes = sorted(used_bottom_nodes)
    n_unique_nodes = len(unique_bottom_nodes)

    # --- 各 bottom節点に対して、厚み方向に n_div+1 層の節点を生成 ---
    total_layers = n_div + 1
    total_new_nodes = n_unique_nodes * total_layers

    node_dtype = nodes_bottom.dtype
    new_nodes = np.empty(total_new_nodes, dtype=node_dtype)

    layered_node_label: dict[tuple[int, int], int] = {}
    current_node_label = start_node_label
    idx = 0

    for nb in unique_bottom_nodes:
        if nb not in bottom_label_to_coord:
            raise ValueError(f"bottom節点 {nb} の座標が見つかりません。")

        # bottom に対応する top節点ラベルを座標から決めたいが、
        # ここでは「既に elems_top が matched 済み」と仮定して、
        # bottomとtopの節点ラベル対応は *座標を直接引く* 方式を取る。
        # つまり、押し出し方向は (top_coord - bottom_coord) とする。

        pb = bottom_label_to_coord[nb]

        # nb に対応する top節点ラベルは、nodes_top から nb をキーに探せないので、
        # 「同じインデックスの elems_top から拾う」などはできない。
        # ここでは「bottomとtopは事前に match してあり、同じ nb が top側にも存在する」
        # という前提は置けないので、別途 bottom->top mapping を渡しても良いが、
        # 既に match 関数で作っているなら、それを引数で受け取るのが一番クリーン。
        #
        # → 妥協案: bottom節点と同じ座標に最も近い top節点を使う（再利用可）。
        #    （本来は bottom_to_top_node 辞書を引数でもらうのが筋）

        # 近傍 top節点を探索
        # 注意: 規模が大きいならKD-treeを検討
        nodes_top["label"].astype(np.int64)
        top_xyz = np.stack([nodes_top["x"], nodes_top["y"], nodes_top["z"]], axis=1).astype(float)
        diff = top_xyz - pb
        dist2 = np.sum(diff * diff, axis=1)
        i_min = int(np.argmin(dist2))
        pt = top_xyz[i_min]

        for layer in range(total_layers):
            t = layer / float(n_div)  # 0..1
            p = (1.0 - t) * pb + t * pt

            layered_node_label[(nb, layer)] = current_node_label

            new_nodes[idx]["label"] = current_node_label
            new_nodes[idx]["x"] = p[0]
            new_nodes[idx]["y"] = p[1]
            new_nodes[idx]["z"] = p[2]

            current_node_label += 1
            idx += 1

    # --- ソリッド要素配列を作成 ---
    #   3角 → 6節点プリズム
    #   4角 → 8節点ヘキサ
    #   ただし配列形状を揃えるため、全て 8節点分を確保し、
    #   3角の場合は後ろ2つを invalid_node でパディングする。
    n_solid_max_nodes = 8
    total_solid_elems = n_elems * n_div
    solid_elems = np.full(
        (total_solid_elems, 1 + n_solid_max_nodes),
        fill_value=invalid_node,
        dtype=np.int64,
    )

    current_elem_label = start_elem_label
    solid_row = 0

    for ei in range(n_elems):
        # bottom要素の有効節点
        raw_nodes = elems_bottom[ei, 1:]
        bottom_nodes = [int(n) for n in raw_nodes if int(n) != invalid_node]
        n_nodes_shell = len(bottom_nodes)

        if n_nodes_shell not in (3, 4):
            raise ValueError(f"bottom要素 {elems_bottom[ei, 0]} の有効節点数 {n_nodes_shell} が 3/4 以外です。")

        for layer in range(n_div):
            # その層のbottom/top節点ラベルを取得
            bottom_layer_labels = [layered_node_label[(nb, layer)] for nb in bottom_nodes]
            top_layer_labels = [layered_node_label[(nb, layer + 1)] for nb in bottom_nodes]

            if n_nodes_shell == 3:
                # 三角プリズム: 6節点 + パディング2
                solid_nodes = bottom_layer_labels + top_layer_labels + [invalid_node, invalid_node]
            else:
                # 四角ヘキサ: 8節点
                solid_nodes = bottom_layer_labels + top_layer_labels

            solid_elems[solid_row, 0] = current_elem_label
            solid_elems[solid_row, 1:] = np.array(solid_nodes, dtype=np.int64)

            current_elem_label += 1
            solid_row += 1

    return new_nodes, solid_elems


def split_prism_and_hex(
    solid_elems: NDArray[np.int64],
    invalid_node: int = 0,
) -> tuple[NDArray[np.int64] | None, NDArray[np.int64] | None]:
    """三角柱要素と直方体要素を solid_elems から分解する.

    想定:
        - solid_elems は shape (n_solid, 1+8) の int64 配列.
        - solid_elems[:, 0] は要素ラベル.
        - solid_elems[:, 1:] は最大 8 個の節点ラベル.
        - 三角柱 (prism) は 6 節点 + 2 パディング (invalid_node).
        - 直方体 (hexa) は 8 節点すべて有効な節点ラベル.

    有効節点数の判定:
        col 1〜8 のうち、invalid_node 以外の節点数が 6 なら三角柱,
        8 なら直方体とみなす。それ以外はエラーとする。

    Args:
        solid_elems: ソリッド要素配列 (1+8列固定).
        invalid_node: 無効節点ラベル（パディングに使用している値）.

    Returns:
        prism_elems:
            三角柱要素のみを集めた配列。
            shape (n_prism, 1+6) で、[elem_label, 6ノード] を格納。
        hex_elems:
            直方体要素のみを集めた配列。
            shape (n_hex, 1+8) で、[elem_label, 8ノード] を格納。

    Raises:
        ValueError: 有効節点数が 6 でも 8 でもない行が存在する場合。
    """
    if solid_elems.ndim != 2 or solid_elems.shape[1] < 2:
        raise ValueError("solid_elems は少なくとも (n, 2) の2次元配列である必要があります。")

    # 節点部のみ取り出し
    node_part = solid_elems[:, 1:]  # shape (n_solid, <=8)

    # 有効節点数をカウント（invalid_node 以外の数）
    valid_mask = node_part != invalid_node
    valid_counts = np.sum(valid_mask, axis=1)  # shape (n_solid,)

    # 三角柱（6節点）と直方体（8節点）のインデックス
    prism_idx = np.where(valid_counts == 6)[0]
    hex_idx = np.where(valid_counts == 8)[0]

    # それ以外が混ざっていたらエラー
    others_idx = np.where((valid_counts != 6) & (valid_counts != 8))[0]
    if others_idx.size > 0:
        bad = others_idx[:5]
        raise ValueError(f"有効節点数が 6 でも 8 でもない要素が存在します。 indices={bad}, counts={valid_counts[bad]}")

    if prism_idx.size > 0:
        # 三角柱: ラベル + 有効6節点のみ抽出
        prism_elems_label = solid_elems[prism_idx, [0]]  # (n_prism, 1)
        prism_nodes_all = node_part[prism_idx]  # (n_prism, 8)
        # 有効節点の位置だけ抜き出す（列順はそのまま）
        prism_nodes_valid = prism_nodes_all[prism_nodes_all != invalid_node].reshape(-1, 6)
        prism_elems = np.concatenate([prism_elems_label, prism_nodes_valid], axis=1)
    else:
        prism_elems = None

    if hex_idx.size > 0:
        # 直方体: もともと 8 節点すべて有効なので、そのまま
        hex_elems_label = solid_elems[hex_idx, [0]]  # (n_hex, 1)
        hex_nodes = node_part[hex_idx]  # (n_hex, 8)
        hex_elems = np.concatenate([hex_elems_label.reshape(-1, 1), hex_nodes], axis=1)

    else:
        hex_elems = None

    return prism_elems, hex_elems


node_coord_array_dtype: DTypeLike = np.dtype([("label", "int32"), ("x", "float32"), ("y", "float32"), ("z", "float32")])


def _area_normal_of_quad(p1, p2, p3, p4):
    n1 = np.cross(p2 - p1, p3 - p1)
    n2 = np.cross(p3 - p1, p4 - p1)
    return n1 + n2  # 面積×法線


def _area_normal_of_tri(
    p1: NDArray[np.floating], p2: NDArray[np.floating], p3: NDArray[np.floating]
) -> NDArray[np.floating]:
    """三角形の面積×法線ベクトル（向き付き）を返す"""
    return np.cross(p2 - p1, p3 - p1)  # 2*Area * n


def _area_normal_of_quad(
    p1: NDArray[np.floating],
    p2: NDArray[np.floating],
    p3: NDArray[np.floating],
    p4: NDArray[np.floating],
) -> NDArray[np.floating]:
    """四角形を2つの三角形に分解し、面積×法線ベクトルを合成"""
    n1 = np.cross(p2 - p1, p3 - p1)
    n2 = np.cross(p3 - p1, p4 - p1)
    return n1 + n2  # 面積×法線（のはずだが、絶対値スケールは後で正規化するので実質方向だけ重要）


def _compute_node_normals(
    elements_data: NDArray[np.int32],
    labels: NDArray[np.int32],
    xyz: NDArray[np.float64],
) -> NDArray[np.float32]:
    """TRI3/QUAD4 面要素から節点法線を計算する。

    elements_data:
        - (Ne, 4): [eid, n1, n2, n3]  … TRI3
        - (Ne, 5): [eid, n1, n2, n3, n4] … QUAD4

    labels:
        node_coord_arr["label"] 相当の節点ラベル配列

    xyz:
        shape (Nnode, 3) の節点座標配列
    """
    id2idx = {int(lbl): i for i, lbl in enumerate(labels)}
    accum = np.zeros((len(labels), 3), dtype=np.float64)

    assert elements_data.ndim == 2, "elements_data must be 2D"
    ncol = elements_data.shape[1]
    assert ncol in (4, 5), "elements_data must be shape (Ne,4) or (Ne,5)"

    if ncol == 5:
        # --- QUAD4 のみ ---
        for row in elements_data:
            _, n1, n2, n3, n4 = map(int, row)
            p1, p2, p3, p4 = (xyz[id2idx[n]] for n in (n1, n2, n3, n4))
            an = _area_normal_of_quad(p1, p2, p3, p4)
            for nid in (n1, n2, n3, n4):
                accum[id2idx[nid]] += an

    else:
        # --- TRI3 のみ ---
        for row in elements_data:
            _, n1, n2, n3 = map(int, row)
            p1, p2, p3 = (xyz[id2idx[n]] for n in (n1, n2, n3))
            an = _area_normal_of_tri(p1, p2, p3)
            for nid in (n1, n2, n3):
                accum[id2idx[nid]] += an

    # 各節点のベクトルを正規化
    norms = np.linalg.norm(accum, axis=1)
    nz = norms > 0
    accum[nz] = (accum[nz].T / norms[nz]).T
    # 孤立点など、法線が定義できない節点はとりあえず +Z
    accum[~nz] = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    return accum.astype(np.float32)


def extrude_quads_to_hex_centered_delta(
    elements_data: NDArray[np.int32],  # (Ne,4 or 5): [eid, n1, n2, n3(,n4)]
    node_coord_array: NDArray[node_coord_array_dtype],  # structured
    thickness: float,  # 全体厚み
    *,
    flip_normals: bool = False,
    start_hex_label: int | None = None,
    next_node_label: int | None = None,
    reuse_maps: dict | None = None,
) -> tuple[
    NDArray[node_coord_array_dtype],  # new_nodes_delta（新規節点のみ）
    NDArray[np.int32],  # new_elements_solid (HEX8またはWED6)
    int,  # next_node_label（更新後）
    dict,  # reuse_maps（更新後）
]:
    """
    中面±(thickness/2) 押し出しで 2D 要素から 3D 要素を生成する。

    - 4節点要素: QUAD4 → HEX8
      elements_data.shape == (Ne, 5)  [eid, n1, n2, n3, n4]
    - 3節点要素: TRI3  → WED6 (プリズム)
      elements_data.shape == (Ne, 4)  [eid, n1, n2, n3]

    返す節点は“新規に作られたものだけ”（差分）。元節点は返さない。

    reuse_maps: { "minus": {orig -> new_minus}, "plus": {orig -> new_plus} }
      同じ元節点からの新節点をセット横断で再利用するために持ち回りする。
    """

    elems = np.asarray(elements_data, dtype=np.int32)
    assert elems.ndim == 2, "elements_data must be 2D"
    assert elems.shape[1] in (4, 5), "elements_data must be shape (Ne,4) or (Ne,5)"

    node_coord_arr = np.asarray(node_coord_array)
    assert node_coord_arr.dtype == node_coord_array_dtype, "node_coord_array dtype mismatch"
    assert thickness is not None and thickness > 0.0, "thickness must be positive"

    labels = node_coord_arr["label"].astype(np.int32, copy=False)
    xyz = np.column_stack([node_coord_arr["x"], node_coord_arr["y"], node_coord_arr["z"]]).astype(np.float64)

    # --- 法線計算 ---
    # _compute_node_normals は QUAD/TRI 混在でも elems[:,1:] から読み取れればOKな前提
    node_normals = _compute_node_normals(elems, labels, xyz).astype(np.float64)
    if flip_normals:
        node_normals *= -1.0

    # --- 対象ノード集合 ---
    used_node_set = set(int(n) for n in np.unique(elems[:, 1:].ravel()))
    id2idx = {int(lbl): i for i, lbl in enumerate(labels)}

    # --- 再利用マップの準備 ---
    if reuse_maps is None:
        reuse_maps = {"minus": {}, "plus": {}}
    minus_map: dict[int, int] = reuse_maps.get("minus", {})
    plus_map: dict[int, int] = reuse_maps.get("plus", {})

    # --- 次の採番 ---
    if next_node_label is None:
        next_node_label = int(labels.max()) + 1

    # --- 新規節点生成（必要な分だけ） ---
    h2 = 0.5 * float(thickness)
    new_nodes_buf: list[tuple[int, float, float, float]] = []  # (label, x, y, z)

    for orig in used_node_set:
        idx = id2idx[orig]
        p = xyz[idx]
        n = node_normals[idx]

        # 下側
        if orig not in minus_map:
            minus_id = next_node_label
            next_node_label += 1
            pm = p - h2 * n
            minus_map[orig] = minus_id
            new_nodes_buf.append((minus_id, pm[0], pm[1], pm[2]))

        # 上側
        if orig not in plus_map:
            plus_id = next_node_label
            next_node_label += 1
            pp = p + h2 * n
            plus_map[orig] = plus_id
            new_nodes_buf.append((plus_id, pp[0], pp[1], pp[2]))

    # --- 差分ノードを structured へ ---
    if new_nodes_buf:
        new_nodes_delta = np.array(new_nodes_buf, dtype=node_coord_array_dtype)
    else:
        new_nodes_delta = np.zeros(0, dtype=node_coord_array_dtype)

    # --- 3D要素生成 ---
    # start_hex_label は HEX/WED 共通の「3D要素開始ラベル」として扱う
    if start_hex_label is None:
        start_hex_label = int(elems[:, 0].max()) + 1

    hex_rows: list[list[int]] = []
    ncol = elems.shape[1]

    for k, row in enumerate(elems):
        if ncol == 5:
            # QUAD4 → HEX8
            _, n1, n2, n3, n4 = map(int, row)
            n1m, n2m, n3m, n4m = (minus_map[n] for n in (n1, n2, n3, n4))
            n1p, n2p, n3p, n4p = (plus_map[n] for n in (n1, n2, n3, n4))
            # Abaqus C3D8 互換: 1-2-3-4(下), 5-6-7-8(上) のイメージ
            hex_rows.append(
                [
                    start_hex_label + k,
                    n1m,
                    n2m,
                    n3m,
                    n4m,
                    n1p,
                    n2p,
                    n3p,
                    n4p,
                ]
            )
        else:
            # TRI3 → WED6 (プリズム)
            _, n1, n2, n3 = map(int, row)
            n1m, n2m, n3m = (minus_map[n] for n in (n1, n2, n3))
            n1p, n2p, n3p = (plus_map[n] for n in (n1, n2, n3))
            # Abaqus C3D6 互換: 1-2-3(下), 4-5-6(上) のイメージ
            hex_rows.append(
                [
                    start_hex_label + k,
                    n1m,
                    n2m,
                    n3m,
                    n1p,
                    n2p,
                    n3p,
                ]
            )

    new_elements_solid = np.array(hex_rows, dtype=np.int32)

    # 更新したマップを戻す
    reuse_maps = {"minus": minus_map, "plus": plus_map}
    return new_nodes_delta, new_elements_solid, next_node_label, reuse_maps


def make_quarter_cylinder_shell(
    node_coord_arr: NDArray,
    R: float,
) -> NDArray:
    """平面シェルメッシュを1/4円筒表面シェルに写像する.

    前提:
        - node_coord_arr[:, 0] が node label (int相当)
        - node_coord_arr[:, 1:4] が (x, y, z)
        - x >= 0, y >= 0 で、atan2(y, x) が [0, pi/2] に入る想定
        - 元の半径 r = sqrt(x^2 + y^2) は無視し、角度 θ だけ利用して
          半径 R の円筒表面へ投影する。

    Args:
        node_coord_arr: (n_node, 4) [label, x, y, z]
        R: 円筒の半径

    Returns:
        cyl_node_coord_arr: (n_node, 4) [label, x, y, z] (1/4円筒表面)
    """
    cyl_node_coord_arr = node_coord_arr.copy()

    labels = node_coord_arr[:, 0]
    xyz = node_coord_arr[:, 1:4]
    x = xyz[:, 0]
    y = xyz[:, 1]
    z = xyz[:, 2]

    r = np.hypot(x, y)

    # r=0 で atan2 が意味を失うので、雑に θ=0 に潰しておく
    # （原点ノードがある場合はここをいい感じに決める余地あり）
    theta = np.where(r > 0.0, np.arctan2(y, x), 0.0)

    # 念のため [0, π/2] にクリップ
    theta = np.clip(theta, 0.0, 0.5 * np.pi)

    x_new = R * np.cos(theta)
    y_new = R * np.sin(theta)
    z_new = z  # z はそのまま

    cyl_node_coord_arr[:, 0] = labels
    cyl_node_coord_arr[:, 1] = x_new
    cyl_node_coord_arr[:, 2] = y_new
    cyl_node_coord_arr[:, 3] = z_new

    return cyl_node_coord_arr
