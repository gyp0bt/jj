"""Obsidian Dailyパーサー

notes/dailyの日報を解析してグラフに追加する。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser
from services.parse.connectors.obsidian.daily import scan_daily_notes

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


class DailyNoteParser(AbstractFileParser):
    """notes/dailyの日報を解析してグラフに追加

    日報内のファイル参照を検出し、dailyノートNodeを作成して
    既存のファイルノードとの間にmentioned_in関係を作成する。
    """

    priority = 95

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        daily_dir = graph.project_root / "notes" / "daily"
        daily_notes = scan_daily_notes(daily_dir)

        if not daily_notes:
            return graph

        # ファイル名→ノードのインデックス
        name_to_nodes: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            name_with_ext = f"{node.name}.{node.format}" if node.format else node.name
            name_to_nodes[name_with_ext].append(node)
            name_to_nodes[node.name].append(node)

        for note in daily_notes:
            if not note.file_references:
                continue

            rel_path = graph.safe_relative_path(note.path)
            daily_node = Node(
                id=graph.next_node_id(),
                type="daily_note",
                name=note.path.stem,
                format="md",
                properties={
                    "path": rel_path,
                    "date": note.date,
                    "tags": note.tags,
                },
            )
            graph.add_node(daily_node)

            linked_node_ids: set[int] = set()
            for ref in note.file_references:
                matched = name_to_nodes.get(ref.filename, [])
                if not matched:
                    stem = Path(ref.filename).stem
                    matched = name_to_nodes.get(stem, [])

                for target_node in matched:
                    if target_node.id in linked_node_ids:
                        continue
                    linked_node_ids.add(target_node.id)

                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="mentioned_in",
                            node1_id=target_node.id,
                            node2_id=daily_node.id,
                        )
                    )

                    if ref.properties:
                        daily_props = target_node.properties.get("daily_notes", {})
                        daily_props[note.date] = ref.properties
                        target_node.properties["daily_notes"] = daily_props

                    if ref.section:
                        sections = target_node.properties.get("daily_sections", [])
                        entry = f"{note.date}: {ref.section}"
                        if entry not in sections:
                            sections.append(entry)
                        target_node.properties["daily_sections"] = sections

        return graph
