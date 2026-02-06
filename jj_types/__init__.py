from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ノードタイプ定数
NODE_TYPE_REPOSITORY = "repository"

# リレーションラベル定数
RELATION_BELONGS_TO = "belongs_to"


class Node(BaseModel):
    id: int
    type: str
    name: str
    format: str
    properties: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    id: int
    label: str
    node1_id: int
    node2_id: int


class GraphModel(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)

    @classmethod
    def empty(cls) -> "GraphModel":
        return cls(nodes=[], relations=[])

    def validate_repository_hierarchy(self) -> list[str]:
        """レポジトリ階層の整合性を検証し、エラーメッセージのリストを返す

        検証項目:
        1. 全非レポジトリノードが belongs_to 関係を持つこと
        2. ルート以外の全レポジトリが belongs_to 関係を持つこと
        3. belongs_to の node2_id が必ず type="repository" であること
        4. is_root="true" のレポジトリが正確に1つであること
        5. belongs_to 関係に循環がないこと

        Returns:
            エラーメッセージのリスト（空なら整合）
        """
        errors: list[str] = []
        node_map: dict[int, Node] = {n.id: n for n in self.nodes}

        # belongs_to関係を収集
        belongs_to_rels = [
            r for r in self.relations if r.label == RELATION_BELONGS_TO
        ]
        # node_id -> 親repository_id のマッピング
        child_to_parent: dict[int, int] = {}
        for rel in belongs_to_rels:
            child_to_parent[rel.node1_id] = rel.node2_id

        # レポジトリノードを取得
        repo_nodes = [n for n in self.nodes if n.type == NODE_TYPE_REPOSITORY]
        root_repos = [
            n for n in repo_nodes
            if n.properties.get("is_root") == "true"
        ]

        # 検証4: ルートレポジトリが正確に1つ
        if len(root_repos) == 0:
            errors.append("ルートレポジトリが存在しません")
        elif len(root_repos) > 1:
            names = [r.name for r in root_repos]
            errors.append(
                f"ルートレポジトリが複数存在します: {names}"
            )

        root_id = root_repos[0].id if root_repos else None

        # 検証1: 全非レポジトリノードが belongs_to を持つ
        for node in self.nodes:
            if node.type == NODE_TYPE_REPOSITORY:
                continue
            if node.id not in child_to_parent:
                errors.append(
                    f"ノード '{node.name}' (id={node.id}, type={node.type}) "
                    f"が belongs_to 関係を持ちません"
                )

        # 検証2: ルート以外の全レポジトリが belongs_to を持つ
        for repo in repo_nodes:
            if repo.id == root_id:
                continue
            if repo.id not in child_to_parent:
                errors.append(
                    f"レポジトリ '{repo.name}' (id={repo.id}) "
                    f"が belongs_to 関係を持ちません（ルートでないのに親がいない）"
                )

        # 検証3: belongs_to の node2_id が必ず repository であること
        for rel in belongs_to_rels:
            parent_node = node_map.get(rel.node2_id)
            if parent_node is None:
                errors.append(
                    f"belongs_to 関係 (id={rel.id}) の node2_id={rel.node2_id} "
                    f"に対応するノードが存在しません"
                )
            elif parent_node.type != NODE_TYPE_REPOSITORY:
                child_node = node_map.get(rel.node1_id)
                child_name = child_node.name if child_node else f"id={rel.node1_id}"
                errors.append(
                    f"ノード '{child_name}' の belongs_to 先 '{parent_node.name}' "
                    f"(type={parent_node.type}) がレポジトリではありません"
                )

        # 検証5: belongs_to に循環がないこと
        for node in self.nodes:
            visited: set[int] = set()
            current = node.id
            while current in child_to_parent:
                if current in visited:
                    errors.append(
                        f"belongs_to 関係に循環が検出されました "
                        f"(ノード id={node.id} '{node.name}' から辿った経路)"
                    )
                    break
                visited.add(current)
                current = child_to_parent[current]

        return errors
