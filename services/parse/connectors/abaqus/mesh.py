"""pymesh統合コネクタ: Abaqus用メッシュの統計情報をグラフノードに付与

pymeshのMesherクラスを使い、.inpファイルからメッシュ統計情報を抽出して
GraphModelのノードプロパティに付与する。

抽出する情報:
- 要素数、節点数
- 要素タイプ別の要素数
- メッシュ品質統計（ヤコビアン、アスペクト比、歪み度）
- 要素集合(Elset)ごとの要素数
- 材料割り当て関係

pymeshは重い処理のため、統合は任意。import失敗時はスキップする。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _safe_import_pymesh():
    """pymeshを安全にimportする

    modules.pymesh として配置されたローカルパッケージを参照する。
    システムの pymesh との競合を回避するため絶対パスインポートは使わない。
    """
    try:
        from modules.pymesh.mesh import mesher as create_mesher
        from modules.pymesh.misc.quality import get_element_quality

        return create_mesher, get_element_quality
    except ImportError:
        return None, None


def extract_mesh_stats(
    inp_path: Path,
    verbose: bool = False,
    cached_abq_data: Any | None = None,
) -> dict[str, Any] | None:
    """Abaqus .inpファイルからメッシュ統計情報を抽出

    pymeshのMesherクラスを使ってメッシュデータを解析し、
    統計情報を辞書形式で返す。

    Args:
        inp_path: .inpファイルのパス
        verbose: 詳細ログを出力するか
        cached_abq_data: キャッシュ済みABQData（指定時はread_inp()をスキップ）

    Returns:
        メッシュ統計情報の辞書。pymesh未導入やパース失敗時はNone。
        {
            "node_count": int,
            "element_count": int,
            "element_types": dict[str, int],  # タイプ名 → 要素数
            "elset_summary": dict[str, int],   # Elset名 → 要素数
            "quality": {                        # 品質統計（計算可能な場合）
                "volume": {"min": float, "max": float, "mean": float},
                "detJ": {"min": float, "max": float, "mean": float},
                "aspect_ratio": {"min": float, "max": float, "mean": float},
                "skewness": {"min": float, "max": float, "mean": float},
            }
        }
    """
    create_mesher, get_element_quality = _safe_import_pymesh()
    if create_mesher is None:
        logger.debug("pymesh not available, skipping mesh stats extraction")
        return None

    if not inp_path.exists() or not str(inp_path).lower().endswith(".inp"):
        return None

    try:
        mesh = create_mesher(str(inp_path), verbose=verbose, cached_abq_data=cached_abq_data)
    except Exception as e:
        logger.warning(f"pymesh failed to parse {inp_path}: {e}")
        return None

    stats: dict[str, Any] = {}

    # 節点数
    try:
        node_count = mesh.get_number_of_nodes()
        stats["node_count"] = int(node_count)
    except Exception:
        stats["node_count"] = 0

    # 要素数と要素タイプ別の集計
    try:
        all_labels = mesh.get_element_labels()
        stats["element_count"] = len(all_labels)

        # 要素タイプ別の集計
        element_types: dict[str, int] = {}
        for key in list(mesh.elements_data.keys()):
            elements = mesh.elements_data[key]
            # keyは "name,type=C3D8" のような形式
            elem_type = "unknown"
            if hasattr(elements, "options") and "type" in elements.options:
                elem_type = elements.options["type"]
            elif ",type=" in key:
                elem_type = key.split(",type=")[-1]
            count = len(elements.data) if hasattr(elements, "data") else 0
            if elem_type in element_types:
                element_types[elem_type] += count
            else:
                element_types[elem_type] = count
        stats["element_types"] = element_types
    except Exception as e:
        logger.debug(f"Element counting failed: {e}")
        stats["element_count"] = 0
        stats["element_types"] = {}

    # Elset要約
    try:
        elset_summary: dict[str, int] = {}
        for name in list(mesh.elset_data.keys()):
            elset = mesh.elset_data[name]
            count = len(elset.data) if hasattr(elset, "data") else 0
            elset_summary[name] = count
        stats["elset_summary"] = elset_summary
    except Exception as e:
        logger.debug(f"Elset summary failed: {e}")
        stats["elset_summary"] = {}

    # メッシュ品質統計
    try:
        quality_stats = _compute_quality_stats(mesh, get_element_quality)
        if quality_stats:
            stats["quality"] = quality_stats
    except Exception as e:
        logger.debug(f"Quality computation failed: {e}")

    return stats


def _compute_quality_for_coord_array(
    coord_array: np.ndarray,
    get_element_quality,
    modes: list[str],
) -> dict[str, np.ndarray]:
    """単一の座標配列に対して品質メトリクスを計算

    同一ノード数の要素群に対して品質計算を実行する。
    バッチ計算が失敗した場合は個別モードにフォールバック。

    Args:
        coord_array: (Ne, Nn, 3)形状の座標配列
        get_element_quality: 品質計算関数
        modes: 計算するモードのリスト

    Returns:
        {モード名: np.ndarray} の辞書
    """
    try:
        return get_element_quality(coord_array, mode=modes)
    except Exception as e:
        logger.debug(f"Batch quality computation failed: {e}, trying individual modes")
        quality: dict[str, np.ndarray] = {}
        for mode in modes:
            try:
                q = get_element_quality(coord_array, mode=[mode])
                quality.update(q)
            except Exception as e2:
                logger.debug(f"Quality mode '{mode}' failed: {e2}")
        return quality


def _compute_quality_stats(mesh, get_element_quality) -> dict[str, Any] | None:
    """メッシュ品質統計を計算

    要素タイプ（ノード数）別にグルーピングして品質を計算し、
    結果を集約する。これにより要素タイプ混在時でも品質計算が可能。

    Args:
        mesh: Mesherインスタンス
        get_element_quality: 品質計算関数

    Returns:
        品質統計の辞書。計算不可の場合はNone。
    """
    if get_element_quality is None:
        return None

    modes = ["volume", "detJ", "aspect", "skewness"]

    # 要素タイプ（ノード数）別にグルーピング
    try:
        element_array_dict = mesh.get_element_array_dict(mode="num_nodes")
    except Exception as e:
        logger.debug(f"get_element_array_dict failed: {e}")
        return None

    if not element_array_dict:
        logger.debug("No element data available, skipping quality computation")
        return None

    # 全ノード座標を取得
    try:
        node_coord = mesh.get_node_coord_with_elements()
    except Exception as e:
        logger.debug(f"get_node_coord_with_elements failed: {e}")
        return None

    # ノード数別に品質計算し、結果を集約
    aggregated: dict[str, list[np.ndarray]] = {}

    for num_nodes, element_array in element_array_dict.items():
        try:
            coord_array = mesh._get_element_node_coord_array(
                element_array=element_array,
                node_coord=node_coord,
            )
        except Exception as e:
            logger.debug(f"coord_array build failed for {num_nodes}-node elements: {e}")
            continue

        if coord_array is None or len(coord_array) == 0:
            continue

        logger.debug(f"Computing quality for {num_nodes}-node elements: shape={coord_array.shape}")

        quality = _compute_quality_for_coord_array(coord_array, get_element_quality, modes)
        for mode_key, arr in quality.items():
            if isinstance(arr, np.ndarray) and len(arr) > 0:
                if mode_key not in aggregated:
                    aggregated[mode_key] = []
                aggregated[mode_key].append(arr)

    if not aggregated:
        return None

    metric_name_map = {
        "volume": "volume",
        "detJ": "detJ",
        "aspect": "aspect_ratio",
        "skewness": "skewness",
    }

    quality_result: dict[str, Any] = {}
    for mode_key, display_name in metric_name_map.items():
        if mode_key in aggregated:
            merged = np.concatenate(aggregated[mode_key])
            valid = merged[~np.isnan(merged)]
            if len(valid) > 0:
                quality_result[display_name] = {
                    "min": float(np.min(valid)),
                    "max": float(np.max(valid)),
                    "mean": float(np.mean(valid)),
                }

    return quality_result if quality_result else None


def extract_element_quality_stats(
    inp_path: Path,
    verbose: bool = False,
    cached_abq_data: Any | None = None,
) -> dict[str, dict[str, Any]] | None:
    """*ELEMENTキーワードブロック（要素タイプ）ごとのメッシュ品質統計を抽出

    各*ELEMENTキーワードで定義された要素グループごとに品質メトリクスを計算する。
    キーは要素タイプ名（C3D8, C3D10等）。

    Args:
        inp_path: .inpファイルのパス
        verbose: 詳細ログを出力するか
        cached_abq_data: キャッシュ済みABQData

    Returns:
        {要素タイプ名: {element_count: int, quality: {...}}} の辞書。
        pymesh未導入やパース失敗時はNone。
    """
    create_mesher, get_element_quality = _safe_import_pymesh()
    if create_mesher is None:
        logger.debug("pymesh not available, skipping element quality stats")
        return None

    if not inp_path.exists() or not str(inp_path).lower().endswith(".inp"):
        return None

    try:
        mesh = create_mesher(str(inp_path), verbose=verbose, cached_abq_data=cached_abq_data)
    except Exception as e:
        logger.warning(f"pymesh failed to parse {inp_path}: {e}")
        return None

    if get_element_quality is None:
        return None

    modes = ["volume", "detJ", "aspect", "skewness"]

    # 要素タイプ（ノード数）別にグルーピング
    try:
        element_array_dict = mesh.get_element_array_dict(mode="num_nodes")
    except Exception as e:
        logger.debug(f"get_element_array_dict failed: {e}")
        return None

    if not element_array_dict:
        return None

    # 全ノード座標を取得
    try:
        node_coord = mesh.get_node_coord_with_elements()
    except Exception as e:
        logger.debug(f"get_node_coord_with_elements failed: {e}")
        return None

    # ノード数別に品質計算し、label → quality値のマッピングを構築
    label_quality: dict[str, dict[int, float]] = {}

    for num_nodes, element_array in element_array_dict.items():
        try:
            coord_array = mesh._get_element_node_coord_array(
                element_array=element_array,
                node_coord=node_coord,
            )
        except Exception as e:
            logger.debug(f"coord_array build failed for {num_nodes}-node elements: {e}")
            continue

        if coord_array is None or len(coord_array) == 0:
            continue

        quality = _compute_quality_for_coord_array(coord_array, get_element_quality, modes)

        labels = element_array[:, 0].tolist()
        for mode_key, arr in quality.items():
            if not isinstance(arr, np.ndarray) or len(arr) != len(labels):
                continue
            if mode_key not in label_quality:
                label_quality[mode_key] = {}
            for lbl, val in zip(labels, arr, strict=True):
                label_quality[mode_key][int(lbl)] = float(val)

    if not label_quality:
        return None

    metric_name_map = {
        "volume": "volume",
        "detJ": "detJ",
        "aspect": "aspect_ratio",
        "skewness": "skewness",
    }

    # *ELEMENTキーワードブロック（要素タイプ）ごとに品質を集計
    result: dict[str, dict[str, Any]] = {}

    for key in list(mesh.elements_data.keys()):
        elements = mesh.elements_data[key]
        # 要素タイプ名を取得
        elem_type = "unknown"
        if hasattr(elements, "options") and "type" in elements.options:
            elem_type = elements.options["type"]
        elif ",type=" in key:
            elem_type = key.split(",type=")[-1]

        elem_labels = elements.data if hasattr(elements, "data") else []
        if not hasattr(elem_labels, "__len__") or len(elem_labels) == 0:
            continue

        # ラベルリストを取得（elements.dataがarrayの場合は先頭列）
        if hasattr(elem_labels, "ndim") and elem_labels.ndim == 2:
            label_list = elem_labels[:, 0].tolist()
        else:
            label_list = list(elem_labels)

        elem_entry: dict[str, Any] = {"element_count": len(label_list)}
        elem_quality: dict[str, Any] = {}

        for mode_key, display_name in metric_name_map.items():
            if mode_key not in label_quality:
                continue
            mode_map = label_quality[mode_key]

            values = []
            for lbl in label_list:
                val = mode_map.get(int(lbl))
                if val is not None and not np.isnan(val):
                    values.append(val)

            if values:
                arr = np.array(values)
                elem_quality[display_name] = {
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "mean": float(np.mean(arr)),
                }

        if elem_quality:
            elem_entry["quality"] = elem_quality

        # 同じ要素タイプが複数の*ELEMENTブロックに分散している場合はマージ
        if elem_type in result:
            existing = result[elem_type]
            existing["element_count"] += elem_entry["element_count"]
            if "quality" in elem_entry and "quality" not in existing:
                existing["quality"] = elem_entry["quality"]
        else:
            result[elem_type] = elem_entry

    return result if result else None


def extract_mesh_topology_groups(
    inp_path: Path,
    verbose: bool = False,
    cached_abq_data: Any | None = None,
) -> list[list[str]] | None:
    """メッシュトポロジーを解析し、ノード共有で接続された要素集団を抽出

    要素間のノード共有関係をUnion-Findで解析し、連結成分（メッシュ整合集団）を
    特定する。各集団に属するelset名をリストにまとめて返す。

    Args:
        inp_path: .inpファイルのパス
        verbose: 詳細ログを出力するか
        cached_abq_data: キャッシュ済みABQData

    Returns:
        [[elset_a, elset_b], [elset_c]] のようなelsetグループのリスト。
        各グループ内のelsetは同じメッシュ整合集団に属する。
        pymesh未導入やパース失敗時はNone。
    """
    create_mesher, _ = _safe_import_pymesh()
    if create_mesher is None:
        logger.debug("pymesh not available, skipping mesh topology analysis")
        return None

    if not inp_path.exists() or not str(inp_path).lower().endswith(".inp"):
        return None

    try:
        mesh = create_mesher(str(inp_path), verbose=verbose, cached_abq_data=cached_abq_data)
    except Exception as e:
        logger.warning(f"pymesh failed to parse {inp_path}: {e}")
        return None

    # elsetが無ければスキップ
    if not mesh.elset_data or len(mesh.elset_data) == 0:
        return None

    # Union-Find実装
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])  # path compression
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # 要素のノード接続情報からUnion-Findを構築
    # node_id → 最初のelement_labelのマッピング
    node_to_first_elem: dict[int, int] = {}

    for key in list(mesh.elements_data.keys()):
        elements = mesh.elements_data[key]
        if not hasattr(elements, "data") or elements.data is None:
            continue
        data = elements.data
        if not hasattr(data, "ndim") or data.ndim != 2:
            continue

        for row in data:
            elem_label = int(row[0])
            parent.setdefault(elem_label, elem_label)
            # ノードIDは列1以降
            for node_id in row[1:]:
                nid = int(node_id)
                if nid == 0:
                    continue  # パディングされたゼロをスキップ
                if nid in node_to_first_elem:
                    union(elem_label, node_to_first_elem[nid])
                else:
                    node_to_first_elem[nid] = elem_label

    # 各要素のグループIDを確定
    elem_to_group: dict[int, int] = {}
    for elem_label in parent:
        elem_to_group[elem_label] = find(elem_label)

    # 各elsetがどのグループに属するかを判定
    # elset内の要素が複数グループにまたがる場合は最初のグループに帰属
    elset_group: dict[str, int] = {}
    for name in list(mesh.elset_data.keys()):
        elset = mesh.elset_data[name]
        elset_labels = elset.data if hasattr(elset, "data") else []
        if not hasattr(elset_labels, "__len__") or len(elset_labels) == 0:
            continue
        # elsetの最初の要素のグループIDを使用
        for lbl in elset_labels:
            gid = elem_to_group.get(int(lbl))
            if gid is not None:
                elset_group[name] = gid
                break

    if not elset_group:
        return None

    # グループIDごとにelset名を集約
    from collections import defaultdict

    group_elsets: dict[int, list[str]] = defaultdict(list)
    for name, gid in elset_group.items():
        group_elsets[gid].append(name)

    # ソートして返す
    result = [sorted(elsets) for elsets in group_elsets.values()]
    return sorted(result, key=lambda x: x[0]) if result else None


def _parse_parameters(inp_path: Path) -> dict[str, str]:
    """*PARAMETERブロックからパラメータ名→値のマッピングを抽出

    Abaqusの*PARAMETERブロック内の代入文を解析する。
    文字列値（"..."で囲まれた値）はクォートを除去して返す。

    Args:
        inp_path: .inpファイルのパス

    Returns:
        {パラメータ名: 値} のマッピング
    """
    params: dict[str, str] = {}
    if not inp_path.exists():
        return params

    in_parameter_block = False
    try:
        with inp_path.open("r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("**"):
                    continue

                norm = line.lower().replace(" ", "")
                if norm.startswith("*parameter"):
                    in_parameter_block = True
                    continue

                if line.startswith("*") and in_parameter_block:
                    in_parameter_block = False

                if in_parameter_block and "=" in line:
                    # 数式を含む場合は最初の=のみ分割
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # 文字列値のクォート除去
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]
                    if key:
                        params[key] = value
    except OSError:
        pass

    return params


def _resolve_parameter_ref(value: str, params: dict[str, str]) -> str:
    """<param_name>形式のパラメータ参照を解決する

    Args:
        value: 解決対象の値（例: "<material>"）
        params: パラメータマッピング

    Returns:
        解決後の値。参照でない場合はそのまま返す。
    """
    if value.startswith("<") and value.endswith(">"):
        param_name = value[1:-1]
        return params.get(param_name, value)
    return value


def extract_material_elset_mapping(inp_path: Path) -> dict[str, list[str]]:
    """材料名とElsetの対応関係を抽出

    *SOLID SECTION等で定義される材料→Elset割り当てを抽出する。
    *PARAMETERブロックのパラメータ参照（<param_name>形式）も解決する。
    pymeshを使わない軽量パーサー。

    Args:
        inp_path: .inpファイルのパス

    Returns:
        {材料名: [割り当てElset名のリスト]}
    """
    if not inp_path.exists():
        return {}

    # *PARAMETERブロックからパラメータを事前に解析
    params = _parse_parameters(inp_path)

    mapping: dict[str, list[str]] = {}

    try:
        with inp_path.open("r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("**"):
                    continue

                norm = line.lower().replace(" ", "")
                # *SOLID SECTION, *SHELL SECTION等
                if (
                    norm.startswith("*solidsection")
                    or norm.startswith("*shellsection")
                    or norm.startswith("*beamsection")
                ):
                    # 元のケースを保持するため、空白除去のみの行からも値を取得
                    orig_no_space = line.replace(" ", "")
                    orig_tokens = [s.strip() for s in orig_no_space.split(",") if s.strip()]
                    material_name = ""
                    elset_name = ""
                    for tok in orig_tokens:
                        tok_lower = tok.lower()
                        if tok_lower.startswith("material="):
                            raw_name = tok.split("=", 1)[1]
                            material_name = _resolve_parameter_ref(raw_name, params)
                        elif tok_lower.startswith("elset="):
                            elset_name = tok.split("=", 1)[1]
                    if material_name:
                        if material_name not in mapping:
                            mapping[material_name] = []
                        if elset_name:
                            mapping[material_name].append(elset_name)
    except OSError:
        pass

    return mapping
