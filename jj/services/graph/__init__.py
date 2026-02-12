"""GraphService: プロジェクトフォルダのパースとグラフデータ管理

このモジュールはjjのコアとなるグラフ機能を提供します。
- プロジェクトフォルダのスキャンとファイル解析
- GraphModelへの変換
- AbstractFileParserパイプラインによるグラフエンリッチメント
- グラフデータの保存・読み込み

Phase R リファクタリングにより、parse/enrich/connectロジックは
AbstractFileParserサブクラス群に分散されました。
旧メソッド群はPhase R4で削除済みです。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional

from config import GraphConfig
from jj_types import GraphModel, Node, Relation

from services.graph.storage import GraphStorage
from services.parse.base import parse as run_parser_pipeline
from services.parse.file_parse import (
    DEFAULT_EXTENSIONS,
    NO_NODE_EXTENSIONS,
    FileParse,
    FileType,
)
from services.parse.file_parse import _parse_prop_token as _parse_prop_token_static

# パーサーサブクラスのimport（自動登録用）
import services.parse.parsers  # noqa: F401
import services.parse.connectors.abaqus.inp_parser  # noqa: F401
import services.parse.connectors.abaqus.result_parser  # noqa: F401
import services.parse.connectors.abaqus.mesh_parser  # noqa: F401
import services.parse.connectors.abaqus.diff_parser  # noqa: F401
import services.parse.connectors.obsidian.daily_parser  # noqa: F401


class GraphService:
    """プロジェクトのグラフデータを管理するサービス

    Phase Rリファクタリングにより、グラフエンリッチメント（リレーション構築、
    プロパティ付与等）はAbstractFileParserパイプラインに委譲されました。
    GraphServiceの責務は以下に限定されます:
    - ファイルスキャンとNode生成
    - パーサーパイプラインの実行
    - グラフデータの保存・読み込み
    """

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
        # token_key_map適用トークンを記録（verbose_name生成で使用）
        token_key_mapped_keys: set[str] = set()
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
                token_key_mapped_keys.add(mapped_key)

        # vocabを使ってpropsのキーと値を変換
        translated_props: dict[str, Any] = {}
        for key, value in props.items():
            translated_key = self.config.vocab.get(key, key)
            translated_value = (
                self.config.vocab.get(str(value), str(value))
                if isinstance(value, str)
                else value
            )
            translated_props[translated_key] = translated_value

        # 日付を取得
        date_formatted = parser.get_date_formatted()

        # oldフォルダに入っていなければactive=True
        parent_dir = (
            file_path.parent.name
            if isinstance(file_path, Path)
            else Path(str(file_path)).parent.name
        )
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

        # vocabでidx/vのマッピングが定義されている場合、
        # 英語キー(index/version)を変換後のキーに統一
        idx_translated = self.config.vocab.get("idx")
        if idx_translated:
            index_val = properties.pop("index", "")
            if index_val and idx_translated not in properties:
                properties[idx_translated] = index_val
        v_translated = self.config.vocab.get("v")
        if v_translated:
            version_val = properties.pop("version", "")
            if version_val and v_translated not in properties:
                properties[v_translated] = version_val

        # 日付がある場合のみ追加
        if date_formatted:
            properties["date"] = date_formatted

        # Abaqusインプット向け: *PARAMETER/**propsブロックからプロパティを読み取る
        inp_param_props = self._read_inp_parameter_props(file_path)
        if inp_param_props:
            properties.update(inp_param_props)

        # verbose_name: config vocabで変換した後の表示名を生成
        # token_key_map適用キーはverbose_nameで値のみ採用（キー名を含めない）
        raw_name = parser.get_basename()
        verbose_name = self._build_verbose_name(
            raw_name,
            resolved_type,
            translated_props,
            tags + config_tags,
            token_key_mapped_keys=token_key_mapped_keys,
        )
        if verbose_name and verbose_name != raw_name:
            properties["verbose_name"] = verbose_name

        # verbose_nameを"_"でsplitしてタグに追加
        if verbose_name:
            verbose_tags = [t for t in verbose_name.split("_") if t]
            existing_tags = properties.get("tags", [])
            for vt in verbose_tags:
                if vt not in existing_tags:
                    existing_tags.append(vt)
            properties["tags"] = existing_tags

        return Node(
            id=self._next_node_id(),
            type=resolved_type,
            name=raw_name,
            format=parser._split_extension()[1].lstrip("."),
            properties=properties,
        )

    def _build_verbose_name(
        self,
        raw_name: str,
        resolved_type: str,
        translated_props: dict[str, Any],
        tags: list[str],
        token_key_mapped_keys: set[str] | None = None,
    ) -> str:
        """config vocabで変換した後の表示名を生成

        ファイル名を構成要素に分解し、vocabで変換された値を用いて再構成する。
        例: go_idx1_w5_t20 → {type翻訳}_{index翻訳}1_{w翻訳}5_{t翻訳}20

        token_key_mapで割り当てたキーは、verbose_nameに値のみ含める。
        例: 形状: ほげほげ24 → "ほげほげ24"（"形状ほげほげ24"ではなく）

        Args:
            raw_name: 生のbasename
            resolved_type: 解決済みタイプ
            translated_props: vocab変換済みプロパティ
            tags: タグリスト
            token_key_mapped_keys: token-key-mapで設定されたキーのセット

        Returns:
            変換後の表示名
        """
        vocab = self.config.vocab
        mapped_keys = token_key_mapped_keys or set()
        # token_key_mapped_keysはvocab変換前のキー名。変換後のキー名も収集
        translated_mapped_keys: set[str] = set()
        for mk in mapped_keys:
            translated_mapped_keys.add(vocab.get(mk, mk))

        # タイプ名の変換
        type_name = vocab.get(resolved_type, resolved_type)

        parts = [type_name]
        # プロパティを追加
        skip_keys = {"path", "tags", "active"}
        for key, value in translated_props.items():
            if key in skip_keys:
                continue
            if isinstance(value, (list, dict)):
                continue
            # token_key_mapで設定されたキーは値のみ（キー名を含めない）
            if key in translated_mapped_keys or key in mapped_keys:
                parts.append(str(value))
            else:
                parts.append(f"{key}{value}")

        # タグを追加
        for tag in tags:
            translated_tag = vocab.get(tag, tag)
            parts.append(translated_tag)

        return "_".join(parts)

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
        full_mode: bool = False,
        debug: bool = False,
    ) -> GraphModel:
        """プロジェクトをパースしてGraphModelを生成

        Phase R リファクタリングにより、ファイルスキャンとノード生成のみを
        GraphServiceが担当し、グラフエンリッチメント（リレーション構築、
        プロパティ付与等）はAbstractFileParserパイプラインに委譲する。

        タイムスタンプ差分: 前回パース時のファイルタイムスタンプを読み込み、
        変更されたファイルのみを重い処理（read_inp等）の対象とする。
        パース完了後にタイムスタンプを保存する。

        Args:
            extensions: 対象拡張子（Noneの場合はDEFAULT_EXTENSIONS + config file-relationsを使用）
            exclude_dirs: 除外ディレクトリ
            full_mode: Trueの場合、requires_full=Trueのパーサーも実行する
            debug: デバッグモード（True: パーサーエラーをraise）

        Returns:
            生成されたGraphModel
        """
        import logging

        from services.graph.project_graph import ProjectGraph

        logger = logging.getLogger(__name__)

        merged_extensions = self._build_scan_extensions(extensions)
        files = self.scan_files(extensions=merged_extensions, exclude_dirs=exclude_dirs)

        # 前回パース時のタイムスタンプを読み込み
        prev_timestamps = self.storage.load_timestamps(self.project_root)

        nodes: list[Node] = []
        current_timestamps: dict[str, float] = {}
        no_node_exts = tuple(e.lower() for e in NO_NODE_EXTENSIONS)

        # ノード生成（GraphServiceの責務: ファイルスキャンとNode変換）
        # NO_NODE_EXTENSIONS に該当するファイルはスキャンされるがNode化しない
        for file_path in files:
            lower_name = file_path.name.lower()
            if any(lower_name.endswith(ext) for ext in no_node_exts):
                continue
            node = self.file_to_node(file_path)
            nodes.append(node)

            # 各ファイルの現在のmtimeを記録
            try:
                abs_path = str(file_path.resolve())
                current_timestamps[abs_path] = file_path.stat().st_mtime
            except OSError:
                pass

        # ProjectGraphを構築してパーサーパイプラインに委譲
        project_graph = ProjectGraph.from_graph_service(
            nodes=nodes,
            relations=[],
            project_root=self.project_root,
            config=self.config,
            node_id_counter=self._node_id_counter,
            relation_id_counter=self._relation_id_counter,
        )

        # タイムスタンプ情報をProjectGraphに設定
        project_graph._prev_timestamps = prev_timestamps
        project_graph._file_timestamps = current_timestamps

        modified_count = sum(
            1 for p in current_timestamps
            if p not in prev_timestamps or prev_timestamps.get(p) != current_timestamps[p]
        )
        total_count = len(current_timestamps)
        if prev_timestamps:
            logger.info(
                f"タイムスタンプ差分: {modified_count}/{total_count}ファイルが変更済み"
            )

        # 全登録パーサーをpriority順に適用
        project_graph = run_parser_pipeline(project_graph, full_mode=full_mode, debug=debug)

        # パース完了後にタイムスタンプを保存
        self.storage.save_timestamps(self.project_root, current_timestamps)

        # IDカウンタを同期
        self._node_id_counter = project_graph._node_id_counter
        self._relation_id_counter = project_graph._relation_id_counter

        return project_graph.to_graph_model()

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
        full_mode: bool = False,
        debug: bool = False,
    ) -> tuple[GraphModel, Path]:
        """プロジェクトをパースして保存

        Returns:
            (生成されたGraphModel, 保存先パス)
        """
        graph = self.parse_project(extensions=extensions, exclude_dirs=exclude_dirs, full_mode=full_mode, debug=debug)
        path = self.save(graph, filename)

        # ABQDataキャッシュの自動クリーンアップ（古いキャッシュの削除）
        try:
            self.storage.cleanup_abq_cache(
                self.project_root,
                max_age_days=self.config.cache_max_age_days,
                max_count=self.config.cache_max_count,
            )
        except Exception:
            pass  # クリーンアップ失敗はパース結果に影響しない

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
            r for r in graph.relations if r.node1_id == node_id or r.node2_id == node_id
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
