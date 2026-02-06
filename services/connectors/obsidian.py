"""Obsidianコネクタ: GraphModelをObsidian向けマークダウンにエクスポート

重要な命名規則:
- 実ファイル: "O-"プレフィックスなし (例: go_test_v1.inp)
- Obsidianファイル: "O-"プレフィックス付き (例: O-go_test_v1.inp.md)
- ディレクトリ: "O-"プレフィックスなし (例: notes/props/go/)

リンク記法:
- 実ファイルへのリンク: [[{相対パス}|{表記名}]]
- mdファイルへのリンク: [[{".md"抜きのファイル名}]]
- ラベル付きリンク（独自記法）: label:[[ファイル名]]

.baseファイル:
- YAML形式のフィルター条件ファイル（拡張子は".base"、".base.md"ではない）
- Obsidian上でフィルター条件に応じてpropertyをテーブル形式で表示

group.mdファイル:
- NodeGroupのメンバー一覧を持つマークダウンファイル
- props/{type}/ 配下に "{type}_idx{index}-group.md" として配置

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from jj_types import GraphModel, Node, Relation
from config import GraphConfig, ObsidianExportConfig


@dataclass
class ObsidianConfig:
    """Obsidianエクスポートの設定"""

    notes_dir: Path = field(default_factory=lambda: Path("notes/props"))
    bases_dir: Path = field(default_factory=lambda: Path("notes/bases"))
    obsidian_prefix: str = "O-"  # Obsidianファイルに付けるプレフィックス


def to_obsidian_filename(real_filename: str, prefix: str = "O-") -> str:
    """実ファイル名をObsidianファイル名に変換

    Args:
        real_filename: 実ファイル名 (例: "go_test_v1.inp")
        prefix: Obsidianファイルに付けるプレフィックス

    Returns:
        Obsidianファイル名 (例: "O-go_test_v1.inp.md")

    Examples:
        >>> to_obsidian_filename("go_test_v1.inp")
        'O-go_test_v1.inp.md'
        >>> to_obsidian_filename("mesh_box.cdb")
        'O-mesh_box.cdb.md'
    """
    return f"{prefix}{real_filename}.md"


def from_obsidian_filename(obsidian_filename: str, prefix: str = "O-") -> str:
    """Obsidianファイル名を実ファイル名に変換

    Args:
        obsidian_filename: Obsidianファイル名 (例: "O-go_test_v1.inp.md")
        prefix: 除去するプレフィックス

    Returns:
        実ファイル名 (例: "go_test_v1.inp")

    Examples:
        >>> from_obsidian_filename("O-go_test_v1.inp.md")
        'go_test_v1.inp'
        >>> from_obsidian_filename("O-mesh_box.cdb.md")
        'mesh_box.cdb'
    """
    name = obsidian_filename
    if name.startswith(prefix):
        name = name[len(prefix) :]
    if name.endswith(".md"):
        name = name[:-3]
    return name


def to_obsidian_link(real_filename: str, prefix: str = "O-") -> str:
    """実ファイル名をObsidianリンク形式に変換

    Args:
        real_filename: 実ファイル名

    Returns:
        Obsidianリンク形式 (例: "[[O-go_test_v1.inp]]")

    Examples:
        >>> to_obsidian_link("go_test_v1.inp")
        '[[O-go_test_v1.inp]]'
    """
    obsidian_name = to_obsidian_filename(real_filename, prefix)
    # .mdを除いた形式でリンク
    link_name = obsidian_name[:-3] if obsidian_name.endswith(".md") else obsidian_name
    return f"[[{link_name}]]"


def to_obsidian_file_link(rel_path: str, display_name: str | None = None) -> str:
    """実ファイルへのObsidianリンクを生成

    Args:
        rel_path: 相対パス
        display_name: 表示名（省略時はファイル名）

    Returns:
        Obsidianリンク形式 (例: "[[path/to/file.inp|file.inp]]")

    Examples:
        >>> to_obsidian_file_link("go/go_test_v1.inp", "go_test_v1")
        '[[go/go_test_v1.inp|go_test_v1]]'
    """
    name = display_name or Path(rel_path).name
    return f"[[{rel_path}|{name}]]"


def to_obsidian_md_link(md_filename: str) -> str:
    """mdファイルへのObsidianリンクを生成

    Args:
        md_filename: mdファイル名（.md付き）

    Returns:
        Obsidianリンク形式 (例: "[[O-go_test_v1.inp]]")

    Examples:
        >>> to_obsidian_md_link("O-go_test_v1.inp.md")
        '[[O-go_test_v1.inp]]'
    """
    # .mdを除いた形式でリンク
    link_name = md_filename[:-3] if md_filename.endswith(".md") else md_filename
    return f"[[{link_name}]]"


def to_labeled_link(label: str, md_filename: str) -> str:
    """ラベル付きリンクを生成（Obsidian独自記法）

    Args:
        label: リレーションのラベル
        md_filename: mdファイル名（.md付き）

    Returns:
        ラベル付きリンク (例: "next_version:[[O-go_test_v2.inp]]")

    Examples:
        >>> to_labeled_link("next_version", "O-go_test_v2.inp.md")
        'next_version:[[O-go_test_v2.inp]]'
    """
    link = to_obsidian_md_link(md_filename)
    return f"{label}:{link}"


def get_directory_for_type(file_type: str) -> str:
    """ファイルタイプからディレクトリ名を取得（O-プレフィックスなし）

    Args:
        file_type: ファイルタイプ (例: "go", "mesh", "docs")

    Returns:
        ディレクトリ名（O-プレフィックスなし）

    Examples:
        >>> get_directory_for_type("go")
        'go'
        >>> get_directory_for_type("O-go")  # 入力にO-があっても除去
        'go'
    """
    dir_name = file_type
    if dir_name.startswith("O-"):
        dir_name = dir_name[2:]
    return dir_name


class ObsidianConnector:
    """GraphModelをObsidian向けにエクスポートするコネクタ"""

    def __init__(
        self,
        project_root: Path | str | None = None,
        config: ObsidianConfig | None = None,
        graph_config: GraphConfig | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.config = config or ObsidianConfig()
        self.graph_config = graph_config or GraphConfig.load(self.project_root)

        # graph_configからObsidian設定を反映
        obs_config = self.graph_config.obsidian
        if obs_config:
            self.config = ObsidianConfig(
                notes_dir=Path(obs_config.notes_dir),
                bases_dir=Path(obs_config.bases_dir),
                obsidian_prefix=obs_config.prefix,
            )

    def get_md_path(self, node: Node) -> Path:
        """ノードからObsidian mdファイルパスを生成

        Args:
            node: 対象ノード

        Returns:
            mdファイルのパス

        Note:
            - ディレクトリ名にはO-プレフィックスは付かない
            - ファイル名にはO-プレフィックスが付く
        """
        notes_dir = self.project_root / self.config.notes_dir
        file_type = node.type
        format_ext = node.format

        # ディレクトリ名はO-なし
        dir_name = get_directory_for_type(file_type)

        # ファイル名はO-付き
        real_filename = f"{node.name}.{format_ext}" if format_ext else node.name
        obsidian_filename = to_obsidian_filename(real_filename, self.config.obsidian_prefix)

        # すべてのタイプで notes/props/{type}/ 配下に配置
        return notes_dir / dir_name / obsidian_filename

    def node_to_frontmatter(self, node: Node, includes: list[str] | None = None) -> dict[str, Any]:
        """ノードからfrontmatterを生成

        Args:
            node: 対象ノード
            includes: includeするファイルのリスト（実ファイル名）

        Returns:
            frontmatter用のdict
        """
        props = dict(node.properties)
        props["idx"] = props.pop("index", "")
        props["ver"] = props.pop("version", "")

        # ファイル情報をpropertyとして追加
        props["node_type"] = node.type
        props["node_format"] = node.format
        real_path = props.get("path", "")
        props["file"] = real_path.replace("\\", "/") if real_path else ""

        # includesは実ファイル名 → Obsidianリンク形式に変換
        if includes:
            props["includes"] = [
                to_obsidian_link(inc, self.config.obsidian_prefix) for inc in includes
            ]

        return props

    def write_md(
        self,
        node: Node,
        includes: list[str] | None = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        """ノードをObsidian mdファイルとして書き出し

        Args:
            node: 対象ノード
            includes: includeするファイルのリスト（実ファイル名）
            overwrite: 既存ファイルを上書きするか

        Returns:
            書き込んだファイルパス（スキップした場合はNone）
        """
        md_path = self.get_md_path(node)

        if md_path.exists() and not overwrite:
            return None

        md_path.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = self.node_to_frontmatter(node, includes)
        content = self._format_md(frontmatter, node)

        md_path.write_text(content, encoding="utf-8")
        return md_path

    def _format_md(
        self,
        frontmatter: dict[str, Any],
        node: Node,
        relations: list[tuple[str, str]] | None = None,
    ) -> str:
        """マークダウンファイルの内容を生成

        Args:
            frontmatter: frontmatter用のdict
            node: 対象ノード
            relations: リレーション情報 [(label, target_md_filename), ...]
        """
        yaml_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

        real_path = node.properties.get("path", "")
        # 実ファイルへのリンク記法: [[path|name]]
        file_link = to_obsidian_file_link(real_path, node.name)

        content = f"""---
{yaml_str.strip()}
---

