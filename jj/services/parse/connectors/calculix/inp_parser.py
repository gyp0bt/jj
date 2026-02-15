"""CalculiX INPパーサー: Abaqusサブセットの.inp解析

Abaqus互換の.inpファイルを解析し、CalculiX固有の拡張キーワードを検出する。
検証環境確保後に本実装を行う（現在はスケルトン）。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

logger = logging.getLogger(__name__)


class CalculixInpParser(AbstractFileParser):
    """CalculiX INPファイル解析パーサー

    Abaqusサブセット形式の.inpファイルを解析し、
    CalculiX固有拡張キーワードの検出、
    .frd/.cvg結果ファイルのメタデータ抽出を行う。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # TODO: 検証環境確保後に実装
        # - .inpファイルの検出（Abaqus/CalculiX判定）
        # - CalculiX固有キーワードの検出
        # - .frd/.cvg結果ファイルの解析
        return graph
