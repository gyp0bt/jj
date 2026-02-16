"""CSV/JSONエクスポーター: GraphModelをCSV/JSON形式でエクスポート

InfoServiceのexport_dataロジックをAbstractExporterサブクラスとして再実装。
既存のInfoService.export_data()との後方互換性を維持するため、
コアロジック（_flatten_properties, _match_unit）はここに集約し、
InfoServiceからはこのモジュールを呼び出す。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import csv
import fnmatch
import json as json_mod
from pathlib import Path
from typing import Any

from jj_types import GraphModel, Node
from services.export import AbstractExporter


class CsvExporter(AbstractExporter):
    """CSV形式エクスポーター

    ノードデータをCSV形式（UTF-8 BOM付き）でエクスポートする。
    """

    format = "csv"
    priority = 10

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """CSVエクスポート

        kwargs:
            project_root: Path - プロジェクトルート
            nodes: list[Node] | None - 事前選択済みノードリスト
            type_filter: str | None - ノードタイプフィルタ
            select_filter: list[str] | None - ファイル名フィルタ
            prop_filters: list[str] | None - プロパティフィルタ
            output_file: str | None - 出力ファイル名
            flatten: bool | None - プロパティ平坦化
            unit_format: str | None - 単位表示形式
            columns: list[str] | None - カラム選択
            units: dict[str, str] - 単位マッピング
            csv_columns: list[str] | None - 設定ファイルのカラム制限
            csv_unit_format: str - 設定ファイルの単位表示形式
        """
        return _export_data(graph, "csv", **kwargs)

    def format_cli_result(self, result: dict[str, Any], project_root: Path) -> str:
        output_path = result.get("output_path")
        count = result.get("count", 0)
        if output_path:
            try:
                rel = Path(output_path).relative_to(project_root)
            except ValueError:
                rel = output_path
            return f"CSVエクスポート完了: {rel} ({count}件)"
        return f"CSVエクスポート完了 ({count}件)"


class JsonExporter(AbstractExporter):
    """JSON形式エクスポーター

    ノードデータをJSON形式でエクスポートする。
    """

    format = "json"
    priority = 11

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """JSONエクスポート（kwargsはCsvExporterと同一）"""
        return _export_data(graph, "json", **kwargs)

    def format_cli_result(self, result: dict[str, Any], project_root: Path) -> str:
        output_path = result.get("output_path")
        count = result.get("count", 0)
        if output_path:
            try:
                rel = Path(output_path).relative_to(project_root)
            except ValueError:
                rel = output_path
            return f"JSONエクスポート完了: {rel} ({count}件)"
        return f"JSONエクスポート完了 ({count}件)"


def _export_data(
    graph: GraphModel,
    target: str,
    *,
    project_root: Path | None = None,
    nodes: list[Node] | None = None,
    type_filter: str | None = None,
    select_filter: list[str] | None = None,
    prop_filters: list[str] | None = None,
    output_file: str | None = None,
    flatten: bool | None = None,
    unit_format: str | None = None,
    columns: list[str] | None = None,
    units: dict[str, str] | None = None,
    csv_columns: list[str] | None = None,
    csv_unit_format: str = "header",
    **_extra: Any,
) -> dict[str, Any]:
    """CSV/JSONエクスポートのコアロジック

    Returns:
        {"output_path": Path, "count": int}
    """
    if project_root is None:
        project_root = Path(".")

    units = units or {}

    # ノードのフィルタリング
    if nodes is not None:
        filtered_nodes = list(nodes)
    else:
        filtered_nodes = list(graph.nodes)
        if type_filter:
            filtered_nodes = [n for n in filtered_nodes if n.type == type_filter]
        if select_filter:
            selected: list[Node] = []
            for n in filtered_nodes:
                name_with_ext = f"{n.name}.{n.format}" if n.format else n.name
                for sel in select_filter:
                    if n.name == sel or name_with_ext == sel or sel in n.name:
                        selected.append(n)
                        break
            filtered_nodes = selected

    # -prop フィルタ
    if prop_filters:
        filtered_nodes = [n for n in filtered_nodes if all(k in n.properties for k in prop_filters)]

    if not filtered_nodes:
        raise ValueError("対象ノードが見つかりません。")

    # 平坦化のデフォルト
    if flatten is None:
        flatten = target == "csv"

    # プロパティを収集
    data_rows: list[dict[str, Any]] = []
    for node in filtered_nodes:
        base: dict[str, Any] = {
            "name": node.name,
            "type": node.type,
            "format": node.format,
        }
        if flatten:
            props = flatten_properties(node.properties)
        else:
            props = dict(node.properties)
        base.update(props)
        data_rows.append(base)

    # キーの収集
    if prop_filters:
        all_keys: list[str] = ["name", "type", "format"]
        seen_keys: set[str] = set(all_keys)
        for row in data_rows:
            for key in row:
                if key in seen_keys:
                    continue
                for pf in prop_filters:
                    if key == pf or key.startswith(pf + "."):
                        all_keys.append(key)
                        seen_keys.add(key)
                        break
    else:
        all_keys = ["name", "type", "format"]
        seen_keys = set(all_keys)
        for row in data_rows:
            for key in row:
                if key not in seen_keys:
                    all_keys.append(key)
                    seen_keys.add(key)

    # CSVカラム制限
    if target == "csv":
        csv_cols = columns or csv_columns
        if csv_cols:
            base_keys = ["name", "type", "format"]
            ordered_keys: list[str] = []
            seen: set[str] = set()
            for k in base_keys:
                if k in all_keys and k not in seen:
                    ordered_keys.append(k)
                    seen.add(k)
            for pattern in csv_cols:
                for k in all_keys:
                    if k not in seen and fnmatch.fnmatch(k, pattern):
                        ordered_keys.append(k)
                        seen.add(k)
            all_keys = ordered_keys

    # null埋めとリスト/辞書値のJSON文字列化（CSVのみ）
    rows: list[dict[str, Any]] = []
    for data_row in data_rows:
        row: dict[str, Any] = {}
        for key in all_keys:
            value = data_row.get(key)
            if value is None:
                row[key] = None
            elif isinstance(value, (list, dict)) and target == "csv":
                row[key] = json_mod.dumps(value, ensure_ascii=False)
            else:
                row[key] = value
        rows.append(row)

    # 出力
    if output_file is None:
        output_file = f"export.{target}"
    output_path = project_root / output_file

    if target == "csv":
        fmt = unit_format or csv_unit_format
        with output_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            if fmt == "row":
                writer.writerow(all_keys)
                unit_row = [match_unit(k, units) for k in all_keys]
                writer.writerow(unit_row)
            else:
                header = []
                for k in all_keys:
                    u = match_unit(k, units)
                    header.append(f"{k}[{u}]" if u else k)
                writer.writerow(header)
            for row in rows:
                writer.writerow([row.get(k) for k in all_keys])

    elif target == "json":
        with output_path.open("w", encoding="utf-8") as f:
            json_mod.dump(rows, f, ensure_ascii=False, indent=2, default=str)

    return {"output_path": output_path, "count": len(rows)}


def match_unit(key: str, units: dict[str, str]) -> str:
    """カラム名に対応する単位を返す（globパターン対応）"""
    if key in units:
        return units[key]
    for pattern, unit in units.items():
        if fnmatch.fnmatch(key, pattern):
            return unit
    return ""


def flatten_properties(props: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """辞書プロパティを"."区切りで平坦化する"""
    result: dict[str, Any] = {}
    for key, value in props.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_properties(value, prefix=full_key))
        else:
            result[full_key] = value
    return result
