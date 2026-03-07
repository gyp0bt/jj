"""Abaqus結果パーサー

.sta/.msg/.datファイルの解析結果をノードのプロパティに付与する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import re
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


# .sta ファイルのインクリメント行パターン（Abaqus Standard形式）
# 形式: STEP  INC  ATT  SEVERE_DISCON  EQUIL_ITERS  TOTAL_ITERS  TOTAL_TIME ...
# ATT列に "U" サフィックスがあるとカットバック（収束失敗→再試行）
_STA_INCREMENT_LINE = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+(\d+)(U?)\s+(\d+)\s+(\d+)\s+(\d+)\s+",
)


def _parse_convergence_info(content: str) -> dict[str, Any]:
    """Abaqus Standard .sta ファイルからインクリメント・収束情報を抽出

    Returns
    -------
    dict with keys:
        - increment_count: 総インクリメント数
        - cutback_count: カットバック（収束失敗→再試行）の回数
        - total_iterations: 全イテレーション数の合計
        - max_equilibrium_iters: 1インクリメントあたりの最大平衡イテレーション数
        - step_count: ステップ数
    """
    info: dict[str, Any] = {}
    increments = 0
    cutbacks = 0
    total_iters = 0
    max_equil = 0
    steps: set[int] = set()

    for line in content.splitlines():
        m = _STA_INCREMENT_LINE.match(line)
        if not m:
            continue

        step_num = int(m.group(1))
        cutback_flag = m.group(4)
        equil_iters = int(m.group(6))
        total_line_iters = int(m.group(7))

        steps.add(step_num)
        increments += 1
        if cutback_flag == "U":
            cutbacks += 1
        total_iters += total_line_iters
        if equil_iters > max_equil:
            max_equil = equil_iters

    if increments > 0:
        info["increment_count"] = increments
        info["cutback_count"] = cutbacks
        info["total_iterations"] = total_iters
        info["max_equilibrium_iters"] = max_equil
        info["step_count"] = len(steps)

    return info


def parse_sta_file(sta_path: Path) -> dict[str, Any]:
    """Abaqus .sta ファイルを解析

    解析成否判定に加え、Abaqus Standardの収束情報を抽出する:
    - カットバック回数（ATT列の "U" サフィックス）
    - インクリメント数・ステップ数
    - 総イテレーション数・最大平衡イテレーション数
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

    # 収束情報の抽出（Abaqus Standard形式）
    convergence = _parse_convergence_info(content)
    result.update(convergence)

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

            # 収束情報をプロパティに付与
            convergence_keys = (
                "increment_count",
                "cutback_count",
                "total_iterations",
                "max_equilibrium_iters",
                "step_count",
            )
            for ck in convergence_keys:
                if ck in sta_info:
                    node.properties[ck] = sta_info[ck]

            inp_node = input_by_name.get(node.name)
            if inp_node:
                inp_node.properties["analysis_status"] = sta_info["analysis_status"]
                if sta_info["errors"]:
                    inp_node.properties["sta_errors"] = sta_info["errors"]
                if sta_info["warnings"]:
                    inp_node.properties["sta_warnings"] = sta_info["warnings"]
                for ck in convergence_keys:
                    if ck in sta_info:
                        inp_node.properties[ck] = sta_info[ck]

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
