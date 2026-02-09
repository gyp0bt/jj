from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from .. import Mesher
from ..etypes import element_type_dict, ElementTypeGroup


def detect_one_layer_solids(mesh: Mesher) -> dict[str, Any]:
    """ソリッド要素の「厚さ1層」候補を検知する.

    PCAは使わず、
        * 外表面 (boundary faces) に属するノード → boundary_nodes
        * 要素の全節点 ⊂ boundary_nodes なら 1層候補
    というトポロジだけの判定を行う。

    対応形状:
        * wedge: 6節点 (C3D6 等)
        * hex:  8節点 (C3D8 系)

    Returns:
        dict:
            {
              "wedge": {...},
              "hex":   {...},
            }
        ratio はその形状全体に対する割合 (0.0〜1.0)。
    """
    # --- 要素タイプ別にノード列を保持 & 面(3節点/4節点)→要素 を集計 ---
    face_map_3: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    face_map_4: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)

    wedge_elems: list[tuple[int, list[int]]] = []
    hex_elems: list[tuple[int, list[int]]] = []

    for elements in mesh.elements_data.values():
        etype_name = elements.options.get("type")
        if not etype_name:
            continue

        info = element_type_dict.get(etype_name.upper())
        if info is None:
            continue

        _, group, num_nodes = info
        if group is not ElementTypeGroup.solid:
            # ソリッド以外は1層厚判定の対象外
            continue

        data = elements.data
        if data.size == 0:
            continue

        for row in data:
            label = int(row[0])
            nodes = [int(x) for x in row[1:] if int(x) != 0]

            if num_nodes == 6:
                # ---- WEDGE / PRISM ----
                wedge_elems.append((label, nodes))
                # 三角面2枚
                tri_faces = [
                    (nodes[0], nodes[1], nodes[2]),
                    (nodes[3], nodes[4], nodes[5]),
                ]
                # 四角面3枚
                quad_faces = [
                    (nodes[0], nodes[1], nodes[4], nodes[3]),
                    (nodes[1], nodes[2], nodes[5], nodes[4]),
                    (nodes[2], nodes[0], nodes[3], nodes[5]),
                ]
                for f in tri_faces:
                    face_map_3[tuple(sorted(f))].append(label)
                for f in quad_faces:
                    face_map_4[tuple(sorted(f))].append(label)

            elif num_nodes == 8:
                # ---- HEX ----
                hex_elems.append((label, nodes))
                faces = [
                    (nodes[0], nodes[1], nodes[2], nodes[3]),
                    (nodes[4], nodes[5], nodes[6], nodes[7]),
                    (nodes[0], nodes[1], nodes[5], nodes[4]),
                    (nodes[1], nodes[2], nodes[6], nodes[5]),
                    (nodes[2], nodes[3], nodes[7], nodes[6]),
                    (nodes[3], nodes[0], nodes[4], nodes[7]),
                ]
                for f in faces:
                    face_map_4[tuple(sorted(f))].append(label)

            else:
                # C3D10, C3D15 等は必要なら後で拡張
                continue

    # --- 1: boundary face に属するノード集合を作る ---
    boundary_nodes: set[int] = set()

    for face, elems in face_map_3.items():
        if len(elems) == 1:  # 外表面三角面
            boundary_nodes.update(face)

    for face, elems in face_map_4.items():
        if len(elems) == 1:  # 外表面四角面
            boundary_nodes.update(face)

    # --- 2: 「全節点が boundary_nodes に含まれる」要素を 1層候補とみなす ---

    def select_one_layer(elems: list[tuple[int, list[int]]]) -> list[int]:
        labels: list[int] = []
        for label, nodes in elems:
            if all((n in boundary_nodes) for n in nodes):
                labels.append(label)
        return labels

    wedge_one = select_one_layer(wedge_elems)
    hex_one = select_one_layer(hex_elems)

    def pack(elems: list[tuple[int, list[int]]], one: list[int]) -> dict[str, Any]:
        total = len(elems)
        count = len(one)
        ratio = float(count) / float(total) if total > 0 else 0.0
        return {"labels": sorted(one), "count": count, "ratio": ratio}

    return {
        "wedge": pack(wedge_elems, wedge_one),
        "hex": pack(hex_elems, hex_one),
    }


