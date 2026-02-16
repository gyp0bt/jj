"""InfoService: グラフ情報検索・エクスポートのビジネスロジック

CLI graph.pyのinfo/export/diffコマンドで使用されるビジネスロジックを集約。
CLI層はargparse解析と出力整形のみに責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from jj_types import GraphModel, Node, Relation
from services.graph import GraphService


class InfoService:
    """グラフ情報検索・エクスポートのビジネスロジック

    GraphServiceのラッパーとして、ノード検索やデータ変換等の
    ビジネスロジックを提供する。
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.service = GraphService(project_root=project_root)
        self._vocab = self.service.config.vocab

    def load_graph(self, filename: str | None = None) -> GraphModel:
        """グラフデータをロード"""
        return self.service.load(filename=filename)

    def parse_and_save(self, filename: str | None = None) -> tuple[GraphModel, Path]:
        """プロジェクトをパースして保存"""
        return self.service.parse_and_save(filename=filename)

    def summary(self, graph: GraphModel) -> dict[str, Any]:
        """グラフのサマリーを生成"""
        return self.service.summary(graph)

    # =========
    # ノード検索
    # =========

    def search_nodes(
        self,
        graph: GraphModel,
        *,
        filenames: list[str] | None = None,
        index_filters: list[str] | None = None,
        version_filters: list[str] | None = None,
        type_filter: str | None = None,
        all_nodes: bool = False,
        active_only: bool = False,
    ) -> list[Node]:
        """複合条件でノードを検索する

        Args:
            graph: 検索対象のグラフ
            filenames: ファイル名で検索（部分一致、複数可）
            index_filters: インデックスで検索（例: ["1", "2"]）
            version_filters: バージョンで検索（例: ["1", "2"]）
            type_filter: ノードタイプでフィルタリング（例: "Abaqusインプット"）
            all_nodes: 全ノードを選択

        Returns:
            マッチしたノードのリスト
        """
        matched_nodes: list[Node] = []

        # -all: 全ノード選択
        if all_nodes:
            matched_nodes = list(graph.nodes)
        else:
            # ファイル名で検索（部分一致）
            if filenames:
                for filename in filenames:
                    normalized = filename.replace("\\", "/")
                    basename = PurePosixPath(normalized).name
                    if basename == filename and "\\" in filename:
                        basename = PureWindowsPath(filename).name

                    for node in graph.nodes:
                        if node in matched_nodes:
                            continue
                        node_path = node.properties.get("path", "").replace("\\", "/")
                        node_file = PurePosixPath(node_path).name if node_path else ""
                        if (
                            node_file in (basename, filename)
                            or node.name == basename
                            or node_path == normalized
                            or basename in node.name
                            or normalized in node_path
                            or node.name == filename
                            or filename in node.name
                        ):
                            matched_nodes.append(node)

            # インデックスで検索（vocab変換後のキーにも対応）
            if index_filters is not None:
                idx_key = self._vocab.get("idx", "")
                for node in graph.nodes:
                    if node in matched_nodes:
                        continue
                    node_index = str(
                        node.properties.get("index", "") or (node.properties.get(idx_key, "") if idx_key else "")
                    )
                    if node_index and node_index in index_filters:
                        matched_nodes.append(node)

            # バージョンで検索（絞り込みまたは単独検索、vocab変換後のキーにも対応）
            if version_filters is not None:
                ver_key = self._vocab.get("v", "") or self._vocab.get("ver", "")

                def _get_version(n: Node) -> str:
                    v = str(n.properties.get("version", ""))
                    if not v and ver_key:
                        v = str(n.properties.get(ver_key, ""))
                    return v

                if filenames or index_filters is not None:
                    # 既存のマッチ結果から絞り込み
                    matched_nodes = [n for n in matched_nodes if _get_version(n) in version_filters]
                else:
                    # バージョンのみ指定の場合は全ノードから検索
                    for node in graph.nodes:
                        node_ver = _get_version(node)
                        if node_ver and node_ver in version_filters:
                            matched_nodes.append(node)

        # タイプフィルタ（他の条件と組み合わせて絞り込み）
        if type_filter:
            matched_nodes = [n for n in matched_nodes if n.type == type_filter]

        # active フィルタ: active == "true" のノードのみ
        if active_only:
            matched_nodes = [n for n in matched_nodes if str(n.properties.get("active", "")).lower() == "true"]

        return matched_nodes

    def get_relations_for_node(self, graph: GraphModel, node_id: int) -> list[Relation]:
        """ノードに関連するリレーションを取得"""
        return self.service.get_relations_for_node(graph, node_id)

    # =========
    # データエクスポート
    # =========

    def export_data(
        self,
        graph: GraphModel,
        target: str,
        *,
        type_filter: str | None = None,
        select_filter: list[str] | None = None,
        output_file: str | None = None,
        prop_filters: list[str] | None = None,
        nodes: list[Node] | None = None,
        flatten: bool | None = None,
        unit_format: str | None = None,
        columns: list[str] | None = None,
    ) -> tuple[Path, int]:
        """ノードデータをCSV/JSON形式でエクスポートする

        内部的にexport/connectors/csv_json.pyのコアロジックに委譲する。

        Args:
            graph: エクスポート対象のグラフ
            target: "csv" or "json"
            type_filter: ノードタイプでフィルタリング
            select_filter: ファイル名でフィルタリング
            output_file: 出力ファイル名
            prop_filters: プロパティキーフィルタ（指定時はAND条件で絞り込み）
            nodes: 事前に選択済みのノードリスト（指定時はgraphからの選択を省略）
            flatten: プロパティを平坦化するか（CSVはデフォルトTrue、JSONはデフォルトFalse）
            unit_format: 単位表示形式 ("header" or "row")。Noneの場合config設定に従う
            columns: エクスポートするカラム名リスト。Noneの場合config設定に従う

        Returns:
            (出力パス, エクスポートされたノード数)
        """
        from services.export.connectors.csv_json import _export_data

        export_config = self.service.config.export

        result = _export_data(
            graph,
            target,
            project_root=self.project_root,
            nodes=nodes,
            type_filter=type_filter,
            select_filter=select_filter,
            prop_filters=prop_filters,
            output_file=output_file,
            flatten=flatten,
            unit_format=unit_format,
            columns=columns,
            units=export_config.units,
            csv_columns=export_config.csv_columns,
            csv_unit_format=export_config.csv_unit_format,
        )
        return result["output_path"], result["count"]

    # =========
    # ファイルパス解決
    # =========

    @staticmethod
    def resolve_file_path(project_root: Path, filename: str) -> Path | None:
        """ファイル名からファイルパスを解決

        直接パス指定、プロジェクトルート相対パス、再帰検索の順に試行する。
        """
        direct = Path(filename)
        if direct.exists():
            return direct
        relative = project_root / filename
        if relative.exists():
            return relative
        for found in project_root.rglob(filename):
            return found
        return None


# 後方互換: 旧コードから参照されている場合のために関数をre-export
from services.export.connectors.csv_json import (  # noqa: F401, E402
    flatten_properties as _flatten_properties,
)
