"""Flow-3D prepinパーサー: prepin.*ファイルのシミュレーションパラメータ解析

prepin.{jobname}形式のインプットファイルからパラメータを抽出する。
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


class Flow3dPrepinParser(AbstractFileParser):
    """Flow-3D prepinファイル解析パーサー

    prepin.*ファイルのシミュレーションパラメータを抽出し、
    ノードプロパティに反映する。
    逆転ファイル名パターン（basename=出力種類、拡張子=ジョブ名）を処理する。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # TODO: 検証環境確保後に実装
        # - prepin.*ファイルの検出
        # - シミュレーションパラメータ抽出
        # - 逆転ファイル名パターンの解決
        return graph
