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
from typing import Any

import yaml

from config import GraphConfig
from jj_types import GraphModel, Node
from services.export import AbstractExporter


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

    def _is_obsidian_origin(self, node: Node) -> bool:
        """ノードがObsidian由来（daily_note等）かどうかを判定"""
        return node.type == "daily_note"

    def get_md_path(self, node: Node) -> Path:
        """ノードからObsidian mdファイルパスを生成

        Args:
            node: 対象ノード

        Returns:
            mdファイルのパス

        Note:
            - ディレクトリ名にはO-プレフィックスは付かない
            - ファイル名にはO-プレフィックスが付く（daily_note由来ノードを除く）
        """
        notes_dir = self.project_root / self.config.notes_dir
        file_type = node.type
        format_ext = node.format

        # ディレクトリ名はO-なし
        dir_name = get_directory_for_type(file_type)

        # ファイル名はO-付き（Obsidian由来ノードはO-なし）
        real_filename = f"{node.name}.{format_ext}" if format_ext else node.name
        if self._is_obsidian_origin(node):
            obsidian_filename = f"{real_filename}.md" if not real_filename.endswith(".md") else real_filename
        else:
            obsidian_filename = to_obsidian_filename(real_filename, self.config.obsidian_prefix)

        # すべてのタイプで notes/props/{type}/ 配下に配置
        return notes_dir / dir_name / obsidian_filename

    @staticmethod
    def _flatten_properties(props: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """辞書プロパティを"."区切りで平坦化する

        ネストされた辞書は再帰的に展開される。
        例: {"mesh_quality": {"aspect_ratio": {"min": 0.5, "max": 1.0}}}
        → {"mesh_quality.aspect_ratio.min": 0.5, "mesh_quality.aspect_ratio.max": 1.0}

        リストは展開せずそのまま保持する。
        """
        result: dict[str, Any] = {}
        for key, value in props.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(ObsidianConnector._flatten_properties(value, prefix=full_key))
            else:
                result[full_key] = value
        return result

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

            ネストされた辞書は"."区切りで平坦化される（CSV exportと同様）。
        """
        # ネストされた辞書を平坦化してからコピー
        props = self._flatten_properties(dict(node.properties))
        vocab = self.graph_config.vocab

        # vocab変換後のキー名を正とする
        idx_canonical = vocab.get("idx", "idx")
        ver_canonical = vocab.get("v", vocab.get("ver", "ver"))

        # index/version の全バリアントキーを収集（rawキー優先順）
        idx_keys_ordered = ["index", "idx"]
        ver_keys_ordered = ["version", "v", "ver"]
        # vocab変換後キーを末尾に追加
        for k in ("idx", "index"):
            translated = vocab.get(k)
            if translated and translated not in idx_keys_ordered:
                idx_keys_ordered.append(translated)
        if idx_canonical not in idx_keys_ordered:
            idx_keys_ordered.append(idx_canonical)
        for k in ("ver", "v", "version"):
            translated = vocab.get(k)
            if translated and translated not in ver_keys_ordered:
                ver_keys_ordered.append(translated)
        if ver_canonical not in ver_keys_ordered:
            ver_keys_ordered.append(ver_canonical)

        # rawキーを優先して値を取得し、全バリアントを除去
        index_value = ""
        for k in idx_keys_ordered:
            val = props.pop(k, "")
            if val and not index_value:
                index_value = val
        version_value = ""
        for k in ver_keys_ordered:
            val = props.pop(k, "")
            if val and not version_value:
                version_value = val

        # 正規化されたキー名で設定
        props[idx_canonical] = index_value
        props[ver_canonical] = version_value

        # ファイル情報をpropertyとして追加
        props["node_type"] = node.type
        props["node_format"] = node.format
        real_path = props.get("path", "")
        props["file"] = real_path.replace("\\", "/") if real_path else ""

        # タグの構築: タイプ、材料名からObsidian用タグを生成
        obsidian_tags: list[str] = []
        # タイプをタグに追加（'_'で分割）
        if node.type:
            for t in _split_tag(node.type):
                if t not in obsidian_tags:
                    obsidian_tags.append(t)
        # 材料名をタグに追加
        materials = props.get("materials", [])
        if isinstance(materials, list):
            for m in materials:
                tag = f"material/{m}"
                if tag not in obsidian_tags:
                    obsidian_tags.append(tag)
        props["tags"] = obsidian_tags

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
    ) -> Path | None:
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
        node_type_tag = node.type
        materials = node.properties.get("materials", [])
        verbose_name = node.properties.get("verbose_name", "")

        tag_items: list[str] = []
        # タイプタグ（'_'で分割）
        for t in _split_tag(node_type_tag):
            tag_items.append(f"#{t}")
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
            content += "\n## 前バージョンとの差分\n\n"
            content += f"比較元: {diff_from}\n\n"
            content += f"### サマリー\n\n{diff_summary}\n\n"
            if diff_details and diff_details != "差分なし":
                content += f"### 詳細\n\n{diff_details}\n"

        # version_diffノード専用: 比較元/比較先ファイルへのリンク
        if node.type == "version_diff":
            content += "\n## バージョン比較\n\n"
            diff_from_file = props.get("diff_from", "")
            diff_to_file = props.get("diff_to", "")
            has_diffs = props.get("has_diffs", False)
            if diff_from_file:
                from_link = to_obsidian_link(Path(diff_from_file).name, self.config.obsidian_prefix)
                content += f"- 旧バージョン: {from_link}\n"
            if diff_to_file:
                to_link = to_obsidian_link(Path(diff_to_file).name, self.config.obsidian_prefix)
                content += f"- 新バージョン: {to_link}\n"
            content += f"- 差分有無: {'あり' if has_diffs else 'なし'}\n"

        # abaqus_elsetノード専用: 材料・親ファイルへのリンク・品質統計
        if node.type == "abaqus_elset":
            content += "\n## Elset情報\n\n"
            element_count = props.get("element_count")
            if element_count is not None:
                content += f"- 要素数: {element_count}\n"
            material = props.get("material", "")
            if material:
                content += f"- 割り当て材料: {material}\n"
            source_file = props.get("source_file", "")
            if source_file:
                source_link = to_obsidian_link(Path(source_file).name, self.config.obsidian_prefix)
                content += f"- ソースファイル: {source_link}\n"
            # 品質統計があれば表で表示
            quality = node.properties.get("quality", {})
            if isinstance(quality, dict) and quality:
                content += "\n### メッシュ品質\n\n"
                content += "| メトリクス | min | max | mean |\n"
                content += "|-----------|-----|-----|------|\n"
                for metric_name, metric_vals in quality.items():
                    if isinstance(metric_vals, dict):
                        content += (
                            f"| {metric_name} "
                            f"| {metric_vals.get('min', '-')} "
                            f"| {metric_vals.get('max', '-')} "
                            f"| {metric_vals.get('mean', '-')} |\n"
                        )

            # Dataview クエリ: Elsetと材料の関係を表示
            content += "\n### 関連材料（Dataview）\n\n"
            content += "```dataview\n"
            content += 'TABLE material AS "材料", element_count AS "要素数"\n'
            content += 'FROM "notes/props/abaqus_elset"\n'
            if material:
                content += f'WHERE material = "{material}"\n'
            content += "SORT element_count DESC\n"
            content += "```\n"

        # goノード: 所属elsetの一覧をDataviewで表示
        if node.type in ("go", "Abaqusインプット") and props.get("elsets"):
            content += "\n### 所属Elset一覧（Dataview）\n\n"
            content += "```dataview\n"
            content += 'TABLE element_count AS "要素数", material AS "材料"\n'
            content += 'FROM "notes/props/abaqus_elset"\n'
            node_name = f"{node.name}.{node.format}" if node.format else node.name
            content += f'WHERE source_file = "{node_name}"\n'
            content += "SORT file.name ASC\n"
            content += "```\n"

        # abaqus_materialノード: 使用しているelsetをDataviewで表示
        if node.type == "abaqus_material":
            content += "\n### 使用Elset（Dataview）\n\n"
            content += "```dataview\n"
            content += 'TABLE element_count AS "要素数", source_file AS "ソースファイル"\n'
            content += 'FROM "notes/props/abaqus_elset"\n'
            content += f'WHERE material = "{node.name}"\n'
            content += "SORT file.name ASC\n"
            content += "```\n"

        return content

    def _get_node_index(self, node: Node) -> str:
        """ノードからindex値を取得（vocab変換後キーにも対応）"""
        idx = node.properties.get("index", "")
        if not idx:
            idx_key = self.graph_config.vocab.get("idx", "")
            if idx_key:
                idx = node.properties.get(idx_key, "")
        return str(idx) if idx else ""

    def _get_node_version(self, node: Node) -> str:
        """ノードからversion値を取得（vocab変換後キーにも対応）"""
        ver = node.properties.get("version", "")
        if not ver:
            ver_key = self.graph_config.vocab.get("v", "") or self.graph_config.vocab.get("ver", "")
            if ver_key:
                ver = node.properties.get(ver_key, "")
        return str(ver) if ver else ""

    def _build_version_groups(self, nodes: list[Node]) -> dict[tuple[str, str], list[Node]]:
        """type + index でノードをバージョン順にグループ化

        Returns:
            {(type, index): [ノードをversion昇順でソート]} のdict
        """
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in nodes:
            index = self._get_node_index(node)
            if index:
                groups[(node.type, index)].append(node)

        # 各グループをversion昇順でソート
        for key in groups:
            groups[key] = sorted(groups[key], key=lambda n: self._get_version_sort_key(n))

        return groups

    def _get_version_sort_key(self, node: Node) -> tuple[int, str]:
        """ノードのバージョンソートキーを返す"""
        ver = self._get_node_version(node)
        if not ver:
            ver = "1"
        try:
            return (0, str(int(ver)).zfill(10))
        except (ValueError, TypeError):
            return (1, str(ver))

    def _build_parent_links(self, version_groups: dict[tuple[str, str], list[Node]]) -> dict[int, str]:
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

            # 最新以外は次のNodeへのリンク（実ファイル名で保持、node_to_frontmatterでO-変換）
            for i in range(len(sorted_nodes) - 1):
                current = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]
                next_filename = f"{next_node.name}.{next_node.format}"
                parent_links[current.id] = next_filename

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

        # Vault設定ファイルを初回のみ自動生成（.obsidian/が存在しない場合）
        vault_paths = self._write_vault_config()
        written.extend(vault_paths)

        # ノードIDからノードへのマッピングを作成
        node_by_id: dict[int, Node] = {node.id: node for node in graph.nodes}

        # ノードごとのリレーション情報を収集
        relations_by_node: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for rel in graph.relations:
            # source → target のリレーションを記録
            target_node = node_by_id.get(rel.node2_id)
            if target_node:
                target_filename = f"{target_node.name}.{target_node.format}"
                if self._is_obsidian_origin(target_node):
                    # Obsidian由来ノードはO-プレフィックスなし
                    target_md = f"{target_filename}.md" if not target_filename.endswith(".md") else target_filename
                else:
                    target_md = to_obsidian_filename(target_filename, self.config.obsidian_prefix)
                relations_by_node[rel.node1_id].append((rel.label, target_md))

        # バージョングループ構築と親リンク決定
        version_groups = self._build_version_groups(graph.nodes)
        parent_links = self._build_parent_links(version_groups)

        # ノードごとにmdファイルを書き出し（props/は上書き前提）
        # 全ノード（ファイル、ディレクトリ、非ファイルノード含む）を出力
        for node in graph.nodes:
            node_relations = relations_by_node.get(node.id, [])
            # 親リンクをincludesに設定
            includes = None
            if node.id in parent_links:
                includes = [parent_links[node.id]]
            path = self.write_md_with_relations(node, node_relations, includes=includes, overwrite=True)
            if path:
                written.append(path)

        # .baseファイル（NodeGroup）を生成（bases/は上書き前提）
        base_paths = self._write_base_files(graph, overwrite=True)
        written.extend(base_paths)

        # Elset-材料関係 Obsidian Canvas を生成
        canvas_path = self._write_elset_material_canvas(graph)
        if canvas_path:
            written.append(canvas_path)

        # Elset-材料-go 3層関係 Obsidian Canvas を生成
        canvas3_path = self._write_elset_material_go_canvas(graph)
        if canvas3_path:
            written.append(canvas3_path)

        # サマリーノート（Dataviewクエリによるプロジェクト概要）を生成
        summary_path = self._write_summary_note(graph)
        if summary_path:
            written.append(summary_path)

        return written

    def write_md_with_relations(
        self,
        node: Node,
        relations: list[tuple[str, str]],
        includes: list[str] | None = None,
        overwrite: bool = False,
    ) -> Path | None:
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

        # 全ノードをbase生成対象に含める
        for node in graph.nodes:
            index = self._get_node_index(node)
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
            keys = {k for k, v in node.properties.items() if k not in exclude_keys and not isinstance(v, (list, dict))}
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

    def _write_elset_material_canvas(
        self,
        graph: GraphModel,
    ) -> Path | None:
        """Elset-材料の関係をObsidian Canvas形式で出力

        Obsidian Canvasは.canvas拡張子のJSONファイルで、ノードとエッジを
        視覚的に配置するビジュアルキャンバスを生成する。
        Elsetノードと材料ノードの関係（uses_material）をグラフ化する。

        Args:
            graph: グラフモデル

        Returns:
            書き込んだcanvasファイルのパス。elsetがない場合はNone。
        """
        import json as json_mod

        elset_nodes = [n for n in graph.nodes if n.type == "abaqus_elset"]
        material_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]

        if not elset_nodes:
            return None

        canvas_nodes: list[dict[str, Any]] = []
        canvas_edges: list[dict[str, Any]] = []

        # 材料ノードの配置（上段）
        material_positions: dict[str, str] = {}  # material_name -> canvas_node_id
        for i, mat_node in enumerate(material_nodes):
            node_id = f"mat_{mat_node.id}"
            canvas_nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "file": str(self._get_canvas_md_path(mat_node)),
                    "x": i * 300,
                    "y": 0,
                    "width": 250,
                    "height": 60,
                    "color": "4",  # 緑系
                }
            )
            material_positions[mat_node.name] = node_id

        # Elsetノードの配置（下段、材料ごとにグループ化）
        material_groups: dict[str, list[Node]] = {}
        unassigned: list[Node] = []
        for elset_node in elset_nodes:
            mat = elset_node.properties.get("material", "")
            if mat and mat in material_positions:
                material_groups.setdefault(mat, []).append(elset_node)
            else:
                unassigned.append(elset_node)

        col = 0
        for mat_name, elsets in material_groups.items():
            for j, elset_node in enumerate(elsets):
                node_id = f"elset_{elset_node.id}"
                canvas_nodes.append(
                    {
                        "id": node_id,
                        "type": "file",
                        "file": str(self._get_canvas_md_path(elset_node)),
                        "x": col * 300,
                        "y": 200 + j * 80,
                        "width": 250,
                        "height": 60,
                        "color": "1",  # 赤系
                    }
                )
                # エッジ: elset -> material
                canvas_edges.append(
                    {
                        "id": f"edge_{elset_node.id}_{mat_name}",
                        "fromNode": node_id,
                        "fromSide": "top",
                        "toNode": material_positions[mat_name],
                        "toSide": "bottom",
                        "label": "uses_material",
                    }
                )
            col += 1

        # 未割り当てelset
        for j, elset_node in enumerate(unassigned):
            node_id = f"elset_{elset_node.id}"
            canvas_nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "file": str(self._get_canvas_md_path(elset_node)),
                    "x": col * 300,
                    "y": 200 + j * 80,
                    "width": 250,
                    "height": 60,
                    "color": "6",  # 灰色系
                }
            )

        canvas_data = {
            "nodes": canvas_nodes,
            "edges": canvas_edges,
        }

        canvas_dir = self.project_root / self.config.notes_dir
        canvas_dir.mkdir(parents=True, exist_ok=True)
        canvas_path = canvas_dir / "elset_material_map.canvas"
        canvas_path.write_text(
            json_mod.dumps(canvas_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return canvas_path

    def _write_elset_material_go_canvas(
        self,
        graph: GraphModel,
    ) -> Path | None:
        """Elset-材料-goの3層関係をObsidian Canvas形式で出力

        3層構造:
        - 上段: goノード（青系、ソースファイルとしてelsetの親）
        - 中段: 材料ノード（緑系）
        - 下段: Elsetノード（赤系、材料ごとにグループ化）

        goノードとelsetの関係はsource_fileプロパティで紐付ける。

        Args:
            graph: グラフモデル

        Returns:
            書き込んだcanvasファイルのパス。elsetがない場合はNone。
        """
        import json as json_mod

        elset_nodes = [n for n in graph.nodes if n.type == "abaqus_elset"]
        material_nodes = [n for n in graph.nodes if n.type == "abaqus_material"]

        if not elset_nodes:
            return None

        # goノードの特定: elsetのsource_fileに対応するノードを収集
        go_types = {"go", "Abaqusインプット"}
        go_candidates = [n for n in graph.nodes if n.type in go_types]
        # source_fileからgoノードへのマッピング
        go_by_filename: dict[str, Node] = {}
        for gn in go_candidates:
            fname = f"{gn.name}.{gn.format}" if gn.format else gn.name
            go_by_filename[fname] = gn
            go_by_filename[gn.name] = gn

        # elsetが参照するgoノードを収集（順序保持）
        referenced_go: dict[str, Node] = {}
        for en in elset_nodes:
            sf = en.properties.get("source_file", "")
            if sf and sf in go_by_filename:
                referenced_go[sf] = go_by_filename[sf]

        canvas_nodes: list[dict[str, Any]] = []
        canvas_edges: list[dict[str, Any]] = []

        # 上段: goノードの配置（Y=0）
        go_positions: dict[str, str] = {}  # source_filename -> canvas_node_id
        for i, (sf, go_node) in enumerate(referenced_go.items()):
            node_id = f"go_{go_node.id}"
            canvas_nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "file": str(self._get_canvas_md_path(go_node)),
                    "x": i * 300,
                    "y": 0,
                    "width": 250,
                    "height": 60,
                    "color": "5",  # 青系
                }
            )
            go_positions[sf] = node_id
            # name単体でもマッピング
            go_positions[go_node.name] = node_id

        # 中段: 材料ノードの配置（Y=150）
        material_positions: dict[str, str] = {}  # material_name -> canvas_node_id
        for i, mat_node in enumerate(material_nodes):
            node_id = f"mat_{mat_node.id}"
            canvas_nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "file": str(self._get_canvas_md_path(mat_node)),
                    "x": i * 300,
                    "y": 150,
                    "width": 250,
                    "height": 60,
                    "color": "4",  # 緑系
                }
            )
            material_positions[mat_node.name] = node_id

        # 下段: Elsetノードの配置（Y=350〜）
        material_groups: dict[str, list[Node]] = {}
        unassigned: list[Node] = []
        for elset_node in elset_nodes:
            mat = elset_node.properties.get("material", "")
            if mat and mat in material_positions:
                material_groups.setdefault(mat, []).append(elset_node)
            else:
                unassigned.append(elset_node)

        col = 0
        for mat_name, elsets in material_groups.items():
            for j, elset_node in enumerate(elsets):
                node_id = f"elset_{elset_node.id}"
                canvas_nodes.append(
                    {
                        "id": node_id,
                        "type": "file",
                        "file": str(self._get_canvas_md_path(elset_node)),
                        "x": col * 300,
                        "y": 350 + j * 80,
                        "width": 250,
                        "height": 60,
                        "color": "1",  # 赤系
                    }
                )
                # エッジ: elset -> material
                canvas_edges.append(
                    {
                        "id": f"edge_{elset_node.id}_{mat_name}",
                        "fromNode": node_id,
                        "fromSide": "top",
                        "toNode": material_positions[mat_name],
                        "toSide": "bottom",
                        "label": "uses_material",
                    }
                )
                # エッジ: elset -> go (source_file)
                sf = elset_node.properties.get("source_file", "")
                if sf and sf in go_positions:
                    canvas_edges.append(
                        {
                            "id": f"edge_go_{elset_node.id}_{sf}",
                            "fromNode": node_id,
                            "fromSide": "top",
                            "toNode": go_positions[sf],
                            "toSide": "bottom",
                            "label": "defined_in",
                        }
                    )
            col += 1

        # 未割り当てelset
        for j, elset_node in enumerate(unassigned):
            node_id = f"elset_{elset_node.id}"
            canvas_nodes.append(
                {
                    "id": node_id,
                    "type": "file",
                    "file": str(self._get_canvas_md_path(elset_node)),
                    "x": col * 300,
                    "y": 350 + j * 80,
                    "width": 250,
                    "height": 60,
                    "color": "6",  # 灰色系
                }
            )
            # 未割り当てでもsource_fileがあればgoへのエッジ
            sf = elset_node.properties.get("source_file", "")
            if sf and sf in go_positions:
                canvas_edges.append(
                    {
                        "id": f"edge_go_{elset_node.id}_{sf}",
                        "fromNode": node_id,
                        "fromSide": "top",
                        "toNode": go_positions[sf],
                        "toSide": "bottom",
                        "label": "defined_in",
                    }
                )

        canvas_data = {
            "nodes": canvas_nodes,
            "edges": canvas_edges,
        }

        canvas_dir = self.project_root / self.config.notes_dir
        canvas_dir.mkdir(parents=True, exist_ok=True)
        canvas_path = canvas_dir / "elset_material_go_map.canvas"
        canvas_path.write_text(
            json_mod.dumps(canvas_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return canvas_path

    def _get_canvas_md_path(self, node: Node) -> Path:
        """Canvas用のmd相対パスを返す（project_rootからの相対）"""
        md_path = self.get_md_path(node)
        try:
            return md_path.relative_to(self.project_root)
        except ValueError:
            return md_path

    def _write_vault_config(self) -> list[Path]:
        """Obsidian Vault設定ファイルを生成（初回のみ）

        .obsidian/ ディレクトリが存在しない場合に、config.yamlのvault設定を
        反映してVault設定を自動生成する。既存のVault設定がある場合は一切変更しない。

        設定はconfig.yamlのobsidian.vaultセクションから読み込む:
        - vault.app → .obsidian/app.json
        - vault.community-plugins → .obsidian/community-plugins.json
        - vault.core-plugins → .obsidian/core-plugins-migration.json

        Returns:
            書き込んだファイルパスのリスト。既存Vaultの場合は空リスト。
        """
        import json as json_mod

        obsidian_dir = self.project_root / ".obsidian"
        if obsidian_dir.exists():
            return []

        written: list[Path] = []
        obsidian_dir.mkdir(parents=True, exist_ok=True)

        # config.yamlのvault設定を取得
        vault_config = self.graph_config.obsidian.vault

        # app.json: config.yamlのvault.appから生成
        app_path = obsidian_dir / "app.json"
        app_path.write_text(
            json_mod.dumps(vault_config.app, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(app_path)

        # community-plugins.json: config.yamlのvault.community-pluginsから生成
        cp_path = obsidian_dir / "community-plugins.json"
        cp_path.write_text(
            json_mod.dumps(vault_config.community_plugins, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(cp_path)

        # core-plugins-migration.json: config.yamlのvault.core-pluginsから生成
        core_path = obsidian_dir / "core-plugins-migration.json"
        core_path.write_text(
            json_mod.dumps(vault_config.core_plugins, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(core_path)

        return written

    def _write_summary_note(self, graph: GraphModel) -> Path | None:
        """プロジェクトサマリーノートを生成（Dataview/プラグイン前提）

        Obsidianプラグイン（Dataview, DB Folder等）がインストールされている前提で、
        プロジェクト全体の概要をDataviewクエリで動的に表示するサマリーノートを生成する。

        Args:
            graph: グラフモデル

        Returns:
            書き込んだファイルのパス。ノードがない場合はNone。
        """
        if not graph.nodes:
            return None

        # タイプ別ノード数を集計
        type_counts: dict[str, int] = defaultdict(int)
        for node in graph.nodes:
            type_counts[node.type] += 1

        notes_dir = self.project_root / self.config.notes_dir
        notes_dir.mkdir(parents=True, exist_ok=True)
        summary_path = notes_dir / "jj-summary.md"

        notes_dir_str = str(self.config.notes_dir).replace("\\", "/")

        content = """---
tags:
  - jj
  - summary
---

## プロジェクト概要

"""
        content += "| タイプ | 件数 |\n"
        content += "|--------|------|\n"
        for node_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            content += f"| {node_type} | {count} |\n"

        content += f"""
総ノード数: {len(graph.nodes)}
総リレーション数: {len(graph.relations)}

## 全ファイル一覧（Dataview）

```dataview
TABLE node_type AS "タイプ", node_format AS "フォーマット", tags AS "タグ"
FROM "{notes_dir_str}"
WHERE node_type != null
SORT node_type ASC, file.name ASC
```

"""
        # タイプ別セクション
        for node_type in sorted(type_counts.keys()):
            dir_name = get_directory_for_type(node_type)
            folder = f"{notes_dir_str}/{dir_name}"
            content += f"""### {node_type} ({type_counts[node_type]}件)

```dataview
TABLE WITHOUT ID file.link AS "ファイル", 番号 AS "番号", バージョン AS "ver"
FROM "{folder}"
SORT file.name ASC
```

"""

        # Canvas リンク
        content += "## Canvas\n\n"
        content += "- [[elset_material_map.canvas|Elset-材料マップ]]\n"
        content += "- [[elset_material_go_map.canvas|Elset-材料-go 3層マップ]]\n"

        summary_path.write_text(content, encoding="utf-8")
        return summary_path


class ObsidianExporter(AbstractExporter):
    """Obsidian形式エクスポーター（AbstractExporterサブクラス）

    ObsidianConnectorをラップし、AbstractExporterレジストリに登録する。
    """

    format = "obsidian"
    priority = 20

    def export(self, graph: GraphModel, **kwargs: Any) -> dict[str, Any]:
        """Obsidianエクスポート

        kwargs:
            project_root: Path - プロジェクトルート
            overwrite: bool - 既存ファイルを上書きするか
        """
        project_root = kwargs.get("project_root")
        overwrite = kwargs.get("overwrite", False)
        connector = ObsidianConnector(project_root=project_root)
        written = connector.export_graph(graph, overwrite=overwrite)
        # Vault初期化されたかどうかを判定
        vault_initialized = any(".obsidian" in str(p) for p in written)
        return {
            "written_paths": written,
            "count": len(written),
            "vault_initialized": vault_initialized,
        }

    def format_cli_result(self, result: dict[str, Any], project_root: Path) -> str:
        written_paths = result.get("written_paths", [])
        vault_initialized = result.get("vault_initialized", False)
        lines = [
            "\n=== エクスポート完了 ===",
            f"書き込みファイル数: {len(written_paths)}",
        ]
        if vault_initialized:
            lines.append("\n[Vault初期化] .obsidian/ ディレクトリを生成しました")
            lines.append("  推奨プラグイン: Dataview, DB Folder")
            lines.append("  Obsidianでこのフォルダを開き、コミュニティプラグインから")
            lines.append("  上記プラグインをインストールしてください")
        if written_paths:
            lines.append("\n書き込んだファイル:")
            for path in written_paths[:10]:
                try:
                    rel_path = Path(path).relative_to(project_root)
                except ValueError:
                    rel_path = path
                lines.append(f"  {rel_path}")
            if len(written_paths) > 10:
                lines.append(f"  ... 他 {len(written_paths) - 10} 件")
        return "\n".join(lines)
