"""ダッシュボード画像ギャラリー専用ユーティリティ

go_ ノードの output / properties から取得した画像情報を、ファイル名や
ディレクトリ名に埋め込まれたパラメータ (vmax, step, frame など) に基づいて
グルーピング・フィルタリングする dashboard 固有のロジックを集約する。

graph 層は「画像メタデータが付与された行」までを返す責務にとどまり、
ここでのファイル名解析・複合キー生成・グルーピングは UI ドメイン固有
(go_ ノードの contour 図命名規則に強く依存する) のため別モジュールに分離。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import contextlib
import re
from typing import Any

# パラメータトークンパターン（負の値対応・単位オプション）: vmax50.0, vmin-50.0, step0, t35mm
_PATH_PROP_PATTERN = re.compile(r"^([A-Za-z]+)(-?\d+(?:\.\d+)?)([A-Za-z]*)$")

# result_keyパターン（ダッシュ含む識別子）: S-S13, U-U3, PEEQ
_PATH_RESULT_KEY_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*(?:-[A-Z][A-Za-z0-9]*(?:\d+)?)?$")


def normalize_group_key(key: str) -> str:
    """グループキーを正規化（daily:日付:キー → キー部分のみ）"""
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
    """画像リストをキー名のリストでフィルタリングする。

    allowed_keys が指定された場合、画像の result_key (output ソース) または
    property_key (property ソース) がリストに含まれるもののみ返す。
    """
    if not allowed_keys:
        return images

    allowed_set = set(allowed_keys)
    result = []

    for img in images:
        if source == "output":
            rk = _extract_result_key_from_path(img.get("image_path", ""))
            if (rk and rk in allowed_set) or (not rk and "(その他)" in allowed_set):
                result.append(img)
        elif source == "property":
            pk = normalize_group_key(img.get("property_key", ""))
            if pk in allowed_set:
                result.append(img)

    return result


def collect_group_keys(images: list[dict[str, Any]], source: str) -> list[str]:
    """画像リストからグループ化に利用できるキーを収集する。"""
    keys: set[str] = set()
    for img in images:
        props = img.get("go_properties", {})
        for k in props:
            if k != "path":
                keys.add(k)
    result = sorted(keys)
    if source == "output":
        has_result_key = any(_extract_result_key_from_path(img.get("image_path", "")) for img in images)
        if has_result_key:
            result = ["result_key", *result]
    if source == "property":
        result = ["property_key", *result]
    return result


def _extract_result_key_from_path(path: str) -> str:
    """画像パスから result_key を抽出する。抽出できない場合は空文字。"""
    normalized = path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

    if "." in filename:
        filename_no_ext = filename.rsplit(".", 1)[0]
    else:
        return ""

    tokens = filename_no_ext.split("_")

    start_idx = 0
    for i, token in enumerate(tokens):
        if i == 0 and token.lower().startswith("go"):
            start_idx = i + 1
            continue
        if i == start_idx and token.lower().startswith("idx"):
            start_idx = i + 1
            continue
        break

    for token in tokens[start_idx:]:
        if _PATH_RESULT_KEY_PATTERN.fullmatch(token) and not _PATH_PROP_PATTERN.fullmatch(token):
            return token

    return ""


def extract_path_metadata(path: str) -> tuple[str, dict[str, str]]:
    """画像パスから result_key とプロパティを抽出する。

    例: results/contours/go_idx1.v3_vmax50.0_vmin-50.0_step0_frame10_S-S13.png
    → ("S-S13", {"vmax": "50.0", "vmin": "-50.0", "step": "0", "frame": "10"})
    """
    normalized = path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1] if "/" in normalized else normalized

    if "." in filename:
        filename_no_ext = filename.rsplit(".", 1)[0]
    else:
        return "", {}

    tokens = filename_no_ext.split("_")

    start_idx = 0
    for i, token in enumerate(tokens):
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

    parts = normalized.split("/")
    for part in parts[:-1]:
        dir_tokens = part.split("_")
        for dt in dir_tokens:
            m = _PATH_PROP_PATTERN.fullmatch(dt)
            if m:
                unit_suffix = m.group(3) or ""
                props[m.group(1)] = m.group(2) + unit_suffix

    for token in tokens[start_idx:]:
        m = _PATH_PROP_PATTERN.fullmatch(token)
        if m:
            unit_suffix = m.group(3) or ""
            props[m.group(1)] = m.group(2) + unit_suffix
            continue
        if _PATH_RESULT_KEY_PATTERN.fullmatch(token) and not result_key:
            result_key = token
            continue

    return result_key, props


def build_composite_group_key(
    result_key: str,
    props: dict[str, str],
    exclude_keys: set[str] | None = None,
    *,
    target_keys: set[str] | None = None,
) -> str:
    """result_key と props から複合グループキーを生成する。

    例: "S-S13(step:0,vmax:50.0,vmin:-50.0)"
    """
    if target_keys is None:
        # 循環import回避のため遅延import
        from config import GalleryDefaults

        target_keys = set(GalleryDefaults().composite_target_keys)
    base = result_key if result_key else "(その他)"
    filtered = {k: v for k, v in props.items() if k.lower() in target_keys}
    if not filtered:
        return base
    param_str = ",".join(f"{k}:{v}" for k, v in sorted(filtered.items()))
    return f"{base}({param_str})"


def group_images_by_composite_key(
    images: list[dict[str, Any]],
    exclude_keys: set[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """画像を result_key+props の複合キーでグルーピングする。

    同じ result_key かつ同じプロパティセット (idx, v 除外) の画像をグループ化する。
    入力 dict を in-place で mutate (img["idx"] = ...) するため、テストや
    呼び出し側がこの挙動に依存している場合は維持すること。
    """
    from collections import OrderedDict

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()

    for img in images:
        path = img.get("image_path", "")
        result_key, props = extract_path_metadata(path)
        idx = props.get("idx", 0)
        with contextlib.suppress(ValueError, TypeError):
            idx = int(idx)
        img["idx"] = idx
        gk = build_composite_group_key(result_key, props, exclude_keys)
        groups.setdefault(gk, []).append(img)

    groups_sorted = groups.copy()
    for k, v in groups.items():
        groups_sorted[k] = list(sorted(v, key=lambda x: x.get("idx", 0)))

    return dict(groups_sorted)
