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
- 同一index: {type}_idx{index}.base（例: Abaqusインプット_idx1.base）
- 同一タイプ: {type}.base（例: Abaqusインプット.base）
- フィルターは対象フォルダのみ（例: file.folder == "notes/props/Abaqusインプット"）
- orderブロックにグループ内ノードのプロパティ積集合を追記

プロパティ型変換:
- 整数文字列 → int、小数文字列 → float、"true"/"false" → bool
- Obsidianのfrontmatterに適切な型で書き出される

上書き方針:
- props/とbases/はObsidianがプロジェクトの現在を真実として追従するため常に上書き

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


def _split_tag(tag: str) -> list[str]:
    """タグを'_'で分割して個別の単語タグに分離する

    Args:
        tag: 分割対象のタグ文字列

    Returns:
        分割後のタグリスト（'_'がない場合は元のタグを1要素リストで返す）

    Examples:
        >>> _split_tag("calculation_input")
        ['calculation', 'input']
        >>> _split_tag("go")
        ['go']
        >>> _split_tag("material/Steel_A")
        ['material/Steel_A']
    """
    # '/'を含むタグ（material/xxx等）は分割しない
    if "/" in tag:
        return [tag]
    parts = [p for p in tag.split("_") if p]
    return parts if parts else [tag]


