"""MLコンフィグパーサー: ML設定ファイル解析

YAML/JSON設定ファイルをテキスト解析し、ML関連のキーワード（learning_rate,
epochs, batch_size等）を含むファイルをexperiment_configノードに昇格させる。

設定値の主要パラメータをプロパティとして抽出する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# ML設定ファイルの対象拡張子
CONFIG_EXTENSIONS = {"yaml", "yml", "json", "toml"}

# ML設定ファイル判定用キーワード（トップレベルまたは1階層目）
ML_CONFIG_KEYWORDS = {
    "learning_rate",
    "lr",
    "batch_size",
    "epochs",
    "optimizer",
    "model",
    "training",
    "n_trials",
    "search_space",
    "objective",
    "num_classes",
    "hidden_dim",
    "dropout",
    "scheduler",
    "weight_decay",
}

# 抽出対象のパラメータキー
EXTRACTABLE_PARAMS = {
    "learning_rate",
    "lr",
    "batch_size",
    "epochs",
    "optimizer",
    "n_trials",
    "objective",
    "num_classes",
    "dropout",
    "seed",
}


class MLConfigParser(AbstractFileParser):
    """ML設定ファイル解析パーサー

    YAML/JSON設定ファイルの内容を解析し、ML関連キーワードを含む
    ファイルをexperiment_configノードに昇格させる。
    """

    priority = 56

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            if node.format not in CONFIG_EXTENSIONS:
                continue
            # すでにdatasetとして処理済みなら対象外
            if node.type == "dataset":
                continue

            path_str = node.properties.get("path", "")
            if not path_str:
                continue

            file_path = graph.project_root / path_str
            if not file_path.exists():
                continue

            config_data = self._load_config(file_path, node.format)
            if config_data is None:
                continue

            # ML関連キーワードの検出
            ml_keys = self._detect_ml_keywords(config_data)
            if not ml_keys:
                continue

            # experiment_configに昇格
            node.type = "experiment_config"
            node.properties["ml_config"] = True
            node.properties["ml_config_keys"] = sorted(ml_keys)

            # 主要パラメータの抽出
            params = self._extract_params(config_data)
            if params:
                node.properties["ml_params"] = params

        return graph

    def _load_config(self, file_path: Path, fmt: str) -> dict | None:
        """設定ファイルを読み込む"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if fmt in ("yaml", "yml"):
                data = yaml.safe_load(content)
            elif fmt == "json":
                data = json.loads(content)
            else:
                return None

            if isinstance(data, dict):
                return data
        except Exception:
            logger.debug("設定ファイル読込失敗: %s", file_path)
        return None

    def _detect_ml_keywords(self, data: dict[str, Any]) -> set[str]:
        """設定データ内のML関連キーワードを検出（2階層まで探索）"""
        found: set[str] = set()

        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in ML_CONFIG_KEYWORDS:
                found.add(key_lower)
            # 1階層下も探索
            if isinstance(value, dict):
                for sub_key in value:
                    sub_lower = sub_key.lower()
                    if sub_lower in ML_CONFIG_KEYWORDS:
                        found.add(sub_lower)

        return found

    def _extract_params(self, data: dict[str, Any]) -> dict[str, Any]:
        """主要パラメータを再帰的に抽出（2階層まで）"""
        params: dict[str, Any] = {}

        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in EXTRACTABLE_PARAMS and not isinstance(value, (dict, list)):
                params[key_lower] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    sub_lower = sub_key.lower()
                    if sub_lower in EXTRACTABLE_PARAMS and not isinstance(sub_value, (dict, list)):
                        params[sub_lower] = sub_value

        return params
