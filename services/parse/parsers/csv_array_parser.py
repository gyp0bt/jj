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
from plugins.base.parser import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class CsvArrayParser(AbstractFileParser):
    """has_output関係のCSVを読み取りGOノードに配列プロパティとして格納

    OutputRelationParser(priority=32)の後に実行。

    接頭辞の決定:
    1. 入力ノードとCSV出力ノードのファイル名トークン差分（従来方式）
    2. サブディレクトリ内CSVの場合、CSVファイル名をそのまま接頭辞に使用

    ヘッダーなしCSV: 1行目が全て数値の場合、col_0, col_1, ... で自動命名。

    csv-max-rows設定:
        0（デフォルト）: 全行を配列として読み込む（従来動作）
        N > 0: N行を超えるCSVはサマリーモード（min/max/mean/count/last）で格納。
        大規模プロジェクト（60K行×1000ファイル等）でのメモリ使用量を抑制する。

    例1 (トークン差分):
        go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv
        余剰トークン: "RF"
        格納: node.properties["RF.time"] = [0.0, 0.5, 1.0]

    例2 (サブディレクトリ):
        go_idx1_w5_t20.inp → go_idx1_w5_t20/history_RF3.csv
        接頭辞: "history_RF3"
        格納: node.properties["history_RF3.time"] = [0.0, 0.5, 1.0]

    例3 (サマリーモード, csv-max-rows: 10000):
        60000行のCSV → サマリー統計量で格納
        格納: node.properties["RF.time"] = {"min": 0.0, "max": 1.0, "mean": 0.5, "count": 60000, "last": 1.0}
    """

    priority = 33

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        csv_max_rows = graph.config.csv_max_rows

        # 入力ノードをIDで引けるようにする（インデックス活用）
        input_nodes: dict[int, Node] = {}
        for node in graph.get_input_nodes():
            input_nodes[node.id] = node

        # has_output関係からCSVノードを収集（インデックス活用）
        for rel in graph.get_relations_by_label("has_output"):
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

            arrays = _read_csv_arrays(csv_path, max_rows=csv_max_rows)
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


def _count_csv_rows(csv_path: Path) -> int:
    """CSVファイルの行数を高速に数える（ヘッダー行含む）"""
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _read_csv_summary(csv_path: Path) -> dict[str, dict[str, float]]:
    """CSVファイルをストリーミング読み込みし、列ごとの統計量のみを返す

    全行をメモリに保持せず、1行ずつ処理して統計量を計算する。
    大規模CSV（60K行×1000ファイル等）でのメモリ使用量を抑制する。

    Args:
        csv_path: CSVファイルパス

    Returns:
        {列名: {"min": float, "max": float, "mean": float, "count": int, "last": float}}
    """
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
            sniffer_reader = csv.reader(f)
            try:
                first_row = next(sniffer_reader)
            except StopIteration:
                return {}

            has_header = _is_header_row(first_row)

            if has_header:
                fieldnames = [cell.strip() for cell in first_row]
            else:
                num_cols = len(first_row)
                fieldnames = [f"col_{i}" for i in range(num_cols)]

            # ストリーミング統計: min, max, sum, count, last
            stats: dict[str, dict[str, float]] = {}
            for col in fieldnames:
                stats[col] = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0, "last": float("nan")}

            def _update_stats(row: list[str]) -> None:
                for i, col in enumerate(fieldnames):
                    val_str = row[i].strip() if i < len(row) else ""
                    try:
                        val = float(val_str)
                    except (ValueError, TypeError):
                        continue
                    if math.isnan(val):
                        continue
                    s = stats[col]
                    if val < s["min"]:
                        s["min"] = val
                    if val > s["max"]:
                        s["max"] = val
                    s["sum"] += val
                    s["count"] += 1
                    s["last"] = val

            if not has_header:
                _update_stats(first_row)

            for row in sniffer_reader:
                _update_stats(row)

            # 結果辞書を構築（有効データがない列は除外）
            result: dict[str, dict[str, float]] = {}
            for col, s in stats.items():
                count = int(s["count"])
                if count == 0:
                    continue
                result[col] = {
                    "min": s["min"],
                    "max": s["max"],
                    "mean": s["sum"] / count,
                    "count": count,
                    "last": s["last"],
                }

            return result
    except OSError:
        return {}


def _read_csv_arrays(csv_path: Path, *, max_rows: int = 0) -> dict[str, list[float] | dict[str, float]]:
    """CSVファイルを読み取り、列名→数値配列（またはサマリー）の辞書を返す

    1行目がヘッダー（非数値を含む）の場合はそのままカラム名として使用。
    1行目が全て数値の場合はヘッダーなしと判断し、col_0, col_1, ... で
    自動命名してデータとして読み込む。

    数値変換できない値はNaNとする。全値がNaNの列は除外される。

    max_rows > 0 の場合、データ行数がmax_rowsを超えるCSVはサマリーモードで読み込む。
    サマリーモードでは全行をメモリに保持せず、統計量（min/max/mean/count/last）のみを返す。

    Args:
        csv_path: CSVファイルパス
        max_rows: CSV最大行数閾値（0=無制限、超過時サマリーモード）

    Returns:
        {列名: [値のリスト]} または {列名: {"min", "max", "mean", "count", "last"}}
    """
    # サマリーモード判定
    if max_rows > 0:
        row_count = _count_csv_rows(csv_path)
        # ヘッダー行を除くデータ行数で判定
        if row_count > max_rows + 1:
            return _read_csv_summary(csv_path)

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
