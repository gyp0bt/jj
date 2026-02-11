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
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _safe_import_pymesh():
    """pymeshを安全にimportする

    modules.pymesh として配置されたローカルパッケージを参照する。
    システムの pymesh との競合を回避するため絶対パスインポートは使わない。
    """
    try:
        from modules.pymesh.mesh import Mesher
        from modules.pymesh.mesh import mesher as create_mesher
        from modules.pymesh.misc.quality import get_element_quality

        return create_mesher, get_element_quality
    except ImportError:
        return None, None


def extract_mesh_stats(
    inp_path: Path,
    verbose: bool = False,
    cached_abq_data: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
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
        mesh = create_mesher(
            str(inp_path), verbose=verbose, cached_abq_data=cached_abq_data
        )
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
        for key in mesh.elements_data:
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
        for name in mesh.elset_data:
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


def _compute_quality_stats(mesh, get_element_quality) -> Optional[dict[str, Any]]:
    """メッシュ品質統計を計算

    Args:
        mesh: Mesherインスタンス
        get_element_quality: 品質計算関数

    Returns:
        品質統計の辞書。計算不可の場合はNone。
    """
    if get_element_quality is None:
        return None

    try:
        coord_array = mesh.get_element_node_coord_array()
    except Exception as e:
        logger.debug(f"get_element_node_coord_array failed: {e}")
        return None

    if coord_array is None or len(coord_array) == 0:
        logger.debug("coord_array is None or empty, skipping quality computation")
        return None

    logger.debug(
        f"coord_array shape: {coord_array.shape if hasattr(coord_array, 'shape') else len(coord_array)}"
    )

    quality_result: dict[str, Any] = {}
    modes = ["volume", "detJ", "aspect", "skewness"]

    try:
        quality = get_element_quality(coord_array, mode=modes)
    except Exception as e:
        # 全モードでの計算が失敗した場合、個別に試す
        logger.debug(f"Batch quality computation failed: {e}, trying individual modes")
        quality = {}
        for mode in modes:
            try:
                q = get_element_quality(coord_array, mode=[mode])
                quality.update(q)
            except Exception as e2:
                logger.debug(f"Quality mode '{mode}' failed: {e2}")

    metric_name_map = {
        "volume": "volume",
        "detJ": "detJ",
        "aspect": "aspect_ratio",
        "skewness": "skewness",
    }

    for mode_key, display_name in metric_name_map.items():
        if mode_key in quality:
            arr = quality[mode_key]
            if isinstance(arr, np.ndarray) and len(arr) > 0:
                # NaNを除外して統計計算
                valid = arr[~np.isnan(arr)]
                if len(valid) > 0:
                    quality_result[display_name] = {
                        "min": float(np.min(valid)),
                        "max": float(np.max(valid)),
                        "mean": float(np.mean(valid)),
                    }

    return quality_result if quality_result else None


def extract_elset_quality_stats(
    inp_path: Path,
    verbose: bool = False,
    cached_abq_data: Optional[Any] = None,
) -> Optional[dict[str, dict[str, Any]]]:
    """Elsetごとのメッシュ品質統計を抽出

    各Elsetに属する要素のみを対象として品質メトリクスを計算する。

    Args:
        inp_path: .inpファイルのパス
        verbose: 詳細ログを出力するか
        cached_abq_data: キャッシュ済みABQData

    Returns:
        {Elset名: {element_count: int, quality: {...}}} の辞書。
        pymesh未導入やパース失敗時はNone。
    """
    create_mesher, get_element_quality = _safe_import_pymesh()
    if create_mesher is None:
        logger.debug("pymesh not available, skipping elset quality stats")
        return None

    if not inp_path.exists() or not str(inp_path).lower().endswith(".inp"):
        return None

    try:
        mesh = create_mesher(
            str(inp_path), verbose=verbose, cached_abq_data=cached_abq_data
        )
    except Exception as e:
        logger.warning(f"pymesh failed to parse {inp_path}: {e}")
        return None

    if get_element_quality is None:
        return None

    # 全要素の座標配列を取得
    try:
        coord_array = mesh.get_element_node_coord_array()
    except Exception as e:
        logger.debug(f"get_element_node_coord_array failed: {e}")
        return None

    if coord_array is None or len(coord_array) == 0:
        return None

    # 全要素のラベルリスト（座標配列と同じ順序）
    try:
        all_labels = list(mesh.get_element_labels())
    except Exception:
        return None

    if len(all_labels) != len(coord_array):
        logger.debug(
            f"Label count ({len(all_labels)}) != coord_array count ({len(coord_array)})"
        )
        return None

    # label → index のマッピング
    label_to_idx: dict[int, int] = {}
    for i, lbl in enumerate(all_labels):
        label_to_idx[int(lbl)] = i

    # 全要素の品質を一括計算
    modes = ["volume", "detJ", "aspect", "skewness"]
    try:
        quality = get_element_quality(coord_array, mode=modes)
    except Exception:
        quality = {}
        for mode in modes:
            try:
                q = get_element_quality(coord_array, mode=[mode])
                quality.update(q)
            except Exception:
                pass

    if not quality:
        return None

    metric_name_map = {
        "volume": "volume",
        "detJ": "detJ",
        "aspect": "aspect_ratio",
        "skewness": "skewness",
    }

    result: dict[str, dict[str, Any]] = {}

    for name in mesh.elset_data:
        elset = mesh.elset_data[name]
        elset_labels = elset.data if hasattr(elset, "data") else []
        if not elset_labels:
            continue

        # elset要素のインデックスを取得
        indices = []
        for lbl in elset_labels:
            idx = label_to_idx.get(int(lbl))
            if idx is not None:
                indices.append(idx)

        if not indices:
            result[name] = {"element_count": len(elset_labels)}
            continue

        elset_entry: dict[str, Any] = {"element_count": len(indices)}
        elset_quality: dict[str, Any] = {}

        for mode_key, display_name in metric_name_map.items():
            if mode_key not in quality:
                continue
            arr = quality[mode_key]
            if not isinstance(arr, np.ndarray) or len(arr) == 0:
                continue

            # elset要素のみ抽出
            subset = arr[indices]
            valid = subset[~np.isnan(subset)]
            if len(valid) > 0:
                elset_quality[display_name] = {
                    "min": float(np.min(valid)),
                    "max": float(np.max(valid)),
                    "mean": float(np.mean(valid)),
                }

        if elset_quality:
            elset_entry["quality"] = elset_quality
        result[name] = elset_entry

    return result if result else None


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
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    if key:
                        params[key] = value
    except (OSError, IOError):
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
                if norm.startswith("*solidsection") or norm.startswith("*shellsection"):
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
    except (OSError, IOError):
        pass

    return mapping
