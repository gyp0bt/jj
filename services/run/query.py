"""Run検索・比較・トレーサビリティサービス

RunQueryServiceはGraphModelに対してRunの検索・比較・分析を提供する。
ComparisonGroupは比較対象のRunグループを表現する。
PropertyTraceはRun-Property双方向追跡の中間表現。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jj_types import (
    RUN_INPUT,
    RUN_MEDIA,
    RUN_OUTPUT,
    GraphModel,
    Node,
    NodeCategory,
)


@dataclass
class RunIO:
    """Runの入力・出力・実行媒体"""

    inputs: list[Node] = field(default_factory=list)
    outputs: list[Node] = field(default_factory=list)
    media: list[Node] = field(default_factory=list)


class ComparisonAxis(str, Enum):
    """比較の軸"""

    INPUT = "input"
    MEDIA = "media"
    VERSION = "version"
    CROSS_DOMAIN = "cross_domain"


@dataclass
class ComparisonGroup:
    """比較対象のRunグループ"""

    runs: list[Node]
    axis: ComparisonAxis
    common_aspects: dict[str, Any] = field(default_factory=dict)
    varying_aspects: list[str] = field(default_factory=list)


@dataclass
class RunDiff:
    """2つのRunの差分"""

    common_inputs: list[Node] = field(default_factory=list)
    diff_inputs: tuple[list[Node], list[Node]] = field(default_factory=lambda: ([], []))
    common_outputs: list[Node] = field(default_factory=list)
    diff_outputs: tuple[list[Node], list[Node]] = field(default_factory=lambda: ([], []))
    common_media: list[Node] = field(default_factory=list)
    diff_media: tuple[list[Node], list[Node]] = field(default_factory=lambda: ([], []))
    property_diffs: dict[str, tuple[Any, Any]] = field(default_factory=dict)


@dataclass
class PropertyTrace:
    """プロパティの帰属情報

    Run-Property双方向追跡の単位。あるプロパティがどのRunの
    どの出力ノードに由来するかを表現する。
    """

    run_id: int
    run_name: str
    node_id: int
    node_name: str
    property_key: str
    property_value: Any
    timestamp: str | None = None


@dataclass
class RunPropertySummary:
    """Runのプロパティ生成サマリー"""

    run_node: Node
    output_nodes: list[Node] = field(default_factory=list)
    properties_by_node: dict[int, list[PropertyTrace]] = field(default_factory=dict)
    total_property_count: int = 0
    unique_keys: set[str] = field(default_factory=set)


# Runメタプロパティ（Run自体の管理用キーで、出力ノードのプロパティではない）
_RUN_META_KEYS = frozenset(
    {
        "run_type",
        "run_status",
        "discovery",
        "exit_code",
        "started_at",
        "finished_at",
        "duration_seconds",
        "host",
        "user",
        "command",
        "path",
    }
)


class RunQueryService:
    """Runの検索・比較・トレーサビリティ分析"""

    def __init__(self, graph: GraphModel) -> None:
        self._graph = graph
        self._node_by_id: dict[int, Node] = {n.id: n for n in graph.nodes}

    def get_runs(self, run_type: str | None = None, run_status: str | None = None) -> list[Node]:
        """条件に合致するRunを検索"""
        runs = [n for n in self._graph.nodes if n.category == NodeCategory.RUN]
        if run_type is not None:
            runs = [r for r in runs if r.properties.get("run_type") == run_type]
        if run_status is not None:
            runs = [r for r in runs if r.properties.get("run_status") == run_status]
        return runs

    def get_run_io(self, run_node: Node) -> RunIO:
        """Runの入力・出力・媒体を取得"""
        inputs: list[Node] = []
        outputs: list[Node] = []
        media: list[Node] = []

        for rel in self._graph.relations:
            if rel.node1_id != run_node.id:
                continue
            target = self._node_by_id.get(rel.node2_id)
            if target is None:
                continue
            if rel.label == RUN_INPUT:
                inputs.append(target)
            elif rel.label == RUN_OUTPUT:
                outputs.append(target)
            elif rel.label == RUN_MEDIA:
                media.append(target)

        return RunIO(inputs=inputs, outputs=outputs, media=media)

    def find_comparable_runs(self, run_node: Node) -> list[ComparisonGroup]:
        """比較可能なRunをグループ化して返す"""
        groups: list[ComparisonGroup] = []
        this_io = self.get_run_io(run_node)
        this_input_ids = {n.id for n in this_io.inputs}
        this_media_ids = {n.id for n in this_io.media}

        all_runs = [r for r in self.get_runs() if r.id != run_node.id]

        # 同一run_typeのRunを候補とする
        same_type_runs = [r for r in all_runs if r.properties.get("run_type") == run_node.properties.get("run_type")]

        # 入力が異なるRun（パラメータスタディ）
        diff_input_runs = []
        for other in same_type_runs:
            other_io = self.get_run_io(other)
            other_input_ids = {n.id for n in other_io.inputs}
            other_media_ids = {n.id for n in other_io.media}
            if this_media_ids & other_media_ids and this_input_ids != other_input_ids:
                diff_input_runs.append(other)

        if diff_input_runs:
            groups.append(
                ComparisonGroup(
                    runs=[run_node, *diff_input_runs],
                    axis=ComparisonAxis.INPUT,
                    common_aspects={"media_ids": sorted(this_media_ids)},
                    varying_aspects=["inputs"],
                )
            )

        # 媒体が異なるRun（ソルバー比較）
        diff_media_runs = []
        for other in all_runs:
            other_io = self.get_run_io(other)
            other_input_ids = {n.id for n in other_io.inputs}
            other_media_ids = {n.id for n in other_io.media}
            if this_input_ids & other_input_ids and this_media_ids != other_media_ids:
                diff_media_runs.append(other)

        if diff_media_runs:
            groups.append(
                ComparisonGroup(
                    runs=[run_node, *diff_media_runs],
                    axis=ComparisonAxis.MEDIA,
                    common_aspects={"input_ids": sorted(this_input_ids)},
                    varying_aspects=["media"],
                )
            )

        return groups

    def diff_runs(self, run_a: Node, run_b: Node) -> RunDiff:
        """2つのRunの差分を取得"""
        io_a = self.get_run_io(run_a)
        io_b = self.get_run_io(run_b)

        a_input_ids = {n.id for n in io_a.inputs}
        b_input_ids = {n.id for n in io_b.inputs}
        a_output_ids = {n.id for n in io_a.outputs}
        b_output_ids = {n.id for n in io_b.outputs}
        a_media_ids = {n.id for n in io_a.media}
        b_media_ids = {n.id for n in io_b.media}

        common_input = [n for n in io_a.inputs if n.id in b_input_ids]
        common_output = [n for n in io_a.outputs if n.id in b_output_ids]
        common_media = [n for n in io_a.media if n.id in b_media_ids]

        diff_inputs_a = [n for n in io_a.inputs if n.id not in b_input_ids]
        diff_inputs_b = [n for n in io_b.inputs if n.id not in a_input_ids]
        diff_outputs_a = [n for n in io_a.outputs if n.id not in b_output_ids]
        diff_outputs_b = [n for n in io_b.outputs if n.id not in a_output_ids]
        diff_media_a = [n for n in io_a.media if n.id not in b_media_ids]
        diff_media_b = [n for n in io_b.media if n.id not in a_media_ids]

        # プロパティの差分
        all_keys = set(run_a.properties.keys()) | set(run_b.properties.keys())
        prop_diffs: dict[str, tuple[Any, Any]] = {}
        for key in all_keys:
            val_a = run_a.properties.get(key)
            val_b = run_b.properties.get(key)
            if val_a != val_b:
                prop_diffs[key] = (val_a, val_b)

        return RunDiff(
            common_inputs=common_input,
            diff_inputs=(diff_inputs_a, diff_inputs_b),
            common_outputs=common_output,
            diff_outputs=(diff_outputs_a, diff_outputs_b),
            common_media=common_media,
            diff_media=(diff_media_a, diff_media_b),
            property_diffs=prop_diffs,
        )

    # --- トレーサビリティ ---

    def get_run_properties(self, run_node: Node) -> list[PropertyTrace]:
        """Run→Property: Runが生成/変更したプロパティを出力ノードから収集

        run_outputリレーション経由で出力ノードを辿り、
        各ノードのプロパティをPropertyTraceとして返す。
        """
        io = self.get_run_io(run_node)
        traces: list[PropertyTrace] = []
        timestamp = run_node.properties.get("started_at")

        for out_node in io.outputs:
            for key, value in out_node.properties.items():
                if key.startswith("_") or key in _RUN_META_KEYS:
                    continue
                traces.append(
                    PropertyTrace(
                        run_id=run_node.id,
                        run_name=run_node.name,
                        node_id=out_node.id,
                        node_name=out_node.name,
                        property_key=key,
                        property_value=value,
                        timestamp=timestamp,
                    )
                )

        return traces

    def get_property_source_runs(self, node: Node) -> list[PropertyTrace]:
        """Property→Run: ノードのプロパティを生成したRunを逆引き

        全Runのrun_outputリレーションを走査し、対象ノードを出力に含むRunを特定する。
        """
        runs = self.get_runs()
        traces: list[PropertyTrace] = []

        for run_node in runs:
            io = self.get_run_io(run_node)
            output_ids = {n.id for n in io.outputs}
            if node.id not in output_ids:
                continue

            timestamp = run_node.properties.get("started_at")
            for key, value in node.properties.items():
                if key.startswith("_") or key in _RUN_META_KEYS:
                    continue
                traces.append(
                    PropertyTrace(
                        run_id=run_node.id,
                        run_name=run_node.name,
                        node_id=node.id,
                        node_name=node.name,
                        property_key=key,
                        property_value=value,
                        timestamp=timestamp,
                    )
                )

        return traces

    def get_run_property_summary(self, run_node: Node) -> RunPropertySummary:
        """Runのプロパティ生成サマリーを返す"""
        io = self.get_run_io(run_node)
        traces = self.get_run_properties(run_node)

        props_by_node: dict[int, list[PropertyTrace]] = {}
        unique_keys: set[str] = set()

        for trace in traces:
            props_by_node.setdefault(trace.node_id, []).append(trace)
            unique_keys.add(trace.property_key)

        return RunPropertySummary(
            run_node=run_node,
            output_nodes=io.outputs,
            properties_by_node=props_by_node,
            total_property_count=len(traces),
            unique_keys=unique_keys,
        )

    def find_runs_by_property(self, property_key: str, property_value: Any = None) -> list[PropertyTrace]:
        """プロパティキー（+値）から関連するRunを検索

        全Runの出力ノードを走査し、指定キーを持つプロパティのRunを返す。
        property_valueが指定された場合、値の一致も条件に含む。
        """
        runs = self.get_runs()
        traces: list[PropertyTrace] = []

        for run_node in runs:
            io = self.get_run_io(run_node)
            timestamp = run_node.properties.get("started_at")

            for out_node in io.outputs:
                if property_key not in out_node.properties:
                    continue
                value = out_node.properties[property_key]
                if property_value is not None and value != property_value:
                    continue
                traces.append(
                    PropertyTrace(
                        run_id=run_node.id,
                        run_name=run_node.name,
                        node_id=out_node.id,
                        node_name=out_node.name,
                        property_key=property_key,
                        property_value=value,
                        timestamp=timestamp,
                    )
                )

        return traces
