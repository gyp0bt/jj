"""ML潜在Run発見パーサー

training_script + dataset + model_checkpoint/serialized_model のパターンから
ML学習Runを発見し、Run Nodeとrun_input/run_output/run_mediaリレーションを構築する。

検出ロジック:
1. グラフからtraining_scriptノードをスキャン
2. trains_with/produces_model/configured_by関係を辿って入出力を収集
3. スクリプトをmedia、データセットをinput、モデルをoutputとしてRunCandidateを生成

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from services.parse.run_discoverer import AbstractRunDiscoverer, RunCandidate

if TYPE_CHECKING:
    from jj_types import Node
    from services.graph.project_graph import ProjectGraph

# MLノードタイプ定義（dataflow_parser.pyと同一定義）
_ML_DATASET_TYPES: frozenset[str] = frozenset({"dataset"})
_ML_MODEL_TYPES: frozenset[str] = frozenset({"model_checkpoint", "serialized_model"})
_ML_SCRIPT_TYPES: frozenset[str] = frozenset({"training_script"})
_ML_CONFIG_TYPES: frozenset[str] = frozenset({"experiment_config", "optimization_config"})
_ML_METRICS_TYPES: frozenset[str] = frozenset({"experiment_metrics"})


class MlTrainingRunDiscoverer(AbstractRunDiscoverer):
    """ML学習潜在Runの発見

    training_scriptノードを起点として、MLDataFlowParser(priority=65)が
    構築した関係を辿り、学習Runを推定する。

    Run構造:
    - input: dataset + experiment_config
    - media: training_script (実行媒体)
    - output: model_checkpoint/serialized_model + experiment_metrics

    既存パーサーとの関係:
    - MLDataFlowParser(priority=65)が作成する trains_with/produces_model/configured_by を利用
    """

    priority = 210

    def discover_runs(self, graph: ProjectGraph) -> list[RunCandidate]:
        candidates: list[RunCandidate] = []

        # training_scriptノードを収集
        scripts: list[Node] = [n for n in graph.nodes if n.type in _ML_SCRIPT_TYPES]

        if not scripts:
            return candidates

        # リレーションインデックスの構築
        # node1_id → [(label, node2_id), ...]
        outgoing: dict[int, list[tuple[str, int]]] = {}
        # node2_id → [(label, node1_id), ...]
        incoming: dict[int, list[tuple[str, int]]] = {}
        for rel in graph.relations:
            outgoing.setdefault(rel.node1_id, []).append((rel.label, rel.node2_id))
            incoming.setdefault(rel.node2_id, []).append((rel.label, rel.node1_id))

        node_by_id: dict[int, Node] = {n.id: n for n in graph.nodes}

        for script in scripts:
            input_ids: list[int] = []
            output_ids: list[int] = []

            # trains_with: script → dataset → 入力
            for label, target_id in outgoing.get(script.id, []):
                if label == "trains_with":
                    target = node_by_id.get(target_id)
                    if target and target.type in _ML_DATASET_TYPES:
                        input_ids.append(target_id)

            # produces_model: script → model → 出力
            for label, target_id in outgoing.get(script.id, []):
                if label == "produces_model":
                    target = node_by_id.get(target_id)
                    if target and target.type in _ML_MODEL_TYPES:
                        output_ids.append(target_id)

            # configured_by: script → config → 入力
            config_ids: list[int] = []
            for label, target_id in outgoing.get(script.id, []):
                if label == "configured_by":
                    target = node_by_id.get(target_id)
                    if target and target.type in _ML_CONFIG_TYPES:
                        config_ids.append(target_id)
                        input_ids.append(target_id)

            # logs_to: metrics → model → metricsを出力に追加
            for out_id in list(output_ids):
                for label, source_id in incoming.get(out_id, []):
                    if label == "logs_to":
                        source = node_by_id.get(source_id)
                        if source and source.type in _ML_METRICS_TYPES:
                            output_ids.append(source_id)

            # データセットもモデルもなければRunは成立しない
            if not input_ids and not output_ids:
                continue

            # フレームワーク検出
            props: dict[str, Any] = {}
            frameworks = script.properties.get("ml_frameworks")
            if frameworks:
                props["frameworks"] = frameworks
            role = script.properties.get("ml_role")
            if role:
                props["role"] = role

            # run_typeの決定
            run_type = "ml_training"
            if role == "preprocessing":
                run_type = "ml_preprocessing"
            elif role == "inference":
                run_type = "ml_inference"

            candidates.append(
                RunCandidate(
                    name=f"{script.name} ML {run_type.replace('ml_', '')}",
                    run_type=run_type,
                    input_node_ids=input_ids,
                    output_node_ids=output_ids,
                    media_node_ids=[script.id],
                    properties=props,
                )
            )

        return candidates
