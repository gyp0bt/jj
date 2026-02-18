"""scikit-learnモデルパーサー: シリアライズ済みモデル検出・メタデータ抽出

.pkl/.joblibファイルを検出し、ノードタイプを「serialized_model」に昇格させる。
ファイル名からモデル種別を推定する。

コア依存のみで動作し、sklearn/joblib等のoptional依存は使用しない。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)

# シリアライズ済みモデル拡張子
MODEL_EXTENSIONS = {"pkl", "joblib"}

# モデル種別推定パターン
MODEL_TYPE_PATTERNS: dict[str, str] = {
    "classifier": "classifier",
    "regressor": "regressor",
    "pipeline": "pipeline",
    "scaler": "scaler",
    "encoder": "encoder",
    "vectorizer": "vectorizer",
    "transformer": "transformer",
    "model": "model",
}

# best/finalモデル判定パターン
BEST_PATTERN = re.compile(r"best|final|prod", re.IGNORECASE)


class SklearnModelParser(AbstractFileParser):
    """scikit-learnシリアライズ済みモデル検出パーサー

    対象拡張子のファイルノードをtype='serialized_model'に昇格させ、
    ファイル名からモデル種別やbest判定を推定する。
    """

    priority = 59

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            if node.format not in MODEL_EXTENSIONS:
                continue

            # serialized_modelノードに昇格
            node.type = "serialized_model"
            node.properties["ml_serialized_model"] = True
            node.properties["serialization_format"] = node.format

            stem = Path(node.name).stem.lower()

            # モデル種別推定
            for pattern, model_type in MODEL_TYPE_PATTERNS.items():
                if pattern in stem:
                    node.properties["model_type"] = model_type
                    break

            # best/finalモデル判定
            if BEST_PATTERN.search(stem):
                node.properties["is_best"] = True

            # ファイルサイズ取得
            path_str = node.properties.get("path", "")
            if path_str:
                file_path = graph.project_root / path_str
                if file_path.exists():
                    try:
                        size_bytes = file_path.stat().st_size
                        node.properties["file_size_bytes"] = size_bytes
                    except OSError:
                        pass

        return graph
