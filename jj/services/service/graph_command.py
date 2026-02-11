"""GraphCommandService: グラフコマンドのビジネスロジック

CLI graph.pyのinit/parse/show/export/info/diff/credentialコマンドで
使用されるビジネスロジックを集約。CLI層はargparse解析と出力整形のみに
責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from jj_types import GraphModel, Node, Relation
from config import GraphConfig, init_graph_config
from services.graph import GraphService
from services.service.info import InfoService
from services.lib.selection import expand_ranges
from services.lib.credentials import (
    load_credentials,
    mask_value,
    save_credentials,
)


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
class ExportObsidianResult:
    """Obsidianエクスポートの結果"""

    written_paths: list[Path]


@dataclass
class ExportDataResult:
    """CSV/JSONエクスポートの結果"""

    output_path: Path
    count: int
    target: str


@dataclass
class ExportNeo4jResult:
    """Neo4j/Cypherエクスポートの結果"""

    uri: str
    stats: dict[str, int] | None  # direct=True時のみ
    output_path: Path | None  # direct=False(cypher)時のみ
    node_count: int
    relation_count: int
    clear_project: bool
    direct: bool


@dataclass
class ExportDashboardJsonResult:
    """dashboard-jsonエクスポートの結果"""

    output_path: Path
    node_count: int
    relation_count: int
    row_count: int


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
            self._graph_service.config = dc_replace(
                self._graph_service.config, directory_max_depth=max_depth
            )

        if output_file is None:
            output_file = f"graph.{format}"

        graph, save_path = self._graph_service.parse_and_save(
            filename=output_file, full_mode=full_mode, debug=debug
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
        graph = self._graph_service.load(filename=filename)

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
            graph = self._graph_service.load(filename=filename)
            return graph, None

    # =========
    # export: obsidian
    # =========

    def export_obsidian(
        self,
        graph: GraphModel,
        overwrite: bool = False,
    ) -> ExportObsidianResult:
        """Obsidianにエクスポート

        Args:
            graph: エクスポート対象のグラフ
            overwrite: 既存ファイルを上書きするか

        Returns:
            ExportObsidianResult
        """
        from services.export.connectors.obsidian import ObsidianConnector

        connector = ObsidianConnector(project_root=self.project_root)
        written = connector.export_graph(graph, overwrite=overwrite)
        return ExportObsidianResult(written_paths=written)

    # =========
    # export: csv/json
    # =========

    def export_data(
        self,
        graph: GraphModel,
        target: str,
        *,
        type_filter: str | None = None,
        select_filter: list[str] | None = None,
        output_file: str | None = None,
        index_filters: list[str] | None = None,
        version_filters: list[str] | None = None,
        all_nodes: bool = False,
        prop_filters: list[str] | None = None,
        flatten: bool = False,
        active_only: bool = False,
        unit_format: str | None = None,
        columns: list[str] | None = None,
    ) -> ExportDataResult:
        """CSV/JSONデータエクスポート

        共通選択オプション（-id, -v, -type, -all）が指定されている場合は
        InfoService.search_nodesで事前にノードを絞り込んでからエクスポートする。

        Args:
            graph: エクスポート対象のグラフ
            target: "csv" or "json"
            type_filter: ノードタイプフィルタ
            select_filter: ファイル名フィルタ
            output_file: 出力ファイル名
            index_filters: インデックスフィルタ
            version_filters: バージョンフィルタ
            all_nodes: 全ノード選択
            prop_filters: プロパティフィルタ
            flatten: 平坦化フラグ
            active_only: activeのみ
            unit_format: 単位表示形式
            columns: カラム選択

        Returns:
            ExportDataResult
        """
        # 共通選択オプションが指定されている場合は事前にノード絞り込み
        pre_selected: list[Node] | None = None
        if index_filters is not None or version_filters is not None or all_nodes or active_only:
            pre_selected = self._info_service.search_nodes(
                graph,
                index_filters=index_filters,
                version_filters=version_filters,
                type_filter=type_filter,
                all_nodes=all_nodes,
                active_only=active_only,
            )
            # search_nodesでtype_filterを適用済みなのでexport_dataには渡さない
            type_filter = None

        # flattenフラグ: --flatten指定時はTrue、未指定はNone（targetに応じたデフォルト）
        flatten_opt: bool | None = True if flatten else None

        output_path, count = self._info_service.export_data(
            graph,
            target,
            type_filter=type_filter,
            select_filter=select_filter,
            output_file=output_file,
            prop_filters=prop_filters,
            nodes=pre_selected,
            flatten=flatten_opt,
            unit_format=unit_format,
            columns=columns,
        )
        return ExportDataResult(
            output_path=output_path,
            count=count,
            target=target,
        )

    # =========
    # export: dashboard-json
    # =========

    def export_dashboard_json(
        self,
        graph: GraphModel,
        *,
        output_file: str | None = None,
        project_name: str | None = None,
    ) -> ExportDashboardJsonResult:
        """dashboard-jsonエクスポート

        GraphModelからダッシュボード向けJSONデータを生成しファイルに出力する。

        Args:
            graph: エクスポート対象のグラフ
            output_file: 出力ファイル名（未指定時は .jj/storage/dashboard.json）
            project_name: プロジェクト名（メタデータ用）

        Returns:
            ExportDashboardJsonResult
        """
        import json

        from services.dashboard.data_provider import DashboardDataProvider

        config = self._graph_service.config
        provider = DashboardDataProvider(
            graph,
            vocab=config.vocab,
            units=config.export.units,
        )

        name = project_name or self.project_root.name
        data = provider.to_dashboard_json(project_name=name)

        if output_file:
            out_path = Path(output_file)
        else:
            storage_dir = self.project_root / ".jj" / "storage"
            storage_dir.mkdir(parents=True, exist_ok=True)
            out_path = storage_dir / "dashboard.json"

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return ExportDashboardJsonResult(
            output_path=out_path,
            node_count=len(graph.nodes),
            relation_count=len(graph.relations),
            row_count=len(data["rows"]),
        )

    # =========
    # export: neo4j/cypher
    # =========

    def export_neo4j(
        self,
        graph: GraphModel,
        *,
        direct: bool = True,
        clear_project: bool = False,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
        output_file: str | None = None,
    ) -> ExportNeo4jResult:
        """Neo4j/Cypherエクスポート

        Args:
            graph: エクスポート対象のグラフ
            direct: Trueの場合Neo4jに直接書き込み、Falseの場合Cypherファイル出力
            clear_project: 既存プロジェクトデータを削除してから投入
            neo4j_uri: Neo4j接続URI（CLI上書き用）
            neo4j_user: Neo4jユーザー名（CLI上書き用）
            neo4j_password: Neo4jパスワード（CLI上書き用）
            output_file: Cypherファイル出力パス

        Returns:
            ExportNeo4jResult
        """
        from services.connectors.neo4j import Neo4jConnector
        from shared.config import Neo4jConfig

        # Neo4j接続設定の構築
        neo4j_config = Neo4jConfig.from_jj_config(self.project_root)
        # CLIオプションで上書き
        if neo4j_uri:
            neo4j_config.uri = neo4j_uri
        if neo4j_user:
            neo4j_config.user = neo4j_user
        if neo4j_password:
            neo4j_config.password = neo4j_password

        connector = Neo4jConnector(project_root=self.project_root, config=neo4j_config)
        try:
            if direct:
                stats = connector.export_graph(graph, clear_project=clear_project)
                return ExportNeo4jResult(
                    uri=neo4j_config.uri,
                    stats=stats,
                    output_path=None,
                    node_count=stats["nodes_created"],
                    relation_count=stats["relations_created"],
                    clear_project=clear_project,
                    direct=True,
                )
            else:
                output_path = connector.export_cypher(
                    graph,
                    output_path=output_file,
                    clear_project=clear_project,
                )
                return ExportNeo4jResult(
                    uri=neo4j_config.uri,
                    stats=None,
                    output_path=output_path,
                    node_count=len(graph.nodes),
                    relation_count=len(graph.relations),
                    clear_project=clear_project,
                    direct=False,
                )
        finally:
            connector.close()

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
        if (
            not filenames
            and index_filters is None
            and version_filters is None
            and not all_nodes
        ):
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
            matched_nodes = [
                n
                for n in matched_nodes
                if all(k in n.properties for k in prop_filters)
            ]

        return InfoResult(
            nodes=matched_nodes,
            graph=graph,
            empty=False,
            no_criteria=False,
        )

    def get_relations_for_node(
        self, graph: GraphModel, node_id: int
    ) -> list[Relation]:
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
            except (OSError, IOError) as e:
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

    def credential_show(
        self, service: str, unmask: bool = False
    ) -> CredentialShowResult:
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
