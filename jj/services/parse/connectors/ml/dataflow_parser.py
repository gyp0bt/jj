"""MLデータフローパーサー: スクリプト→データセット→モデル間リレーション構築

ML関連ノード間の論理的な依存関係（データフロー）を検出し、
リレーションとしてグラフに追加する。
同一実験ディレクトリ内のノード、同一親ディレクトリ内のノード、
プロジェクトスコープのノードを段階的にマッチングする。

コア依存のみで動作する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from jj_types import Relation
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# ML関連ノードタイプ
ML_DATASET_TYPES = {"dataset"}
ML_MODEL_TYPES = {"model_checkpoint", "serialized_model"}
ML_SCRIPT_TYPES = {"training_script"}
ML_CONFIG_TYPES = {"experiment_config", "optimization_config"}
ML_METRICS_TYPES = {"experiment_metrics"}
ML_ALL_TYPES = ML_DATASET_TYPES | ML_MODEL_TYPES | ML_SCRIPT_TYPES | ML_CONFIG_TYPES | ML_METRICS_TYPES


def _parent_dir(path_str: str) -> str:
    """パスの親ディレクトリを返す"""
    parent = str(PurePosixPath(path_str).parent)
    return parent if parent != "." else ""


def _experiment_id(node: Any) -> str | None:
    """ノードのexperiment_idを取得"""
    return node.properties.get("experiment_id")


class MLDataFlowParser(AbstractFileParser):
    """MLデータフローパーサー

    ML関連ノード間にリレーションを構築する:
    - trains_with: training_script → dataset
    - produces_model: training_script → model_checkpoint
    - configured_by: training_script → experiment_config
    - evaluated_on: model_checkpoint → dataset (評価スクリプト経由)
    - logs_to: experiment_metrics → model_checkpoint (同一実験)
    """

    priority = 65

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # ノードをタイプ別に分類
        datasets: list[Any] = []
        models: list[Any] = []
        scripts: list[Any] = []
        configs: list[Any] = []
        metrics: list[Any] = []

        for node in graph.nodes:
            if node.type in ML_DATASET_TYPES:
                datasets.append(node)
            elif node.type in ML_MODEL_TYPES:
                models.append(node)
            elif node.type in ML_SCRIPT_TYPES:
                scripts.append(node)
            elif node.type in ML_CONFIG_TYPES:
                configs.append(node)
            elif node.type in ML_METRICS_TYPES:
                metrics.append(node)

        # ML関連ノードが不十分な場合はスキップ
        if not scripts and not models:
            return graph

        # 重複防止用セット（既存リレーションも含む）
        linked: set[tuple[int, int, str]] = {(r.node1_id, r.node2_id, r.label) for r in graph.relations}
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

        # experiment_id別のインデックス構築
        exp_nodes: dict[str, list[Any]] = defaultdict(list)
        for node in graph.nodes:
            eid = _experiment_id(node)
            if eid:
                exp_nodes[eid].append(node)

        # 1. trains_with: training_script → dataset
        for script in scripts:
            matched_datasets = self._find_related_datasets(script, datasets, exp_nodes)
            for ds in matched_datasets:
                _add_relation("trains_with", script, ds)

        # 2. produces_model: training_script → model_checkpoint
        for script in scripts:
            matched_models = self._find_related_models(script, models, exp_nodes)
            for model in matched_models:
                _add_relation("produces_model", script, model)

        # 3. configured_by: training_script → experiment_config
        for script in scripts:
            matched_configs = self._find_related_configs(script, configs, exp_nodes)
            for cfg in matched_configs:
                _add_relation("configured_by", script, cfg)

        # 4. logs_to: experiment_metrics → model_checkpoint (同一実験)
        for metric_node in metrics:
            eid = _experiment_id(metric_node)
            if not eid:
                continue
            for exp_node in exp_nodes.get(eid, []):
                if exp_node.type in ML_MODEL_TYPES:
                    _add_relation("logs_to", metric_node, exp_node)

        if new_relations:
            graph.add_relations(new_relations)
            logger.debug("MLデータフロー: %d件のリレーションを追加", len(new_relations))

        return graph

    def _find_related_datasets(
        self,
        script: Any,
        datasets: list[Any],
        exp_nodes: dict[str, list[Any]],
    ) -> list[Any]:
        """スクリプトに関連するデータセットを検出"""
        result: list[Any] = []

        # 1. 同一experiment_id
        eid = _experiment_id(script)
        if eid:
            for node in exp_nodes.get(eid, []):
                if node.type in ML_DATASET_TYPES:
                    result.append(node)
            if result:
                return result

        # 2. 同一親ディレクトリまたは兄弟ディレクトリ
        script_path = script.properties.get("path", "")
        script_parent = _parent_dir(script_path)
        script_grandparent = _parent_dir(script_parent) if script_parent else ""

        for ds in datasets:
            ds_path = ds.properties.get("path", "")
            ds_parent = _parent_dir(ds_path)
            ds_grandparent = _parent_dir(ds_parent) if ds_parent else ""

            # 同一親ディレクトリ or 兄弟ディレクトリ（共通の祖父母）
            if (script_parent and ds_parent and script_parent == ds_parent) or (
                script_grandparent and ds_grandparent and script_grandparent == ds_grandparent
            ):
                result.append(ds)

        return result

    def _find_related_models(
        self,
        script: Any,
        models: list[Any],
        exp_nodes: dict[str, list[Any]],
    ) -> list[Any]:
        """スクリプトに関連するモデルを検出"""
        result: list[Any] = []

        # 1. 同一experiment_id
        eid = _experiment_id(script)
        if eid:
            for node in exp_nodes.get(eid, []):
                if node.type in ML_MODEL_TYPES:
                    result.append(node)
            if result:
                return result

        # 2. 同一親ディレクトリまたは兄弟ディレクトリ
        script_path = script.properties.get("path", "")
        script_parent = _parent_dir(script_path)
        script_grandparent = _parent_dir(script_parent) if script_parent else ""

        for model in models:
            model_path = model.properties.get("path", "")
            model_parent = _parent_dir(model_path)
            model_grandparent = _parent_dir(model_parent) if model_parent else ""

            if (script_parent and model_parent and script_parent == model_parent) or (
                script_grandparent and model_grandparent and script_grandparent == model_grandparent
            ):
                result.append(model)

        return result

    def _find_related_configs(
        self,
        script: Any,
        configs: list[Any],
        exp_nodes: dict[str, list[Any]],
    ) -> list[Any]:
        """スクリプトに関連する設定ファイルを検出"""
        result: list[Any] = []

        # 1. 同一experiment_id
        eid = _experiment_id(script)
        if eid:
            for node in exp_nodes.get(eid, []):
                if node.type in ML_CONFIG_TYPES:
                    result.append(node)
            if result:
                return result

        # 2. 同一親ディレクトリまたは兄弟ディレクトリ
        script_path = script.properties.get("path", "")
        script_parent = _parent_dir(script_path)
        script_grandparent = _parent_dir(script_parent) if script_parent else ""

        for cfg in configs:
            cfg_path = cfg.properties.get("path", "")
            cfg_parent = _parent_dir(cfg_path)
            cfg_grandparent = _parent_dir(cfg_parent) if cfg_parent else ""

            if (script_parent and cfg_parent and script_parent == cfg_parent) or (
                script_grandparent and cfg_grandparent and cfg_grandparent == script_grandparent
            ):
                result.append(cfg)

        return result
