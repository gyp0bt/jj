"""クエリサービス

services/query の汎用フィルタ/ソートロジックを利用し、
GraphModelに対するノードフィルタリングを提供する。
API層（services/api）はこのサービスを経由してクエリ操作を行う。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from typing import Any

from jj_types import GraphModel, Node
from services.query.filters import (
    apply_prop_filters,
    node_prop_getter,
    parse_prop_filters,
)


class QueryService:
    """グラフデータに対するクエリ操作を提供するサービス

    GraphModelのノードに対してフィルタリング（type, active, name,
    propsプロパティ条件式）を適用し、結果を返す。
    """

    @staticmethod
    def filter_nodes(
        nodes: list[Node],
        *,
        type_filter: str | None = None,
        active_filter: bool | None = None,
        name_filter: str | None = None,
        query_params: dict[str, str] | None = None,
    ) -> list[Node]:
        """ノードリストにフィルタを一括適用する

        Args:
            nodes: フィルタ対象のノードリスト
            type_filter: ノードタイプでフィルタ（Noneで無効）
            active_filter: activeフラグでフィルタ（Noneで無効）
            name_filter: 名前の部分一致フィルタ（Noneで無効）
            query_params: クエリパラメータ辞書（props条件式フィルタ用）

        Returns:
            フィルタ通過したノードリスト
        """
        result = nodes

        if type_filter is not None:
            result = [n for n in result if n.type == type_filter]

        if active_filter is not None:
            result = [
                n
                for n in result
                if n.properties.get("active") == active_filter
            ]

        if name_filter is not None:
            name_lower = name_filter.lower()
            result = [n for n in result if name_lower in n.name.lower()]

        if query_params:
            prop_filters = parse_prop_filters(query_params)
            if prop_filters:
                result = apply_prop_filters(
                    result, prop_filters, prop_getter=node_prop_getter
                )

        return result

    @staticmethod
    def parse_prop_filters(
        query_params: dict[str, str],
    ) -> list[tuple[str, str, float]]:
        """クエリパラメータからprops条件式フィルタを抽出する

        services.query.parse_prop_filters への委譲。

        Args:
            query_params: リクエストのクエリパラメータ辞書

        Returns:
            [(プロパティキー, オペレータ, 比較値), ...] のリスト
        """
        return parse_prop_filters(query_params)

    @staticmethod
    def apply_prop_filters_to_nodes(
        nodes: list[Node],
        filters: list[tuple[str, str, float]],
    ) -> list[Node]:
        """ノードリストにprops条件式フィルタを適用する

        Args:
            nodes: フィルタ対象のノードリスト
            filters: [(プロパティキー, オペレータ, 比較値), ...]

        Returns:
            フィルタ通過したノードリスト
        """
        return apply_prop_filters(nodes, filters, prop_getter=node_prop_getter)
