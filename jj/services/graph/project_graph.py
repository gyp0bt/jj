"""ProjectGraph型: パーサーパイプラインで使用するプロジェクトグラフ

プロジェクトのファイルツリーとグラフデータを統合的に管理する型群。
AbstractFileParserサブクラスのapply()メソッドはProjectGraphを受け取り、
ノード・リレーションの追加や属性付与を行って返す。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from config import GraphConfig
from jj_types import GraphModel, Node, Relation


@dataclass
class ProjectFile:
    """プロジェクト内のファイルを表現"""

    path: Path
    node: Node | None = None


@dataclass
class ProjectDirectory:
    """プロジェクト内のディレクトリを表現"""

    path: Path
    parent: ProjectDirectory | None = None
    children: list[ProjectDirectory] = field(default_factory=list)
    files: list[ProjectFile] = field(default_factory=list)


@dataclass
class ProjectGraph:
    """パーサーパイプラインで使用するプロジェクトグラフ

    GraphServiceがスキャン結果から構築し、各パーサーのapply()で
    ノード・リレーションが追加・更新される。最終的にto_graph_model()で
    GraphModelに変換して永続化する。

    Attributes:
        nodes: ノードのリスト
        relations: リレーションのリスト
        project_root: プロジェクトルートのパス
        config: グラフ設定
    """

    nodes: list[Node]
    relations: list[Relation]
    project_root: Path
    config: GraphConfig
    _node_id_counter: int = field(default=0, repr=False)
    _relation_id_counter: int = field(default=0, repr=False)
    _node_by_path: dict[str, Node] = field(default_factory=dict, repr=False)
    _node_by_id: dict[int, Node] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """既存ノードのインデックスを構築"""
        for node in self.nodes:
            path = node.properties.get("path", "")
            if path:
                self._node_by_path[path] = node
            self._node_by_id[node.id] = node
            if node.id > self._node_id_counter:
                self._node_id_counter = node.id
        for rel in self.relations:
            if rel.id > self._relation_id_counter:
                self._relation_id_counter = rel.id

    def next_node_id(self) -> int:
        """次のノードIDを発番"""
        self._node_id_counter += 1
        return self._node_id_counter

    def next_relation_id(self) -> int:
        """次のリレーションIDを発番"""
        self._relation_id_counter += 1
        return self._relation_id_counter

    def add_node(self, node: Node) -> None:
        """ノードを追加しインデックスを更新"""
        self.nodes.append(node)
        path = node.properties.get("path", "")
        if path:
            self._node_by_path[path] = node
        self._node_by_id[node.id] = node

    def add_nodes(self, nodes: list[Node]) -> None:
        """複数ノードを一括追加"""
        for node in nodes:
            self.add_node(node)

    def add_relation(self, relation: Relation) -> None:
        """リレーションを追加"""
        self.relations.append(relation)

    def add_relations(self, relations: list[Relation]) -> None:
        """複数リレーションを一括追加"""
        self.relations.extend(relations)

    def get_node_by_path(self, path: str) -> Node | None:
        """パスからノードを取得"""
        return self._node_by_path.get(path)

    def get_node_by_id(self, node_id: int) -> Node | None:
        """IDからノードを取得"""
        return self._node_by_id.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[Node]:
        """タイプでノードをフィルタリング"""
        return [n for n in self.nodes if n.type == node_type]

    def get_input_nodes(self) -> list[Node]:
        """入力ファイルノード（input_extensions）を取得"""
        input_exts = self.config.file_relations.input_extensions
        return [
            n for n in self.nodes
            if f".{n.format}".lower() in input_exts
        ]

    def get_relations_for_node(self, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return [
            r for r in self.relations
            if r.node1_id == node_id or r.node2_id == node_id
        ]

    def get_relations_by_label(self, label: str) -> list[Relation]:
        """ラベルでリレーションをフィルタリング"""
        return [r for r in self.relations if r.label == label]

    def safe_relative_path(self, file_path: Path) -> str:
        """POSIX形式の相対パスを生成（先頭./なし）"""
        try:
            resolved = file_path.resolve()
            rel = resolved.relative_to(self.project_root.resolve())
            result = rel.as_posix()
        except ValueError:
            result = file_path.as_posix()
        while result.startswith("./"):
            result = result[2:]
        return result

    def get_node_index(self, node: Node) -> str:
        """ノードからindex値を取得（vocab変換後のキーにも対応）"""
        idx = node.properties.get("index", "")
        if not idx:
            translated_key = self.config.vocab.get("idx")
            if translated_key:
                idx = str(node.properties.get(translated_key, ""))
        return idx

    def get_node_version(self, node: Node) -> str:
        """ノードからversion値を取得（vocab変換後のキーにも対応）"""
        ver = node.properties.get("version", "")
        if not ver:
            translated_key = self.config.vocab.get("v")
            if translated_key:
                ver = str(node.properties.get(translated_key, ""))
        return ver

    def remove_nodes(self, node_ids: set[int]) -> None:
        """指定IDのノードとそれに関わるリレーションを除去"""
        self.nodes = [n for n in self.nodes if n.id not in node_ids]
        self.relations = [
            r for r in self.relations
            if r.node1_id not in node_ids and r.node2_id not in node_ids
        ]
        # インデックス再構築
        self._node_by_id = {n.id: n for n in self.nodes}
        self._node_by_path = {}
        for n in self.nodes:
            path = n.properties.get("path", "")
            if path:
                self._node_by_path[path] = n

    def iterate_directories(self) -> Iterator[ProjectDirectory]:
        """ノードのパス情報からディレクトリツリーを構築してイテレート

        ファイルノードのパスを解析し、ProjectDirectory/ProjectFile
        のツリー構造を生成する。ルートからの幅優先走査で返す。
        """
        # ディレクトリ→ファイルのマッピングを構築
        dir_files: dict[str, list[ProjectFile]] = defaultdict(list)
        dir_set: set[str] = set()

        for node in self.nodes:
            path_str = node.properties.get("path", "")
            if not path_str or node.format == "directory":
                continue
            file_path = Path(path_str)
            parent_dir = file_path.parent.as_posix()
            if parent_dir == ".":
                parent_dir = ""
            dir_files[parent_dir].append(
                ProjectFile(path=self.project_root / path_str, node=node)
            )
            # 親ディレクトリを再帰的に登録
            parts = Path(parent_dir).parts if parent_dir else ()
            for i in range(len(parts)):
                dir_set.add(str(Path(*parts[: i + 1])))

        # ProjectDirectoryオブジェクトを構築
        dir_objects: dict[str, ProjectDirectory] = {}
        root = ProjectDirectory(path=self.project_root)
        dir_objects[""] = root

        for dir_path in sorted(dir_set):
            pd = ProjectDirectory(path=self.project_root / dir_path)
            dir_objects[dir_path] = pd
            # 親を設定
            parent_path = str(Path(dir_path).parent)
            if parent_path == ".":
                parent_path = ""
            parent = dir_objects.get(parent_path, root)
            pd.parent = parent
            parent.children.append(pd)

        # ファイルを配置
        for dir_path, files in dir_files.items():
            directory = dir_objects.get(dir_path, root)
            directory.files = files

        # 幅優先走査
        queue = [root]
        while queue:
            current = queue.pop(0)
            yield current
            queue.extend(current.children)

    def to_graph_model(self) -> GraphModel:
        """GraphModelに変換して返す"""
        return GraphModel(nodes=list(self.nodes), relations=list(self.relations))

    @classmethod
    def from_graph_service(
        cls,
        nodes: list[Node],
        relations: list[Relation],
        project_root: Path,
        config: GraphConfig,
        node_id_counter: int = 0,
        relation_id_counter: int = 0,
    ) -> ProjectGraph:
        """GraphServiceの内部状態からProjectGraphを構築"""
        pg = cls(
            nodes=list(nodes),
            relations=list(relations),
            project_root=project_root,
            config=config,
        )
        if node_id_counter > pg._node_id_counter:
            pg._node_id_counter = node_id_counter
        if relation_id_counter > pg._relation_id_counter:
            pg._relation_id_counter = relation_id_counter
        return pg
