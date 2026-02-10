"""InfoService: グラフ情報検索・エクスポートのビジネスロジック

CLI graph.pyのinfo/export/diffコマンドで使用されるビジネスロジックを集約。
CLI層はargparse解析と出力整形のみに責務を限定する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import csv
import fnmatch
import json as json_mod
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Optional

from jj_types import GraphModel, Node, Relation
from config import GraphConfig
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

    def parse_and_save(
        self, filename: str | None = None
    ) -> tuple[GraphModel, Path]:
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
                            node.name == basename
                            or node_file == basename
                            or node_path == normalized
                            or basename in node.name
                            or normalized in node_path
                            or node.name == filename
                            or node_file == filename
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
                        node.properties.get("index", "")
                        or (node.properties.get(idx_key, "") if idx_key else "")
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
                    matched_nodes = [
                        n
                        for n in matched_nodes
                        if _get_version(n) in version_filters
                    ]
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
            matched_nodes = [
                n for n in matched_nodes
                if str(n.properties.get("active", "")).lower() == "true"
            ]

        return matched_nodes

    def get_relations_for_node(
        self, graph: GraphModel, node_id: int
    ) -> list[Relation]:
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
        export_config = self.service.config.export

        # ノードのフィルタリング
        if nodes is not None:
            filtered_nodes = list(nodes)
        else:
            filtered_nodes = list(graph.nodes)

            if type_filter:
                filtered_nodes = [n for n in filtered_nodes if n.type == type_filter]
            if select_filter:
                selected: list[Node] = []
                for n in filtered_nodes:
                    name_with_ext = f"{n.name}.{n.format}" if n.format else n.name
                    for sel in select_filter:
                        if n.name == sel or name_with_ext == sel or sel in n.name:
                            selected.append(n)
                            break
                filtered_nodes = selected

        # -prop フィルタ: 指定プロパティを持つノードのみ（AND条件）
        if prop_filters:
            filtered_nodes = [
                n
                for n in filtered_nodes
                if all(k in n.properties for k in prop_filters)
            ]

        if not filtered_nodes:
            raise ValueError("対象ノードが見つかりません。")

        # 平坦化のデフォルト: CSVはTrue、JSONはFalse
        if flatten is None:
            flatten = (target == "csv")

        # プロパティを収集（flattenフラグに応じて平坦化）
        data_rows: list[dict[str, Any]] = []
        for node in filtered_nodes:
            base: dict[str, Any] = {
                "name": node.name,
                "type": node.type,
                "format": node.format,
            }
            if flatten:
                props = _flatten_properties(node.properties)
            else:
                props = dict(node.properties)
            base.update(props)
            data_rows.append(base)

        # キーの収集（-prop指定時は base + 指定キーのみ）
        if prop_filters:
            all_keys: list[str] = ["name", "type", "format"]
            seen_keys: set[str] = set(all_keys)
            for row in data_rows:
                for key in row:
                    if key in seen_keys:
                        continue
                    for pf in prop_filters:
                        if key == pf or key.startswith(pf + "."):
                            all_keys.append(key)
                            seen_keys.add(key)
                            break
        else:
            all_keys = ["name", "type", "format"]
            seen_keys = set(all_keys)
            for row in data_rows:
                for key in row:
                    if key not in seen_keys:
                        all_keys.append(key)
                        seen_keys.add(key)

        # CSVカラム制限（config.export.csv-columns またはCLI --columns）
        # configで指定したキー順を保持する。glob パターンに対応。
        if target == "csv":
            csv_columns = columns or export_config.csv_columns
            if csv_columns:
                base_keys = ["name", "type", "format"]
                ordered_keys: list[str] = []
                seen: set[str] = set()
                # base_keysを先頭に
                for k in base_keys:
                    if k in all_keys and k not in seen:
                        ordered_keys.append(k)
                        seen.add(k)
                # config指定順にカラム追加（globパターン対応）
                for pattern in csv_columns:
                    for k in all_keys:
                        if k not in seen and fnmatch.fnmatch(k, pattern):
                            ordered_keys.append(k)
                            seen.add(k)
                all_keys = ordered_keys

        # null埋めとリスト/辞書値のJSON文字列化（CSVのみ）
        rows: list[dict[str, Any]] = []
        for data_row in data_rows:
            row: dict[str, Any] = {}
            for key in all_keys:
                value = data_row.get(key)
                if value is None:
                    row[key] = None
                elif isinstance(value, (list, dict)) and target == "csv":
                    row[key] = json_mod.dumps(value, ensure_ascii=False)
                else:
                    row[key] = value
            rows.append(row)

        # 出力
        if output_file is None:
            output_file = f"export.{target}"
        output_path = self.project_root / output_file

        if target == "csv":
            # 単位マッピングと表示形式を決定
            units = export_config.units
            fmt = unit_format or export_config.csv_unit_format

            # UTF-8 BOM付きで出力（Excel等での日本語文字化け対策）
            with output_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)

                if fmt == "row":
                    # 1行目: カラム名、2行目: 単位
                    writer.writerow(all_keys)
                    unit_row = [_match_unit(k, units) for k in all_keys]
                    writer.writerow(unit_row)
                else:
                    # デフォルト(header): {column}[{unit}] 形式
                    header = []
                    for k in all_keys:
                        u = _match_unit(k, units)
                        header.append(f"{k}[{u}]" if u else k)
                    writer.writerow(header)

                # データ行
                for row in rows:
                    writer.writerow([row.get(k) for k in all_keys])

        elif target == "json":
            with output_path.open("w", encoding="utf-8") as f:
                json_mod.dump(rows, f, ensure_ascii=False, indent=2, default=str)

        return output_path, len(rows)

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


def _match_unit(key: str, units: dict[str, str]) -> str:
    """カラム名に対応する単位を返す（globパターン対応）

    完全一致を優先し、見つからなければglobパターンでマッチングを試みる。

    Args:
        key: カラム名
        units: カラム名→単位のマッピング（globパターン可）

    Returns:
        マッチした単位文字列。マッチしない場合は空文字列
    """
    # 完全一致を優先
    if key in units:
        return units[key]
    # globパターンマッチ
    for pattern, unit in units.items():
        if fnmatch.fnmatch(key, pattern):
            return unit
    return ""


def _flatten_properties(
    props: dict[str, Any], prefix: str = ""
) -> dict[str, Any]:
    """辞書プロパティを"."区切りで平坦化する

    ネストされた辞書は再帰的に展開される。
    例: {"mesh_quality": {"aspect_ratio": {"min": 0.5, "max": 1.0}}}
    → {"mesh_quality.aspect_ratio.min": 0.5, "mesh_quality.aspect_ratio.max": 1.0}

    リストは展開せずそのまま保持する。

    Args:
        props: 平坦化対象の辞書
        prefix: キーのプレフィックス（再帰用）

    Returns:
        平坦化された辞書
    """
    result: dict[str, Any] = {}
    for key, value in props.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_properties(value, prefix=full_key))
        else:
            result[full_key] = value
    return result
