"""JSONプロパティパーサー

go_*.inpに紐づいた".odb.json"以外の".json"ファイルの中を開き、
JSON内のキー名を採用してgo_*.inpノードのプロパティに平坦化して割り当てる。

JSON内の階層は"."繋ぎでカラム名を作成する（ファイル名サフィックスはプレフィックスに使用しない）。

例: results/go_idx0.v29_stress.json（内容: {"center": 0.25, "edge": 1.0}）
    → go_idx0.v29.inpに
    properties["center"] = 0.25
    properties["edge"] = 1.0

例: results/go_idx0.v29_stress.json（内容: {"results": {"max": 1.5}}）
    → go_idx0.v29.inpに
    properties["results.max"] = 1.5

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class JsonPropertyParser(AbstractFileParser):
    """go_*.inpに紐づくJSONのキーを"."繋ぎで平坦化してプロパティに割り当て

    OutputRelationParserのhas_output関係を利用して、
    go_*.inpノードに紐づく.jsonファイル（.odb.json除外）を特定し、
    JSON内のキー名を採用してgo_*.inpのプロパティに追加する。

    JSON内の階層を"."繋ぎで平坦化してプロパティキーとする。
    ファイル名サフィックスはプレフィックスとして使用しない。
    例: go_idx0.v29_stress.json → properties["center"] = 0.25
    """

    priority = 33  # OutputRelationParser(32)の直後

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions

        # go_*.inpノードを収集
        go_inp_nodes: list[Node] = []
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue
            name_lower = node.name.lower()
            if name_lower.startswith("go_") or name_lower == "go":
                go_inp_nodes.append(node)

        # .jsonノード（.odb.json除外）を収集
        json_nodes: list[Node] = []
        for node in graph.nodes:
            if node.format != "json":
                continue
            # .odb.jsonは除外（name末尾が.odbの場合）
            if node.name.lower().endswith(".odb"):
                continue
            json_nodes.append(node)

        # go_*.inpのbasenameを接頭辞としてマッチするJSONを探す
        for inp_node in go_inp_nodes:
            inp_basename = inp_node.name  # 例: go_idx0.v29
            inp_index = graph.get_node_index(inp_node)

            for json_node in json_nodes:
                json_name = json_node.name  # 例: go_idx0.v29_stress

                # basename接頭辞マッチ
                if not json_name.startswith(inp_basename + "_"):
                    continue

                # 同一indexの確認
                json_index = graph.get_node_index(json_node)
                if inp_index and json_index and inp_index != json_index:
                    continue

                # サフィックスを取得（例: "stress", "dat_warning"）
                suffix = json_name[len(inp_basename) + 1:]
                if not suffix:
                    continue

                # JSONファイルを読み込み（キャッシュ対応）
                json_path = graph.project_root / json_node.properties.get("path", "")
                cache_key = f"json:{json_path}"
                if not graph.is_file_modified(str(json_path)):
                    cached_data = graph.get_cache(cache_key)
                    if cached_data is not None:
                        json_data = cached_data
                    else:
                        json_data = self._read_json(json_path)
                        if json_data is not None:
                            graph.set_cache(cache_key, json_data)
                else:
                    json_data = self._read_json(json_path)
                    if json_data is not None:
                        graph.set_cache(cache_key, json_data)
                if json_data is None:
                    continue

                # JSON内のキー名を"."繋ぎで平坦化してプロパティに割り当て
                # ファイル名サフィックスはプレフィックスに使用しない
                flattened = _flatten_json(json_data, prefix="")
                inp_node.properties.update(flattened)

        return graph

    @staticmethod
    def _read_json(json_path) -> dict[str, Any] | None:
        """JSONファイルを読み込み（NaN/Infinity対応）"""
        try:
            with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except (OSError, IOError):
            return None

        # NaN/Infinityをnullに置換してからパース
        # -Infinityを先に置換しないとInfinity置換で-nullになる
        content = re.sub(r'\bNaN\b', 'null', content)
        content = re.sub(r'-Infinity\b', 'null', content)
        content = re.sub(r'\bInfinity\b', 'null', content)

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        return data


def _flatten_json(
    data: dict[str, Any], prefix: str = ""
) -> dict[str, Any]:
    """辞書を"."区切りで再帰的に平坦化する

    Args:
        data: 平坦化対象の辞書
        prefix: キーのプレフィックス

    Returns:
        平坦化された辞書

    例:
        {"center": 0.25, "nested": {"a": 1, "b": 2}}
        prefix="stress"
        → {"stress.center": 0.25, "stress.nested.a": 1, "stress.nested.b": 2}
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_json(value, prefix=full_key))
        else:
            result[full_key] = value
    return result
