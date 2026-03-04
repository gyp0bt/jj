"""CAE潜在Run発見パーサー

.inpファイル（Abaqus等）と対応する結果ファイル（.sta, .msg, .dat等）のペアから
CAE潜在Runを発見し、Run Nodeとrun_input/run_output/run_mediaリレーションを構築する。

検出ロジック:
1. グラフからgo_*.inp等の計算入力ノードをスキャン
2. result_of/has_output関係を辿って結果・出力ノードを収集
3. includes関係を辿って追加入力ノード（mesh, material等）を収集
4. ペアが見つかればRunCandidateを生成

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from services.parse.run_discoverer import AbstractRunDiscoverer, RunCandidate

if TYPE_CHECKING:
    from jj_types import Node
    from services.graph.project_graph import ProjectGraph

# 計算入力ファイルのformat値（拡張子からドットを除いたもの）
_INPUT_FORMATS: frozenset[str] = frozenset({"inp", "k", "key"})

# 結果ファイルのformat値
_RESULT_FORMATS: frozenset[str] = frozenset({"sta", "msg", "dat", "odb", "frd", "cvg"})

# 計算入力ノードのtype値（FileNameParserで付与されるファイルタイプ）
_INPUT_NODE_TYPES: frozenset[str] = frozenset({"go"})

# format値からソルバーを推定するマッピング
_FORMAT_TO_SOLVER: dict[str, str] = {
    "inp": "abaqus",
    "k": "lsdyna",
    "key": "lsdyna",
}


class CaeRunDiscoverer(AbstractRunDiscoverer):
    """CAE潜在Runの発見

    ファイル名パターンマッチングと既存リレーションにより、
    計算入力ファイルと結果ファイルのペアからCAE Runを推定する。

    既存パーサーとの関係:
    - ResultRelationParser(priority=30)が作成するresult_of関係を利用
    - OutputRelationParser(priority=32)が作成するhas_output関係を利用
    - IncludesRelationParser(priority=40)が作成するincludes関係を利用
    """

    priority = 200

    def discover_runs(self, graph: ProjectGraph) -> list[RunCandidate]:
        candidates: list[RunCandidate] = []

        # 設定から追加の入力/結果拡張子を取得
        input_formats = set(_INPUT_FORMATS)
        result_formats = set(_RESULT_FORMATS)

        for ext in graph.config.file_relations.input_extensions:
            input_formats.add(ext.lstrip(".").lower())
        for ext in graph.config.file_relations.result_extensions:
            result_formats.add(ext.lstrip(".").lower())

        # ソルバープロファイルの拡張子もマージ
        for profile in graph.config.solver_profiles.values():
            for ext in profile.input_extensions:
                input_formats.add(ext.lstrip(".").lower())
            for ext in profile.result_extensions:
                result_formats.add(ext.lstrip(".").lower())

        # basename(name) → ノードリストのマップ構築
        by_name: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            by_name[node.name].append(node)

        for _name, nodes in by_name.items():
            # 入力ノードと結果ノードを分類
            input_nodes: list[Node] = []
            result_nodes: list[Node] = []

            for node in nodes:
                fmt = node.format.lower() if node.format else ""
                # 結果拡張子を優先チェック（.datはLS-DYNA入力かつAbaqus結果のため）
                if fmt in result_formats:
                    result_nodes.append(node)
                elif fmt in input_formats and node.type in _INPUT_NODE_TYPES:
                    input_nodes.append(node)

            if not input_nodes:
                continue

            # 結果ノードがない場合でも、has_output関係がある可能性がある
            for inp_node in input_nodes:
                # result_of関係から結果ノードを取得（result→input方向）
                result_ids = set()
                for rel in graph.relations:
                    if rel.label == "result_of" and rel.node2_id == inp_node.id:
                        result_ids.add(rel.node1_id)

                # has_output関係から出力ノードを取得（input→output方向）
                output_ids = set()
                for rel in graph.relations:
                    if rel.label == "has_output" and rel.node1_id == inp_node.id:
                        output_ids.add(rel.node2_id)

                # basename一致の結果ノードも追加
                for rn in result_nodes:
                    result_ids.add(rn.id)

                # 結果も出力もなければRunは成立しない
                all_output_ids = result_ids | output_ids
                if not all_output_ids:
                    continue

                # includes関係から追加入力ノードを取得
                included_ids = _get_included_node_ids(graph, inp_node)

                # ソルバー推定
                solver = _detect_solver(inp_node)

                props: dict[str, Any] = {"solver": solver}
                # 解析ステータスがあれば追加
                analysis_status = inp_node.properties.get("analysis_status")
                if analysis_status:
                    props["analysis_status"] = analysis_status

                candidates.append(
                    RunCandidate(
                        name=f"{inp_node.name} {solver}解析",
                        run_type="cae_job",
                        input_node_ids=[inp_node.id, *included_ids],
                        output_node_ids=sorted(all_output_ids),
                        properties=props,
                    )
                )

        return candidates


def _get_included_node_ids(graph: ProjectGraph, node: Node) -> list[int]:
    """includes関係にあるノードのIDリストを返す"""
    included_ids = []
    for rel in graph.relations:
        if rel.node1_id == node.id and rel.label == "includes":
            included_ids.append(rel.node2_id)
    return included_ids


def _detect_solver(node: Node) -> str:
    """入力ファイルのformat値からソルバーを推定する"""
    fmt = node.format.lower() if node.format else ""
    return _FORMAT_TO_SOLVER.get(fmt, "unknown")
