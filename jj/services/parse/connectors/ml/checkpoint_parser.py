"""PyTorchチェックポイントパーサー: モデルチェックポイント検出・メタデータ抽出

.pt/.pth/.ckptファイルを検出し、ノードタイプを「model_checkpoint」に昇格させる。
ファイル名からエポック番号やbest modelフラグを推定する。

コア依存のみで動作し、torch等のoptional依存は使用しない。

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

# PyTorchチェックポイント拡張子
CHECKPOINT_EXTENSIONS = {"pt", "pth", "ckpt"}

# エポック番号抽出パターン
EPOCH_PATTERN = re.compile(r"epoch[_\-]?(\d+)", re.IGNORECASE)

# best model判定パターン
BEST_PATTERN = re.compile(r"best", re.IGNORECASE)

# step番号抽出パターン
STEP_PATTERN = re.compile(r"step[_\-]?(\d+)", re.IGNORECASE)


class TorchCheckpointParser(AbstractFileParser):
    """PyTorchチェックポイント検出・メタデータ抽出パーサー

    対象拡張子のファイルノードをtype='model_checkpoint'に昇格させ、
    ファイル名からエポック番号やbest modelフラグを抽出する。
    """

    priority = 58

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        for node in graph.nodes:
            if node.format not in CHECKPOINT_EXTENSIONS:
                continue

            # model_checkpointノードに昇格
            node.type = "model_checkpoint"
            node.properties["ml_checkpoint"] = True
            node.properties["checkpoint_format"] = node.format

            stem = Path(node.name).stem.lower()

            # エポック番号抽出
            epoch_match = EPOCH_PATTERN.search(stem)
            if epoch_match:
                node.properties["epoch"] = int(epoch_match.group(1))

            # ステップ番号抽出
            step_match = STEP_PATTERN.search(stem)
            if step_match:
                node.properties["step"] = int(step_match.group(1))

            # best model判定
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
