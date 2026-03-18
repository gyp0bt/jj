"""ダッシュボード クエリ・フィルタ・ソートロジック

汎用のフィルタ/ソートロジックは services/query/ に昇格済み。
本モジュールはダッシュボード固有の関数（graph.yaml検知、
画像ギャラリーユーティリティ）を保持しつつ、
services/query からの再エクスポートにより後方互換性を維持する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ==================================================================
# services/query からの再エクスポート（後方互換）
# ==================================================================
from services.query.filters import (  # noqa: F401
    apply_chained_filters,
    apply_filters,
    apply_saved_view_filters,
    is_truthy,
    merge_filters,
    saved_view_filters_to_provider_filters,
)
from services.query.sort import (  # noqa: F401
    select_table_columns,
    sort_columns_by_vocab,
    sort_rows_by_index,
)
from services.query.transform import summarize_list_columns  # noqa: F401

# ====================================================================
# graph.yaml 検知ユーティリティ（dashboard固有）
# ====================================================================

_GRAPH_EXTENSIONS = ("yaml", "yml", "json")


def find_graph_path(project_root: Path) -> Path | None:
    """graph.yamlの実パスを検出

    Args:
        project_root: プロジェクトルート

    Returns:
        graph.yamlのパス。見つからない場合はNone。
    """
    storage_dir = project_root / ".j2" / "storage"
    for ext in _GRAPH_EXTENSIONS:
        p = storage_dir / f"graph.{ext}"
        if p.exists():
            return p
    return None


def get_graph_mtime(project_root: Path) -> float:
    """graph.yamlの更新時刻を取得

    Args:
        project_root: プロジェクトルート

    Returns:
        更新時刻（epoch秒）。ファイルが存在しない場合は0.0。
    """
    graph_path = find_graph_path(project_root)
    if graph_path is not None:
        return graph_path.stat().st_mtime
    return 0.0


# ====================================================================
# 画像ギャラリー ユーティリティ（dashboard固有）
# ====================================================================


def normalize_group_key(key: str) -> str:
    """グループキーを正規化（daily:日付:キー -> キー部分のみ）

    property_keyが "daily:2026-01-15:screenshot" の場合、
    グルーピング用に "screenshot" に正規化する。

    Args:
        key: 生のグループキー

    Returns:
        正規化されたキー
    """
    if key.startswith("daily:"):
        parts = key.split(":", 2)
        if len(parts) >= 3:
            return parts[2]
    return key


def filter_images_by_keys(
    images: list[dict[str, Any]],
    allowed_keys: list[str] | None = None,
    source: str = "output",
) -> list[dict[str, Any]]:
    """画像リストをキー名のリストでフィルタリングする

    allowed_keysが指定された場合、画像のresult_key（outputソース）
    またはproperty_key（propertyソース）がリストに含まれるもののみ返す。

    Args:
        images: 画像情報のリスト
        allowed_keys: 許可するキー名のリスト（Noneの場合はフィルタなし）
        source: "output" or "property"

    Returns:
        フィルタ済み画像リスト
    """
    if not allowed_keys:
        return images

    allowed_set = set(allowed_keys)
    result = []

    for img in images:
        if source == "output":
            # result_keyベースのフィルタ（パスから抽出）
            rk = _extract_result_key_from_path(img.get("image_path", ""))
            if (rk and rk in allowed_set) or (not rk and "(その他)" in allowed_set):
                result.append(img)
        elif source == "property":
            # property_keyベースのフィルタ
            pk = normalize_group_key(img.get("property_key", ""))
            if pk in allowed_set:
                result.append(img)

    return result


def collect_group_keys(images: list[dict[str, Any]], source: str) -> list[str]:
    """画像リストからグループ化に利用できるキーを収集

    Args:
        images: 画像情報のリスト
        source: "output" or "property"

    Returns:
        グループ化に利用可能なキーのリスト
    """
    keys: set[str] = set()
    for img in images:
        props = img.get("go_properties", {})
        for k in props:
            if k != "path":
                keys.add(k)
    result = sorted(keys)
    # outputソースの場合はresult_key（パスベース）でのグルーピングも追加
    if source == "output":
        # 画像パスからresult_keyが抽出可能か確認
        has_result_key = any(
            _extract_result_key_from_path(img.get("image_path", "")) for img in images
        )
        if has_result_key:
            result = ["result_key", *result]
    # propertyソースの場合はproperty_keyでのグルーピングも追加
    if source == "property":
        result = ["property_key", *result]
    return result


# ====================================================================
# 画像パスからのresult_key/プロパティ抽出
# ====================================================================

# パラメータトークンパターン（負の値対応・単位オプション）: vmax50.0, vmin-50.0, step0, t35mm
_PATH_PROP_PATTERN = re.compile(r"^([A-Za-z]+)(-?\d+(?:\.\d+)?)([A-Za-z]*)$")

# result_keyパターン（ダッシュ含む識別子）: S-S13, U-U3, PEEQ
_PATH_RESULT_KEY_PATTERN = re.compile(
    r"^[A-Z][A-Za-z0-9]*(?:-[A-Z][A-Za-z0-9]*(?:\d+)?)?$"
)


def _extract_result_key_from_path(path: str) -> str:
    """画像パスからresult_keyを抽出

    ファイル名からgo_basename部分を除去した残りのトークンから
    result_keyパターン（S-S13, U-U3等）にマッチする部分を抽出する。

    Args:
        path: 画像ファイルパス

    Returns:
        result_key文字列（抽出できない場合は空文字）
    """
    normalized = path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

    # 拡張子を除去
    if "." in filename:
        filename_no_ext = filename.rsplit(".", 1)[0]
    else:
        return ""

    # go_プレフィックスを持つbasenameの後のトークンを解析
    # go_で始まる部分の終端を探す（バージョン.vNを含む）
    tokens = filename_no_ext.split("_")

    # go_basenameの終端を特定（go_idx1.v3 等）
    start_idx = 0
    for i, token in enumerate(tokens):
        if i == 0 and token.lower().startswith("go"):
            start_idx = i + 1
            continue
        if i == start_idx and token.lower().startswith("idx"):
            start_idx = i + 1
            continue
        break

    # 残りのトークンからresult_keyを探す
    for token in tokens[start_idx:]:
        if _PATH_RESULT_KEY_PATTERN.fullmatch(
            token
        ) and not _PATH_PROP_PATTERN.fullmatch(token):
            return token

    return ""


def extract_path_metadata(path: str) -> tuple[str, dict[str, str]]:
    """画像パスからresult_keyとプロパティを抽出

    パス例: results/contours/go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13.png
    戻り値: ("S-S13", {"vmax": "50.0", "vmin": "-50.0", "step": "0", "frame": "10"})

    負の値はハイフン記法（vmin-50.0）で表現する。
    ハイフンの使い分け:
    - パラメータの負の値: [A-Za-z]+ の直後に -数字 → 負の数値
    - result_keyのセパレータ: [A-Z] の直後に -[A-Z] → result_key内ダッシュ

    Args:
        path: 画像ファイルパス

    Returns:
        (result_key, properties_dict)
        抽出できない場合は ("", {})
    """
    normalized = path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

    # 拡張子を除去
    if "." in filename:
        filename_no_ext = filename.rsplit(".", 1)[0]
    else:
        return "", {}

    # go_basename部分をスキップ
    tokens = filename_no_ext.split("_")

    # go_basenameの終端を特定
    start_idx = 0
    for i, token in enumerate(tokens):
        # go_ の先頭部分（go, go.v3, idx1, idx1.v3）
        # ドット区切りのバージョンを含むトークンをチェック
        base_token = token.split(".")[0].lower()
        if i == 0 and base_token.startswith("go"):
            start_idx = i + 1
            continue
        if i <= start_idx and base_token.startswith("idx"):
            start_idx = i + 1
            continue
        break

    result_key = ""
    props: dict[str, str] = {}

    # ディレクトリ名からもプロパティを抽出
    parts = normalized.split("/")
    for part in parts[:-1]:
        dir_tokens = part.split("_")
        for dt in dir_tokens:
            m = _PATH_PROP_PATTERN.fullmatch(dt)
            if m:
                unit_suffix = m.group(3) or ""
                props[m.group(1)] = m.group(2) + unit_suffix

    # ファイル名トークンの解析
    for token in tokens[start_idx:]:
        # パラメータパターン（vmax50.0, vmin-50.0, step0, t35mm等）
        m = _PATH_PROP_PATTERN.fullmatch(token)
        if m:
            unit_suffix = m.group(3) or ""
            props[m.group(1)] = m.group(2) + unit_suffix
            continue
        # result_keyパターン（S-S13, U-U3, PEEQ等）
        if _PATH_RESULT_KEY_PATTERN.fullmatch(token) and not result_key:
            result_key = token
            continue

    return result_key, props


def build_composite_group_key(
    result_key: str,
    props: dict[str, str],
    exclude_keys: set[str] | None = None,
) -> str:
    """result_keyとpropsから複合グループキーを生成

    除外キー（デフォルト: idx, v）を除いたpropsをソート済みで結合する。
    例: "S-S13(step:0,vmax:50.0,vmin:-50.0)"

    Args:
        result_key: 画像のresult_key（空文字の場合は "(その他)"）
        props: 画像パスから抽出されたプロパティ辞書
        exclude_keys: 除外するプロパティキー（デフォルト: {"idx", "v", "frame"}）

    Returns:
        複合グループキー文字列
    """
    # if exclude_keys is None:
    # exclude_keys = {"idx", "v"}
    # TODO: target_keysはデフォルトをこれとして、ハードコードをconfigに逃がす
    target_keys = {"step", "frame", "vmax", "vmin", "gallery"}
    base = result_key if result_key else "(その他)"
    # filtered = {k: v for k, v in props.items() if k.lower() not in exclude_keys}
    filtered = {k: v for k, v in props.items() if k.lower() in target_keys}
    if not filtered:
        return base
    param_str = ",".join(f"{k}:{v}" for k, v in sorted(filtered.items()))
    return f"{base}({param_str})"


def group_images_by_composite_key(
    images: list[dict[str, Any]],
    exclude_keys: set[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """画像をresult_key+propsの複合キーでグルーピング

    同じresult_keyかつ同じプロパティセット（idx, v除外）の画像をグループ化する。
    グループキーの形式: "result_key(param1:val1,param2:val2)"

    Args:
        images: 画像情報のリスト
        exclude_keys: 除外するプロパティキー

    Returns:
        {composite_key: [画像情報, ...], ...}
    """
    from collections import OrderedDict

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()

    for img in images:
        path = img.get("image_path", "")
        result_key, props = extract_path_metadata(path)
        idx = props.get("idx", 0)
        try:
            idx = int(idx)
        except Exception:
            pass
        img["idx"] = idx
        gk = build_composite_group_key(result_key, props, exclude_keys)
        groups.setdefault(gk, []).append(img)

    groups_sorted = groups.copy()
    for k, v in groups.items():
        groups_sorted[k] = list(sorted(v, key=lambda x: x.get("idx", 0)))

    return dict(groups_sorted)
