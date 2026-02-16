"""results/サブディレクトリのメタデータ抽出パーサー

results/のサブディレクトリ内にある結果可視化画像ファイルから
メタデータを抽出し、ファイルノードと対応するgo_*.inpノードに
プロパティを付与する。

ディレクトリ名パターン: results/step{N}_frame{M}/
ファイル名パターン: {go_basename}_{result_key}_{params}.{ext}

例: results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin_5.0.png
  → ファイルノード: step=0, frame=10, vmax=10.0, vmin=5.0
  → go_idx1.v1.inp の properties["results.S-S33"] にリスト形式で追加

同じresult_keyでstep/frame/vmin/vmax違いがあれば別エントリとして扱う。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# results/直下ではなくサブディレクトリ内のファイルを対象とする判定用
_INFO_ONLY_DIRECTORIES: frozenset[str] = frozenset({"results"})

# ディレクトリ名からキー値ペアを抽出するパターン（例: step0 → step=0, frame10 → frame=10）
_DIR_PROP_PATTERN = re.compile(r"([A-Za-z]+)(\d+)")

# ファイル名のパラメータトークン（浮動小数点対応）: vmax10.0 → vmax=10.0
_FLOAT_PROP_PATTERN = re.compile(r"^([A-Za-z]+)(\d+(?:\.\d+)?)$")

# 結果キーパターン（ダッシュ含む識別子）: S-S33, U-U3, PEEQ 等
_RESULT_KEY_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*(?:-[A-Z][A-Za-z0-9]*(?:\d+)?)?$")


def _is_in_results_subdirectory(path: str) -> tuple[bool, str]:
    """パスがresults/のサブディレクトリ内かを判定

    Returns:
        (判定結果, サブディレクトリ名)
        例: ("results/step0_frame10/foo.png", True) → (True, "step0_frame10")
    """
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    dir_parts = parts[:-1]
    for i, part in enumerate(dir_parts):
        if part in _INFO_ONLY_DIRECTORIES:
            # サブディレクトリが存在する場合（深さ2以上）
            depth = len(dir_parts) - i - 1
            if depth >= 1:
                return True, dir_parts[i + 1]
    return False, ""


def _parse_directory_metadata(dirname: str) -> dict[str, str]:
    """ディレクトリ名からメタデータを抽出

    例: "step0_frame10" → {"step": "0", "frame": "10"}
    """
    metadata: dict[str, str] = {}
    tokens = dirname.split("_")
    for token in tokens:
        match = _DIR_PROP_PATTERN.fullmatch(token)
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata


def _parse_result_filename(
    filename_without_ext: str,
    go_basenames: set[str],
) -> tuple[str, str, dict[str, str]]:
    """結果ファイル名を解析してgo_basename、result_key、パラメータを返す

    Args:
        filename_without_ext: 拡張子なしのファイル名
        go_basenames: 既知のgo_*.inpのbasename集合

    Returns:
        (go_basename, result_key, params)
        マッチしない場合は ("", "", {})

    例: "go_idx1.v1_S-S33_vmax10.0_vmin_5.0"
        → ("go_idx1.v1", "S-S33", {"vmax": "10.0", "vmin": "5.0"})
    """
    # go_basenameとのマッチを試行（長い名前から順にマッチ）
    matched_basename = ""
    for basename in sorted(go_basenames, key=len, reverse=True):
        prefix = basename + "_"
        if filename_without_ext.startswith(prefix):
            matched_basename = basename
            break

    if not matched_basename:
        return "", "", {}

    # basenameの後のサフィックスを取得
    suffix = filename_without_ext[len(matched_basename) + 1 :]
    if not suffix:
        return matched_basename, "", {}

    # サフィックスをトークンに分割
    tokens = suffix.split("_")

    # result_keyとパラメータを分離
    result_key = ""
    params: dict[str, str] = {}
    pending_key: str | None = None

    for token in tokens:
        # 浮動小数点パラメータ: vmax10.0
        float_match = _FLOAT_PROP_PATTERN.fullmatch(token)
        if float_match:
            if pending_key is not None:
                # 前のpending_keyは値なしのままresult_keyとして扱う
                if not result_key:
                    result_key = pending_key
                pending_key = None
            params[float_match.group(1)] = float_match.group(2)
            continue

        # 数値のみのトークン: 前のpending_keyの値として扱う
        if pending_key is not None and re.fullmatch(r"\d+(?:\.\d+)?", token):
            params[pending_key] = token
            pending_key = None
            continue

        # 結果キーパターン（S-S33等、ダッシュ含む識別子）
        if _RESULT_KEY_PATTERN.fullmatch(token) and not result_key:
            if pending_key is not None:
                # 前のpending_keyもresult_keyになりうる
                result_key = pending_key
                pending_key = token
            else:
                # まだresult_keyが確定していない場合、このトークンをresult_keyに
                result_key = token
            continue

        # アルファベットのみのトークン: パラメータキーの可能性
        if re.fullmatch(r"[A-Za-z]+", token):
            if pending_key is not None and not result_key:
                result_key = pending_key
            pending_key = token
            continue

        # それ以外: result_keyの一部として扱う
        if not result_key:
            result_key = token

    # pending_keyが残っている場合
    if pending_key is not None and not result_key:
        result_key = pending_key

    return matched_basename, result_key, params


class ResultsMetadataParser(AbstractFileParser):
    """results/サブディレクトリの結果可視化画像メタデータを抽出

    results/のサブディレクトリ内にあるファイル（.png等）から
    メタデータを抽出し、以下を実行する:

    1. ファイルノードにstep/frame/vmax/vmin等のプロパティを付与
    2. 対応するgo_*.inpノードのpropertiesに
       "results.{result_key}" キーでリスト形式のエントリを追加

    同じresult_keyでstep/frame/vmin/vmax違いがあれば別エントリとして格納。
    """

    priority = 34  # OutputRelationParser(32), JsonPropertyParser(33)の直後

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions

        # go_*.inpノードを収集
        go_inp_nodes: dict[str, Node] = {}
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue
            name_lower = node.name.lower()
            if name_lower.startswith("go_") or name_lower == "go":
                go_inp_nodes[node.name] = node

        go_basenames = set(go_inp_nodes.keys())
        if not go_basenames:
            return graph

        # results/サブディレクトリ内のファイルノードを処理
        # go_basename → result_key → エントリのリスト
        results_map: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

        for node in graph.nodes:
            node_path = node.properties.get("path", "")
            if not node_path:
                continue

            in_subdir, subdir_name = _is_in_results_subdirectory(node_path)
            if not in_subdir:
                continue

            # ディレクトリ名からメタデータ抽出
            dir_metadata = _parse_directory_metadata(subdir_name)

            # ファイル名から結果キーとパラメータを抽出
            go_basename, result_key, file_params = _parse_result_filename(node.name, go_basenames)

            if not go_basename or not result_key:
                continue

            # ファイルノードにプロパティを付与
            node.properties.update(dir_metadata)
            node.properties.update(file_params)
            node.properties["result_key"] = result_key

            # エントリを構築
            entry: dict[str, Any] = {"path": node_path}
            entry.update(dir_metadata)
            entry.update(file_params)

            results_map[go_basename][result_key].append(entry)

        # go_*.inpノードにresults.{result_key}プロパティを割り当て
        for go_basename, key_entries in results_map.items():
            inp_node = go_inp_nodes.get(go_basename)
            if inp_node is None:
                continue
            for result_key, entries in key_entries.items():
                prop_key = f"results.{result_key}"
                existing = inp_node.properties.get(prop_key, [])
                if isinstance(existing, list):
                    existing.extend(entries)
                else:
                    existing = entries
                inp_node.properties[prop_key] = existing

        return graph
