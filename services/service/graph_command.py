"""GraphCommandService: グラフコマンドのビジネスロジック

CLI graph.pyのinit/parse/show/export/info/diff/credentialコマンドで
使用されるビジネスロジックを集約。CLI層はargparse解析と出力整形のみに
責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.export import AbstractExporter

from config import init_graph_config
from jj_types import GraphModel, Node, Relation
from services.graph import GraphService
from services.lib.credentials import (
    load_credentials,
    mask_value,
    save_credentials,
)
from services.service.info import InfoService

# =========
# 戻り値データクラス
# =========


@dataclass
class ParseResult:
    """parseコマンドの結果"""

    graph: GraphModel
    summary: dict[str, Any]
    save_path: Path
    full_mode: bool


@dataclass
class ShowResult:
    """showコマンドの結果"""

    nodes: list[Node]
    relations: list[Relation]
    summary: dict[str, Any] | None
    empty: bool


@dataclass
class InfoResult:
    """infoコマンドの結果"""

    nodes: list[Node]
    graph: GraphModel
    empty: bool  # グラフデータが空
    no_criteria: bool  # 検索条件が未指定


@dataclass
class DiffResult:
    """diffコマンドの結果"""

    file1: Path | None = None
    file2: Path | None = None
    is_inp: bool = False
    has_diffs: bool = False
    # INPファイル用
    summary_table: str | None = None
    detail_markdown: str | None = None
    # 汎用ファイル用
    unified_diff_lines: list[str] = field(default_factory=list)
    # エラー
    error: str | None = None


@dataclass
class CredentialShowResult:
    """credential showの結果"""

    found: bool
    service: str
    credentials: dict[str, str] | None = None


# =========
# サービス本体
# =========


class GraphCommandService:
    """グラフコマンドのビジネスロジック

    CLI graph.pyの各コマンド(init/parse/show/export/info/diff/credential)で
    使用されるビジネスロジックを集約する。
    CLI層はargparse解析と出力整形のみに責務を限定する。
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._graph_service = GraphService(project_root=project_root)
        self._info_service = InfoService(project_root=project_root)

    @property
    def graph_service(self) -> GraphService:
        """GraphServiceへのアクセス（configオーバーライド等に使用）"""
        return self._graph_service

    # =========
    # init
    # =========

    def init_config(self, overwrite: bool = False) -> Path:
        """設定ファイルを初期化

        Args:
            overwrite: 既存の設定ファイルを上書きするか

        Returns:
            生成された設定ファイルのパス
        """
        return init_graph_config(base_dir=self.project_root, overwrite=overwrite)

    # =========
    # parse
    # =========

    def parse(
        self,
        output_file: str | None = None,
        format: str = "yaml",
        full_mode: bool = False,
        max_depth: int | None = None,
        debug: bool = False,
        trace: bool = False,
    ) -> ParseResult:
        """プロジェクトをパースしてサマリーを返却

        Args:
            output_file: 出力ファイル名（Noneの場合はformat依存）
            format: 出力フォーマット（yaml/json）
            full_mode: 全パーサー実行（True）/軽量モード（False）
            max_depth: ディレクトリ階層の最大深さ
            debug: デバッグモード（True: パーサーエラーをraise）

        Returns:
            ParseResult
        """
        from dataclasses import replace as dc_replace

        if max_depth is not None:
            self._graph_service.config = dc_replace(self._graph_service.config, directory_max_depth=max_depth)

        if output_file is None:
            output_file = f"graph.{format}"

        graph, save_path = self._graph_service.parse_and_save(
            filename=output_file, full_mode=full_mode, debug=debug, trace=trace
        )
        summary = self._graph_service.summary(graph)

        return ParseResult(
            graph=graph,
            summary=summary,
            save_path=save_path,
            full_mode=full_mode,
        )

    # =========
    # show
    # =========

    def show(
        self,
        filename: str | None = None,
        type_filter: str | None = None,
        summary_only: bool = False,
    ) -> ShowResult:
        """グラフ表示用データを返却

        Args:
            filename: 読み込むファイル名
            type_filter: ノードタイプでフィルタリング
            summary_only: サマリーのみ表示

        Returns:
            ShowResult
        """
        graph = self._graph_service.load(filename=filename, resolve_externalized=True)

        if not graph.nodes and not graph.relations:
            return ShowResult(nodes=[], relations=[], summary=None, empty=True)

        summary = None
        if summary_only:
            summary = self._graph_service.summary(graph)

        nodes = list(graph.nodes)
        if type_filter:
            nodes = self._graph_service.get_nodes_by_type(graph, type_filter)

        return ShowResult(
            nodes=nodes,
            relations=list(graph.relations),
            summary=summary,
            empty=False,
        )

    # =========
    # export: load or parse
    # =========

    def load_or_parse(
        self,
        filename: str | None = None,
        do_parse: bool = False,
        full_mode: bool = False,
    ) -> tuple[GraphModel, ParseResult | None]:
        """グラフデータをロード。do_parse=Trueの場合はparse後にロード

        Returns:
            (グラフデータ, ParseResult(parse実行時) or None)
        """
        if do_parse:
            result = self.parse(full_mode=full_mode)
            return result.graph, result
        else:
            graph = self._graph_service.load(filename=filename, resolve_externalized=True)
            return graph, None

    # =========
    # export: 統一エクスポート
    # =========

    def export_unified(
        self,
        graph: GraphModel,
        target: str,
        **cli_kwargs: Any,
    ) -> tuple[dict[str, Any], AbstractExporter]:
        """統一エクスポートパイプライン

        全エクスポート形式をレジストリ経由で統一的に呼び出す。
        CLI引数から構築されたkwargsをエクスポーターに渡し、
        結果とエクスポーターインスタンスを返す。

        CSV/JSONの共通選択オプション（-id, -v, -type, -all等）は
        事前にノード絞り込みを行い、pre_selectedとして注入する。

        dashboard-jsonではconfig設定（vocab, units）を自動注入する。

        Args:
            graph: エクスポート対象のグラフ
            target: エクスポート形式
            **cli_kwargs: CLIから構築されたkwargsデータ

        Returns:
            (エクスポート結果辞書, エクスポーターインスタンス)
        """
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format(target)
        if exporter_cls is None:
            raise ValueError(f"未対応のエクスポート形式: {target}")

        # project_rootをデフォルト注入
        cli_kwargs.setdefault("project_root", self.project_root)

        # CSV/JSON: 共通選択オプションによる事前ノード絞り込み
        if target in ("csv", "json"):
            cli_kwargs = self._prepare_data_export_kwargs(graph, cli_kwargs)

        # dashboard-json: config設定を自動注入
        if target == "dashboard-json":
            config = self._graph_service.config
            cli_kwargs.setdefault("vocab", config.vocab)
            cli_kwargs.setdefault("units", config.export.units)

        exporter = exporter_cls()
        result = exporter.export(graph, **cli_kwargs)
        return result, exporter

    def _prepare_data_export_kwargs(
        self,
        graph: GraphModel,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """CSV/JSONエクスポート用のkwargsを準備（ノード事前選択を含む）"""
        index_filters = kwargs.pop("index_filters", None)
        version_filters = kwargs.pop("version_filters", None)
        all_nodes = kwargs.pop("all_nodes", False)
        active_only = kwargs.pop("active_only", False)
        type_filter = kwargs.get("type_filter")
        flatten = kwargs.pop("flatten", False)

        # 共通選択オプションが指定されている場合は事前にノード絞り込み
        if index_filters is not None or version_filters is not None or all_nodes or active_only:
            pre_selected = self._info_service.search_nodes(
                graph,
                index_filters=index_filters,
                version_filters=version_filters,
                type_filter=type_filter,
                all_nodes=all_nodes,
                active_only=active_only,
            )
            kwargs["nodes"] = pre_selected
            # search_nodesでtype_filterを適用済みなのでexport_dataには渡さない
            kwargs.pop("type_filter", None)

        # flattenフラグ: --flatten指定時はTrue、未指定はNone
        kwargs["flatten"] = True if flatten else None

        return kwargs

    def export_by_format(
        self,
        graph: GraphModel,
        target: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """AbstractExporterレジストリ経由でエクスポート

        全エクスポート形式を統一的に呼び出す。
        レジストリに登録されていない形式の場合はValueErrorを送出する。

        Args:
            graph: エクスポート対象のグラフ
            target: エクスポート形式（"csv", "json", "obsidian", "neo4j", "cypher", "dashboard-json"）
            **kwargs: エクスポーター固有のオプション

        Returns:
            エクスポーター固有の結果辞書
        """
        # コネクタモジュールをインポートしてレジストリ登録を確実にする
        import services.export.connectors  # noqa: F401
        from services.export import get_exporter_for_format

        exporter_cls = get_exporter_for_format(target)
        if exporter_cls is None:
            raise ValueError(f"未対応のエクスポート形式: {target}")

        # project_rootをデフォルトで注入
        kwargs.setdefault("project_root", self.project_root)

        exporter = exporter_cls()
        return exporter.export(graph, **kwargs)

    # =========
    # info
    # =========

    def info(
        self,
        *,
        filenames: list[str] | None = None,
        index_filters: list[str] | None = None,
        version_filters: list[str] | None = None,
        type_filter: str | None = None,
        all_nodes: bool = False,
        prop_filters: list[str] | None = None,
        active_only: bool = False,
        graph_filename: str | None = None,
    ) -> InfoResult:
        """ノード情報検索

        Args:
            filenames: ファイル名で検索（複数可）
            index_filters: インデックスで検索
            version_filters: バージョンで検索
            type_filter: ノードタイプでフィルタリング
            all_nodes: 全ノード選択
            prop_filters: プロパティフィルタ（AND条件）
            active_only: activeのみ
            graph_filename: 読み込むグラフファイル名

        Returns:
            InfoResult
        """
        graph = self._info_service.load_graph(filename=graph_filename)

        if not graph.nodes:
            return InfoResult(nodes=[], graph=graph, empty=True, no_criteria=False)

        # 何も指定がない場合
        if not filenames and index_filters is None and version_filters is None and not all_nodes:
            return InfoResult(nodes=[], graph=graph, empty=False, no_criteria=True)

        # InfoServiceでノード検索
        matched_nodes = self._info_service.search_nodes(
            graph,
            filenames=filenames or None,
            index_filters=index_filters,
            version_filters=version_filters,
            type_filter=type_filter,
            all_nodes=all_nodes,
            active_only=active_only,
        )

        # -prop フィルタ: 指定プロパティを持つノードのみに絞り込み
        if prop_filters:
            matched_nodes = [n for n in matched_nodes if all(k in n.properties for k in prop_filters)]

        return InfoResult(
            nodes=matched_nodes,
            graph=graph,
            empty=False,
            no_criteria=False,
        )

    def get_relations_for_node(self, graph: GraphModel, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return self._info_service.get_relations_for_node(graph, node_id)

    # =========
    # diff
    # =========

    def diff(
        self,
        file1_arg: str,
        file2_arg: str,
        show_detail: bool = False,
    ) -> DiffResult:
        """ファイル差分を計算

        Args:
            file1_arg: 比較元ファイル（パスまたはファイル名）
            file2_arg: 比較先ファイル（パスまたはファイル名）
            show_detail: 詳細表示

        Returns:
            DiffResult
        """
        from services.parse.connectors.abaqus import (
            diff_abq_blocks,
            format_diff_blocks_markdown,
            format_diff_summary_table,
        )
        from services.parse.connectors.abaqus import (
            read_inp as abq_read_inp,
        )

        file1 = InfoService.resolve_file_path(self.project_root, file1_arg)
        if file1 is None:
            return DiffResult(error=f"ファイルが見つかりません: {file1_arg}")

        file2 = InfoService.resolve_file_path(self.project_root, file2_arg)
        if file2 is None:
            return DiffResult(error=f"ファイルが見つかりません: {file2_arg}")

        if file1.suffix.lower() == ".inp" and file2.suffix.lower() == ".inp":
            left_abq = abq_read_inp(str(file1), verbose=False)
            right_abq = abq_read_inp(str(file2), verbose=False)
            diffs = diff_abq_blocks(left_abq, right_abq)

            summary_table = None
            detail_markdown = None
            if diffs:
                summary_table = format_diff_summary_table(diffs)
                if show_detail:
                    detail_markdown = format_diff_blocks_markdown(diffs)

            return DiffResult(
                file1=file1,
                file2=file2,
                is_inp=True,
                has_diffs=bool(diffs),
                summary_table=summary_table,
                detail_markdown=detail_markdown,
            )
        else:
            import difflib

            try:
                text1 = file1.read_text(encoding="utf-8", errors="ignore").splitlines()
                text2 = file2.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError as e:
                return DiffResult(error=f"ファイル読み込みエラー: {e}")

            diff_lines = list(
                difflib.unified_diff(
                    text1,
                    text2,
                    fromfile=str(file1.name),
                    tofile=str(file2.name),
                    lineterm="",
                )
            )
            return DiffResult(
                file1=file1,
                file2=file2,
                is_inp=False,
                has_diffs=bool(diff_lines),
                unified_diff_lines=diff_lines,
            )

    # =========
    # credential
    # =========

    def credential_set(self, service: str, creds: dict[str, str]) -> Path:
        """クレデンシャルを暗号化して保存

        Args:
            service: サービス名
            creds: クレデンシャル辞書

        Returns:
            保存先パス
        """
        return save_credentials(self.project_root, service, creds)

    def credential_show(self, service: str, unmask: bool = False) -> CredentialShowResult:
        """保存済みクレデンシャルを表示

        Args:
            service: サービス名
            unmask: マスキングせずに表示

        Returns:
            CredentialShowResult
        """
        creds = load_credentials(self.project_root, service)
        if creds is None:
            return CredentialShowResult(found=False, service=service)

        if not unmask:
            creds = {k: mask_value(v) for k, v in creds.items()}

        return CredentialShowResult(
            found=True,
            service=service,
            credentials=creds,
        )

    def credential_delete(self, service: str) -> bool:
        """保存済みクレデンシャルを削除

        Args:
            service: サービス名

        Returns:
            削除に成功した場合True
        """
        import json as json_mod

        from services.lib.credentials import _get_credentials_path

        cred_path = _get_credentials_path(self.project_root)
        if not cred_path.exists():
            return False

        all_creds = json_mod.loads(cred_path.read_text(encoding="utf-8"))
        if service not in all_creds:
            return False

        del all_creds[service]
        cred_path.write_text(
            json_mod.dumps(all_creds, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
