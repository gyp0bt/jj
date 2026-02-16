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

            vn_parts = [type_name, *mat_names]
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

        inp_materials: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

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
    """go_*.inpのelset名をNode化（メッシュごとに分離）

    go_*.inpファイル（include先含む）で定義されているelset名を
    Node(type="abaqus_elset")として生成する。
    同一elset名で異なるメッシュ（異なるinclude先.inp）に属する場合、
    メッシュごとに別のelsetノードを生成する。
    各elsetノードにはelement数と材料割り当て情報もproperty化する。
    材料が割り当てられているelsetは、対応するabaqus_materialノードへの
    uses_material relationを持つ。
    """

    priority = 98

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        includes_map: dict[int, list[int]] = defaultdict(list)
        for rel in graph.relations:
            if rel.label == "includes":
                includes_map[rel.node1_id].append(rel.node2_id)

        # abaqus_materialノードを材料名(小文字)でインデックス化
        mat_by_name: dict[str, Node] = {}
        for n in graph.nodes:
            if n.type == "abaqus_material":
                mat_by_name[n.name.lower()] = n

        for node in list(graph.nodes):
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            mat_elsets = node.properties.get("material_elsets", {})
            # material_elsets を逆引き: elset_name → material_name
            elset_to_material: dict[str, str] = {}
            if isinstance(mat_elsets, dict):
                for mat_name, elset_list in mat_elsets.items():
                    if isinstance(elset_list, list):
                        for es in elset_list:
                            elset_to_material[es] = mat_name

            # メッシュソースごとにelsetを収集
            # (mesh_source_name, elset_name) → {summary, quality, source_file}
            # mesh_sourceはinclude先のノード名、go自身は自分のノード名
            mesh_sources: list[tuple[str, Node]] = []

            # go_*自身のメッシュデータ
            self_elsets = node.properties.get("mesh_elset_summary", {})
            if isinstance(self_elsets, dict) and self_elsets:
                mesh_sources.append((node.name, node))

            # include先のメッシュデータ
            for child_id in includes_map.get(node.id, []):
                child = graph.get_node_by_id(child_id)
                if child is None:
                    continue
                child_elsets = child.properties.get("mesh_elset_summary", {})
                if isinstance(child_elsets, dict) and child_elsets:
                    mesh_sources.append((child.name, child))

            # material_elsetsにしかないelset名も回収（mesh_sourceはgo自身）
            all_mesh_elset_names: set[str] = set()
            for _, src_node in mesh_sources:
                src_summary = src_node.properties.get("mesh_elset_summary", {})
                if isinstance(src_summary, dict):
                    all_mesh_elset_names.update(src_summary.keys())

            go_elset_names: list[str] = []
            created_elset_names: set[str] = set()

            # メッシュソースごとにelsetノードを生成
            for mesh_name, src_node in mesh_sources:
                src_summary = src_node.properties.get("mesh_elset_summary", {})
                if not isinstance(src_summary, dict):
                    continue
                src_quality = src_node.properties.get("mesh_elset_quality", {})
                if not isinstance(src_quality, dict):
                    src_quality = {}

                for elset_name in sorted(src_summary.keys()):
                    elset_props: dict[str, Any] = {
                        "verbose_name": elset_name,
                        "source_file": src_node.properties.get("path", ""),
                        "mesh_source": mesh_name,
                    }

                    # elset別element数
                    elset_props["element_count"] = src_summary[elset_name]

                    # elset別品質統計
                    if elset_name in src_quality:
                        eq = src_quality[elset_name]
                        if isinstance(eq, dict) and "quality" in eq:
                            elset_props["quality"] = eq["quality"]

                    # 材料割り当て
                    assigned_material_name = elset_to_material.get(elset_name)
                    if assigned_material_name:
                        elset_props["material"] = assigned_material_name

                    elset_node = Node(
                        id=graph.next_node_id(),
                        type="abaqus_elset",
                        name=elset_name,
                        format="elset",
                        properties=elset_props,
                    )
                    graph.add_node(elset_node)
                    if elset_name not in created_elset_names:
                        go_elset_names.append(elset_name)
                        created_elset_names.add(elset_name)

                    # has_elset: go_*.inp → elsetノード
                    graph.add_relation(
                        Relation(
                            id=graph.next_relation_id(),
                            label="has_elset",
                            node1_id=node.id,
                            node2_id=elset_node.id,
                        )
                    )

                    # uses_material: elsetノード → abaqus_materialノード
                    if assigned_material_name:
                        mat_node = mat_by_name.get(assigned_material_name.lower())
                        if mat_node:
                            graph.add_relation(
                                Relation(
                                    id=graph.next_relation_id(),
                                    label="uses_material",
                                    node1_id=elset_node.id,
                                    node2_id=mat_node.id,
                                )
                            )

            # material_elsetsにのみ存在するelset（meshデータなし）も生成
            if isinstance(mat_elsets, dict):
                for mat_name, elset_list in mat_elsets.items():
                    if not isinstance(elset_list, list):
                        continue
                    for elset_name in elset_list:
                        if elset_name in all_mesh_elset_names:
                            continue
                        if elset_name in created_elset_names:
                            continue
                        elset_props = {
                            "verbose_name": elset_name,
                            "source_file": node.properties.get("path", ""),
                            "material": mat_name,
                        }
                        elset_node = Node(
                            id=graph.next_node_id(),
                            type="abaqus_elset",
                            name=elset_name,
                            format="elset",
                            properties=elset_props,
                        )
                        graph.add_node(elset_node)
                        go_elset_names.append(elset_name)
                        created_elset_names.add(elset_name)

                        graph.add_relation(
                            Relation(
                                id=graph.next_relation_id(),
                                label="has_elset",
                                node1_id=node.id,
                                node2_id=elset_node.id,
                            )
                        )
                        mat_node = mat_by_name.get(mat_name.lower())
                        if mat_node:
                            graph.add_relation(
                                Relation(
                                    id=graph.next_relation_id(),
                                    label="uses_material",
                                    node1_id=elset_node.id,
                                    node2_id=mat_node.id,
                                )
                            )

            if go_elset_names:
                node.properties["elsets"] = sorted(go_elset_names)

        return graph


