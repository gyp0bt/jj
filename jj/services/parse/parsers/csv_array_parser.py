"""CSV配列プロパティパーサー

has_output関係で紐づいたCSVファイルを読み取り、
GOノードのプロパティに配列データとして格納する。

ファイル名のトークン差分で接頭辞を決定する:
- go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv
  → 余剰トークン"RF" → プロパティ: RF.time, RF.RF3 (各列の配列)

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class CsvArrayParser(AbstractFileParser):
    """has_output関係のCSVを読み取りGOノードに配列プロパティとして格納

    OutputRelationParser(priority=32)の後に実行。
    入力ノードとCSV出力ノードのファイル名トークンを比較し、
    余剰トークンを接頭辞として使用する。

    例:
        go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv
        余剰トークン: "RF"
        CSV内容: time,RF3
                 0.0,0.0
                 0.5,123.4
        格納: node.properties["RF.time"] = [0.0, 0.5, 1.0]
              node.properties["RF.RF3"] = [0.0, 123.4, 456.7]
    """

    priority = 33

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions

        # 入力ノードをIDで引けるようにする
        input_nodes: dict[int, Node] = {}
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_nodes[node.id] = node

        # has_output関係からCSVノードを収集
        for rel in graph.relations:
            if rel.label != "has_output":
                continue
            inp_node = input_nodes.get(rel.node1_id)
            if inp_node is None:
                continue

            out_node = graph.get_node_by_id(rel.node2_id)
            if out_node is None:
                continue

            # CSV拡張子チェック
            out_ext = (out_node.format or "").lower()
            if out_ext != "csv":
                continue

            # トークン差分から接頭辞を算出
            prefix = _compute_extra_token(inp_node.name, out_node.name)
            if not prefix:
                continue

            # CSVファイルを読み取り
            csv_path = graph.project_root / out_node.properties.get("path", "")
            if not csv_path.exists():
                continue

            arrays = _read_csv_arrays(csv_path)
            if not arrays:
                continue

            # GOノードのプロパティに格納
            for col_name, values in arrays.items():
                prop_key = f"{prefix}.{col_name}"
                inp_node.properties[prop_key] = values

        return graph


def _compute_extra_token(inp_name: str, csv_name: str) -> str:
    """入力ノード名とCSVノード名のトークン差分から余剰トークンを返す

    入力名のトークン集合に対してCSV名のトークン集合が
    ちょうど1つ多い場合、その余剰トークンを返す。
    プロパティ値（数値部分）は除外してキー部分のみ比較する。

    Args:
        inp_name: 入力ノード名（例: "go_idx1_w5_t20"）
        csv_name: CSVノード名（例: "go_idx1_w5_t20_RF" or "go_idx1_w5_t20"）

    Returns:
        余剰トークン文字列。条件不一致時は空文字。
    """
    # ファイル名をトークン化（go_プレフィックス含む全体をアンダースコアで分割）
    inp_tokens = inp_name.split("_")
    csv_tokens = csv_name.split("_")

    # CSVのトークンが入力より1つ多いか確認
    if len(csv_tokens) != len(inp_tokens) + 1:
        return ""

    # 入力トークンリストに含まれない余剰トークンを探す
    remaining = list(inp_tokens)
    extra: list[str] = []

    for token in csv_tokens:
        if token in remaining:
            remaining.remove(token)
        else:
            extra.append(token)

    if len(extra) == 1:
        return extra[0]

    return ""


def _read_csv_arrays(csv_path: Path) -> dict[str, list[float]]:
    """CSVファイルを読み取り、列名→数値配列の辞書を返す

    数値変換できない値はスキップする。全行が数値でない列は除外される。

    Args:
        csv_path: CSVファイルパス

    Returns:
        {列名: [値のリスト]} の辞書。空の場合は空辞書。
    """
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return {}

            columns: dict[str, list[float]] = {
                col: [] for col in reader.fieldnames
            }

            for row in reader:
                for col in reader.fieldnames:
                    val = row.get(col, "").strip()
                    try:
                        columns[col].append(float(val))
                    except (ValueError, TypeError):
                        columns[col].append(float("nan"))

            # 全値がNaNの列を除外
            import math
            result: dict[str, list[float]] = {}
            for col, values in columns.items():
                if values and not all(math.isnan(v) for v in values):
                    result[col] = values

            return result
    except (OSError, IOError):
        return {}
