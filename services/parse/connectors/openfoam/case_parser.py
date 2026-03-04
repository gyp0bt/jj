"""OpenFOAMケースパーサー: ケースディレクトリ構造の検出・controlDict解析

system/controlDictからソルバータイプ・制御パラメータを抽出する。
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


class OpenFoamCaseParser(AbstractFileParser):
    """OpenFOAMケースディレクトリ解析パーサー

    system/controlDictからソルバータイプ・制御パラメータを抽出し、
    constant/transportPropertiesからの物性値抽出、
    タイムステップディレクトリの結果メタデータを収集する。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # TODO: 検証環境確保後に実装
        # - system/controlDictの検出・解析
        # - ソルバータイプ・制御パラメータ抽出
        # - タイムステップディレクトリの認識
        return graph
