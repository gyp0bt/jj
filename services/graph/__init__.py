"""GraphService: プロジェクトフォルダのパースとグラフデータ管理

このモジュールはjjのコアとなるグラフ機能を提供します。
- プロジェクトフォルダのスキャンとファイル解析
- GraphModelへの変換
- サブバージョン関係・グループ関係の構築
- 同一ファイルタイプの関連付け（has_output）
- フォルダベースの関連付け（contains）
- material.inpの高度な解析（abaqus_material）
- 解析結果ファイルの解析（analysis_status）
- グラフデータの保存・読み込み

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

from jj_types import GraphModel, Node, Relation
from services.storage import GraphStorage
from services.parse.file_parse import FileParse, FileType, DEFAULT_EXTENSIONS, _parse_prop_token as _parse_prop_token_static
from services.connectors.pymesh_connector import extract_mesh_stats, extract_material_elset_mapping
from config import GraphConfig


# 解析結果ファイルの成否判定用パターン
_STA_SUCCESS_PATTERN = re.compile(
    r"THE ANALYSIS HAS COMPLETED SUCCESSFULLY", re.IGNORECASE
)
_STA_NOT_COMPLETED_PATTERN = re.compile(
    r"THE ANALYSIS HAS NOT BEEN COMPLETED", re.IGNORECASE
)
_STA_ERROR_PATTERN = re.compile(r"\*\*\*ERROR:\s*(.+)", re.IGNORECASE)
_STA_WARNING_PATTERN = re.compile(r"\*\*\*WARNING:\s*(.+)", re.IGNORECASE)

# .msg ファイル解析用パターン
_MSG_ERROR_PATTERN = re.compile(r"\*\*\*ERROR:\s*(.+)", re.IGNORECASE)
_MSG_WARNING_PATTERN = re.compile(r"\*\*\*WARNING:\s*(.+)", re.IGNORECASE)

# has_output 関係で対象とする出力ファイル拡張子
OUTPUT_EXTENSIONS: frozenset[str] = frozenset({
    ".csv", ".json", ".png", ".gif", ".xlsx", ".yaml", ".pptx",
    ".pdf", ".svg", ".html", ".txt",
})


def parse_sta_file(sta_path: Path) -> dict[str, Any]:
    """Abaqus .sta ファイルを解析して解析結果のステータスを返す

    Args:
        sta_path: .staファイルのパス

    Returns:
        解析結果の辞書:
        - analysis_status: "completed" | "failed" | "unknown"
        - errors: エラーメッセージのリスト
        - warnings: 警告メッセージのリスト
    """
    result: dict[str, Any] = {
        "analysis_status": "unknown",
        "errors": [],
        "warnings": [],
    }

    try:
        with sta_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, IOError):
        return result

    if _STA_SUCCESS_PATTERN.search(content):
        result["analysis_status"] = "completed"
    elif _STA_NOT_COMPLETED_PATTERN.search(content):
        result["analysis_status"] = "failed"

    for match in _STA_ERROR_PATTERN.finditer(content):
        result["errors"].append(match.group(1).strip())

    for match in _STA_WARNING_PATTERN.finditer(content):
        result["warnings"].append(match.group(1).strip())

    return result


def parse_material_blocks(inp_path: Path) -> list[dict[str, Any]]:
    """Abaqus .inp ファイルから *MATERIAL ブロックを解析

    軽量なパーサーで *MATERIAL ブロックを抽出し、物性定義データを返す。
    abaqus_connector の read_inp() は重いため、material専用の軽量パーサーを使用。

    Args:
        inp_path: .inpファイルのパス

    Returns:
        物性情報のリスト。各要素は:
        - name: 物性名
        - properties: プロパティ辞書
        - keywords: 含まれるキーワードのリスト
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

        # キーワード行
        if line.startswith("*"):
            norm = re.sub(r"\s+", "", line).lower()
            tokens = [s for s in norm.split(",") if s]
            keyword = tokens[0].replace("*", "")

            # *MATERIAL 行
            if keyword == "material":
                _flush_keyword()
                # 前のmaterialを保存
                if current_material:
                    materials.append(current_material)

                # name を取得
                name = ""
                for tok in tokens[1:]:
                    if tok.startswith("name="):
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

            # material配下のキーワード
            if current_material is not None:
                _flush_keyword()
                current_keyword = keyword
                current_data = []
                continue

        # データ行（materialブロック配下）
        if current_material is not None and current_keyword:
            try:
                values = [
                    float(v.strip()) for v in line.split(",")
                    if v.strip()
                ]
                if values:
                    current_data.append(values)
            except ValueError:
                pass

    # 最後のブロックを保存
    _flush_keyword()
    if current_material:
        materials.append(current_material)

    return materials


