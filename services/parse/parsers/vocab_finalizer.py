"""Vocab最終置換パーサー（廃止済み - 空操作）

vocab変換はparse時ではなく表示時のみ適用する設計に変更。
詳細: docs/specs/vocab-display-time.md

表示時変換はmodules/vocab_display.pyを使用する。

このクラスは後方互換のために残すが、apply()は空操作。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.base.parser import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class VocabFinalizer(AbstractFileParser):
    """Vocab最終置換パーサー（廃止済み - 空操作）

    vocab変換はparse時ではなく表示時のみ適用する設計に変更。
    modules/vocab_display.pyに表示時変換ロジックを移動済み。
    """

    priority = 100

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        return graph
