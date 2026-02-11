"""出力ファイル関係パーサー群

入力-結果関係（result_of）、アセット関係（derived_from）、
includes関係、出力関係（has_output）を構築する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# has_output 関係で対象とする出力ファイル拡張子
OUTPUT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".csv",
        ".json",
        ".png",
        ".gif",
        ".xlsx",
        ".yaml",
        ".pptx",
        ".pdf",
        ".svg",
        ".html",
        ".txt",
    }
)


class ResultRelationParser(AbstractFileParser):
    """入力ファイルと結果ファイルの関係（result_of）を構築

    同じbasenameを持つファイルのうち、入力ファイル（.inp）と
    結果ファイル（.odb, .sta等）の間にresult_of関係を作成する。
    """

    priority = 30

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions
        result_extensions = graph.config.file_relations.result_extensions

        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            by_basename[node.name].append(node)

        for _basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            input_nodes = []
            result_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in result_extensions:
                    result_nodes.append(node)

            for input_node in input_nodes:
                for result_node in result_nodes:
                    if _nodes_have_same_props(input_node, result_node, vocab=graph.config.vocab):
                        graph.add_relation(
                            Relation(
                                id=graph.next_relation_id(),
                                label="result_of",
                                node1_id=result_node.id,
                                node2_id=input_node.id,
                            )
                        )

        return graph


class AssetRelationParser(AbstractFileParser):
    """アセットファイルと入力ファイルの関係（derived_from）を構築

    同じbasenameを持つファイルのうち、アセットファイル（.modfem等）と
    入力ファイル（.inp）の間にderived_from関係を作成する。
    """

    priority = 31

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions
        asset_extensions = graph.config.file_relations.asset_extensions

        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            by_basename[node.name].append(node)

        for _basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            input_nodes = []
            asset_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in asset_extensions:
                    asset_nodes.append(node)

            for input_node in input_nodes:
                for asset_node in asset_nodes:
                    if _nodes_have_same_props(input_node, asset_node, vocab=graph.config.vocab):
                        graph.add_relation(
                            Relation(
                                id=graph.next_relation_id(),
                                label="derived_from",
                                node1_id=input_node.id,
                                node2_id=asset_node.id,
                            )
                        )

        return graph


class IncludesRelationParser(AbstractFileParser):
    """inpファイルの*includeディレクティブからincludes関係を構築

    ファイル未変更時はキャッシュからincludeパスリストを取得し、
    ディスクI/Oをスキップする。
    """

    priority = 40

    @staticmethod
    def _extract_includes(file_path: Path) -> list[str]:
        """ファイルから*includeパスを抽出する"""
        include_pattern = re.compile(
            r"^\*include\s*,\s*input\s*=\s*(.+)$", re.IGNORECASE
        )
        includes: list[str] = []
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("**"):
                        continue
                    match = include_pattern.match(line)
                    if match:
                        includes.append(match.group(1).strip())
        except (OSError, IOError):
            pass
        return includes

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions

        for node in list(graph.nodes):
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            # キャッシュキー: ファイル未変更ならキャッシュからincludeパスを取得
            cache_key = f"includes:{file_path}"
            if not graph.is_file_modified(str(file_path)):
                cached_includes = graph.get_cache(cache_key)
                if cached_includes is not None:
                    include_paths = cached_includes
                else:
                    include_paths = self._extract_includes(file_path)
                    graph.set_cache(cache_key, include_paths)
            else:
                include_paths = self._extract_includes(file_path)
                graph.set_cache(cache_key, include_paths)

            for include_path in include_paths:
                include_filename = Path(include_path).name

                target_node = None
                for path, n in graph._node_by_path.items():
                    if (
                        path.endswith(include_path)
                        or Path(path).name == include_filename
                    ):
                        target_node = n
                        break

                if target_node:
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="includes",
                            node1_id=node.id,
                            node2_id=target_node.id,
                        )
                    )

        return graph


class OutputRelationParser(AbstractFileParser):
    """同一ファイルタイプのprops差分関連付け（has_output）を構築

    入力ファイルのbasenameを接頭辞として持つ出力ファイルを検出し、
    has_output関係でリンクする。
    例: go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv (has_output)
    """

    priority = 32

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        input_extensions = graph.config.file_relations.input_extensions
        result_extensions = graph.config.file_relations.result_extensions

        input_nodes: list[Node] = []
        output_candidates: list[Node] = []

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            ext_lower = ext.lower()
            if ext_lower in input_extensions:
                input_nodes.append(node)
            elif ext_lower in OUTPUT_EXTENSIONS or ext_lower in result_extensions:
                output_candidates.append(node)

        for inp_node in input_nodes:
            inp_basename = inp_node.name
            inp_index = graph.get_node_index(inp_node)

            for out_node in output_candidates:
                # 完全一致はresult_ofで処理済み
                if out_node.name == inp_basename:
                    continue

                # basename接頭辞マッチ
                if not out_node.name.startswith(inp_basename + "_"):
                    continue

                # 同じindexか確認
                out_index = graph.get_node_index(out_node)
                if inp_index and out_index and inp_index != out_index:
                    continue

                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="has_output",
                        node1_id=inp_node.id,
                        node2_id=out_node.id,
                    )
                )

        return graph


def _nodes_have_same_props(
    node1: Node,
    node2: Node,
    vocab: dict[str, str] | None = None,
) -> bool:
    """2つのノードが同じ主要プロパティを持つかチェック

    Args:
        node1: 比較元ノード
        node2: 比較先ノード
        vocab: config.vocabマッピング。idxのvocab変換後キーも比較対象に含める。
    """
    compare_keys: set[str] = {"index", "w", "t"}
    # vocabでidxが変換されている場合、変換後のキーも比較対象に含める
    if vocab:
        idx_translated = vocab.get("idx")
        if idx_translated:
            compare_keys.add(idx_translated)

    for key in compare_keys:
        val1 = node1.properties.get(key, "")
        val2 = node2.properties.get(key, "")
        if val1 and val2 and val1 != val2:
            return False

    return True