def parse_keyword_blocks(inp_path: Path) -> list[dict[str, Any]]:
    """Abaqus .inpファイルからキーワードブロックを抽出

    *で始まる行のカンマ前がキーワード名、カンマ後がオプション。
    **で始まるコメント行は除外。

    Returns:
        [{"keyword": str, "options": dict[str, str]}, ...]
        同一キーワードは1回のみ（最初の出現）。
    """
    keywords: list[dict[str, Any]] = []
    seen_keywords: set[str] = set()

    try:
        with inp_path.open("r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("**"):
                    continue
                if not line.startswith("*"):
                    continue

                # *KEYWORD, opt1=val1, opt2=val2 の形式
                tokens = [t.strip() for t in line.split(",") if t.strip()]
                if not tokens:
                    continue

                keyword_name = tokens[0].lstrip("*").strip()
                if not keyword_name:
                    continue

                keyword_upper = keyword_name.upper()
                if keyword_upper in seen_keywords:
                    continue
                seen_keywords.add(keyword_upper)

                options: dict[str, str] = {}
                for tok in tokens[1:]:
                    if "=" in tok:
                        key, _, val = tok.partition("=")
                        options[key.strip()] = val.strip()
                    else:
                        # 値なしオプション
                        options[tok.strip()] = ""

                keywords.append(
                    {
                        "keyword": keyword_name,
                        "options": options,
                    }
                )
    except OSError:
        pass

    return keywords


class AbaqusKeywordParser(AbstractFileParser):
    """Abaqus .inpファイルのキーワードをNode化

    *で始まるキーワード行を解析し、Node(type="abaqus_keyword")を生成する。
    キーワード名をnameとし、オプションをプロパティにする。
    キーワードを使っている.inpファイルとの間にuses_keyword relationを作る。
    """

    priority = 55

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # キーワードの重複をグローバルで管理
        keyword_nodes: dict[str, Node] = {}

        for node in list(graph.nodes):
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = graph.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            kw_blocks = parse_keyword_blocks(file_path)

            for kw in kw_blocks:
                kw_name = kw["keyword"]
                kw_upper = kw_name.upper()

                if kw_upper not in keyword_nodes:
                    kw_props: dict[str, Any] = {}
                    for opt_key, opt_val in kw["options"].items():
                        if opt_val:
                            kw_props[opt_key] = opt_val
                        else:
                            kw_props[opt_key] = True

                    kw_node = Node(
                        id=graph.next_node_id(),
                        type="abaqus_keyword",
                        name=kw_upper,
                        format="keyword",
                        properties=kw_props,
                    )
                    graph.add_node(kw_node)
                    keyword_nodes[kw_upper] = kw_node

                # uses_keyword: .inpファイル → キーワードノード
                graph.add_relation(
                    Relation(
                        id=graph.next_relation_id(),
                        label="uses_keyword",
                        node1_id=node.id,
                        node2_id=keyword_nodes[kw_upper].id,
                    )
                )

        return graph
