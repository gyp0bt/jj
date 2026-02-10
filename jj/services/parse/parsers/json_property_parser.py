"""JSONプロパティパーサー

go_*.inpに紐づいた".odb.json"以外の".json"ファイルの中を開き、
第一階層のkey-valueをgo_*.inpノードのプロパティに割り当てる。

例: results/go_idx0.v29_stress.json → go_idx0.v29.inpに
    {"0(center)": 0.25, "1": NaN, "2(edge)": NaN} を割り当て
    → node.properties["stress"] = {"0(center)": 0.25, "1": null, "2(edge)": null}

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import json
import math
import re
from typing import TYPE_CHECKING, Any

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class JsonPropertyParser(AbstractFileParser):
    """go_*.inpに紐づくJSONの第一階層key-valueをプロパティとして割り当て

    OutputRelationParserのhas_output関係を利用して、
    go_*.inpノードに紐づく.jsonファイル（.odb.json除外）を特定し、
    JSONの第一階層key-valueをgo_*.inpのプロパティに追加する。

    JSONファイル名からinp basenameを除いたサフィックスをキーとし、
    第一階層の辞書全体を値として格納する。
    例: go_idx0.v29_stress.json → properties["stress"] = {...}
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

                # サフィックスを取得（例: "stress"）
                suffix = json_name[len(inp_basename) + 1:]
                if not suffix:
                    continue

                # JSONファイルを読み込み
                json_path = graph.project_root / json_node.properties.get("path", "")
                json_data = self._read_json(json_path)
                if json_data is None:
                    continue

                # 第一階層key-valueをgo_*.inpのプロパティに割り当て
                inp_node.properties[suffix] = json_data

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
        content = re.sub(r'\bNaN\b', 'null', content)
        content = re.sub(r'\bInfinity\b', 'null', content)
        content = re.sub(r'\b-Infinity\b', 'null', content)

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        return data
