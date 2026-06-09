"""ProjectGraph型: パーサーパイプラインで使用するプロジェクトグラフ

プロジェクトのファイルツリーとグラフデータを統合的に管理する型群。
AbstractFileParserサブクラスのapply()メソッドはProjectGraphを受け取り、
ノード・リレーションの追加や属性付与を行って返す。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import GraphConfig
from jj_types import (
    GraphModel,
    Node,
    NodeCategory,
    Relation,
)


@dataclass
class ProjectNonFileNode:
    """実ファイルを持たないノードを表現"""

    node: Node | None = None


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
    non_file_nodes: list[ProjectNonFileNode] = field(default_factory=list)


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
    _parser_cache: dict[str, Any] = field(default_factory=dict, repr=False)
    _file_timestamps: dict[str, float] = field(default_factory=dict, repr=False)
    _prev_timestamps: dict[str, float] = field(default_factory=dict, repr=False)
    # パフォーマンス用インデックス（O(N)線形走査 → O(1)ハッシュ参照）
    _relations_by_label: dict[str, list[Relation]] = field(default_factory=lambda: defaultdict(list), repr=False)
    _relations_by_node: dict[int, list[Relation]] = field(default_factory=lambda: defaultdict(list), repr=False)
    _nodes_by_type: dict[str, list[Node]] = field(default_factory=lambda: defaultdict(list), repr=False)
    _nodes_by_category: dict[NodeCategory, list[Node]] = field(default_factory=lambda: defaultdict(list), repr=False)

    def __post_init__(self) -> None:
        """既存ノード・リレーションのインデックスを構築"""
        for node in self.nodes:
            path = node.properties.get("path", "")
            if path:
                self._node_by_path[path] = node
            self._node_by_id[node.id] = node
            self._nodes_by_type[node.type].append(node)
            if node.category is not None:
                self._nodes_by_category[node.category].append(node)
            if node.id > self._node_id_counter:
                self._node_id_counter = node.id
        for rel in self.relations:
            self._relations_by_label[rel.label].append(rel)
            self._relations_by_node[rel.node1_id].append(rel)
            self._relations_by_node[rel.node2_id].append(rel)
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
        self._nodes_by_type[node.type].append(node)
        if node.category is not None:
            self._nodes_by_category[node.category].append(node)

    def add_nodes(self, nodes: list[Node]) -> None:
        """複数ノードを一括追加"""
        for node in nodes:
            self.add_node(node)

    def add_relation(self, relation: Relation) -> None:
        """リレーションを追加しインデックスを更新"""
        self.relations.append(relation)
        self._relations_by_label[relation.label].append(relation)
        self._relations_by_node[relation.node1_id].append(relation)
        self._relations_by_node[relation.node2_id].append(relation)

    def add_relations(self, relations: list[Relation]) -> None:
        """複数リレーションを一括追加"""
        self.relations.extend(relations)
        for relation in relations:
            self._relations_by_label[relation.label].append(relation)
            self._relations_by_node[relation.node1_id].append(relation)
            self._relations_by_node[relation.node2_id].append(relation)

    def get_node_by_path(self, path: str) -> Node | None:
        """パスからノードを取得"""
        return self._node_by_path.get(path)

    def get_node_by_id(self, node_id: int) -> Node | None:
        """IDからノードを取得"""
        return self._node_by_id.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[Node]:
        """タイプでノードをフィルタリング（インデックス参照: O(1)）"""
        return list(self._nodes_by_type.get(node_type, []))

    def get_input_nodes(self) -> list[Node]:
        """入力ファイルノード（input_extensions）を取得"""
        input_exts = self.config.file_relations.input_extensions
        return [n for n in self.nodes if f".{n.format}".lower() in input_exts]

    def get_relations_for_node(self, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得（インデックス参照: O(1)）"""
        return list(self._relations_by_node.get(node_id, []))

    def get_relations_by_label(self, label: str) -> list[Relation]:
        """ラベルでリレーションをフィルタリング（インデックス参照: O(1)）"""
        return list(self._relations_by_label.get(label, []))

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
        """ノードからindex値を取得（生キー: index）"""
        return str(node.properties.get("index", ""))

    def get_node_version(self, node: Node) -> str:
        """ノードからversion値を取得（生キー: version）"""
        return str(node.properties.get("version", ""))

    def remove_nodes(self, node_ids: set[int]) -> None:
        """指定IDのノードとそれに関わるリレーションを除去"""
        self.nodes = [n for n in self.nodes if n.id not in node_ids]
        self.relations = [r for r in self.relations if r.node1_id not in node_ids and r.node2_id not in node_ids]
        # 全インデックス再構築
        self._rebuild_all_indexes()

    def _rebuild_all_indexes(self) -> None:
        """全インデックスを再構築（remove_nodes後等に使用）"""
        self._node_by_id = {}
        self._node_by_path = {}
        self._nodes_by_type = defaultdict(list)
        self._nodes_by_category = defaultdict(list)
        for n in self.nodes:
            self._node_by_id[n.id] = n
            path = n.properties.get("path", "")
            if path:
                self._node_by_path[path] = n
            self._nodes_by_type[n.type].append(n)
            if n.category is not None:
                self._nodes_by_category[n.category].append(n)
        self._relations_by_label = defaultdict(list)
        self._relations_by_node = defaultdict(list)
        for r in self.relations:
            self._relations_by_label[r.label].append(r)
            self._relations_by_node[r.node1_id].append(r)
            self._relations_by_node[r.node2_id].append(r)

    def get_cache(self, key: str) -> Any:
        """パーサー間で共有するキャッシュから値を取得

        Args:
            key: キャッシュキー

        Returns:
            キャッシュされた値。存在しない場合はNone。
        """
        return self._parser_cache.get(key)

    def set_cache(self, key: str, value: Any) -> None:
        """パーサー間で共有するキャッシュに値を設定

        Args:
            key: キャッシュキー
            value: キャッシュする値
        """
        self._parser_cache[key] = value

    def get_cached_plugin_data(self, namespace: str, file_path: str) -> Any:
        """プラグインキャッシュから値を取得

        Args:
            namespace: プラグイン名前空間（例: "abaqus"）
            file_path: ファイルパス文字列

        Returns:
            キャッシュされたデータ。存在しない場合はNone。
        """
        return self._parser_cache.get(f"{namespace}:{file_path}")

    def set_cached_plugin_data(self, namespace: str, file_path: str, data: Any) -> None:
        """プラグインキャッシュに値を保存

        Args:
            namespace: プラグイン名前空間（例: "abaqus"）
            file_path: ファイルパス文字列
            data: キャッシュするデータ
        """
        self._parser_cache[f"{namespace}:{file_path}"] = data

    # =========================================================
    # タイムスタンプ差分キャッシュ
    # =========================================================

    def record_file_timestamp(self, file_path: str, mtime: float) -> None:
        """現在のパース実行時のファイルタイムスタンプを記録"""
        self._file_timestamps[file_path] = mtime

    def is_file_modified(self, file_path: str) -> bool:
        """ファイルが前回パース時から変更されているかを判定

        前回のタイムスタンプ情報がない場合（初回実行等）はTrueを返す。
        """
        if not self._prev_timestamps:
            return True
        prev_mtime = self._prev_timestamps.get(file_path)
        if prev_mtime is None:
            return True
        try:
            current_mtime = Path(file_path).stat().st_mtime
        except OSError:
            return True
        return current_mtime != prev_mtime

    def collect_file_timestamps(self) -> dict[str, float]:
        """現在のパースで記録されたタイムスタンプを返す"""
        return dict(self._file_timestamps)

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
            dir_files[parent_dir].append(ProjectFile(path=self.project_root / path_str, node=node))
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

        # 実ファイルを持たないノード（material, elset等）をnon_file_nodesに配置
        for node in self.nodes:
            path_str = node.properties.get("path", "")
            if path_str or node.format == "directory":
                continue
            # source_fileからディレクトリを決定
            source_file = node.properties.get("source_file", "")
            if source_file:
                parent_dir = str(Path(source_file).parent)
                if parent_dir == ".":
                    parent_dir = ""
            else:
                parent_dir = ""
            directory = dir_objects.get(parent_dir, root)
            directory.non_file_nodes.append(ProjectNonFileNode(node=node))

        # 幅優先走査
        queue = [root]
        while queue:
            current = queue.pop(0)
            yield current
            queue.extend(current.children)

    def get_nodes_by_category(self, category: NodeCategory) -> list[Node]:
        """カテゴリでノードをフィルタリング（インデックス参照: O(1)）"""
        return list(self._nodes_by_category.get(category, []))

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
