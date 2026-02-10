"""メッシュプロパティ継承パーサー

go_*.inpが*INCLUDEで参照するmesh_*.inpのプロパティを
go_*.inpノードに継承する。

継承対象:
- ファイル名から解析されたプロパティ（例: mesh_t50_v1.inp → t:50）
- メッシュ統計情報（mesh_node_count, mesh_element_count, mesh_quality等）

除外:
- index/version相当のキー（idx/v/条件/バージョン等）
- path, tags, active, verbose_name等のメタプロパティ

priority=81: IncludesRelationParser(40)とAbaqusMeshParser(80)の後に実行。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from jj_types import Node
from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# 継承しないメタプロパティキー
_SKIP_KEYS: frozenset[str] = frozenset({
    "path",
    "tags",
    "active",
    "verbose_name",
    "date",
    "index",
    "version",
})


class MeshInheritParser(AbstractFileParser):
    """go_*.inpにincludeされたmesh_*.inpのプロパティを継承する

    includes関係を辿り、mesh_*.inpノードのプロパティのうち
    index/version以外をgo_*.inpに複製する。
    メッシュ統計情報（mesh_node_count等）も含めて継承する。
    """

    priority = 81  # IncludesRelationParser(40), AbaqusMeshParser(80)の後

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # vocab変換後のidx/vキーも除外対象に追加
        skip_keys = set(_SKIP_KEYS)
        vocab = graph.config.vocab
        for raw_key in ("idx", "v", "ver"):
            translated = vocab.get(raw_key)
            if translated:
                skip_keys.add(translated)

        # includes関係マップ: node1_id(go) → [node2_id(mesh)]
        includes_map: dict[int, list[int]] = defaultdict(list)
        for rel in graph.relations:
            if rel.label == "includes":
                includes_map[rel.node1_id].append(rel.node2_id)

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            # includeされたmesh_*.inpを探す
            for child_id in includes_map.get(node.id, []):
                child = graph.get_node_by_id(child_id)
                if child is None:
                    continue
                child_lower = child.name.lower()
                if not (child_lower.startswith("mesh_") or child_lower == "mesh"):
                    continue

                # meshのプロパティを継承（既存キーは上書きしない）
                for key, value in child.properties.items():
                    if key in skip_keys:
                        continue
                    if key not in node.properties:
                        node.properties[key] = value

        return graph
