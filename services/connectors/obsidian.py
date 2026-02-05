"""Obsidianコネクタ: GraphModelをObsidian向けマークダウンにエクスポート

重要な命名規則:
- 実ファイル: "O-"プレフィックスなし (例: go_test_v1.inp)
- Obsidianファイル: "O-"プレフィックス付き (例: O-go_test_v1.inp.md)
- ディレクトリ: "O-"プレフィックスなし (例: notes/props/inp/go/)

リンク記法:
- 実ファイルへのリンク: [[{相対パス}|{表記名}]]
- mdファイルへのリンク: [[{".md"抜きのファイル名}]]
- ラベル付きリンク（独自記法）: label:[[ファイル名]]

.baseファイル:
- NodeGroupに相当し、folder/filter機能でグループを指定可能
- views設定でtable形式の表示を定義

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

        # タイプに応じてディレクトリ構造を決定
        if file_type in ("docs", "reports", "tools"):
            return notes_dir / dir_name / obsidian_filename
        else:
            return notes_dir / "inp" / dir_name / obsidian_filename

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

        # ノードごとにmdファイルを書き出し
        for node in graph.nodes:
            node_relations = relations_by_node.get(node.id, [])
            path = self.write_md_with_relations(node, node_relations, overwrite=overwrite)
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
        """NodeGroup（.base）ファイルを生成

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

        # グループごとに.baseファイルを生成
        for (node_type, index), nodes in groups.items():
            if len(nodes) < 2:
                continue

            base_filename = f"{node_type}_idx{index}.base.md"
            base_path = bases_dir / get_directory_for_type(node_type) / base_filename

            if base_path.exists() and not overwrite:
                continue

            base_path.parent.mkdir(parents=True, exist_ok=True)

            content = self._format_base_file(node_type, index, nodes)
            base_path.write_text(content, encoding="utf-8")
            written.append(base_path)

        return written

    def _format_base_file(
        self,
        node_type: str,
        index: str,
        nodes: list[Node],
    ) -> str:
        """NodeGroup用の.baseファイルの内容を生成

        Args:
            node_type: ノードタイプ
            index: インデックス
            nodes: グループ内のノード

        Returns:
            .baseファイルの内容
        """
        # views設定を取得
        default_views = self.graph_config.obsidian.default_views

        # ノートのフォルダパスを算出
        dir_name = get_directory_for_type(node_type)
        if node_type in ("docs", "reports", "tools"):
            folder_path = f"{self.config.notes_dir}/{dir_name}"
        else:
            folder_path = f"{self.config.notes_dir}/inp/{dir_name}"

        # views設定をカスタマイズ
        views = []
        for view in default_views:
            custom_view = dict(view)
            # filtersにfolder条件を追加
            if "filters" not in custom_view:
                custom_view["filters"] = {"and": []}
            if isinstance(custom_view["filters"], dict) and "and" in custom_view["filters"]:
                filters = list(custom_view["filters"]["and"])
                filters.insert(0, f'file.folder == "{folder_path}"')
                custom_view["filters"]["and"] = filters
            views.append(custom_view)

        # frontmatter生成
        frontmatter = {
            "type": "nodegroup",
            "node_type": node_type,
            "index": index,
            "member_count": len(nodes),
        }

        yaml_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
        views_yaml = yaml.safe_dump({"views": views}, allow_unicode=True, sort_keys=False)

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

## Views設定

```yaml
{views_yaml.strip()}
```
"""