## ファイル情報

- 実ファイル: {file_link}
- タイプ: {node.type}
- フォーマット: {node.format}
"""
        # リレーション情報を追加
        if relations:
            content += "\n## 関連ファイル\n\n"
            for label, target_md in relations:
                labeled_link = to_labeled_link(label, target_md)
                content += f"- {labeled_link}\n"

        return content

    def _build_version_groups(
        self, nodes: list[Node]
    ) -> dict[tuple[str, str], list[Node]]:
        """type + index でノードをバージョン順にグループ化

        Returns:
            {(type, index): [ノードをversion昇順でソート]} のdict
        """
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in nodes:
            index = node.properties.get("index", "")
            if index:
                groups[(node.type, index)].append(node)

        # 各グループをversion昇順でソート
        for key in groups:
            groups[key] = sorted(groups[key], key=lambda n: self._get_version_sort_key(n))

        return groups

    @staticmethod
    def _get_version_sort_key(node: Node) -> tuple[int, str]:
        """ノードのバージョンソートキーを返す"""
        ver = node.properties.get("version", "")
        if not ver:
            ver = "1"
        try:
            return (0, str(int(ver)).zfill(10))
        except (ValueError, TypeError):
            return (1, str(ver))

    def _build_parent_links(
        self, version_groups: dict[tuple[str, str], list[Node]]
    ) -> dict[int, str]:
        """各ノードの親リンクを構築

        最新ver → {type}_idx{index}.base へのリンク
        それ以外 → 次のversionのNodeへのリンク

        Returns:
            {node_id: parent_link_string} のdict
        """
        parent_links: dict[int, str] = {}

        for (node_type, index), sorted_nodes in version_groups.items():
            if len(sorted_nodes) < 2:
                # 1つしかない場合は.baseリンクのみ
                if sorted_nodes:
                    base_name = f"{node_type}_idx{index}.base"
                    parent_links[sorted_nodes[0].id] = base_name
                continue

            # 最新ver（最後の要素）は.baseリンク
            latest = sorted_nodes[-1]
            base_name = f"{node_type}_idx{index}.base"
            parent_links[latest.id] = base_name

            # 最新以外は次のNodeへのリンク
            for i in range(len(sorted_nodes) - 1):
                current = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]
                next_filename = f"{next_node.name}.{next_node.format}"
                next_obsidian = to_obsidian_filename(next_filename, self.config.obsidian_prefix)
                # .md拡張子を除いてリンク名にする
                link_name = next_obsidian[:-3] if next_obsidian.endswith(".md") else next_obsidian
                parent_links[current.id] = link_name

        return parent_links

    def export_graph(
        self,
        graph: GraphModel,
        overwrite: bool = False,
    ) -> list[Path]:
        """GraphModelをObsidianファイルとしてエクスポート

        Args:
            graph: エクスポートするグラフ
            overwrite: 既存ファイルを上書きするか

        Returns:
            書き込んだファイルパスのリスト
        """
        written: list[Path] = []

        # ノードIDからノードへのマッピングを作成
        node_by_id: dict[int, Node] = {node.id: node for node in graph.nodes}

        # ノードごとのリレーション情報を収集
        relations_by_node: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for rel in graph.relations:
            # source → target のリレーションを記録
            target_node = node_by_id.get(rel.node2_id)
            if target_node:
                target_filename = f"{target_node.name}.{target_node.format}"
                target_md = to_obsidian_filename(target_filename, self.config.obsidian_prefix)
                relations_by_node[rel.node1_id].append((rel.label, target_md))

        # バージョングループ構築と親リンク決定
        version_groups = self._build_version_groups(graph.nodes)
        parent_links = self._build_parent_links(version_groups)

        # ノードごとにmdファイルを書き出し
        for node in graph.nodes:
            node_relations = relations_by_node.get(node.id, [])
            # 親リンクをincludesに設定
            includes = None
            if node.id in parent_links:
                includes = [parent_links[node.id]]
            path = self.write_md_with_relations(
                node, node_relations, includes=includes, overwrite=overwrite
            )
            if path:
                written.append(path)

        # .baseファイル（NodeGroup）を生成
        base_paths = self._write_base_files(graph, overwrite=overwrite)
        written.extend(base_paths)

        return written

    def write_md_with_relations(
        self,
        node: Node,
        relations: list[tuple[str, str]],
        includes: list[str] | None = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        """リレーション情報を含めてノードをObsidian mdファイルとして書き出し

        Args:
            node: 対象ノード
            relations: リレーション情報 [(label, target_md_filename), ...]
            includes: includeするファイルのリスト（実ファイル名）
            overwrite: 既存ファイルを上書きするか

        Returns:
            書き込んだファイルパス（スキップした場合はNone）
        """
        md_path = self.get_md_path(node)

        if md_path.exists() and not overwrite:
            return None

        md_path.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = self.node_to_frontmatter(node, includes)
        content = self._format_md(frontmatter, node, relations)

        md_path.write_text(content, encoding="utf-8")
        return md_path

    def _write_base_files(
        self,
        graph: GraphModel,
        overwrite: bool = False,
    ) -> list[Path]:
        """NodeGroup用の.base（フィルター条件）ファイルを生成

        .baseファイル:
            YAML形式のフィルター条件ファイル（Obsidianでテーブル表示用）。
            notes/bases/{type}/ 配下に配置。
            最新verのNodeがこの.baseファイルへのリンクを持つ。

        Args:
            graph: グラフモデル
            overwrite: 既存ファイルを上書きするか

        Returns:
            書き込んだファイルパスのリスト
        """
        written: list[Path] = []
        bases_dir = self.project_root / self.config.bases_dir

        # type + index でグループ化
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in graph.nodes:
            index = node.properties.get("index", "")
            if index:
                groups[(node.type, index)].append(node)

        # グループごとに .base を生成
        for (node_type, index), nodes in groups.items():
            if len(nodes) < 2:
                continue

            dir_name = get_directory_for_type(node_type)

            # --- .base ファイル（フィルター条件、YAML形式） ---
            base_filename = f"{node_type}_idx{index}.base"
            base_path = bases_dir / dir_name / base_filename

            if not base_path.exists() or overwrite:
                base_path.parent.mkdir(parents=True, exist_ok=True)
                base_content = self._format_base_filter(node_type, index, nodes)
                base_path.write_text(base_content, encoding="utf-8")
                written.append(base_path)

        return written

    def _format_base_filter(
        self,
        node_type: str,
        index: str,
        nodes: list[Node],
    ) -> str:
        """NodeGroup用の.baseファイル内容を生成（YAML形式、フィルター条件のみ）

        旧base_template形式: views/filters/sort のYAML構造。
        Obsidian上でフィルター条件に応じてpropertyをテーブル形式で表示する。

        Args:
            node_type: ノードタイプ
            index: インデックス
            nodes: グループ内のノード

        Returns:
            YAML形式のフィルター条件
        """
        default_views = self.graph_config.obsidian.default_views
        dir_name = get_directory_for_type(node_type)
        # パスは常にスラッシュ区切りにする（Windows対応）
        notes_dir_str = str(self.config.notes_dir).replace("\\", "/")
        folder_path = f"{notes_dir_str}/{dir_name}"

        # views設定をカスタマイズ
        views = []
        for view in default_views:
            custom_view = dict(view)
            if "filters" not in custom_view:
                custom_view["filters"] = {"and": []}
            if isinstance(custom_view["filters"], dict) and "and" in custom_view["filters"]:
                filters = list(custom_view["filters"]["and"])
                filters.insert(0, f'file.folder == "{folder_path}"')
                custom_view["filters"]["and"] = filters
            views.append(custom_view)

        data = {"views": views}
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

    def _format_group_file(
        self,
        node_type: str,
        index: str,
        nodes: list[Node],
    ) -> str:
        """NodeGroup用の-group.mdファイル内容を生成（frontmatter + メンバーリンク）

        Args:
            node_type: ノードタイプ
            index: インデックス
            nodes: グループ内のノード

        Returns:
            -group.mdファイルの内容
        """
        frontmatter = {
            "type": "nodegroup",
            "node_type": node_type,
            "index": index,
            "member_count": len(nodes),
        }

        yaml_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

        # メンバーノードへのリンク生成
        member_links: list[str] = []
        for node in sorted(nodes, key=lambda n: n.properties.get("version", "")):
            filename = f"{node.name}.{node.format}"
            link = to_obsidian_link(filename, self.config.obsidian_prefix)
            member_links.append(f"- {link}")

        return f"""---
{yaml_str.strip()}
---

## NodeGroup: {node_type} / idx{index}

このファイルは同一index（{index}）を持つ{node_type}タイプのノードをグループ化しています。

## メンバー

{chr(10).join(member_links)}
"""
