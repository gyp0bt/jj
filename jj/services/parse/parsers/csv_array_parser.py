"""CSV配列プロパティパーサー

has_output関係で紐づいたCSVファイルを読み取り、
GOノードのプロパティに配列データとして格納する。

接頭辞の決定方法:
1. トークン差分方式（同一ディレクトリ）:
   go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv
   → 余剰トークン"RF" → プロパティ: RF.time, RF.RF3

2. サブディレクトリ方式:
   go_idx1_w5_t20.inp → go_idx1_w5_t20/history_RF3.csv
   → CSVファイル名 "history_RF3" → プロパティ: history_RF3.time, history_RF3.RF3

ヘッダーなしCSV対応:
   1行目が全て数値の場合、col_0, col_1, ... で自動命名する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import TYPE_CHECKING

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class CsvArrayParser(AbstractFileParser):
    """has_output関係のCSVを読み取りGOノードに配列プロパティとして格納

    OutputRelationParser(priority=32)の後に実行。

    接頭辞の決定:
    1. 入力ノードとCSV出力ノードのファイル名トークン差分（従来方式）
    2. サブディレクトリ内CSVの場合、CSVファイル名をそのまま接頭辞に使用

    ヘッダーなしCSV: 1行目が全て数値の場合、col_0, col_1, ... で自動命名。

    例1 (トークン差分):
        go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv
        余剰トークン: "RF"
        格納: node.properties["RF.time"] = [0.0, 0.5, 1.0]

    例2 (サブディレクトリ):
        go_idx1_w5_t20.inp → go_idx1_w5_t20/history_RF3.csv
        接頭辞: "history_RF3"
        格納: node.properties["history_RF3.time"] = [0.0, 0.5, 1.0]
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

            # 接頭辞を算出
            prefix = _compute_prefix(inp_node, out_node)
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


def _compute_prefix(inp_node: Node, out_node: Node) -> str:
    """入力ノードとCSV出力ノードから接頭辞を決定する

    1. トークン差分方式: CSVファイル名のトークンが入力名より1つ多い場合
    2. サブディレクトリ方式: CSVが入力名と同名のディレクトリ内にある場合、
       CSVファイル名（拡張子除く）を接頭辞として使用

    Args:
        inp_node: 入力ノード
        out_node: CSV出力ノード

    Returns:
        接頭辞文字列。決定できない場合は空文字。
    """
    # パターン1: トークン差分方式
    prefix = _compute_extra_token(inp_node.name, out_node.name)
    if prefix:
        return prefix

    # パターン2: サブディレクトリ方式
    out_path = out_node.properties.get("path", "")
    if out_path:
        parent_dir = Path(out_path).parent.name
        if parent_dir == inp_node.name:
            # CSVファイル名（拡張子除く）を接頭辞とする
            return out_node.name

    return ""


def _compute_extra_token(inp_name: str, csv_name: str) -> str:
    """入力ノード名とCSVノード名のトークン差分から余剰トークンを返す

    入力名のトークン集合に対してCSV名のトークン集合が
    ちょうど1つ多い場合、その余剰トークンを返す。
    プロパティ値（数値部分）は除外してキー部分のみ比較する。

    Note:
        本プロジェクトのファイル命名規約により、同一トークンがファイル名中に
        2回出現することはない。そのため list.remove() による先頭一致の削除で
        正しく動作する。

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


def _is_header_row(row: list[str]) -> bool:
    """行がヘッダー行（非数値を含む）かどうかを判定する

    全セルが数値に変換可能な場合はデータ行（ヘッダーなし）と判断する。
    空行の場合はヘッダーなしと見なす。

    Args:
        row: CSVの行（文字列リスト）

    Returns:
        True: ヘッダー行（少なくとも1つの非数値セルがある）
    """
    if not row:
        return False
    for cell in row:
        cell = cell.strip()
        if not cell:
            continue
        try:
            float(cell)
        except (ValueError, TypeError):
            return True
    return False


def _read_csv_arrays(csv_path: Path) -> dict[str, list[float]]:
    """CSVファイルを読み取り、列名→数値配列の辞書を返す

    1行目がヘッダー（非数値を含む）の場合はそのままカラム名として使用。
    1行目が全て数値の場合はヘッダーなしと判断し、col_0, col_1, ... で
    自動命名してデータとして読み込む。

    数値変換できない値はNaNとする。全値がNaNの列は除外される。

    Args:
        csv_path: CSVファイルパス

    Returns:
        {列名: [値のリスト]} の辞書。空の場合は空辞書。
    """
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            # まず最初の行を読み取ってヘッダー有無を判定
            sniffer_reader = csv.reader(f)
            try:
                first_row = next(sniffer_reader)
            except StopIteration:
                return {}

            has_header = _is_header_row(first_row)

            if has_header:
                # ヘッダーありの場合: 1行目をカラム名とする
                fieldnames = [cell.strip() for cell in first_row]
            else:
                # ヘッダーなしの場合: col_N で自動命名
                num_cols = len(first_row)
                fieldnames = [f"col_{i}" for i in range(num_cols)]

            columns: dict[str, list[float]] = {col: [] for col in fieldnames}

            def _append_row(row: list[str]) -> None:
                for i, col in enumerate(fieldnames):
                    val = row[i].strip() if i < len(row) else ""
                    try:
                        columns[col].append(float(val))
                    except (ValueError, TypeError):
                        columns[col].append(float("nan"))

            # ヘッダーなしの場合、1行目をデータとして格納
            if not has_header:
                _append_row(first_row)

            # 残りの行を読み取り
            for row in sniffer_reader:
                _append_row(row)

            # 全値がNaNの列を除外
            result: dict[str, list[float]] = {}
            for col, values in columns.items():
                if values and not all(math.isnan(v) for v in values):
                    result[col] = values

            return result
    except OSError:
        return {}