def parse_msg_file(msg_path: Path) -> dict[str, Any]:
    """Abaqus .msg ファイルを解析してエラーと警告を抽出する

    .msgファイルはAbaqusの解析実行中の詳細メッセージログで、
    ***ERROR や ***WARNING といったマーカーでエラー・警告を記録する。

    Args:
        msg_path: .msgファイルのパス

    Returns:
        解析結果の辞書:
        - errors: エラーメッセージのリスト
        - warnings: 警告メッセージのリスト
    """
    result: dict[str, Any] = {
        "errors": [],
        "warnings": [],
    }

    try:
        with msg_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, IOError):
        return result

    for match in _MSG_ERROR_PATTERN.finditer(content):
        result["errors"].append(match.group(1).strip())

    for match in _MSG_WARNING_PATTERN.finditer(content):
        result["warnings"].append(match.group(1).strip())

    return result


class GraphService:
    """プロジェクトのグラフデータを管理するサービス"""

    def __init__(
        self,
        project_root: Path | str | None = None,
        storage: GraphStorage | None = None,
        config: GraphConfig | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.storage = storage or GraphStorage()
        self.config = config or GraphConfig.load(self.project_root)
        self._node_id_counter = 0
        self._relation_id_counter = 0

    def _next_node_id(self) -> int:
        self._node_id_counter += 1
        return self._node_id_counter

    def _next_relation_id(self) -> int:
        self._relation_id_counter += 1
        return self._relation_id_counter

    def scan_files(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
    ) -> list[Path]:
        """プロジェクトルートからファイルをスキャン

        Args:
            extensions: 対象拡張子（デフォルト: DEFAULT_EXTENSIONS）
            exclude_dirs: 除外するディレクトリ名（ignore設定とマージ）

        Returns:
            スキャンされたファイルパスのリスト
        """
        ext_set = set(extensions or DEFAULT_EXTENSIONS)
        # デフォルトの除外ディレクトリ
        default_exclude = {".git", ".jj", "__pycache__", "node_modules", ".venv"}
        exclude_set = set(exclude_dirs or default_exclude)

        files: list[Path] = []
        for root, dirs, filenames in os.walk(self.project_root):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in exclude_set]

            root_path = Path(root)
            for filename in filenames:
                file_path = root_path / filename
                rel_path = self._safe_relative_path(file_path)

                # ignore設定でチェック
                if self.config.ignore.should_ignore(rel_path):
                    continue

                # 拡張子チェック
                lower_name = filename.lower()
                if any(lower_name.endswith(ext.lower()) for ext in ext_set):
                    files.append(file_path)

        return sorted(files)

    def scan_directories(
        self,
        exclude_dirs: Iterable[str] | None = None,
    ) -> list[Path]:
        """プロジェクトルートからディレクトリをスキャン

        名前がファイル命名規則に合致するディレクトリ（go_idx1_v1等）を検索。

        Args:
            exclude_dirs: 除外するディレクトリ名

        Returns:
            スキャンされたディレクトリパスのリスト
        """
        default_exclude = {".git", ".jj", "__pycache__", "node_modules", ".venv"}
        exclude_set = set(exclude_dirs or default_exclude)

        dirs_found: list[Path] = []
        for root, dirs, _ in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in exclude_set]

            root_path = Path(root)
            for dirname in dirs:
                dir_path = root_path / dirname
                rel_path = self._safe_relative_path(dir_path)

                if self.config.ignore.should_ignore(rel_path):
                    continue

                # ディレクトリ名がファイル命名規則に合致するかチェック
                parser = FileParse(dirname)
                if parser.get_file_type() != FileType.UNKNOWN:
                    dirs_found.append(dir_path)

        return sorted(dirs_found)

    def file_to_node(self, file_path: Path) -> Node:
        """ファイルパスからNodeを生成"""
        parser = FileParse(file_path)
        file_type = parser.get_file_type()
        props = parser.get_props()
        tags = parser.get_tags()

        # 相対パスを安全に生成（Windows対応）
        rel_path = self._safe_relative_path(file_path)
        filename = file_path.name

        # path-type-mapからタイプを取得（設定が優先）
        config_type = self.config.path_type_map.get_type(rel_path, filename)
        resolved_type = config_type if config_type else file_type.value

        # path-property-mapからプロパティを取得
        config_props = self.config.path_property_map.get_properties(rel_path)

        # path-tag-mapからタグを取得
        config_tags = self.config.path_tag_map.get_tags(rel_path)

        # token-key-mapの適用: 生トークンに対してマッチングし、
        # マッチしたトークンは指定キーのプロパティに変換。
        # 通常のprop解析で分割された結果は上書きする。
        raw_tokens = parser.get_tokens()
        for token in raw_tokens:
            mapped_key = self.config.token_key_map.get_key(token)
            if mapped_key:
                # 通常の解析で分割された結果を除去（例: hogehoge24 → hogehoge:24）
                parsed = _parse_prop_token_static(token)
                if parsed:
                    props.pop(parsed[0], None)
                # タグからも除去
                if token in tags:
                    tags.remove(token)
                # token-key-mapのキーで全トークンを値として設定
                props[mapped_key] = token

        # vocabを使ってpropsのキーと値を変換
        translated_props: dict[str, Any] = {}
        for key, value in props.items():
            translated_key = self.config.vocab.get(key, key)
            translated_value = self.config.vocab.get(str(value), str(value)) if isinstance(value, str) else value
            translated_props[translated_key] = translated_value

        # 日付を取得
        date_formatted = parser.get_date_formatted()

        # oldフォルダに入っていなければactive=True
        parent_dir = file_path.parent.name if isinstance(file_path, Path) else Path(str(file_path)).parent.name
        active = "false" if parent_dir == "old" else "true"

        properties: dict[str, Any] = {
            "path": rel_path,
            "index": parser.get_index(),
            "version": parser.get_version(),
            "tags": tags + config_tags,
            "active": active,
            **translated_props,
            **config_props,  # 設定からのプロパティが優先
        }

        # 日付がある場合のみ追加
        if date_formatted:
            properties["date"] = date_formatted

        # Abaqusインプット向け: *PARAMETER/**propsブロックからプロパティを読み取る
        inp_param_props = self._read_inp_parameter_props(file_path)
        if inp_param_props:
            properties.update(inp_param_props)

        return Node(
            id=self._next_node_id(),
            type=resolved_type,
            name=parser.get_basename(),
            format=parser._split_extension()[1].lstrip("."),
            properties=properties,
        )

    def _read_inp_parameter_props(self, file_path: Path) -> dict[str, str]:
        """INPファイルの*PARAMETER/**propsブロックからプロパティを読み取る

        *PARAMETER キーワードの直後に **props コメントがある場合、
        そのブロック内のkey=value形式のパラメータをプロパティとして抽出する。
        vocabマッピングを適用してキーと値を変換する。

        Args:
            file_path: INPファイルのパス

        Returns:
            抽出されたプロパティの辞書
        """
        # INPファイルのみ対象
        if not str(file_path).lower().endswith(".inp"):
            return {}
        if not file_path.exists():
            return {}

        props: dict[str, str] = {}
        try:
            with file_path.open(encoding="utf-8", errors="ignore") as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    s = line.strip()
                    s_l = s.lower().replace(" ", "")
                    if s_l.startswith("*parameter"):
                        header = f.readline()
                        if not header:
                            break
                        header_s = header.strip().lower().replace(" ", "")
                        if not header_s.startswith("**props"):
                            continue
                        while True:
                            line2 = f.readline()
                            if not line2:
                                break
                            t = line2.strip()
                            if not t:
                                continue
                            if t.startswith("**"):
                                continue
                            if t.lstrip().startswith("*"):
                                break
                            u = t.replace(" ", "")
                            if "=" not in u:
                                continue
                            k, v = u.split("=", 1)
                            if k:
                                k = self.config.vocab.get(k, k)
                                v = self.config.vocab.get(v, v)
                                props[k] = v
                        return props
        except (OSError, IOError):
            pass
        return props

    def _safe_relative_path(self, file_path: Path) -> str:
        """Windowsでも安全に相対パスを生成

        先頭の ``./`` を除去し、常にPOSIX形式（/区切り）で返す。

        Args:
            file_path: 対象ファイルパス

        Returns:
            POSIX形式の相対パス文字列（先頭 ./ なし）
        """
        try:
            resolved = file_path.resolve()
            rel = resolved.relative_to(self.project_root.resolve())
            # 常にPOSIX形式（/）で返す
            result = rel.as_posix()
        except ValueError:
            # relative_toが失敗した場合（異なるドライブ等）
            result = file_path.as_posix()

        # 先頭の ./ を除去
        while result.startswith("./"):
            result = result[2:]
        return result

    def _build_scan_extensions(
        self,
        extensions: Iterable[str] | None = None,
    ) -> set[str]:
        """スキャン対象の拡張子セットを構築

        明示的にextensionsが指定されない場合、DEFAULT_EXTENSIONSに加えて
        file-relations設定のinput/result/asset拡張子を自動マージする。
        これにより、CLIからのjj g parse実行時に.inp, .odb, .sta等も確実にスキャンされる。
        """
        if extensions is not None:
            return set(extensions)
        ext_set = set(DEFAULT_EXTENSIONS)
        ext_set.update(self.config.file_relations.input_extensions)
        ext_set.update(self.config.file_relations.result_extensions)
        ext_set.update(self.config.file_relations.asset_extensions)
        return ext_set

    def parse_project(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
    ) -> GraphModel:
        """プロジェクトをパースしてGraphModelを生成

        Args:
            extensions: 対象拡張子（Noneの場合はDEFAULT_EXTENSIONS + config file-relationsを使用）
            exclude_dirs: 除外ディレクトリ

        Returns:
            生成されたGraphModel
        """
        merged_extensions = self._build_scan_extensions(extensions)
        files = self.scan_files(extensions=merged_extensions, exclude_dirs=exclude_dirs)

        nodes: list[Node] = []
        node_by_path: dict[str, Node] = {}

        # ノード生成
        for file_path in files:
            node = self.file_to_node(file_path)
            nodes.append(node)
            node_by_path[node.properties.get("path", "")] = node

        # リレーション生成
        relations: list[Relation] = []

        # サブバージョン関係とグループ関係を構築
        version_relations, group_relations = self._build_version_and_group_relations(nodes)
        relations.extend(version_relations)
        relations.extend(group_relations)

        # 入力-結果関係を構築
        result_relations = self._build_result_relations(nodes)
        relations.extend(result_relations)

        # アセット関係を構築
        asset_relations = self._build_asset_relations(nodes)
        relations.extend(asset_relations)

        # includes関係を構築（inpファイルの*includeディレクティブ）
        includes_relations = self._build_includes_relations(nodes, node_by_path)
        relations.extend(includes_relations)

        # 同一ファイルタイプのprops差分関連付け（has_output）
        output_relations = self._build_output_relations(nodes)
        relations.extend(output_relations)

        # フォルダベースの関連付け（contains）
        dir_nodes, contains_relations = self._build_directory_relations(
            nodes, extensions=extensions, exclude_dirs=exclude_dirs
        )
        nodes.extend(dir_nodes)
        relations.extend(contains_relations)

        # material.inpの高度な解析（abaqus_material）
        mat_nodes, mat_relations = self._build_material_nodes(nodes)
        nodes.extend(mat_nodes)
        relations.extend(mat_relations)

        # pymeshによるメッシュ統計エンリッチメント
        self._enrich_mesh_stats(nodes)

        # 材料割り当て関係の構築（material→elset→element）
        mat_assign_relations = self._build_material_assignment_relations(
            nodes, mat_nodes
        )
        relations.extend(mat_assign_relations)

        # 解析結果ファイルの解析（analysis_status）
        self._enrich_sta_status(nodes)

        # .msgファイルの解析（errors/warnings抽出）
        self._enrich_msg_status(nodes)

        return GraphModel(nodes=nodes, relations=relations)

    def _build_version_and_group_relations(
        self, nodes: list[Node]
    ) -> tuple[list[Relation], list[Relation]]:
        """サブバージョン関係とグループ関係を構築

        同一type/indexのノードをグループ化し、version順にサブバージョン関係を作成

        Args:
            nodes: ノードのリスト

        Returns:
            (サブバージョン関係のリスト, グループ関係のリスト)
        """
        version_relations: list[Relation] = []
        group_relations: list[Relation] = []

        # type + index でノードをグループ化
        groups: dict[tuple[str, str], list[Node]] = defaultdict(list)
        for node in nodes:
            node_type = node.type
            index = node.properties.get("index", "")
            if index:  # indexがあるノードのみグループ化
                groups[(node_type, index)].append(node)

        for (node_type, index), group_nodes in groups.items():
            if len(group_nodes) < 2:
                continue

            # version順にソート（versionが空の場合は"1"として扱う）
            def get_version_key(n: Node) -> tuple[int, str]:
                ver = n.properties.get("version", "")
                # versionが空の場合はデフォルトで"1"として扱う
                if not ver:
                    ver = "1"
                # 数値として解釈できる場合は数値でソート
                try:
                    return (0, str(int(ver)).zfill(10))
                except (ValueError, TypeError):
                    return (1, str(ver))

            sorted_nodes = sorted(group_nodes, key=get_version_key)

            # サブバージョン関係を作成（version順にリンク）
            for i in range(len(sorted_nodes) - 1):
                prev_node = sorted_nodes[i]
                next_node = sorted_nodes[i + 1]
                version_relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="next_version",
                        node1_id=prev_node.id,
                        node2_id=next_node.id,
                    )
                )

            # グループ関係を作成（すべてのノードを同一グループとしてリンク）
            representative = sorted_nodes[0]
            for member in sorted_nodes[1:]:
                group_relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="same_index_group",
                        node1_id=representative.id,
                        node2_id=member.id,
                    )
                )

        return version_relations, group_relations

    def _build_result_relations(self, nodes: list[Node]) -> list[Relation]:
        """入力ファイルと結果ファイルの関係を構築

        同じbasename（go_idx1_w5_t20等）を持つファイルのうち、
        入力ファイル（.inp）と結果ファイル（.odb, .sta, .csv等）の間に
        result_of関係を作成します。
        """
        relations: list[Relation] = []

        input_extensions = self.config.file_relations.input_extensions
        result_extensions = self.config.file_relations.result_extensions

        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in nodes:
            basename = node.name
            by_basename[basename].append(node)

        for basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            input_nodes = []
            result_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in result_extensions:
                    result_nodes.append(node)

            for input_node in input_nodes:
                for result_node in result_nodes:
                    if self._nodes_have_same_props(input_node, result_node):
                        relations.append(
                            Relation(
                                id=self._next_relation_id(),
                                label="result_of",
                                node1_id=result_node.id,
                                node2_id=input_node.id,
                            )
                        )

        return relations

    def _build_asset_relations(self, nodes: list[Node]) -> list[Relation]:
        """アセットファイルと入力ファイルの関係を構築

        同じbasename（mesh等）を持つファイルのうち、
        アセットファイル（.modfem, .stl等）と入力ファイル（.inp）の間に
        derived_from関係を作成します。
        """
        relations: list[Relation] = []

        input_extensions = self.config.file_relations.input_extensions
        asset_extensions = self.config.file_relations.asset_extensions

        by_basename: dict[str, list[Node]] = defaultdict(list)
        for node in nodes:
            basename = node.name
            by_basename[basename].append(node)

        for basename, group_nodes in by_basename.items():
            if len(group_nodes) < 2:
                continue

            input_nodes = []
            asset_nodes = []

            for node in group_nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() in input_extensions:
                    input_nodes.append(node)
                elif ext.lower() in asset_extensions:
                    asset_nodes.append(node)

            for input_node in input_nodes:
                for asset_node in asset_nodes:
                    if self._nodes_have_same_props(input_node, asset_node):
                        relations.append(
                            Relation(
                                id=self._next_relation_id(),
                                label="derived_from",
                                node1_id=input_node.id,
                                node2_id=asset_node.id,
                            )
                        )

        return relations

    def _build_includes_relations(
        self, nodes: list[Node], node_by_path: dict[str, Node]
    ) -> list[Relation]:
        """inpファイルの*includeディレクティブを解析してincludes関係を構築"""
        relations: list[Relation] = []

        include_pattern = re.compile(r"^\*include\s*,\s*input\s*=\s*(.+)$", re.IGNORECASE)
        input_extensions = self.config.file_relations.input_extensions

        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() not in input_extensions:
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("**"):
                            continue

                        match = include_pattern.match(line)
                        if match:
                            include_path = match.group(1).strip()
                            include_filename = Path(include_path).name

                            target_node = None
                            for path, n in node_by_path.items():
                                if path.endswith(include_path) or Path(path).name == include_filename:
                                    target_node = n
                                    break

                            if target_node:
                                relations.append(
                                    Relation(
                                        id=self._next_relation_id(),
                                        label="includes",
                                        node1_id=node.id,
                                        node2_id=target_node.id,
                                    )
                                )
            except (OSError, IOError):
                continue

        return relations

    def _build_output_relations(self, nodes: list[Node]) -> list[Relation]:
        """同一ファイルタイプのprops差分関連付け（has_output）

        入力ファイルのbasenameを接頭辞として持つ出力ファイルを検出し、
        has_output関係でリンクする。

        例: go_idx1_w5_t20.inp → go_idx1_w5_t20_RF.csv (has_output)

        出力ファイルの追加タグ（RF等）はそのノードのtagsプロパティとして保持される。
        """
        relations: list[Relation] = []

        input_extensions = self.config.file_relations.input_extensions
        result_extensions = self.config.file_relations.result_extensions

        input_nodes: list[Node] = []
        output_candidates: list[Node] = []

        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            ext_lower = ext.lower()
            if ext_lower in input_extensions:
                input_nodes.append(node)
            elif ext_lower in OUTPUT_EXTENSIONS or ext_lower in result_extensions:
                output_candidates.append(node)

        for inp_node in input_nodes:
            inp_basename = inp_node.name
            inp_index = inp_node.properties.get("index", "")

            for out_node in output_candidates:
                # 完全一致はresult_ofで処理済み
                if out_node.name == inp_basename:
                    continue

                # basename接頭辞マッチ
                if not out_node.name.startswith(inp_basename + "_"):
                    continue

                # 同じindexか確認
                out_index = out_node.properties.get("index", "")
                if inp_index and out_index and inp_index != out_index:
                    continue

                relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="has_output",
                        node1_id=inp_node.id,
                        node2_id=out_node.id,
                    )
                )

        return relations

    def _build_directory_relations(
        self,
        nodes: list[Node],
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
    ) -> tuple[list[Node], list[Relation]]:
        """フォルダベースの関連付け（contains）

        2種類のディレクトリノードを生成する:
        1. 命名規則に合致するディレクトリ（go_idx1_v1/等）→ type="{fileType}_directory"
        2. ファイルノードを含む全ディレクトリ（reports/等）→ type="directory"

        いずれもcontains関係でディレクトリ内のファイルとリンクする。
        命名規則合致ディレクトリは同名入力ファイルとhas_output関係も作成する。
        """
        dir_nodes: list[Node] = []
        relations: list[Relation] = []

        input_extensions = self.config.file_relations.input_extensions

        # 既にノード化済みのディレクトリパスを追跡
        handled_dir_paths: set[str] = set()

        # --- (1) 命名規則に合致するディレクトリ ---
        named_dirs = self.scan_directories(exclude_dirs=exclude_dirs)

        for dir_path in named_dirs:
            rel_path = self._safe_relative_path(dir_path)
            dirname = dir_path.name
            parser = FileParse(dirname)

            dir_node = Node(
                id=self._next_node_id(),
                type=parser.get_file_type().value + "_directory",
                name=dirname,
                format="directory",
                properties={
                    "path": rel_path,
                    "index": parser.get_index(),
                    "version": parser.get_version(),
                    "tags": parser.get_tags(),
                    **parser.get_props(),
                },
            )
            dir_nodes.append(dir_node)
            handled_dir_paths.add(rel_path.replace("\\", "/").rstrip("/"))

            # ディレクトリ内のファイルをcontains関係でリンク
            # パス比較は正規化済み（POSIX形式、先頭./なし）で行う
            dir_prefix = rel_path.replace("\\", "/").rstrip("/") + "/"
            for node in nodes:
                node_path = node.properties.get("path", "").replace("\\", "/")
                # 先頭の ./ を除去して比較
                while node_path.startswith("./"):
                    node_path = node_path[2:]
                if node_path.startswith(dir_prefix):
                    relations.append(
                        Relation(
                            id=self._next_relation_id(),
                            label="contains",
                            node1_id=dir_node.id,
                            node2_id=node.id,
                        )
                    )

            # 同名の入力ファイルとhas_output関係を作成
            for node in nodes:
                ext = f".{node.format}" if node.format else ""
                if ext.lower() not in input_extensions:
                    continue
                if node.name == dirname:
                    relations.append(
                        Relation(
                            id=self._next_relation_id(),
                            label="has_output",
                            node1_id=node.id,
                            node2_id=dir_node.id,
                        )
                    )

        # --- (2) ファイルノードを含む全ディレクトリ ---
        # ファイルノードの親ディレクトリを収集
        parent_dirs: dict[str, list[Node]] = defaultdict(list)
        for node in nodes:
            node_path = node.properties.get("path", "").replace("\\", "/")
            while node_path.startswith("./"):
                node_path = node_path[2:]
            if "/" in node_path:
                parent_dir = node_path.rsplit("/", 1)[0]
                parent_dirs[parent_dir].append(node)

        for dir_rel_path, child_nodes in sorted(parent_dirs.items()):
            # 既に命名規則ディレクトリとして処理済みならスキップ
            if dir_rel_path in handled_dir_paths:
                continue

            dirname = dir_rel_path.rsplit("/", 1)[-1] if "/" in dir_rel_path else dir_rel_path

            dir_node = Node(
                id=self._next_node_id(),
                type="directory",
                name=dirname,
                format="directory",
                properties={
                    "path": dir_rel_path,
                },
            )
            dir_nodes.append(dir_node)
            handled_dir_paths.add(dir_rel_path)

            # contains関係を作成
            for child_node in child_nodes:
                relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="contains",
                        node1_id=dir_node.id,
                        node2_id=child_node.id,
                    )
                )

        return dir_nodes, relations

    @staticmethod
    def _is_material_source_node(node: Node) -> bool:
        """abaqus materialを読み取る対象ノードかどうかを判定

        materialはmaterial系.inpまたはgo系.inpからのみ読み取る。
        .datファイルなどからは読み取らない。

        判定基準:
        - 拡張子が.inpであること
        - ファイル名がgo_*、material_*で始まる、またはgo、materialそのものであること
        """
        ext = f".{node.format}" if node.format else ""
        if ext.lower() != ".inp":
            return False
        name_lower = node.name.lower()
        if name_lower.startswith("go_") or name_lower == "go":
            return True
        if name_lower.startswith("material_") or name_lower == "material":
            return True
        return False

    def _build_material_nodes(
        self, nodes: list[Node]
    ) -> tuple[list[Node], list[Relation]]:
        """material.inpの高度な解析 - Node(abaqus_material)を生成

        material系.inpまたはgo系.inpから*MATERIALブロックを抽出し、
        各物性定義をNode(type="abaqus_material")として生成。
        入力ファイルとの間にdefined_in関係を作成する。

        注意: .datファイル等からはmaterialを読み取らない。
        """
        mat_nodes: list[Node] = []
        relations: list[Relation] = []

        for node in nodes:
            if not self._is_material_source_node(node):
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            materials = parse_material_blocks(file_path)

            for mat in materials:
                if not mat["name"]:
                    continue

                properties: dict[str, Any] = {
                    "source_file": node.properties.get("path", ""),
                    "keywords": mat["keywords"],
                }

                for keyword, data in mat["properties"].items():
                    properties[keyword] = data

                mat_node = Node(
                    id=self._next_node_id(),
                    type="abaqus_material",
                    name=mat["name"],
                    format="material",
                    properties=properties,
                )
                mat_nodes.append(mat_node)

                relations.append(
                    Relation(
                        id=self._next_relation_id(),
                        label="defined_in",
                        node1_id=mat_node.id,
                        node2_id=node.id,
                    )
                )

        return mat_nodes, relations

    def _enrich_mesh_stats(self, nodes: list[Node]) -> None:
        """pymeshを使ってメッシュ統計情報をノードのプロパティに付与

        .inpファイルの要素数、節点数、要素タイプ別集計、品質統計等を
        対応するノードのpropertiesに追加する。
        """
        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            stats = extract_mesh_stats(file_path, verbose=False)
            if stats is None:
                continue

            if stats.get("node_count"):
                node.properties["mesh_node_count"] = stats["node_count"]
            if stats.get("element_count"):
                node.properties["mesh_element_count"] = stats["element_count"]
            if stats.get("element_types"):
                node.properties["mesh_element_types"] = stats["element_types"]
            if stats.get("elset_summary"):
                node.properties["mesh_elset_summary"] = stats["elset_summary"]
            if stats.get("quality"):
                node.properties["mesh_quality"] = stats["quality"]

    def _build_material_assignment_relations(
        self,
        all_nodes: list[Node],
        mat_nodes: list[Node],
    ) -> list[Relation]:
        """材料割り当て関係の構築

        .inpファイルの*SOLID SECTION/*SHELL SECTIONで定義される
        材料→Elset割り当てを解析し、abaqus_materialノードと
        入力ファイルノードの間にassigned_to関係を作成する。

        Args:
            all_nodes: 全ノード
            mat_nodes: マテリアルノード

        Returns:
            材料割り当てリレーションのリスト
        """
        relations: list[Relation] = []

        # マテリアル名でマテリアルノードを索引
        mat_by_name: dict[str, list[Node]] = defaultdict(list)
        for mnode in mat_nodes:
            mat_by_name[mnode.name.lower()].append(mnode)

        # 入力ファイルノードから材料割り当てを抽出
        for node in all_nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".inp":
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            mapping = extract_material_elset_mapping(file_path)
            if not mapping:
                continue

            # 材料名→materialノードへのassigned_to関係
            for mat_name, elset_names in mapping.items():
                matched_mats = mat_by_name.get(mat_name.lower(), [])
                for mnode in matched_mats:
                    # materialノードにelset情報を付与
                    if elset_names:
                        mnode.properties["assigned_elsets"] = elset_names
                    relations.append(
                        Relation(
                            id=self._next_relation_id(),
                            label="assigned_to",
                            node1_id=mnode.id,
                            node2_id=node.id,
                        )
                    )

        return relations

    def _enrich_sta_status(self, nodes: list[Node]) -> None:
        """解析結果ファイル（.sta）のステータスをノードのプロパティに付与

        .staファイルの内容を解析し、対応する.staノードおよび
        同名の入力ファイル(.inp)ノードのpropertiesに
        analysis_status, errors, warningsを追加する。
        """
        # 入力ファイルノードのインデックスを構築
        input_extensions = self.config.file_relations.input_extensions
        input_by_name: dict[str, Node] = {}
        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_by_name[node.name] = node

        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".sta":
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            sta_info = parse_sta_file(file_path)
            node.properties["analysis_status"] = sta_info["analysis_status"]
            if sta_info["errors"]:
                node.properties["errors"] = sta_info["errors"]
            if sta_info["warnings"]:
                node.properties["warnings"] = sta_info["warnings"]

            # 同名の入力ファイルにも集約
            inp_node = input_by_name.get(node.name)
            if inp_node:
                inp_node.properties["analysis_status"] = sta_info["analysis_status"]
                if sta_info["errors"]:
                    inp_node.properties["sta_errors"] = sta_info["errors"]
                if sta_info["warnings"]:
                    inp_node.properties["sta_warnings"] = sta_info["warnings"]

    def _enrich_msg_status(self, nodes: list[Node]) -> None:
        """メッセージファイル（.msg）のエラー・警告をノードのプロパティに付与

        .msgファイルの内容を解析し、対応する.msgノードおよび
        同名の入力ファイル(.inp)ノードのpropertiesに
        msg_errors, msg_warningsを追加する。
        """
        # 入力ファイルノードのインデックスを構築
        input_extensions = self.config.file_relations.input_extensions
        input_by_name: dict[str, Node] = {}
        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() in input_extensions:
                input_by_name[node.name] = node

        for node in nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".msg":
                continue

            file_path = self.project_root / node.properties.get("path", "")
            if not file_path.exists():
                continue

            msg_info = parse_msg_file(file_path)
            if msg_info["errors"]:
                node.properties["msg_errors"] = msg_info["errors"]
            if msg_info["warnings"]:
                node.properties["msg_warnings"] = msg_info["warnings"]

            # 同名の入力ファイルにも集約
            inp_node = input_by_name.get(node.name)
            if inp_node:
                if msg_info["errors"]:
                    inp_node.properties["msg_errors"] = msg_info["errors"]
                if msg_info["warnings"]:
                    inp_node.properties["msg_warnings"] = msg_info["warnings"]

    def _nodes_have_same_props(self, node1: Node, node2: Node) -> bool:
        """2つのノードが同じ主要プロパティを持つかチェック"""
        compare_keys = {"index", "w", "t", "番号"}

        for key in compare_keys:
            val1 = node1.properties.get(key, "")
            val2 = node2.properties.get(key, "")
            if val1 and val2 and val1 != val2:
                return False

        return True

    def load(self, filename: Optional[str] = None) -> GraphModel:
        """グラフデータを読み込み"""
        return self.storage.load(self.project_root, filename)

    def save(self, graph: GraphModel, filename: Optional[str] = None) -> Path:
        """グラフデータを保存"""
        return self.storage.save(self.project_root, graph, filename)

    def parse_and_save(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
        filename: Optional[str] = None,
    ) -> tuple[GraphModel, Path]:
        """プロジェクトをパースして保存

        Returns:
            (生成されたGraphModel, 保存先パス)
        """
        graph = self.parse_project(extensions=extensions, exclude_dirs=exclude_dirs)
        path = self.save(graph, filename)
        return graph, path

    def get_nodes_by_type(self, graph: GraphModel, node_type: str) -> list[Node]:
        """タイプでノードをフィルタリング"""
        return [n for n in graph.nodes if n.type == node_type]

    def get_node_by_id(self, graph: GraphModel, node_id: int) -> Optional[Node]:
        """IDでノードを取得"""
        for node in graph.nodes:
            if node.id == node_id:
                return node
        return None

    def get_relations_for_node(self, graph: GraphModel, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return [
            r
            for r in graph.relations
            if r.node1_id == node_id or r.node2_id == node_id
        ]

    def summary(self, graph: GraphModel) -> dict[str, Any]:
        """グラフのサマリーを生成"""
        type_counts: dict[str, int] = {}
        for node in graph.nodes:
            type_counts[node.type] = type_counts.get(node.type, 0) + 1

        relation_counts: dict[str, int] = {}
        for rel in graph.relations:
            relation_counts[rel.label] = relation_counts.get(rel.label, 0) + 1

        return {
            "total_nodes": len(graph.nodes),
            "total_relations": len(graph.relations),
            "nodes_by_type": type_counts,
            "relations_by_label": relation_counts,
        }
