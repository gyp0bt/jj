"""実験ディレクトリパーサー: 実験ラン構造の認識・メタデータ抽出

実験ディレクトリパターン（exp_001, run_001等）内のファイルを検出し、
実験IDを付与する。metrics.jsonがある場合はキーメトリクスを抽出する。

コア依存のみで動作する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# 実験ディレクトリパターン
EXPERIMENT_DIR_PATTERNS = [
    re.compile(r"^exp[_\-]?(\d+)$", re.IGNORECASE),
    re.compile(r"^run[_\-]?(\d+)$", re.IGNORECASE),
    re.compile(r"^experiment[_\-]?(\d+)$", re.IGNORECASE),
    re.compile(r"^trial[_\-]?(\d+)$", re.IGNORECASE),
]

# メトリクスファイル名
METRICS_FILENAMES = {"metrics.json", "results.json", "scores.json"}

# 抽出対象のメトリクスキー
EXTRACTABLE_METRICS = {
    "best_val_accuracy",
    "best_val_loss",
    "best_epoch",
    "final_train_loss",
    "final_val_loss",
    "test_accuracy",
    "test_loss",
    "f1_score",
    "auc",
    "rmse",
    "mae",
}


class ExperimentRunParser(AbstractFileParser):
    """実験ディレクトリ構造認識パーサー

    実験ディレクトリパターンに一致するパス内のファイルに
    experiment_id情報を付与する。metrics.jsonの内容から
    キーメトリクスを抽出してプロパティに追加する。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            path_str = node.properties.get("path", "")
            if not path_str:
                continue

            # パスから実験ディレクトリを検出
            exp_info = self._detect_experiment_dir(path_str)
            if not exp_info:
                continue

            exp_id, exp_dir_name = exp_info
            node.properties["experiment_id"] = exp_id
            node.properties["experiment_dir"] = exp_dir_name

            # メトリクスファイルの処理
            if node.name.lower() in METRICS_FILENAMES and node.format == "json":
                self._enrich_metrics(node, graph)

        return graph

    def _detect_experiment_dir(self, path_str: str) -> tuple[str, str] | None:
        """パスから実験ディレクトリ名とIDを抽出"""
        parts = Path(path_str).parts
        for part in parts:
            for pattern in EXPERIMENT_DIR_PATTERNS:
                match = pattern.match(part)
                if match:
                    return match.group(1), part
        return None

    def _enrich_metrics(self, node: Any, graph: Any) -> None:
        """metrics.jsonからキーメトリクスを抽出"""
        path_str = node.properties.get("path", "")
        if not path_str:
            return

        file_path = graph.project_root / path_str
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                data = json.loads(f.read())
        except (json.JSONDecodeError, OSError):
            logger.debug("メトリクス読込失敗: %s", path_str)
            return

        if not isinstance(data, dict):
            return

        # ノードタイプをexperiment_metricsに昇格
        node.type = "experiment_metrics"
        node.properties["ml_metrics"] = True

        # キーメトリクスの抽出
        metrics: dict[str, Any] = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in EXTRACTABLE_METRICS and isinstance(value, (int, float)):
                metrics[key_lower] = value
        if metrics:
            node.properties["ml_key_metrics"] = metrics
