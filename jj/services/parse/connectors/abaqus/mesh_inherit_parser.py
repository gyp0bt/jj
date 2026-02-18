"""include先プロパティ継承パーサー（Abaqusプラグイン）

go_*.inpが*INCLUDEで参照する全ファイル（mesh_*, material_*, step_*等）の
プロパティをgo_*.inpノードに直接継承する。

継承対象:
- ファイル名から解析されたプロパティ（例: mesh_t50_v1.inp → t:50）
- メッシュ統計情報（mesh_node_count, mesh_element_count, mesh_quality等）
- material/step等のinclude先が持つ任意のプロパティ

除外:
- index/version相当のキー（idx/v/条件/バージョン等）
- path, tags, active, verbose_name等のメタプロパティ

priority=81: IncludesRelationParser(40)とAbaqusMeshParser(80)の後に実行。

status-088でservices/parse/parsers/からAbaqusプラグインに移動。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from services.parse.base import AbstractFileParser

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph

# 継承しないメタプロパティキー
_SKIP_KEYS: frozenset[str] = frozenset(
    {
        "path",
        "active",
        "verbose_name",
        "date",
        "index",
        "version",
    }
)

# 複数include先からマージする辞書型プロパティキー
# 例: 2つのmeshファイルをincludeする場合、elset情報を統合する
_MERGE_DICT_KEYS: frozenset[str] = frozenset(
    {
        "mesh_elset_summary",
        "mesh_element_quality",
        "mesh_element_types",
    }
)


class MeshInheritParser(AbstractFileParser):
    """go_*.inpにincludeされた全ファイルのプロパティを継承する

    includes関係を辿り、include先ノードのプロパティのうち
    index/version/メタプロパティ以外をgo_*.inpの直下プロパティに追加する。
    メッシュ統計情報（mesh_node_count, mesh_quality等）も含めて継承する。
    go_*が既に持っているキーは上書きしない（go_*自身の値を優先）。
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

        # includes関係マップ: node1_id(go) → [node2_id(included)]
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

            # includeされた全ファイルのプロパティを継承
            for child_id in includes_map.get(node.id, []):
                child = graph.get_node_by_id(child_id)
                if child is None:
                    continue

                # include先のプロパティを直下に追加
                for key, value in child.properties.items():
                    if key in skip_keys:
                        continue
                    if key not in node.properties:
                        node.properties[key] = value
                    elif key in _MERGE_DICT_KEYS and isinstance(node.properties[key], dict) and isinstance(value, dict):
                        # メッシュ関連の辞書プロパティは複数include先からマージ
                        node.properties[key] = {**node.properties[key], **value}

        return graph
