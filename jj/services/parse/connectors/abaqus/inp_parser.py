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
from typing import TYPE_CHECKING, Any, Optional

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
    except (OSError, IOError):
        return materials

    current_material: Optional[dict[str, Any]] = None
    current_keyword: Optional[str] = None
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
        if name_lower.startswith("material_") or name_lower == "material":
            return True
        return False

    def _build_material_nodes(self, graph: ProjectGraph) -> None:
        """material.inpの高度な解析 - Node(abaqus_material)を生成

        materialは.inpから切り出された定義であり、実ファイルが存在しない。
        vocab/token-key-mapを適用して、材料名のプロパティ変換・verbose_name生成を行う。
        """
        mat_nodes: list[Node] = []
        mat_relations: list[Relation] = []
        vocab = graph.config.vocab
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

                # vocabでpropsのキーと値を変換
                translated_props: dict[str, Any] = {}
                for key, value in mat_props.items():
                    tk = vocab.get(key, key)
                    tv = vocab.get(str(value), str(value))
                    translated_props[tk] = tv

                # verbose_name構築
                translated_mapped_keys: set[str] = set()
                for mk in token_key_mapped_keys:
                    translated_mapped_keys.add(vocab.get(mk, mk))

                verbose_parts: list[str] = []
                for key, value in translated_props.items():
                    if key in translated_mapped_keys or key in token_key_mapped_keys:
                        verbose_parts.append(str(value))
                    else:
                        verbose_parts.append(f"{key}{value}")
                for tag in mat_tags:
                    verbose_parts.append(vocab.get(tag, tag))

                verbose_name = "_".join(verbose_parts) if verbose_parts else mat_name

                properties: dict[str, Any] = {
                    "source_file": node.properties.get("path", ""),
                    "keywords": mat["keywords"],
                    "tags": list(mat_tags),
                    **translated_props,
                }

                if verbose_name and verbose_name != mat_name:
                    properties["verbose_name"] = verbose_name
                    # verbose_nameの各部分をタグに追加
                    for vt in verbose_name.split("_"):
                        if vt and vt not in properties["tags"]:
                            properties["tags"].append(vt)

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
        """material.inpのverbose_nameに含まれる材料名を設定しタグ化"""
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
            vocab = graph.config.vocab
            type_name = vocab.get("material", "material")

            vn_parts = [type_name] + mat_names
            verbose_name = "_".join(vn_parts)
            node.properties["verbose_name"] = verbose_name

            tags = node.properties.get("tags", [])
            for part in vn_parts:
                if part and part not in tags:
                    tags.append(part)
            node.properties["tags"] = tags