def _coerce_property_value(value: Any) -> Any:
    """プロパティ値をObsidian向けに適切な型に変換

    - "true" / "false" → bool (True / False)
    - 整数文字列 → int
    - 小数文字列 → float
    - それ以外はそのまま返す

    Args:
        value: 変換対象の値

    Returns:
        型変換された値
    """
    if not isinstance(value, str):
        return value
    lower = value.strip().lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    # 整数判定（負の数にも対応）
    try:
        int_val = int(value)
        # 元の文字列が数値表現と一致する場合のみ変換
        if str(int_val) == value.strip():
            return int_val
    except (ValueError, TypeError):
        pass
    # 小数判定
    try:
        float_val = float(value)
        return float_val
    except (ValueError, TypeError):
        pass
    return value


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

        Note:
            プロパティ値はObsidian向けに型変換される:
            - "true"/"false" → bool
            - 整数文字列 → int
            - 小数文字列 → float

            index/idx/番号 や version/ver/バージョン が混在する場合、
            vocabで変換したキー名を正として統一し、変換前のキーは破棄する。
        """
        props = dict(node.properties)
        vocab = self.graph_config.vocab

        # index/version の値を取得してから全バリアントを除去
        index_value = props.pop("index", "")
        version_value = props.pop("version", "")

        # vocab変換後のキー名を正とする
        idx_canonical = vocab.get("idx", "idx")
        ver_canonical = vocab.get("v", vocab.get("ver", "ver"))

        # index系バリアントを全て除去（raw + vocab変換後の重複）
        for k in ("idx", "index"):
            props.pop(k, None)
            translated = vocab.get(k)
            if translated:
                props.pop(translated, None)
        # version系バリアントを全て除去
        for k in ("ver", "v", "version"):
            props.pop(k, None)
            translated = vocab.get(k)
            if translated:
                props.pop(translated, None)

        # 正規化されたキー名で設定
        props[idx_canonical] = index_value
        props[ver_canonical] = version_value

        # ファイル情報をpropertyとして追加
        props["node_type"] = node.type
        props["node_format"] = node.format
        real_path = props.get("path", "")
        props["file"] = real_path.replace("\\", "/") if real_path else ""

        # タグの拡充: タイプ、材料名などをtags listに追加
        # '_'を含むタグは単語ごとに分離する
        existing_tags = props.get("tags", [])
        if not isinstance(existing_tags, list):
            existing_tags = [existing_tags] if existing_tags else []
        # 既存タグを'_'で分割して展開
        split_tags: list[str] = []
        for t in existing_tags:
            split_tags.extend(_split_tag(str(t)))
        existing_tags = split_tags
        # タイプをタグに追加（'_'で分割）
        if node.type:
            for t in _split_tag(node.type):
                if t not in existing_tags:
                    existing_tags.append(t)
        # 材料名をタグに追加
        materials = props.get("materials", [])
        if isinstance(materials, list):
            for m in materials:
                tag = f"material/{m}"
                if tag not in existing_tags:
                    existing_tags.append(tag)
        props["tags"] = existing_tags

        # includesはObsidianリンク形式に変換
        # 相対パス（'/'を含む）はそのまま[[path]]形式、ファイル名は従来のO-プレフィックス形式
        if includes:
            links: list[str] = []
            for inc in includes:
                if "/" in inc:
                    # 相対パス → [[path]]形式（O-プレフィックス不要）
                    links.append(f"[[{inc}]]")
                else:
                    links.append(to_obsidian_link(inc, self.config.obsidian_prefix))
            props["includes"] = links

        # プロパティ値をObsidian向け型に変換（int, float, bool）
        for key, value in props.items():
            if isinstance(value, list):
                props[key] = [_coerce_property_value(v) for v in value]
            else:
                props[key] = _coerce_property_value(value)

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

        Note:
            warning/error/diff情報はfrontmatterのpropertyにも入れるが、
            視認性のためmarkdown本文にも記載する。
        """
        yaml_str = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)

        real_path = node.properties.get("path", "")

        content = f"""---
{yaml_str.strip()}
---

## ファイル情報

"""
        # directoryノードでは実ファイルリンクを出力しない
        if node.format != "directory" and real_path:
            file_link = to_obsidian_file_link(real_path, node.name)
            content += f"- 実ファイル: {file_link}\n"

        content += f"- タイプ: {node.type}\n"
        content += f"- フォーマット: {node.format}\n"

        # タグ情報を#tagname形式で出力
        tags = node.properties.get("tags", [])
        node_type_tag = node.type
        materials = node.properties.get("materials", [])
        verbose_name = node.properties.get("verbose_name", "")

        tag_items: list[str] = []
        # タイプタグ（'_'で分割）
        for t in _split_tag(node_type_tag):
            tag_items.append(f"#{t}")
        # ファイルタグ（'_'で分割）
        if isinstance(tags, list):
            for t in tags:
                for st in _split_tag(str(t)):
                    tag_items.append(f"#{st}")
        # 材料タグ
        if isinstance(materials, list):
            for m in materials:
                tag_items.append(f"#material/{m}")
        # verbose_nameタグ
        if verbose_name:
            tag_items.append(f"#name/{verbose_name}")

        # 重複除去して出力
        unique_tags = list(dict.fromkeys(tag_items))
        if unique_tags:
            content += "\n" + " ".join(unique_tags) + "\n"

        # リレーション情報を追加
        if relations:
            content += "\n## 関連ファイル\n\n"
            for label, target_md in relations:
                labeled_link = to_labeled_link(label, target_md)
                content += f"- {labeled_link}\n"

        # Warnings/Errors情報をmarkdown本文にも記載
        props = node.properties
        has_warnings = False

        # sta_warnings
        sta_warnings = props.get("sta_warnings", [])
        if sta_warnings:
            if not has_warnings:
                content += "\n## 警告・エラー\n\n"
                has_warnings = True
            content += "### .sta Warnings\n\n"
            for w in sta_warnings:
                content += f"- {w}\n"
            content += "\n"

        # sta_errors
        sta_errors = props.get("sta_errors", [])
        if sta_errors:
            if not has_warnings:
                content += "\n## 警告・エラー\n\n"
                has_warnings = True
            content += "### .sta Errors\n\n"
            for e in sta_errors:
                content += f"- {e}\n"
            content += "\n"

        # msg_warnings
        msg_warnings = props.get("msg_warnings", [])
        if msg_warnings:
            if not has_warnings:
                content += "\n## 警告・エラー\n\n"
                has_warnings = True
            content += "### .msg Warnings\n\n"
            for w in msg_warnings:
                content += f"- {w}\n"
            content += "\n"

        # msg_errors
        msg_errors = props.get("msg_errors", [])
        if msg_errors:
            if not has_warnings:
                content += "\n## 警告・エラー\n\n"
                has_warnings = True
            content += "### .msg Errors\n\n"
            for e in msg_errors:
                content += f"- {e}\n"
            content += "\n"

        # バージョン差分情報をmarkdown本文にも記載
        diff_from = props.get("diff_from", "")
        diff_summary = props.get("diff_summary", "")
        diff_details = props.get("diff_details", "")
        if diff_from and diff_summary and diff_summary != "差分なし":
            content += f"\n## 前バージョンとの差分\n\n"
            content += f"比較元: {diff_from}\n\n"
            content += f"### サマリー\n\n{diff_summary}\n\n"
            if diff_details and diff_details != "差分なし":
                content += f"### 詳細\n\n{diff_details}\n"

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

        最新ver → notes/bases/{dir}/{type}_idx{index}.base への相対パスリンク
        それ以外 → 次のversionのNodeへのObsidianリンク名

        Returns:
            {node_id: parent_link_string} のdict
            値はそのまま[[...]]で囲んでObsidianリンクにできる形式
        """
        parent_links: dict[int, str] = {}
        bases_dir_rel = str(self.config.bases_dir).replace("\\", "/")

        for (node_type, index), sorted_nodes in version_groups.items():
            dir_name = get_directory_for_type(node_type)
            base_filename = f"{node_type}_idx{index}.base"
            base_path = f"{bases_dir_rel}/{dir_name}/{base_filename}"

            if len(sorted_nodes) < 2:
                # 1つしかない場合は.baseリンクのみ
                if sorted_nodes:
                    parent_links[sorted_nodes[0].id] = base_path
                continue

            # 最新ver（最後の要素）は.base相対パスリンク
            latest = sorted_nodes[-1]
            parent_links[latest.id] = base_path

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

        props/とbasesはObsidianがプロジェクトの現在を真実として追従するため、
        overwrite引数に関わらず常に上書きする。

        Args:
            graph: エクスポートするグラフ
            overwrite: 既存ファイルを上書きするか（props/basesは常に上書き）

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

        # ノードごとにmdファイルを書き出し（props/は上書き前提）
        for node in graph.nodes:
            node_relations = relations_by_node.get(node.id, [])
            # 親リンクをincludesに設定
            includes = None
            if node.id in parent_links:
                includes = [parent_links[node.id]]
            path = self.write_md_with_relations(
                node, node_relations, includes=includes, overwrite=True
            )
            if path:
                written.append(path)

        # .baseファイル（NodeGroup）を生成（bases/は上書き前提）
        base_paths = self._write_base_files(graph, overwrite=True)
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

        生成されるファイル:
            - 同一index .base: {type}_idx{index}.base（同一type+indexのグループ、2ノード以上）
            - 同一type .base: {type}.base（同一typeの全ノード、2ノード以上）

        props/とbasesは上書き前提（Obsidianはプロジェクトの現在を真実として追従する）。

        Args:
            graph: グラフモデル
            overwrite: 既存ファイルを上書きするか（props/bases向けは常に上書き）

        Returns:
            書き込んだファイルパスのリスト
        """
        written: list[Path] = []
        bases_dir = self.project_root / self.config.bases_dir

        # type + index でグループ化
        idx_groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        # type でグループ化（同一タイプ）
        type_groups: dict[str, list[Node]] = defaultdict(list)

        for node in graph.nodes:
            index = node.properties.get("index", "")
            if index:
                idx_groups[(node.type, index)].append(node)
            type_groups[node.type].append(node)

        # 同一indexグループごとに .base を生成
        for (node_type, index), nodes in idx_groups.items():
            if len(nodes) < 2:
                continue

            dir_name = get_directory_for_type(node_type)
            base_filename = f"{node_type}_idx{index}.base"
            base_path = bases_dir / dir_name / base_filename

            # props/basesは上書き前提
            base_path.parent.mkdir(parents=True, exist_ok=True)
            base_content = self._format_base_filter(node_type, index, nodes)
            base_path.write_text(base_content, encoding="utf-8")
            written.append(base_path)

        # 同一タイプグループごとに .base を生成
        for node_type, nodes in type_groups.items():
            if len(nodes) < 2:
                continue

            dir_name = get_directory_for_type(node_type)
            base_filename = f"{node_type}.base"
            base_path = bases_dir / dir_name / base_filename

            # props/basesは上書き前提
            base_path.parent.mkdir(parents=True, exist_ok=True)
            base_content = self._format_base_filter(node_type, None, nodes)
            base_path.write_text(base_content, encoding="utf-8")
            written.append(base_path)

        return written

    def _compute_intersection_properties(self, nodes: list[Node]) -> list[str]:
        """ノードグループ内のプロパティキーの積集合を返す

        全ノードが共通して持つプロパティキーのリストを返す。
        内部管理用キー（path, tags）は除外する。

        Args:
            nodes: グループ内のノード

        Returns:
            共通プロパティキーのリスト
        """
        if not nodes:
            return []
        # 除外するキー（内部管理用・リスト型）
        exclude_keys = {"path", "tags"}
        # 各ノードのプロパティキー集合
        key_sets = []
        for node in nodes:
            keys = {k for k, v in node.properties.items()
                    if k not in exclude_keys and not isinstance(v, (list, dict))}
            key_sets.append(keys)
        # 積集合
        common = key_sets[0]
        for ks in key_sets[1:]:
            common = common & ks
        return sorted(common)

    def _vocab_translate_order(self, order: list[str]) -> list[str]:
        """orderリスト内のキー名をvocabで変換

        index/idx → vocab変換後キー、version/ver/v → vocab変換後キー、
        その他のキーもvocabにあれば変換。重複は除去。

        Args:
            order: 元のorderリスト

        Returns:
            vocab変換後のorderリスト（重複なし）
        """
        vocab = self.graph_config.vocab
        idx_canonical = vocab.get("idx", "idx")
        ver_canonical = vocab.get("v", vocab.get("ver", "ver"))

        # 変換マッピング
        key_map: dict[str, str] = {
            "idx": idx_canonical,
            "index": idx_canonical,
            "ver": ver_canonical,
            "v": ver_canonical,
            "version": ver_canonical,
        }

        translated: list[str] = []
        seen: set[str] = set()
        for key in order:
            new_key = key_map.get(key, vocab.get(key, key))
            if new_key not in seen:
                translated.append(new_key)
                seen.add(new_key)
        return translated

    def _vocab_translate_sort(self, sort_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """sortリスト内のpropertyキー名をvocabで変換

        Args:
            sort_list: 元のsortリスト

        Returns:
            vocab変換後のsortリスト
        """
        vocab = self.graph_config.vocab
        idx_canonical = vocab.get("idx", "idx")
        ver_canonical = vocab.get("v", vocab.get("ver", "ver"))

        key_map: dict[str, str] = {
            "idx": idx_canonical,
            "index": idx_canonical,
            "ver": ver_canonical,
            "v": ver_canonical,
            "version": ver_canonical,
        }

        translated: list[dict[str, Any]] = []
        for entry in sort_list:
            new_entry = dict(entry)
            prop = new_entry.get("property", "")
            new_entry["property"] = key_map.get(prop, vocab.get(prop, prop))
            translated.append(new_entry)
        return translated

    def _format_base_filter(
        self,
        node_type: str,
        index: str | None,
        nodes: list[Node],
    ) -> str:
        """NodeGroup用の.baseファイル内容を生成（YAML形式、フィルター条件のみ）

        Obsidian上でフィルター条件に応じてpropertyをテーブル形式で表示する。
        フィルターは対象フォルダのみに限定する（余計なand条件は追加しない）。
        orderブロックにはグループ内ノードのプロパティ積集合を追記する。
        orderとsortのキー名はvocabで変換する。

        Args:
            node_type: ノードタイプ
            index: インデックス（同一タイプグループの場合はNone）
            nodes: グループ内のノード

        Returns:
            YAML形式のフィルター条件
        """
        default_views = self.graph_config.obsidian.default_views
        dir_name = get_directory_for_type(node_type)
        # パスは常にスラッシュ区切りにする（Windows対応）
        notes_dir_str = str(self.config.notes_dir).replace("\\", "/")
        folder_path = f"{notes_dir_str}/{dir_name}"

        # グループ内のプロパティ積集合を算出
        intersection_props = self._compute_intersection_properties(nodes)

        # views設定をカスタマイズ
        views = []
        for view in default_views:
            custom_view = dict(view)
            # フィルターは対象フォルダのみ
            custom_view["filters"] = f'file.folder == "{folder_path}"'
            # orderにプロパティ積集合を追記（vocab変換済み）
            if "order" in custom_view:
                order = list(custom_view["order"])
            else:
                order = []
            for prop in intersection_props:
                if prop not in order:
                    order.append(prop)
            custom_view["order"] = self._vocab_translate_order(order)
            # sortのpropertyもvocab変換
            if "sort" in custom_view:
                custom_view["sort"] = self._vocab_translate_sort(list(custom_view["sort"]))
            views.append(custom_view)

        data = {"views": views}
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

