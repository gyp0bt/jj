"""サロゲートワークフロー検出器: CAE↔ML層間リレーション構築

CAEタスク（Layer 1）とMLタスク（Layer 2）、最適化タスク（Layer 3）を
跨ぐリレーションを検出し構築する。

三層データフローモデル:
  Layer 1 (CAE):   calculation_input, result, mesh, output, asset
  Layer 2 (ML):    dataset, model_checkpoint, training_script, etc.
  Layer 3 (Optim): optimization_study, optimization_config, trial_history

コア依存のみで動作する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from jj_types import Relation
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# Layer 1: CAEタイプ
CAE_NODE_TYPES = {
    "calculation_input",
    "result",
    "mesh",
    "output",
    "asset",
}

# CAE固有の拡張子
CAE_FORMATS = {
    "inp",
    "odb",
    "dat",
    "sta",
    "msg",
    "cae",
    "cas",
    "msh",
    "jou",
    "sif",
}

# Layer 2: MLタイプ
ML_NODE_TYPES = {
    "dataset",
    "model_checkpoint",
    "serialized_model",
    "training_script",
    "experiment_config",
    "experiment_metrics",
}

# Layer 3: 最適化タイプ
OPTIM_NODE_TYPES = {
    "optimization_study",
    "optimization_config",
    "trial_history",
}


def _get_layer(node: Any) -> int | None:
    """ノードの所属レイヤーを判定"""
    if node.type in CAE_NODE_TYPES or node.format in CAE_FORMATS:
        return 1
    if node.type in ML_NODE_TYPES:
        return 2
    if node.type in OPTIM_NODE_TYPES:
        return 3
    return None


def _project_root_segment(path_str: str) -> str:
    """パスの最上位ディレクトリを取得（プロジェクト共存判定用）

    例: "project/cae/file.inp" → "project"
         "cae/file.inp" → "cae"
         "file.inp" → ""  (ルート直下はマッチ対象外)
    """
    parts = PurePosixPath(path_str).parts
    return parts[0] if len(parts) >= 2 else ""


class SurrogateWorkflowDetector(AbstractFileParser):
    """サロゲートモデルワークフロー検出器

    CAE-ML-最適化の三層データフローにおける層間リレーションを構築:
    - extracted_from: dataset → CAE result (CAE結果からデータ抽出)
    - surrogate_of: model_checkpoint → CAE input (サロゲートモデルがCAEを近似)
    - optimizes: optimization_study → model_checkpoint (最適化対象)
    - uses_objective: optimization_study → training_script (目的関数の定義元)
    """

    priority = 70

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # レイヤー別にノードを分類
        layer1_nodes: list[Any] = []  # CAE
        layer2_nodes: list[Any] = []  # ML
        layer3_nodes: list[Any] = []  # Optimization

        for node in graph.nodes:
            layer = _get_layer(node)
            if layer == 1:
                layer1_nodes.append(node)
            elif layer == 2:
                layer2_nodes.append(node)
            elif layer == 3:
                layer3_nodes.append(node)

        # 層間リレーションの構築条件: 複数レイヤーに跨るノードが存在
        if not ((layer1_nodes and layer2_nodes) or (layer2_nodes and layer3_nodes) or (layer1_nodes and layer3_nodes)):
            return graph

        linked: set[tuple[int, int, str]] = set()
        new_relations: list[Relation] = []

        def _add_relation(label: str, node1: Any, node2: Any) -> None:
            key = (node1.id, node2.id, label)
            if key in linked:
                return
            linked.add(key)
            new_relations.append(
                Relation(
                    id=graph.next_relation_id(),
                    label=label,
                    node1_id=node1.id,
                    node2_id=node2.id,
                )
            )

        # L1-L2: extracted_from (dataset → CAE result)
        self._build_extracted_from(layer1_nodes, layer2_nodes, _add_relation)

        # L1-L2: surrogate_of (model → CAE input)
        self._build_surrogate_of(layer1_nodes, layer2_nodes, _add_relation)

        # L2-L3: optimizes (study → model)
        self._build_optimizes(layer2_nodes, layer3_nodes, _add_relation)

        # L2-L3: uses_objective (study → training_script)
        self._build_uses_objective(layer2_nodes, layer3_nodes, _add_relation)

        if new_relations:
            graph.add_relations(new_relations)
            logger.debug(
                "サロゲートワークフロー: %d件の層間リレーションを追加",
                len(new_relations),
            )

        return graph

    def _build_extracted_from(
        self,
        cae_nodes: list[Any],
        ml_nodes: list[Any],
        add_fn: Any,
    ) -> None:
        """dataset → CAE result の extracted_from リレーション構築

        データセットがCAE結果と同一プロジェクト内に共存する場合、
        そのデータセットはCAE結果から抽出されたと判定する。
        """
        cae_results = [n for n in cae_nodes if n.type in ("result", "output")]
        datasets = [n for n in ml_nodes if n.type == "dataset"]

        if not cae_results or not datasets:
            return

        # プロジェクトルートの近接性で判定
        for ds in datasets:
            ds_path = ds.properties.get("path", "")
            ds_root = _project_root_segment(ds_path)

            for cae_result in cae_results:
                cae_path = cae_result.properties.get("path", "")
                cae_root = _project_root_segment(cae_path)

                # 同一プロジェクト内に共存（上位2階層が同じ）
                if ds_root and cae_root and ds_root == cae_root:
                    add_fn("extracted_from", ds, cae_result)

    def _build_surrogate_of(
        self,
        cae_nodes: list[Any],
        ml_nodes: list[Any],
        add_fn: Any,
    ) -> None:
        """model → CAE input の surrogate_of リレーション構築

        サロゲートモデルがCAE入力テンプレートと同一プロジェクト内に
        共存する場合、サロゲートモデルはそのCAEシミュレーションを
        近似するモデルと判定する。
        """
        cae_inputs = [n for n in cae_nodes if n.type == "calculation_input"]
        models = [n for n in ml_nodes if n.type in ("model_checkpoint", "serialized_model")]

        if not cae_inputs or not models:
            return

        for model in models:
            model_path = model.properties.get("path", "")
            model_root = _project_root_segment(model_path)

            for cae_input in cae_inputs:
                cae_path = cae_input.properties.get("path", "")
                cae_root = _project_root_segment(cae_path)

                if model_root and cae_root and model_root == cae_root:
                    add_fn("surrogate_of", model, cae_input)

    def _build_optimizes(
        self,
        ml_nodes: list[Any],
        optim_nodes: list[Any],
        add_fn: Any,
    ) -> None:
        """optimization_study → model の optimizes リレーション構築

        最適化スタディとモデルが同一プロジェクト内に共存する場合、
        そのスタディはモデルの最適化を行っていると判定する。
        """
        studies = [n for n in optim_nodes if n.type == "optimization_study"]
        models = [n for n in ml_nodes if n.type in ("model_checkpoint", "serialized_model")]

        if not studies or not models:
            return

        for study in studies:
            study_path = study.properties.get("path", "")
            study_root = _project_root_segment(study_path)

            for model in models:
                model_path = model.properties.get("path", "")
                model_root = _project_root_segment(model_path)

                if study_root and model_root and study_root == model_root:
                    add_fn("optimizes", study, model)

    def _build_uses_objective(
        self,
        ml_nodes: list[Any],
        optim_nodes: list[Any],
        add_fn: Any,
    ) -> None:
        """optimization_study → training_script の uses_objective 構築

        最適化スタディと学習スクリプトが同一プロジェクト内に共存する場合。
        スクリプトにoptuna frameworkが検出されている場合は優先的にマッチ。
        """
        studies = [n for n in optim_nodes if n.type == "optimization_study"]
        scripts = [n for n in ml_nodes if n.type == "training_script"]
        # 最適化フラグ付きスクリプトも対象
        optim_scripts = [n for n in ml_nodes if n.properties.get("ml_optimization") and n.format == "py"]
        target_scripts = scripts + [s for s in optim_scripts if s not in scripts]

        if not studies or not target_scripts:
            return

        for study in studies:
            study_path = study.properties.get("path", "")
            study_root = _project_root_segment(study_path)

            for script in target_scripts:
                script_path = script.properties.get("path", "")
                script_root = _project_root_segment(script_path)

                if study_root and script_root and study_root == script_root:
                    add_fn("uses_objective", study, script)
