"""ダッシュボード向けデータ供給クラス（薄い表示ラッパ）

GraphModelを受け取り、テーブル/カード/プロット/ステータスの
各ビュー向けデータ構造に変換する。汎用なクエリ・行整形・外部化
プロパティ解決は services.graph.query.GraphQuery に委譲し、
本クラスは vocab/units/verbose_name の表示変換を担う。

ソフトウェア固有のデータ供給（例: Abaqus物性テーブル）は
plugins/{solver}/dashboard.py のコネクターに移動済み。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jj_types import RUN_INPUT, RUN_MEDIA, RUN_OUTPUT, GraphModel, Node, NodeCategory, Relation
from services.graph.query.graph_query import (
    EXT_KEYS_FIELD,
    GraphQuery,
    format_float_value,  # noqa: F401  公開名互換のため再エクスポート
)

# 後方互換: 旧シンボル
_EXT_KEYS_FIELD = EXT_KEYS_FIELD


def _compute_histogram_bins(values: list[float]) -> int:
    """データ分布に応じたヒストグラムビン数を動的に決定する (Sturges則)"""
    n = len(values)
    if n <= 1:
        return 1
    if n <= 5:
        return n
    sturges = math.ceil(math.log2(n) + 1)
    return max(10, min(50, sturges))


def _percentile(sorted_values: list[float], pct: float) -> float:
    """ソート済みリストからパーセンタイル値を線形補間で計算"""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_values[0]
    k = (pct / 100.0) * (n - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def _is_go_node(node: Node) -> bool:
    name_lower = node.name.lower()
    return name_lower.startswith("go_") or name_lower == "go"


class DashboardDataProvider:
    """ダッシュボード向けデータ供給（表示変換層）

    GraphQuery (汎用クエリ層) の結果に vocab/units/verbose_name を載せて
    各ビューへ供給する。

    Args:
        graph: 対象のGraphModel
        vocab: config.vocabマッピング（キー/値の翻訳用）
        units: config.export.unitsマッピング（カラム名への単位付加用）
        verbose_name_format: 廃止済み（後方互換のため残置、parse時に処理される）
        global_columns: グローバルカラム設定（globパターン対応、export.csv-columnsから昇格）
    """

    def __init__(
        self,
        graph: GraphModel,
        vocab: dict[str, str] | None = None,
        units: dict[str, str] | None = None,
        verbose_name_format: str | None = None,
        global_columns: list[str] | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.graph = graph
        self.vocab = vocab or {}
        self.units = units or {}
        self._verbose_name_format = verbose_name_format  # 後方互換のため保持
        self._global_columns = global_columns
        self._project_root = project_root

        storage: Any | None = None
        if project_root is not None:
            from services.graph.storage import GraphStorage

            storage = GraphStorage()
        self._storage = storage

        self._gq = GraphQuery(graph, storage=storage, project_root=project_root)

        # 生キーで統一（vocab変換は表示時のみ）
        self._verbose_name_key = "verbose_name"
        self._index_key = "index"
        self._version_key = "version"

    # ------------------------------------------------------------------
    # 後方互換: GraphQuery 内部インデックスへの read-only プロキシ
    # ------------------------------------------------------------------

    @property
    def _node_by_id(self) -> dict[int, Node]:
        return self._gq._node_by_id

    @property
    def _relations_by_node(self) -> dict[int, list[Relation]]:
        return self._gq._relations_by_node

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def get_go_table(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """go_ファイルのテーブルデータ（プロパティ展開済み）"""
        rows: list[dict[str, Any]] = []
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            row = self._node_to_row(node)
            if filters and not self._matches_filters(row, filters):
                continue
            rows.append(row)
        return rows

    def get_run_nodes(self) -> list[dict[str, Any]]:
        """Runノード一覧を返す"""
        results: list[dict[str, Any]] = []
        for node in self.graph.nodes:
            if node.category != NodeCategory.RUN:
                continue
            inputs: list[int] = []
            outputs: list[int] = []
            media: list[int] = []
            for rel in self._gq.query_relations(node.id, direction="outgoing"):
                if rel.label == RUN_INPUT:
                    inputs.append(rel.node2_id)
                elif rel.label == RUN_OUTPUT:
                    outputs.append(rel.node2_id)
                elif rel.label == RUN_MEDIA:
                    media.append(rel.node2_id)
            results.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "run_type": node.properties.get("run_type", ""),
                    "run_status": node.properties.get("run_status", ""),
                    "discovery": node.properties.get("discovery", ""),
                    "properties": {
                        k: v
                        for k, v in node.properties.items()
                        if k not in ("path", "run_type", "run_status", "discovery")
                    },
                    "input_ids": inputs,
                    "output_ids": outputs,
                    "media_ids": media,
                }
            )
        return results

    def get_run_for_node(self, node_id: int) -> dict[str, Any] | None:
        """指定ノードを出力に持つRunノードを返す（run_output逆引き）"""
        for rel in self._gq.query_relations(node_id, label=RUN_OUTPUT, direction="incoming"):
            run_node = self._node_by_id.get(rel.node1_id)
            if run_node is not None and run_node.category == NodeCategory.RUN:
                return {
                    "id": run_node.id,
                    "name": run_node.name,
                    "run_type": run_node.properties.get("run_type", ""),
                    "run_status": run_node.properties.get("run_status", ""),
                    "discovery": run_node.properties.get("discovery", ""),
                    "duration_seconds": run_node.properties.get("duration_seconds"),
                    "started_at": run_node.properties.get("started_at"),
                    "finished_at": run_node.properties.get("finished_at"),
                    "command": run_node.properties.get("command"),
                    "host": run_node.properties.get("host"),
                    "user": run_node.properties.get("user"),
                    "exit_code": run_node.properties.get("exit_code"),
                }
        return None

    def get_node_card(self, node_id: int) -> dict[str, Any] | None:
        """ノード詳細カード（関連ノード含む）"""
        node = self._node_by_id.get(node_id)
        if node is None:
            return None

        card: dict[str, Any] = {
            "id": node.id,
            "type": node.type,
            "name": node.name,
            "format": node.format,
            "properties": dict(node.properties),
            "relations": [],
        }
        for rel in self._gq.query_relations(node_id):
            other_id = rel.node2_id if rel.node1_id == node_id else rel.node1_id
            other_node = self._node_by_id.get(other_id)
            card["relations"].append(
                {
                    "label": rel.label,
                    "direction": "outgoing" if rel.node1_id == node_id else "incoming",
                    "node_id": other_id,
                    "node_name": other_node.name if other_node else str(other_id),
                    "node_type": other_node.type if other_node else "unknown",
                }
            )
        return card

    def get_plot_data(
        self,
        x_key: str,
        y_key: str,
        color_key: str | None = None,
        extra_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """プロット用データ（数値プロパティのみ）"""
        points: list[dict[str, Any]] = []
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            x_val = node.properties.get(x_key)
            y_val = node.properties.get(y_key)
            if x_val is None or y_val is None:
                continue
            try:
                x_num = float(x_val)
                y_num = float(y_val)
            except (ValueError, TypeError):
                continue
            point: dict[str, Any] = {
                "name": node.name,
                self._verbose_name_key: self._get_display_name(node),
                "id": node.id,
                x_key: x_num,
                y_key: y_num,
            }
            if color_key:
                point[color_key] = node.properties.get(color_key, "")
            if extra_keys:
                for ek in extra_keys:
                    if ek not in point:
                        point[ek] = node.properties.get(ek, "")
            points.append(point)
        return points

    def get_property_keys(self) -> list[str]:
        """利用可能なプロパティキー一覧（vocab順）"""
        keys: set[str] = set()
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            keys.update(node.properties.keys())
        keys -= {"path"}
        return self._sort_by_vocab(keys)

    def _sort_by_vocab(self, keys: set[str] | list[str]) -> list[str]:
        """vocab順でキーをソート（接頭辞エスケープキー対応）"""
        from services.graph.query.sort import get_base_key

        vocab_order: dict[str, int] = {}
        for idx, v in enumerate(self.vocab.values()):
            if v not in vocab_order:
                vocab_order[v] = idx
        for idx, k in enumerate(self.vocab.keys()):
            if k not in vocab_order:
                vocab_order[k] = len(self.vocab) + idx

        max_order = len(vocab_order) + len(self.vocab)

        def _sort_key(col: str) -> tuple[int, int, str]:
            if col in vocab_order:
                return (vocab_order[col], 0, col)
            base = get_base_key(col)
            if base != col and base in vocab_order:
                return (vocab_order[base], 1, col)
            return (max_order, 0, col)

        return sorted(keys, key=_sort_key)

    def get_status_summary(self) -> dict[str, Any]:
        """実行ステータスサマリー（go_ノード集計 + CPU/警告統計）"""
        total = 0
        completed = 0
        failed = 0
        unknown = 0
        items: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            total += 1
            status = node.properties.get("analysis_status", "unknown")
            if status == "completed":
                completed += 1
            elif status == "failed":
                failed += 1
            else:
                unknown += 1

            item: dict[str, Any] = {
                "name": node.name,
                "analysis_status": status,
            }
            if "cpu_time" in node.properties:
                item["cpu_time"] = node.properties["cpu_time"]
                errors = (
                    node.properties.get("sta_errors", [])
                    + node.properties.get("msg_errors", [])
                    + node.properties.get("dat_errors", [])
                )
                item["errors"] = errors
                warnings = (
                    node.properties.get("sta_warnings", [])
                    + node.properties.get("msg_warnings", [])
                    + node.properties.get("dat_warnings", [])
                )
                item["warnings"] = warnings
            items.append(item)

        cpu_times = [i["cpu_time"] for i in items if "cpu_time" in i and i["cpu_time"] is not None]
        cpu_stats: dict[str, Any] = {}
        if cpu_times:
            numeric_cpu = [float(t) for t in cpu_times if isinstance(t, (int, float))]
            if numeric_cpu:
                cpu_stats = {
                    "count": len(numeric_cpu),
                    "min": min(numeric_cpu),
                    "max": max(numeric_cpu),
                    "mean": sum(numeric_cpu) / len(numeric_cpu),
                    "values": numeric_cpu,
                    "nbins": _compute_histogram_bins(numeric_cpu),
                }
                if len(numeric_cpu) >= 2:
                    sorted_vals = sorted(numeric_cpu)
                    n = len(sorted_vals)
                    cpu_stats["median"] = _percentile(sorted_vals, 50)
                    cpu_stats["q1"] = _percentile(sorted_vals, 25)
                    cpu_stats["q3"] = _percentile(sorted_vals, 75)
                    mean = cpu_stats["mean"]
                    cpu_stats["std"] = (sum((v - mean) ** 2 for v in sorted_vals) / n) ** 0.5

        warning_counts = [i["warnings"] for i in items if "warnings" in i and isinstance(i["warnings"], (int, float))]
        warning_stats: dict[str, Any] = {}
        if warning_counts:
            int_warnings = [int(w) for w in warning_counts]
            warning_stats = {
                "count": len(int_warnings),
                "total": sum(int_warnings),
                "values": int_warnings,
                "nbins": _compute_histogram_bins([float(w) for w in int_warnings]),
            }
            if len(int_warnings) >= 2:
                warning_stats["min"] = min(int_warnings)
                warning_stats["max"] = max(int_warnings)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "unknown": unknown,
            "items": items,
            "cpu_stats": cpu_stats,
            "warning_stats": warning_stats,
        }

    def get_related_files(
        self,
        node_id: int,
        label: str | None = None,
    ) -> list[dict[str, Any]]:
        """関連ファイル一覧（リレーションラベルで絞り込み可）"""
        related: list[dict[str, Any]] = []
        for rel in self._gq.query_relations(node_id, label=label):
            other_id = rel.node2_id if rel.node1_id == node_id else rel.node1_id
            other_node = self._node_by_id.get(other_id)
            if other_node is None:
                continue
            related.append(
                {
                    "id": other_node.id,
                    "name": other_node.name,
                    "type": other_node.type,
                    "format": other_node.format,
                    "label": rel.label,
                    "direction": "outgoing" if rel.node1_id == node_id else "incoming",
                }
            )
        return related

    def to_dashboard_json(self, project_name: str = "") -> dict[str, Any]:
        """dashboard-json形式のエクスポートデータを生成"""
        rows = self.get_go_table()
        columns = self._collect_columns(rows)
        return {
            "metadata": {
                "project": project_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "node_count": len(self.graph.nodes),
                "relation_count": len(self.graph.relations),
            },
            "columns": columns,
            "rows": rows,
            "graph": {
                "nodes": [n.model_dump() for n in self.graph.nodes],
                "relations": [r.model_dump() for r in self.graph.relations],
            },
        }

    def get_output_images(
        self,
        node_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """画像出力ファイル一覧（has_output関係から取得）"""
        image_formats = {"png", "gif", "jpg", "jpeg", "bmp", "svg", "tiff"}
        results: list[dict[str, Any]] = []

        target_nodes: list[Node] = []
        if node_id is not None:
            node = self._node_by_id.get(node_id)
            if node is not None:
                target_nodes = [node]
        else:
            target_nodes = [n for n in self.graph.nodes if _is_go_node(n)]

        for go_node in target_nodes:
            for rel in self._gq.query_relations(go_node.id, label="has_output", direction="outgoing"):
                output_node = self._node_by_id.get(rel.node2_id)
                if output_node is None:
                    continue
                fmt = output_node.format.lower() if output_node.format else ""
                path_str = output_node.properties.get("path", "")
                ext = path_str.rsplit(".", 1)[-1].lower() if "." in path_str else ""
                if fmt not in image_formats and ext not in image_formats:
                    continue
                results.append(
                    {
                        "go_node_id": go_node.id,
                        "go_node_name": go_node.name,
                        "display_name": self._get_display_name(go_node),
                        "image_node_id": output_node.id,
                        "image_name": output_node.name,
                        "image_path": path_str,
                        "image_format": fmt or ext,
                        "go_properties": {k: v for k, v in go_node.properties.items() if k != "path"},
                    }
                )
        return results

    def get_property_images(
        self,
        daily_notes_dir: str = "notes/daily",
    ) -> list[dict[str, Any]]:
        """プロパティに画像ファイルパスを持つノードの画像情報を取得"""
        image_extensions = {"png", "gif", "jpg", "jpeg", "bmp", "svg", "tiff"}
        results: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            go_props = {k: v for k, v in node.properties.items() if k != "path"}
            display_name = self._get_display_name(node)

            for key, value in node.properties.items():
                if key == "path":
                    continue
                if key == "daily_notes" and isinstance(value, dict):
                    GraphQuery.extract_daily_note_images(
                        results,
                        node,
                        display_name,
                        value,
                        go_props,
                        image_extensions,
                        daily_notes_dir,
                    )
                    continue
                GraphQuery.extract_image_paths(
                    results,
                    node,
                    display_name,
                    key,
                    value,
                    go_props,
                    image_extensions,
                )
        return results

    def get_array_property_keys(self) -> list[str]:
        """go_ノードの配列型プロパティキー（PREFIX.列名形式）を返す。

        外部化プロパティ (_ext_keys マーカー) も考慮する。
        """
        keys: set[str] = set()
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            for key, value in node.properties.items():
                if "." in key and isinstance(value, list):
                    keys.add(key)
            ext_keys = node.properties.get(EXT_KEYS_FIELD)
            if isinstance(ext_keys, list):
                for key in ext_keys:
                    if "." in key:
                        keys.add(key)
        return sorted(keys)

    def get_array_plot_data(
        self,
        node_id: int,
        x_key: str,
        y_keys: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """特定ノードの配列プロパティをプロット用データに変換"""
        node = self._node_by_id.get(node_id)
        if node is None:
            return None

        props = self._gq._resolve_node_properties(node)

        x_values = props.get(x_key)
        if not isinstance(x_values, list):
            return None

        if y_keys is None:
            prefix = x_key.split(".")[0] + "."
            y_keys = sorted(k for k in props if k.startswith(prefix) and k != x_key and isinstance(props[k], list))

        series = []
        for y_key in y_keys:
            y_values = props.get(y_key)
            if isinstance(y_values, list) and len(y_values) == len(x_values):
                series.append({"key": y_key, "values": y_values})

        if not series:
            return None

        return {
            "name": node.name,
            "x_key": x_key,
            "x_values": x_values,
            "series": series,
        }

    def get_array_grid_data(
        self,
        x_key: str,
        y_key: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """全GOノードの配列プロパティをグリッドプロット用に返す"""
        results: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            ext_keys = node.properties.get(EXT_KEYS_FIELD)
            has_inline = isinstance(node.properties.get(x_key), list)
            if not has_inline and not (isinstance(ext_keys, list) and x_key in ext_keys):
                continue

            props = self._gq._resolve_node_properties(node)

            x_vals = props.get(x_key)
            y_vals = props.get(y_key)
            if not isinstance(x_vals, list) or not isinstance(y_vals, list):
                continue
            if len(x_vals) != len(y_vals):
                continue

            row = self._node_to_row(node)
            if filters and not self._matches_filters(row, filters):
                continue

            display_name = self._get_display_name(node)
            results.append(
                {
                    "node_id": node.id,
                    "name": node.name,
                    "display_name": display_name,
                    "index": props.get("index", ""),
                    "version": props.get("version", ""),
                    "x_values": x_vals,
                    "y_values": y_vals,
                    "properties": {
                        k: v for k, v in props.items() if k != "path" and not (isinstance(v, list) and "." in k)
                    },
                }
            )

        return results

    def get_filtered_property_keys(self) -> list[str]:
        """グローバルカラム設定でフィルタされたプロパティキー一覧"""
        all_keys = self.get_property_keys()
        if not self._global_columns:
            return all_keys
        filtered: list[str] = []
        seen: set[str] = set()
        for pattern in self._global_columns:
            for k in all_keys:
                if k not in seen and fnmatch.fnmatch(k, pattern):
                    filtered.append(k)
                    seen.add(k)
        return filtered

    # ------------------------------------------------------------------
    # Provider 内部ヘルパー（vocab/units/verbose_name 関連）
    # ------------------------------------------------------------------

    def _node_to_row(self, node: Node) -> dict[str, Any]:
        """Node を行 dict に変換し、verbose_name を付与する。

        汎用的な行整形は GraphQuery.nodes_to_rows に委譲し、ここでは
        vocab依存の verbose_name のみを後付けする。
        """
        row = self._gq.nodes_to_rows([node])[0]
        row[self._verbose_name_key] = self._get_display_name(node)
        return row

    def _matches_filters(self, row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """行がフィルタ条件に一致するか判定（vocab マッピング込み）。

        bool値はYAML由来(True/False)と文字列("true"/"false")の両方に対応。
        self.vocab でキーをmappingしてから判定する。
        """
        mapped = self._get_vocab_mapped_filters(filters)
        if mapped is None:
            return True
        return self._gq._match_row(row, mapped)

    def _get_vocab_mapped_filters(self, filters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """filtersのキーを生キーに正規化する"""
        if filters is None:
            return filters
        from modules.vocab_display import reverse_vocab

        rev = reverse_vocab(self.vocab)
        return {rev.get(k, k): v for k, v in filters.items()}

    def _get_display_name(self, node: Node) -> str:
        """ノードの表示名を取得（verbose_nameプロパティ参照、なければnode.name）"""
        display = node.properties.get(self._verbose_name_key)
        if display:
            return str(display)
        display = node.properties.get("verbose_name")
        if display:
            return str(display)
        return node.name

    def _collect_columns(self, rows: list[dict[str, Any]]) -> list[str]:
        """行データからカラムリストを収集（vocab順）"""
        fixed = ["id", "name", "type", "format"]
        dynamic: set[str] = set()
        seen: set[str] = set(fixed)
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    dynamic.add(key)
        return fixed + self._sort_by_vocab(dynamic)
