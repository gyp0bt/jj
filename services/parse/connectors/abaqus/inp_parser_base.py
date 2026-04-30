"""Abaqus INP解析パーサー

material.inpの高度な解析（abaqus_material Node化）、
*PARAMETER/**propsブロックからのプロパティ読み取り、
材料割り当て関係の構築、elset Node化を行う。

[READMEへ戻る](../../../../../README.md)
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jj_types import Node, Relation
from services.parse.base import AbstractFileParser, _parse_prop_token

if TYPE_CHECKING:
    from services.graph.project_graph import ProjectGraph


def parse_material_blocks(inp_path: Path) -> list[dict[str, Any]]:
    """Abaqus .inp ファイルから *MATERIAL ブロックを解析

    軽量なパーサーで *MATERIAL ブロックを抽出し、物性定義データを返す。
    """
    materials: list[dict[str, Any]] = []

    try:
        with inp_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return materials

    current_material: dict[str, Any] | None = None
    current_keyword: str | None = None
    current_data: list[list[float]] = []

    def _flush_keyword():
        nonlocal current_keyword, current_data
        if current_material is not None and current_keyword:
            current_material["keywords"].append(current_keyword)
            if current_data:
                current_material["properties"][current_keyword] = current_data
            current_keyword = None
            current_data = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("**"):
            continue

        if line.startswith("*"):
            norm = re.sub(r"\s+", "", line).lower()
            tokens = [s for s in norm.split(",") if s]
            keyword = tokens[0].replace("*", "")

            if keyword == "material":
                _flush_keyword()
                if current_material:
                    materials.append(current_material)

                orig_no_space = re.sub(r"\s+", "", line)
                orig_tokens = [s for s in orig_no_space.split(",") if s]
                name = ""
                for tok in orig_tokens[1:]:
                    if tok.lower().startswith("name="):
                        name = tok.split("=", 1)[1]
                        break

                current_material = {
                    "name": name,
                    "properties": {},
                    "keywords": [],
                }
                current_keyword = None
                current_data = []
                continue

            if current_material is not None:
                _flush_keyword()
                current_keyword = keyword
                current_data = []
                continue

        if current_material is not None and current_keyword:
            try:
                values = [float(v.strip()) for v in line.split(",") if v.strip()]
                if values:
                    current_data.append(values)
            except ValueError:
                pass

    _flush_keyword()
    if current_material:
        materials.append(current_material)

    return materials


class AbaqusInpParser(AbstractFileParser):
    """Abaqus INP解析パーサー

    material.inpの高度な解析（abaqus_material Node化）と
    *PARAMETER/**propsブロックからのプロパティ読み取りを行う。
    """

    priority = 60

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # material Nodeの構築
        self._build_material_nodes(graph)
        return graph

    @staticmethod
    def _is_material_source_node(node: Node) -> bool:
        """materialを読み取る対象ノードかどうかを判定"""
        ext = f".{node.format}" if node.format else ""
        if ext.lower() != ".inp":
            return False
        name_lower = node.name.lower()
        if name_lower.startswith("go_") or name_lower == "go":
            return True
        return bool(name_lower.startswith("material_") or name_lower == "material")

    def _build_material_nodes(self, graph: ProjectGraph) -> None:
        """material.inpの高度な解析 - Node(abaqus_material)を生成

        materialは.inpから切り出された定義であり、実ファイルが存在しない。
        vocab/token-key-mapを適用して、材料名のプロパティ変換・verbose_name生成を行う。
        """
        mat_nodes: list[Node] = []
        mat_relations: list[Relation] = []
        token_key_map = graph.config.token_key_map

        for node in list(graph.nodes):
            if not self._is_material_source_node(node):
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            materials = parse_material_blocks(file_path)

            for mat in materials:
                if not mat["name"]:
                    continue

                mat_name = mat["name"]

                # 材料名をトークン分割し、token-key-mapとvocabを適用
                raw_tokens = [t for t in mat_name.split("_") if t]
                mat_props: dict[str, str] = {}
                mat_tags: list[str] = []
                token_key_mapped_keys: set[str] = set()

                for token in raw_tokens:
                    mapped_key = token_key_map.get_key(token)
                    if mapped_key:
                        # token-key-map指定トークンは通常分割を上書き
                        parsed = _parse_prop_token(token)
                        if parsed:
                            mat_props.pop(parsed[0], None)
                        if token in mat_tags:
                            mat_tags.remove(token)
                        mat_props[mapped_key] = token
                        token_key_mapped_keys.add(mapped_key)
                    else:
                        parsed = _parse_prop_token(token)
                        if parsed:
                            mat_props[parsed[0]] = parsed[1]
                        else:
                            mat_tags.append(token)

                # 生キーのまま保持（vocab変換は表示時のみ）
                translated_props: dict[str, Any] = dict(mat_props)

                # verbose_name構築（生キーベース）
                verbose_parts: list[str] = []
                for key, value in translated_props.items():
                    if key in token_key_mapped_keys:
                        verbose_parts.append(str(value))
                    else:
                        verbose_parts.append(f"{key}{value}")
                for tag in mat_tags:
                    verbose_parts.append(tag)

                verbose_name = "_".join(verbose_parts) if verbose_parts else mat_name

                properties: dict[str, Any] = {
                    "source_file": node.properties.get("path", ""),
                    "keywords": mat["keywords"],
                    **translated_props,
                }

                if verbose_name and verbose_name != mat_name:
                    properties["verbose_name"] = verbose_name

                for keyword, data in mat["properties"].items():
                    properties[keyword] = data

                mat_node = Node(
                    id=graph.next_node_id(),
                    type="abaqus_material",
                    name=mat_name,
                    format="material",
                    properties=properties,
                )
                mat_nodes.append(mat_node)

                mat_relations.append(
                    Relation(
                        id=graph.next_relation_id(),
                        label="defined_in",
                        node1_id=mat_node.id,
                        node2_id=node.id,
                    )
                )

        graph.add_nodes(mat_nodes)
        graph.add_relations(mat_relations)

        # material verbose_nameと材料タグを更新
        self._enrich_material_verbose_name(graph, mat_nodes, mat_relations)

    @staticmethod
    def _enrich_material_verbose_name(
        graph: ProjectGraph,
        mat_nodes: list[Node],
        mat_relations: list[Relation],
    ) -> None:
        """material.inpのverbose_nameに含まれる材料名を設定"""
        source_materials: dict[int, list[str]] = defaultdict(list)
        for rel in mat_relations:
            if rel.label == "defined_in":
                for mn in mat_nodes:
                    if mn.id == rel.node1_id:
                        source_materials[rel.node2_id].append(mn.name)
                        break

        for node in graph.nodes:
            if node.id not in source_materials:
                continue
            name_lower = node.name.lower()
            if not (name_lower.startswith("material_") or name_lower == "material"):
                continue

            mat_names = sorted(source_materials[node.id])

            vn_parts = ["material", *mat_names]
            verbose_name = "_".join(vn_parts)
            node.properties["verbose_name"] = verbose_name