def detect_one_layer_tetra_by_groups(
    mesh: Mesher,
    angle_deg_threshold: float = 85.0,
) -> dict[str, Any]:
    """テトラ要素の「厚さ1層」候補を検知する.

    アルゴリズム概要:
        1) solid かつ節点数4の要素だけを抽出 (C3D4 系)
        2) 各tetの4面から face_key(3節点)→[(tet_idx, local_face_id)] を作る
        3) len(list)==1 の面を「外表面」とみなす
        4) 外表面同士で
               - 1辺(節点2個)を共有
               - 法線同士の角度 <= angle_deg_threshold
           を満たすものをグラフで連結し、連結成分ごとに面グループを作る
        5) 各グループの代表法線 = グループ内面法線の平均を正規化
        6) 各tetについて:
               - 自分の外表面が属するグループ集合 G を求める
               - G 内の任意の2グループ (g1, g2) について
                     n_g1・n_g2 < 0 なら
                 そのtetを「厚さ1層」候補と判定

    Args:
        mesh: Mesher インスタンス
        angle_deg_threshold: 接続角度の閾値 [deg]。
            例: 85 → 法線のなす角が 85° 以下なら同一グループとみなす。

    Returns:
        dict[str, Any]: 結果
            {
                "labels": [1層候補tetラベル...],
                "count":  int,
                "ratio":  float (1層候補数 / tet総数),
            }
    """
    # ---------------------------
    # 1) tet 抽出 と face_map 構築
    # ---------------------------
    tet_elems: list[tuple[int, list[int]]] = []  # (label, [n1,n2,n3,n4])
    face_map: dict[tuple[int, int, int], list[tuple[int, int]]] = defaultdict(list)
    # face_key -> [(tet_idx, local_face_id), ...]

    for elements in mesh.elements_data.values():
        etype = elements.options.get("type")
        if not etype:
            continue

        info = element_type_dict.get(etype.upper())
        if info is None:
            continue

        _, group, num_nodes = info
        if group is not ElementTypeGroup.solid:
            continue
        if num_nodes != 4:
            # テトラ専用
            continue

        data = elements.data
        if data.size == 0:
            continue

        for row in data:
            label = int(row[0])
            nodes = [int(x) for x in row[1:] if int(x) != 0]
            if len(nodes) != 4:
                continue

            tet_idx = len(tet_elems)
            tet_elems.append((label, nodes))

            # local faces (0..3)
            faces = [
                (nodes[0], nodes[1], nodes[2]),
                (nodes[0], nodes[1], nodes[3]),
                (nodes[1], nodes[2], nodes[3]),
                (nodes[0], nodes[2], nodes[3]),
            ]
            for local_id, f in enumerate(faces):
                key = tuple(sorted(f))
                face_map[key].append((tet_idx, local_id))

    if not tet_elems:
        return {"labels": [], "count": 0, "ratio": 0.0}

    # ノード座標
    node_arr = mesh.get_node_coord_array()
    xyz = np.stack(
        [
            node_arr["x"].astype(float),
            node_arr["y"].astype(float),
            node_arr["z"].astype(float),
        ],
        axis=1,
    )
    label2idx = {int(lbl): i for i, lbl in enumerate(node_arr["label"])}

    # ---------------------------
    # 2) 外表面(境界面)一覧 & 法線ベクトル
    # ---------------------------
    boundary_faces: list[dict[str, Any]] = []
    # id -> {'nodes': (n1,n2,n3), 'tet_idx': int, 'local_face': int, 'normal': np.ndarray}
    tetface_to_faceid: dict[tuple[int, int], int] = {}

    for key, owners in face_map.items():
        if len(owners) != 1:
            # 共有面 = 内部面 → 外表面ではない
            continue
        tet_idx, local_face = owners[0]
        _, tet_nodes = tet_elems[tet_idx]

        # local_face に応じて元の順番の節点3つを取る
        if local_face == 0:
            fnodes = (tet_nodes[0], tet_nodes[1], tet_nodes[2])
        elif local_face == 1:
            fnodes = (tet_nodes[0], tet_nodes[1], tet_nodes[3])
        elif local_face == 2:
            fnodes = (tet_nodes[1], tet_nodes[2], tet_nodes[3])
        else:  # 3
            fnodes = (tet_nodes[0], tet_nodes[2], tet_nodes[3])

        try:
            p0 = xyz[label2idx[fnodes[0]]]
            p1 = xyz[label2idx[fnodes[1]]]
            p2 = xyz[label2idx[fnodes[2]]]
        except KeyError:
            continue

        # 法線（長さは任意。あとで正規化）
        n = np.cross(p1 - p0, p2 - p0)
        norm = np.linalg.norm(n)
        if norm < 1.0e-12:
            continue
        n /= norm

        face_id = len(boundary_faces)
        boundary_faces.append(
            {
                "nodes": fnodes,
                "tet_idx": tet_idx,
                "local_face": local_face,
                "normal": n,
            }
        )
        tetface_to_faceid[(tet_idx, local_face)] = face_id

    if not boundary_faces:
        return {"labels": [], "count": 0, "ratio": 0.0}

    n_faces = len(boundary_faces)

    # ---------------------------
    # 3) 外表面同士の隣接関係 (edge共有) を構築
    # ---------------------------
    edge_map: dict[tuple[int, int], list[int]] = defaultdict(list)
    for fid, f in enumerate(boundary_faces):
        n1, n2, n3 = f["nodes"]
        edges = [
            (min(n1, n2), max(n1, n2)),
            (min(n2, n3), max(n2, n3)),
            (min(n3, n1), max(n3, n1)),
        ]
        for e in edges:
            edge_map[e].append(fid)

    # ---------------------------
    # 4) 接続角度<=threshold の隣接面でグラフ連結 → グループ化
    # ---------------------------
    cos_thr = float(np.cos(np.deg2rad(angle_deg_threshold)))
    normals = [f["normal"] for f in boundary_faces]

    face_group = [-1] * n_faces
    groups: list[list[int]] = []

    for fid in range(n_faces):
        if face_group[fid] != -1:
            continue

        gid = len(groups)
        groups.append([])
        queue = [fid]
        face_group[fid] = gid

        while queue:
            cur = queue.pop()
            groups[gid].append(cur)

            n1 = normals[cur]

            # cur に接続する候補 = 共有エッジを持つ面
            n_a, n_b, n_c = boundary_faces[cur]["nodes"]
            edges = [
                (min(n_a, n_b), max(n_a, n_b)),
                (min(n_b, n_c), max(n_b, n_c)),
                (min(n_c, n_a), max(n_c, n_a)),
            ]
            neighbor_faces: set[int] = set()
            for e in edges:
                neighbor_faces.update(edge_map[e])

            for nb in neighbor_faces:
                if nb == cur or face_group[nb] != -1:
                    continue
                n2 = normals[nb]
                cosang = float(np.dot(n1, n2))
                if cosang >= cos_thr:
                    face_group[nb] = gid
                    queue.append(nb)

    # ---------------------------
    # 5) グループ代表法線
    # ---------------------------
    group_normals: list[np.ndarray] = []
    for fids in groups:
        v = np.zeros(3, dtype=float)
        for fid in fids:
            v += normals[fid]
        norm = np.linalg.norm(v)
        if norm < 1.0e-12:
            group_normals.append(np.array([0.0, 0.0, 0.0]))
        else:
            group_normals.append(v / norm)

    # ---------------------------
    # 6) 各tetが「反対向きグループ」にまたがっているか判定
    # ---------------------------
    one_layer_labels: set[int] = set()

    for tet_idx, (label, nodes) in enumerate(tet_elems):
        # このtetの外表面が属するグループ一覧
        gset: set[int] = set()
        for local_face in range(4):
            key = (tet_idx, local_face)
            fid = tetface_to_faceid.get(key)
            if fid is None:
                continue
            gid = face_group[fid]
            if gid >= 0:
                gset.add(gid)

        if len(gset) < 2:
            continue

        g_list = list(gset)
        found = False
        for i in range(len(g_list)):
            gi = g_list[i]
            ni = group_normals[gi]
            for j in range(i + 1, len(g_list)):
                gj = g_list[j]
                nj = group_normals[gj]
                if np.dot(ni, nj) < 0.0:
                    found = True
                    break
            if found:
                break

        if found:
            one_layer_labels.add(label)

    labels = sorted(one_layer_labels)
    count = len(labels)
    ratio = float(count) / float(len(tet_elems)) if tet_elems else 0.0

    return {"labels": labels, "count": count, "ratio": ratio}
