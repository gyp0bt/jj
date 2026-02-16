"""Abaqus結果パーサー

.sta/.msg/.datファイルの解析結果をノードのプロパティに付与し、
includeファイルのプロパティをgo_*.inpに伝搬する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# 解析結果ファイルの成否判定用パターン
_STA_SUCCESS_PATTERN = re.compile(r"THE ANALYSIS HAS COMPLETED SUCCESSFULLY", re.IGNORECASE)
_STA_NOT_COMPLETED_PATTERN = re.compile(r"THE ANALYSIS HAS NOT BEEN COMPLETED", re.IGNORECASE)
_STA_ERROR_PATTERN = re.compile(r"\*\*\*ERROR:\s*(.+)", re.IGNORECASE)
_STA_WARNING_PATTERN = re.compile(r"\*\*\*WARNING:\s*(.+)", re.IGNORECASE)
_MSG_ERROR_PATTERN = re.compile(r"\*\*\*ERROR:\s*(.+)", re.IGNORECASE)
_MSG_WARNING_PATTERN = re.compile(r"\*\*\*WARNING:\s*(.+)", re.IGNORECASE)

# 数値正規化用パターン（重複排除で使用）
_NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?\b")


def _normalize_numbers(text: str) -> str:
    """メッセージ中の数値をプレースホルダに置換して正規化する

    例: "THE SYSTEM MATRIX HAS 289 NEGATIVE EIGENVALUES."
      → "THE SYSTEM MATRIX HAS {N} NEGATIVE EIGENVALUES."
    """
    return _NUMBER_PATTERN.sub("{N}", text)


def _deduplicate_messages(messages: list[str]) -> list[str]:
    """メッセージリストから重複を排除する

    数値のみが異なるメッセージは同一とみなす。
    例: "THE SYSTEM MATRIX HAS 289 NEGATIVE EIGENVALUES." と
        "THE SYSTEM MATRIX HAS 6 NEGATIVE EIGENVALUES." は重複。
    """
    seen: set[str] = set()
    result: list[str] = []
    for msg in messages:
        normalized = _normalize_numbers(msg)
        if normalized not in seen:
            seen.add(normalized)
            result.append(msg)
    return result


def parse_sta_file(sta_path: Path) -> dict[str, Any]:
    """Abaqus .sta ファイルを解析

    TODO(v0.2): カットバック・インクリメント収束情報の収集
    - Abaqus Standard: "1U", "2U" 等の表記でカットバック回数を検出。
      各表示行が1回のカットバック（ニュートンラフソン収束失敗→時間増分削減→再トライ）。
      インクリメント数・収束イテレーション数も収集する。
    - Abaqus Explicit: 別形式のstaファイル。サンプル入手後に対応。
    - 出力: cutback_count, increment_count, convergence_history 等をpropsに追加。
    - サンプルファイルが必要。後日対応。
    """
    result: dict[str, Any] = {
        "analysis_status": "unknown",
        "errors": [],
        "warnings": [],
    }
    try:
        with sta_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return result

    if _STA_SUCCESS_PATTERN.search(content):
        result["analysis_status"] = "completed"
    elif _STA_NOT_COMPLETED_PATTERN.search(content):
        result["analysis_status"] = "failed"

    for match in _STA_ERROR_PATTERN.finditer(content):
        result["errors"].append(match.group(1).strip())
    for match in _STA_WARNING_PATTERN.finditer(content):
        result["warnings"].append(match.group(1).strip())

    result["errors"] = _deduplicate_messages(result["errors"])
    result["warnings"] = _deduplicate_messages(result["warnings"])

    return result


def parse_msg_file(msg_path: Path) -> dict[str, Any]:
    """Abaqus .msg ファイルを解析"""
    result: dict[str, Any] = {"errors": [], "warnings": []}
    try:
        with msg_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return result

    for match in _MSG_ERROR_PATTERN.finditer(content):
        result["errors"].append(match.group(1).strip())
    for match in _MSG_WARNING_PATTERN.finditer(content):
        result["warnings"].append(match.group(1).strip())

    result["errors"] = _deduplicate_messages(result["errors"])
    result["warnings"] = _deduplicate_messages(result["warnings"])

    return result


def parse_dat_file(dat_path: Path) -> dict[str, Any]:
    """Abaqus .dat ファイルから計算時間情報を抽出"""
    result: dict[str, Any] = {}
    try:
        with dat_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return result

    num = r"([+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"

    # findallで全マッチを取得し、最後の値（最終サマリー）を採用
    cpu_matches = re.findall(rf"TOTAL\s+CPU\s+TIME\s*\(SEC\)\s*=\s*{num}", content, re.IGNORECASE)
    if cpu_matches:
        result["cpu_time"] = float(cpu_matches[-1])

    wall_matches = re.findall(rf"WALL\s*CLOCK\s+TIME\s*\(SEC\)\s*=\s*{num}", content, re.IGNORECASE)
    if wall_matches:
        result["wallclock_time"] = float(wall_matches[-1])

    # .datファイルからもwarning/errorを抽出
    for match in _MSG_ERROR_PATTERN.finditer(content):
        result.setdefault("errors", []).append(match.group(1).strip())
    for match in _MSG_WARNING_PATTERN.finditer(content):
        result.setdefault("warnings", []).append(match.group(1).strip())
    if "errors" in result:
        result["errors"] = _deduplicate_messages(result["errors"])
    if "warnings" in result:
        result["warnings"] = _deduplicate_messages(result["warnings"])

    return result


class AbaqusResultParser(AbstractFileParser):
    """Abaqus結果ファイル（.sta/.msg/.dat）の解析結果をプロパティに付与"""

    priority = 70

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        self._enrich_sta_status(graph)
        self._enrich_msg_status(graph)
        self._enrich_dat_status(graph)
        return graph

    @staticmethod
    def _enrich_sta_status(graph: ProjectGraph) -> None:
        input_extensions = graph.config.file_relations.input_extensions
        input_by_name: dict[str, Node] = {}
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_by_name[node.name] = node

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".sta":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            sta_info = parse_sta_file(file_path)
            node.properties["analysis_status"] = sta_info["analysis_status"]
            if sta_info["errors"]:
                node.properties["errors"] = sta_info["errors"]
            if sta_info["warnings"]:
                node.properties["warnings"] = sta_info["warnings"]

            inp_node = input_by_name.get(node.name)
            if inp_node:
                inp_node.properties["analysis_status"] = sta_info["analysis_status"]
                if sta_info["errors"]:
                    inp_node.properties["sta_errors"] = sta_info["errors"]
                if sta_info["warnings"]:
                    inp_node.properties["sta_warnings"] = sta_info["warnings"]

    @staticmethod
    def _enrich_msg_status(graph: ProjectGraph) -> None:
        input_extensions = graph.config.file_relations.input_extensions
        input_by_name: dict[str, Node] = {}
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_by_name[node.name] = node

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".msg":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            msg_info = parse_msg_file(file_path)
            if msg_info["errors"]:
                node.properties["msg_errors"] = msg_info["errors"]
            if msg_info["warnings"]:
                node.properties["msg_warnings"] = msg_info["warnings"]

            inp_node = input_by_name.get(node.name)
            if inp_node:
                if msg_info["errors"]:
                    inp_node.properties["msg_errors"] = msg_info["errors"]
                if msg_info["warnings"]:
                    inp_node.properties["msg_warnings"] = msg_info["warnings"]

    @staticmethod
    def _enrich_dat_status(graph: ProjectGraph) -> None:
        input_extensions = graph.config.file_relations.input_extensions
        input_by_name: dict[str, Node] = {}
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_by_name[node.name] = node

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".dat":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            dat_info = parse_dat_file(file_path)
            if dat_info.get("cpu_time") is not None:
                node.properties["cpu_time"] = dat_info["cpu_time"]
            if dat_info.get("wallclock_time") is not None:
                node.properties["wallclock_time"] = dat_info["wallclock_time"]
            if dat_info.get("errors"):
                node.properties["dat_errors"] = dat_info["errors"]
            if dat_info.get("warnings"):
                node.properties["dat_warnings"] = dat_info["warnings"]

            inp_node = input_by_name.get(node.name)
            if inp_node:
                if dat_info.get("cpu_time") is not None:
                    inp_node.properties["cpu_time"] = dat_info["cpu_time"]
                if dat_info.get("wallclock_time") is not None:
                    inp_node.properties["wallclock_time"] = dat_info["wallclock_time"]
                if dat_info.get("errors"):
                    inp_node.properties["dat_errors"] = dat_info["errors"]
                if dat_info.get("warnings"):
                    inp_node.properties["dat_warnings"] = dat_info["warnings"]


class AbaqusIncludePropertyParser(AbstractFileParser):
    """includeファイルのプロパティをgo_*.inpに伝搬"""

    priority = 86

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        includes_map: dict[int, list[int]] = defaultdict(list)
        for rel in graph.relations:
            if rel.label == "includes":
                includes_map[rel.node1_id].append(rel.node2_id)

        if not includes_map:
            return graph

        for parent_id, child_ids in includes_map.items():
            parent = graph.get_node_by_id(parent_id)
            if parent is None:
                continue

            name_lower = parent.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            include_props: dict[str, dict[str, Any]] = {}

            for child_id in child_ids:
                child = graph.get_node_by_id(child_id)
                if child is None:
                    continue

                child_file = child.properties.get("path", child.name)
                child_summary: dict[str, Any] = {}

                for key in (
                    "mesh_node_count",
                    "mesh_element_count",
                    "mesh_element_types",
                    "mesh_elset_summary",
                    "mesh_quality",
                ):
                    if key in child.properties:
                        child_summary[key] = child.properties[key]
                        if key not in parent.properties:
                            parent.properties[key] = child.properties[key]

                for key in (
                    "analysis_status",
                    "sta_errors",
                    "sta_warnings",
                    "msg_errors",
                    "msg_warnings",
                ):
                    if key in child.properties:
                        child_summary[key] = child.properties[key]

                if "keywords" in child.properties:
                    child_summary["keywords"] = child.properties["keywords"]

                if child_summary:
                    include_props[child_file] = child_summary

            if include_props:
                parent.properties["include_properties"] = include_props

        return graph