class AbaqusMaterialAssignmentParser(AbstractFileParser):
    """材料割り当て関係の構築と情報集約

    .inpファイルの*SOLID SECTION/*SHELL SECTIONで定義される
    材料→Elset割り当てを解析する。
    """

    priority = 85

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        from services.parse.connectors.abaqus.mesh import (
            extract_material_elset_mapping,
        )

        mat_nodes = graph.get_nodes_by_type("abaqus_material")

        # マテリアル名でインデックス
        mat_by_name: dict[str, list[Node]] = defaultdict(list)
        for mnode in mat_nodes:
            mat_by_name[mnode.name.lower()].append(mnode)

        mat_assign_relations: list[Relation] = []

        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            mapping = extract_material_elset_mapping(file_path)
            if not mapping:
                continue

            for mat_name, elset_names in mapping.items():
                matched_mats = mat_by_name.get(mat_name.lower(), [])
                for mnode in matched_mats:
                    if elset_names:
                        mnode.properties["assigned_elsets"] = elset_names
                    rel = Relation(
                        id=graph.next_relation_id(),
                        label="assigned_to",
                        node1_id=mnode.id,
                        node2_id=node.id,
                    )
                    mat_assign_relations.append(rel)

        graph.add_relations(mat_assign_relations)

        # elsetと材料名をgo_*.inpのプロパティに追加
        self._enrich_material_assignment_props(graph, mat_nodes, mat_assign_relations)

        return graph

    @staticmethod
    def _enrich_material_assignment_props(
        graph: ProjectGraph,
        mat_nodes: list[Node],
        mat_relations: list[Relation],
    ) -> None:
        """elsetと材料名をgo_*.inpのプロパティに追加"""
        node_by_id: dict[int, Node] = {}
        for n in graph.nodes:
            node_by_id[n.id] = n
        for n in mat_nodes:
            node_by_id[n.id] = n

        inp_materials: dict[int, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for rel in mat_relations:
            if rel.label != "assigned_to":
                continue
            mat_node = node_by_id.get(rel.node1_id)
            inp_node = node_by_id.get(rel.node2_id)
            if mat_node is None or inp_node is None:
                continue

            name_lower = inp_node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            mat_name = mat_node.name
            elsets = mat_node.properties.get("assigned_elsets", [])
            if isinstance(elsets, list):
                inp_materials[inp_node.id][mat_name].extend(elsets)
            elif isinstance(elsets, str):
                inp_materials[inp_node.id][mat_name].append(elsets)

        for node_id, mat_elset_map in inp_materials.items():
            node = node_by_id.get(node_id)
            if node is None:
                continue
            node.properties["materials"] = sorted(mat_elset_map.keys())
            node.properties["material_elsets"] = dict(mat_elset_map)


class AbaqusElsetParser(AbstractFileParser):
    """go_*.inpのelset名をNode化

    go_*.inpファイル（include先含む）で定義されているelset名を
    Node(type="abaqus_elset")として生成する。
    各elsetノードにはelement数と材料割り当て情報もproperty化する。
    """

    priority = 98

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        includes_map: dict[int, list[int]] = defaultdict(list)
        for rel in graph.relations:
            if rel.label == "includes":
                includes_map[rel.node1_id].append(rel.node2_id)

        for node in list(graph.nodes):
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            elset_names: set[str] = set()

            # mesh_elset_summaryを統合（go_*自身 + include先）
            merged_elset_summary: dict[str, int] = {}

            elset_summary = node.properties.get("mesh_elset_summary", {})
            if isinstance(elset_summary, dict):
                elset_names.update(elset_summary.keys())
                merged_elset_summary.update(elset_summary)

            for child_id in includes_map.get(node.id, []):
                child = graph.get_node_by_id(child_id)
                if child is None:
                    continue
                child_elsets = child.properties.get("mesh_elset_summary", {})
                if isinstance(child_elsets, dict):
                    elset_names.update(child_elsets.keys())
                    for k, v in child_elsets.items():
                        if k not in merged_elset_summary:
                            merged_elset_summary[k] = v

            mat_elsets = node.properties.get("material_elsets", {})
            if isinstance(mat_elsets, dict):
                for elset_list in mat_elsets.values():
                    if isinstance(elset_list, list):
                        elset_names.update(elset_list)

            if not elset_names:
                continue

            # material_elsets を逆引き: elset_name → material_name
            elset_to_material: dict[str, str] = {}
            if isinstance(mat_elsets, dict):
                for mat_name, elset_list in mat_elsets.items():
                    if isinstance(elset_list, list):
                        for es in elset_list:
                            elset_to_material[es] = mat_name

            go_elset_names: list[str] = []
            for elset_name in sorted(elset_names):
                elset_tags = [t for t in elset_name.split("_") if t]

                elset_props: dict[str, Any] = {
                    "verbose_name": elset_name,
                    "tags": elset_tags,
                    "source_file": node.properties.get("path", ""),
                }

                # elset別element数
                if elset_name in merged_elset_summary:
                    elset_props["element_count"] = merged_elset_summary[elset_name]

                # 材料割り当て
                if elset_name in elset_to_material:
                    elset_props["material"] = elset_to_material[elset_name]

                elset_node = Node(
                    id=graph.next_node_id(),
                    type="abaqus_elset",
                    name=elset_name,
                    format="elset",
                    properties=elset_props,
                )
                graph.add_node(elset_node)
                go_elset_names.append(elset_name)

                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="has_elset",
                        node1_id=node.id,
                        node2_id=elset_node.id,
                    )
                )

            if go_elset_names:
                node.properties["elsets"] = go_elset_names

        return graph
