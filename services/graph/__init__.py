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

import contextlib
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# 汎用パーサーサブクラスのimport（コア機能、自動登録用）
import services.parse.parsers  # noqa: F401
from config import GraphConfig
from jj_types import GraphModel, Node, Relation
from services.graph.storage import GraphStorage
from services.parse.base import parse as run_parser_pipeline
from services.parse.file_parse import (
    DEFAULT_EXTENSIONS,
    NO_NODE_EXTENSIONS,
    FileParse,
)
from services.parse.file_parse import _parse_prop_token as _parse_prop_token_static
from services.sdk.cache import CacheProvider

# プラグインの動的発見を実行（Abaqus/Obsidian等のコネクタを登録）
from services.sdk.plugin_registry import load_all_plugins as _load_all_plugins

_load_all_plugins()


class GraphService:
    """プロジェクトのグラフデータを管理するサービス

    Phase Rリファクタリングにより、グラフエンリッチメント（リレーション構築、
    プロパティ付与等）はAbstractFileParserパイプラインに委譲されました。
    GraphServiceの責務は以下に限定されます:
    - ファイルスキャンとNode生成
    - パーサーパイプラインの実行
    - グラフデータの保存・読み込み

    CacheProvider DI:
        storageパラメータはCacheProviderプロトコルを受け入れます。
        デフォルトはGraphStorage()（ファイルベースのYAML/JSON永続化）。
        テストやプラグインでは独自のCacheProvider実装を注入できます。
    """

    def __init__(
        self,
        project_root: Path | str | None = None,
        storage: CacheProvider | GraphStorage | None = None,
        config: GraphConfig | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.storage: CacheProvider = storage or GraphStorage()
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
        # TODO:　configに逃がす
        default_exclude = {".git", ".j2", "__pycache__", "node_modules", ".venv"}
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
        """ファイルパスからNodeを生成
        TODO: これはparseへ移動。またversion, index, activeがハードコードでややこしい。index, versionは特殊かつ必須なのでconfigでversion: vなどを強制。
        """
        parser = FileParse(file_path)
        file_type = parser.get_file_type()
        props = parser.get_props()
        extra_tokens = parser.get_tags()  # 非プロパティトークン（verbose_name構築用）

        # 相対パスを安全に生成（Windows対応）
        rel_path = self._safe_relative_path(file_path)
        filename = file_path.name

        # path-type-mapからタイプを取得（設定が優先）
        config_type = self.config.path_type_map.get_type(rel_path, filename)
        resolved_type = config_type if config_type else file_type.value

        # path-property-mapからプロパティを取得
        config_props = self.config.path_property_map.get_properties(rel_path)

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
                # extra_tokensからも除去
                if token in extra_tokens:
                    extra_tokens.remove(token)
                # token-key-mapのキーで全トークンを値として設定
                props[mapped_key] = token
                token_key_mapped_keys.add(mapped_key)

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

        # verbose_name: config vocabで変換した後の表示名を生成
        # token_key_map適用キーはverbose_nameで値のみ採用（キー名を含めない）
        raw_name = parser.get_basename()
        verbose_name = self._build_verbose_name(
            raw_name,
            resolved_type,
            translated_props,
            extra_tokens,
            token_key_mapped_keys=token_key_mapped_keys,
        )
        if verbose_name and verbose_name != raw_name:
            properties["verbose_name"] = verbose_name

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
        extra_tokens: list[str],
        token_key_mapped_keys: set[str] | None = None,
    ) -> str:
        """config vocabで変換した後の表示名を生成

        verbose-name-formatが設定されている場合はフォーマットテンプレートを使用。
        例: "条件{条件}(高さ{高さ},荷重{荷重})" → "条件1(高さ5,荷重20)"
        テンプレート内の{キー名}はtranslated_propsの値で置換される。
        存在しないキーは空文字に置換される。

        未設定の場合は従来方式（アンダースコア結合）:
        例: go_idx1_w5_t20 → {type翻訳}_{index翻訳}1_{w翻訳}5_{t翻訳}20

        token_key_mapで割り当てたキーは、verbose_nameに値のみ含める。
        例: 形状: ほげほげ24 → "ほげほげ24"（"形状ほげほげ24"ではなく）

        Args:
            raw_name: 生のbasename
            resolved_type: 解決済みタイプ
            translated_props: vocab変換済みプロパティ
            extra_tokens: ファイル名から抽出した非プロパティトークン
            token_key_mapped_keys: token-key-mapで設定されたキーのセット

        Returns:
            変換後の表示名
        """
        # フォーマットテンプレートが設定されている場合
        fmt = getattr(self.config, "verbose_name_format", None)
        if fmt:
            return self._apply_verbose_name_format(fmt, resolved_type, translated_props)

        # 従来方式: アンダースコア結合
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

        # 非プロパティトークンを追加
        for token in extra_tokens:
            translated_token = vocab.get(token, token)
            parts.append(translated_token)

        return "_".join(parts)

    def _apply_verbose_name_format(
        self,
        fmt: str,
        resolved_type: str,
        translated_props: dict[str, Any],
    ) -> str:
        """フォーマットテンプレートでverbose_nameを生成

        テンプレート内の{キー名}をプロパティ値で置換する。
        vocabの変換前・変換後どちらのキー名でも参照可能。
        存在しないキーは空文字に置換される。

        Args:
            fmt: フォーマットテンプレート（例: "条件{条件}(高さ{高さ})"）
            resolved_type: 解決済みタイプ
            translated_props: vocab変換済みプロパティ

        Returns:
            フォーマット適用後の表示名
        """
        vocab = self.config.vocab

        # プロパティ値の辞書を構築（vocab変換前後のキーで参照可能）
        values: dict[str, str] = {}
        # タイプ名をtype/変換後キーの両方で参照可能に
        type_name = vocab.get(resolved_type, resolved_type)
        values["type"] = type_name
        type_translated = vocab.get("type")
        if type_translated:
            values[type_translated] = type_name

        for key, value in translated_props.items():
            if isinstance(value, (list, dict)):
                continue
            values[key] = str(value)

        # vocab変換前のキー名でも参照可能にする
        # （例: フォーマットに{idx}と書いてあるが、propsでは"条件"キーになっている場合）
        for orig_key, translated_key in vocab.items():
            if translated_key in values and orig_key not in values:
                values[orig_key] = values[translated_key]

        # format_mapで置換（KeyError回避のためdefaultdict使用）
        from collections import defaultdict

        safe_values = defaultdict(str, values)
        return fmt.format_map(safe_values)

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
            1 for p in current_timestamps if p not in prev_timestamps or prev_timestamps.get(p) != current_timestamps[p]
        )
        total_count = len(current_timestamps)
        if prev_timestamps:
            logger.info(f"タイムスタンプ差分: {modified_count}/{total_count}ファイルが変更済み")

        # 全登録パーサーをpriority順に適用
        project_graph = run_parser_pipeline(project_graph, full_mode=full_mode, debug=debug)

        # パース完了後にタイムスタンプを保存
        self.storage.save_timestamps(self.project_root, current_timestamps)

        # IDカウンタを同期
        self._node_id_counter = project_graph._node_id_counter
        self._relation_id_counter = project_graph._relation_id_counter

        return project_graph.to_graph_model()

    def load(self, filename: str | None = None) -> GraphModel:
        """グラフデータを読み込み"""
        return self.storage.load(self.project_root, filename)

    def save(self, graph: GraphModel, filename: str | None = None) -> Path:
        """グラフデータを保存"""
        return self.storage.save(self.project_root, graph, filename)

    def parse_and_save(
        self,
        extensions: Iterable[str] | None = None,
        exclude_dirs: Iterable[str] | None = None,
        filename: str | None = None,
        full_mode: bool = False,
        debug: bool = False,
    ) -> tuple[GraphModel, Path]:
        """プロジェクトをパースして保存

        Returns:
            (生成されたGraphModel, 保存先パス)
        """
        graph = self.parse_project(extensions=extensions, exclude_dirs=exclude_dirs, full_mode=full_mode, debug=debug)
        path = self.save(graph, filename)

        # プラグインキャッシュの自動クリーンアップ（古いキャッシュの削除）
        with contextlib.suppress(Exception):
            self.storage.cleanup_plugin_cache(
                self.project_root,
                max_age_days=self.config.cache_max_age_days,
                max_count=self.config.cache_max_count,
            )

        return graph, path

    def get_nodes_by_type(self, graph: GraphModel, node_type: str) -> list[Node]:
        """タイプでノードをフィルタリング"""
        return [n for n in graph.nodes if n.type == node_type]

    def get_node_by_id(self, graph: GraphModel, node_id: int) -> Node | None:
        """IDでノードを取得"""
        for node in graph.nodes:
            if node.id == node_id:
                return node
        return None

    def get_relations_for_node(self, graph: GraphModel, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return [r for r in graph.relations if r.node1_id == node_id or r.node2_id == node_id]

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
