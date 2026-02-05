"""Obsidianコネクタ: GraphModelをObsidian向けマークダウンにエクスポート

重要な命名規則:
- 実ファイル: "O-"プレフィックスなし (例: go_test_v1.inp)
- Obsidianファイル: "O-"プレフィックス付き (例: O-go_test_v1.inp.md)
- ディレクトリ: "O-"プレフィックスなし (例: notes/props/inp/go/)

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from jj_types import GraphModel, Node


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
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.config = config or ObsidianConfig()

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

    def _format_md(self, frontmatter: dict[str, Any], node: Node) -> str:
        """マークダウンファイルの内容を生成"""
        yaml_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

        real_path = node.properties.get("path", "")

        return f"""---
{yaml_str.strip()}
---

## ファイル情報

- 実ファイル: `{real_path}`
- タイプ: {node.type}
- フォーマット: {node.format}
"""

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
        for node in graph.nodes:
            # TODO: リレーションからincludesを取得
            path = self.write_md(node, overwrite=overwrite)
            if path:
                written.append(path)
        return written
