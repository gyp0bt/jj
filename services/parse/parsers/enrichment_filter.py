"""Enrichment-onlyノードフィルタ

.sta, .msg, .datノードをグラフから除外する。
これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
ノード自体はグラフから除外する。

results/ディレクトリ直下のファイルについて:
- go_inpと同じプロパティ（追加パラメータなし）のファイルは除外する
  例: results/go_idx1.v1_RF3.csv（RF3はresult_keyのみ、追加パラメータなし）
- go_inpと異なるプロパティ（追加パラメータあり）のファイルはノードとして残す
  例: results/go_idx1.v1_RF3_step0.csv（step0は追加パラメータ）

results/のサブディレクトリ内のファイル（例: results/step0/go_idx1.v1_RF3.csv）は
常にノードとして残す。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jj_types import Node
from plugins.base.parser import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# .sta, .msg, .dat はNode化せず情報のみgo_*.inpに割り当てる対象拡張子
_ENRICHMENT_ONLY_EXTENSIONS: frozenset[str] = frozenset({".sta", ".msg", ".dat"})

# 情報のみ読み取り、Node化しないディレクトリ名
_INFO_ONLY_DIRECTORIES: frozenset[str] = frozenset({"results"})


def _is_in_info_only_directory(path: str) -> bool:
    """ノードのパスがinfo-onlyディレクトリ直下かを判定

    results/直下のファイル（例: results/foo.json）は除外候補。
    results/のサブディレクトリ内のファイル（例: results/step0_frame10/foo.png）は
    除外しない（ノードとして残す）。
    """
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    # ファイル名を除いたディレクトリパーツを取得
    dir_parts = parts[:-1]
    for i, part in enumerate(dir_parts):
        if part in _INFO_ONLY_DIRECTORIES:
            # info-onlyディレクトリの直下（深さ1）のみ除外候補
            # サブディレクトリ（深さ2+）は除外しない
            depth = len(dir_parts) - i - 1
            if depth == 0:
                return True
    return False


def _count_suffix_tokens(filename: str, go_basenames: set[str]) -> int:
    """結果ファイル名からgo_basename後のサフィックストークン数を返す

    go_basename接頭辞マッチし、'_'区切りで分割したトークン数を返す。
    トークン数1 = result_keyのみ（追加パラメータなし）
    トークン数2+ = 追加パラメータあり

    マッチしない場合は0を返す。

    例:
        go_idx1.v1_RF3 (basenames={"go_idx1.v1"}) → 1（"RF3"のみ）
        go_idx1.v1_RF3_step0 → 2（"RF3", "step0"）
        go_idx1_RF3 (basenames={"go_idx1"}) → 1（"RF3"のみ）
        go_idx1_RF3_step0 → 2（"RF3", "step0"）
    """
    for basename in sorted(go_basenames, key=len, reverse=True):
        prefix = basename + "_"
        if filename.startswith(prefix):
            suffix = filename[len(prefix) :]
            if not suffix:
                return 0
            return len(suffix.split("_"))
    return 0


def _has_extra_params(node: Node, go_basenames: set[str]) -> bool:
    """results/直下のファイルがgo_inpに対して追加パラメータを持つか判定

    go_basename + result_key（1トークン）のみならFalse（同じプロパティ）。
    それ以上のトークンがあればTrue（追加パラメータあり）。

    例:
        go_idx1.v1_RF3.csv → False（result_keyのみ）
        go_idx1.v1_RF3_step0.csv → True（step0が追加パラメータ）
    """
    token_count = _count_suffix_tokens(node.name, go_basenames)
    return token_count >= 2


class EnrichmentOnlyFilter(AbstractFileParser):
    """enrichment-onlyノード（.sta, .msg, .dat, results/直下の一部）をグラフから除外

    これらのファイルの情報はgo_*.inpのプロパティに集約済みのため、
    ノード自体はグラフから除外する。.odbは残す。

    results/直下のファイルは追加パラメータの有無で判定:
    - 追加パラメータなし → 除外（go_inpと同じプロパティ）
    - 追加パラメータあり → ノードとして残す
    results/のサブディレクトリ内のファイルはノードとして残す。
    """

    priority = 99

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        excluded_ids: set[int] = set()

        # go_*.inpノードのbasename集合を構築
        input_extensions = graph.config.file_relations.input_extensions
        go_basenames: set[str] = set()
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue
            name_lower = node.name.lower()
            if name_lower.startswith("go_") or name_lower == "go":
                go_basenames.add(node.name)

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in _ENRICHMENT_ONLY_EXTENSIONS:
                excluded_ids.add(node.id)
                continue

            # results/直下のファイルを判定
            node_path = node.properties.get("path", "")
            if node_path and _is_in_info_only_directory(node_path):
                # 追加パラメータがある場合はノードとして残す
                if go_basenames and _has_extra_params(node, go_basenames):
                    continue
                excluded_ids.add(node.id)

        if excluded_ids:
            graph.remove_nodes(excluded_ids)

        return graph
