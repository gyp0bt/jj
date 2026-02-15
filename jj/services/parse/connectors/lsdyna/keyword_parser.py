"""LS-DYNAキーワードパーサー: .k/.key/.datファイルのキーワードカード解析

*KEYWORD行以降のカードデータを解析し、ノードプロパティに反映する。
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


class LsDynaKeywordParser(AbstractFileParser):
    """LS-DYNAキーワードカード解析パーサー

    .k/.key/.datファイルの*KEYWORDカードを解析し、
    材料・パート・セクション等の情報をノードプロパティに抽出する。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # TODO: 検証環境確保後に実装
        # - .k/.key/.datファイルの検出
        # - *KEYWORDカード解析
        # - 材料/パート/セクション情報の抽出
        return graph
