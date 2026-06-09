"""GraphQuery: GraphModel に対する汎用クエリ + データ供給クラス

dashboard / api 共通の問い合わせ層。汎用クエリ（query_nodes / query_relations /
nodes_to_rows / apply_view）に加えて、旧 DashboardDataProvider が担っていた
go_ ノード向けのデータ供給メソッド（get_go_table / get_array_plot_data /
get_output_images / get_status_summary 等）と vocab/units の表示変換を統合する。

UI（streamlit / pandas / plotly）には依存しない。表示は services/dashboard/ の
UI層が本クラスの戻り値を描画する。

主な公開メソッド:
    クエリ:
        query_nodes(filters)         — Node 単位の絞り込み
        query_relations(node_id, ..) — リレーション抽出 (方向指定可)
        nodes_to_rows(nodes, ..)     — Node → 行 dict 変換
        apply_view(rows, ..)         — 保存ビュー filters + (idx,ver) ソート適用
    データ供給（go_ ノード中心）:
        get_go_table / get_plot_data / get_array_plot_data / get_array_grid_data /
        get_output_images / get_property_images / get_status_summary /
        get_node_card / get_related_files /
        get_property_keys / get_filtered_property_keys / to_dashboard_json

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import fnmatch
import math
import posixpath
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jj_types import GraphModel, Node, Relation
from services.graph.query.filters import apply_saved_view_filters
from services.graph.query.sort import sort_rows_by_index

EXT_KEYS_FIELD = "_ext_keys"


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


def format_float_value(value: float) -> str | float:
    """float値を表示用にフォーマット

    絶対値が1e4以上または1e-2未満（0を除く）の場合、
    指数表示で小数2桁にフォーマットする。
    """
    if not isinstance(value, (int, float)):
        return value
    if isinstance(value, bool):
        return value
    fval = float(value)
    if math.isnan(fval) or math.isinf(fval):
        return value
    abs_val = abs(fval)
    if abs_val == 0:
        return value
    if abs_val >= 1e4 or abs_val < 1e-2:
        return f"{fval:.2e}"
    return value


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v)


def _is_boollike(v: Any) -> bool:
    return isinstance(v, bool) or (isinstance(v, str) and v.strip().lower() in ("true", "false"))


class GraphQuery:
    """GraphModel への問い合わせ + 行整形 + データ供給

    Args:
        graph: 対象 GraphModel
        storage: 外部化プロパティ解決用 (CacheProvider / GraphStorage)。
                 None かつ project_root 指定時は GraphStorage() を自動生成する。
        project_root: storage が解決パスを必要とする場合に使用。
        vocab: config.vocab マッピング（キー/値の表示翻訳・列ソート順）
        units: config.export.units マッピング（列名への単位付加用）
        global_columns: グローバルカラム設定（globパターン対応）
    """

    def __init__(
        self,
        graph: GraphModel,
        storage: Any | None = None,
        project_root: Path | None = None,
        vocab: dict[str, str] | None = None,
        units: dict[str, str] | None = None,
        global_columns: list[str] | None = None,
    ) -> None:
        self.graph = graph
        if storage is None and project_root is not None:
            from services.graph.storage import GraphStorage

            storage = GraphStorage()
        self._storage = storage
        self._project_root = project_root
        self.vocab = vocab or {}
        self.units = units or {}
        self._global_columns = global_columns
        self._verbose_name_key = "verbose_name"
        self._node_by_id: dict[int, Node] = {n.id: n for n in graph.nodes}
        self._relations_by_node: dict[int, list[Relation]] = {}
        for r in graph.relations:
            self._relations_by_node.setdefault(r.node1_id, []).append(r)
            self._relations_by_node.setdefault(r.node2_id, []).append(r)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query_nodes(self, filters: dict[str, Any] | None = None) -> list[Node]:
        """属性 + properties で絞り込んだ Node リストを返す。

        フィルタキーは Node の標準フィールド (type/name/format/category) を
        最優先し、それ以外は properties[key] とマッチする。値が list の場合は
        in 判定、bool/bool文字列の場合は truthy 正規化して比較する。
        """
        if not filters:
            return list(self.graph.nodes)
        result: list[Node] = []
        for node in self.graph.nodes:
            if self._match_node(node, filters):
                result.append(node)
        return result

    def query_relations(
        self,
        node_id: int,
        label: str | None = None,
        direction: str = "both",
    ) -> list[Relation]:
        """ノードIDを起点としたリレーション抽出。

        Args:
            node_id: 起点ノードID
            label: ラベル一致でフィルタ (Noneなら全ラベル)
            direction: "outgoing" (node1_id起点) / "incoming" (node2_id起点) / "both"
        """
        rels = self._relations_by_node.get(node_id, [])
        out: list[Relation] = []
        for r in rels:
            if label is not None and r.label != label:
                continue
            if direction == "outgoing" and r.node1_id != node_id:
                continue
            if direction == "incoming" and r.node2_id != node_id:
                continue
            out.append(r)
        return out

    def nodes_to_rows(
        self,
        nodes: list[Node],
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Node を dict 行に変換する。

        固定列: id, name, type, format。properties を path を除いて展開し、
        float は format_float_value を適用する。_ext_keys が存在し storage が
        利用可能ならオンデマンドで解決する。related_files (純グラフ情報) も
        付与する。verbose_name は付けない (Provider が後付け)。

        Args:
            nodes: 対象ノードリスト
            columns: 指定時は固定列(id/name/type/format)+columnsの組のみ保持
        """
        rows: list[dict[str, Any]] = []
        for node in nodes:
            self._resolve_node_properties(node)
            row: dict[str, Any] = {
                "id": node.id,
                "name": node.name,
                "type": node.type,
                "format": node.format,
            }
            for key, value in node.properties.items():
                if key == "path":
                    continue
                row[key] = format_float_value(value) if isinstance(value, float) else value

            related: list[dict[str, str]] = []
            for rel in self._relations_by_node.get(node.id, []):
                if rel.node1_id != node.id:
                    continue
                other = self._node_by_id.get(rel.node2_id)
                if other:
                    related.append({"name": other.name, "relation": rel.label})
            if related:
                row["related_files"] = related

            if columns is not None:
                fixed = {"id", "name", "type", "format"}
                keep = fixed | set(columns)
                row = {k: v for k, v in row.items() if k in keep}

            rows.append(row)
        return rows

    def apply_view(
        self,
        rows: list[dict[str, Any]],
        view_filters: dict[str, Any] | None = None,
        sort: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """保存ビューの filters と (idx_key, ver_key) ソートを適用する。"""
        out = apply_saved_view_filters(rows, view_filters or {})
        if sort:
            out = sort_rows_by_index(out, sort[0], sort[1])
        return out

    # ------------------------------------------------------------------
    # Internal helpers (used by Provider as well)
    # ------------------------------------------------------------------

    def _resolve_node_properties(self, node: Node) -> dict[str, Any]:
        """外部化プロパティをオンデマンドで解決してノードのプロパティを返す。

        _ext_keys マーカーが存在し storage が利用可能なら、外部化プロパティを
        ロードしてノードの properties に in-place マージする。
        """
        ext_keys = node.properties.get(EXT_KEYS_FIELD)
        if not ext_keys:
            return node.properties
        if self._storage is None or self._project_root is None:
            return node.properties
        ext_props = self._storage.load_node_properties(self._project_root, node.id)
        if ext_props:
            node.properties.update(ext_props)
            node.properties.pop(EXT_KEYS_FIELD, None)
        return node.properties

    def _has_ext_keys(self, node: Node) -> bool:
        return bool(node.properties.get(EXT_KEYS_FIELD))

    def _match_row(self, row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """row が filters に一致するか判定 (vocab 非依存版)。

        `_matches_filters` の vocab マッピングを除いた中核ロジック。
        bool/bool 文字列値は truthy 正規化、list 値は in 判定。
        """
        for key, value in filters.items():
            row_value = row.get(key)
            if row_value is None:
                return False
            if isinstance(value, list):
                if row_value not in value:
                    return False
            elif _is_boollike(value):
                if _to_bool(row_value) != _to_bool(value):
                    return False
            elif row_value != value:
                return False
        return True

    def _match_node(self, node: Node, filters: dict[str, Any]) -> bool:
        """Node が filters に一致するか判定 (標準フィールド + properties)。"""
        for key, value in filters.items():
            if key == "type":
                node_value: Any = node.type
            elif key == "name":
                node_value = node.name
            elif key == "format":
                node_value = node.format
            elif key == "category":
                node_value = getattr(node.category, "value", node.category)
            else:
                node_value = node.properties.get(key)
            if node_value is None:
                return False
            if isinstance(value, list):
                if node_value not in value:
                    return False
            elif _is_boollike(value):
                if _to_bool(node_value) != _to_bool(value):
                    return False
            elif node_value != value:
                return False
        return True

    # ------------------------------------------------------------------
    # データ供給 API（go_ ノード中心。旧 DashboardDataProvider を統合）
    # ------------------------------------------------------------------

    def get_go_table(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """go_ ファイルのテーブルデータ（プロパティ展開済み + verbose_name）"""
        rows: list[dict[str, Any]] = []
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            row = self._node_to_row(node)
            if filters and not self._matches_filters(row, filters):
                continue
            rows.append(row)
        return rows

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
        for rel in self.query_relations(node_id):
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

    def get_status_summary(self) -> dict[str, Any]:
        """実行ステータスサマリー（go_ ノード集計 + CPU/警告統計）"""
        total = completed = failed = unknown = 0
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

            item: dict[str, Any] = {"name": node.name, "analysis_status": status}
            if "cpu_time" in node.properties:
                item["cpu_time"] = node.properties["cpu_time"]
                item["errors"] = (
                    node.properties.get("sta_errors", [])
                    + node.properties.get("msg_errors", [])
                    + node.properties.get("dat_errors", [])
                )
                item["warnings"] = (
                    node.properties.get("sta_warnings", [])
                    + node.properties.get("msg_warnings", [])
                    + node.properties.get("dat_warnings", [])
                )
            items.append(item)

        cpu_times = [i["cpu_time"] for i in items if i.get("cpu_time") is not None]
        cpu_stats: dict[str, Any] = {}
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

        warning_counts = [i["warnings"] for i in items if isinstance(i.get("warnings"), (int, float))]
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

    def get_related_files(self, node_id: int, label: str | None = None) -> list[dict[str, Any]]:
        """関連ファイル一覧（リレーションラベルで絞り込み可）"""
        related: list[dict[str, Any]] = []
        for rel in self.query_relations(node_id, label=label):
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
        """dashboard-json 形式のエクスポートデータを生成"""
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

    def get_output_images(self, node_id: int | None = None) -> list[dict[str, Any]]:
        """画像出力ファイル一覧（has_output 関係から取得）"""
        image_formats = {"png", "gif", "jpg", "jpeg", "bmp", "svg", "tiff"}
        results: list[dict[str, Any]] = []

        if node_id is not None:
            node = self._node_by_id.get(node_id)
            target_nodes = [node] if node is not None else []
        else:
            target_nodes = [n for n in self.graph.nodes if _is_go_node(n)]

        for go_node in target_nodes:
            for rel in self.query_relations(go_node.id, label="has_output", direction="outgoing"):
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

    def get_property_images(self, daily_notes_dir: str = "notes/daily") -> list[dict[str, Any]]:
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
                        results, node, display_name, value, go_props, image_extensions, daily_notes_dir
                    )
                    continue
                GraphQuery.extract_image_paths(
                    results, node, display_name, key, value, go_props, image_extensions
                )
        return results

    def get_array_property_keys(self) -> list[str]:
        """go_ ノードの配列型プロパティキー（PREFIX.列名形式）を返す（外部化考慮）"""
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
        props = self._resolve_node_properties(node)
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
        return {"name": node.name, "x_key": x_key, "x_values": x_values, "series": series}

    def get_array_grid_data(
        self,
        x_key: str,
        y_key: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """全 GO ノードの配列プロパティをグリッドプロット用に返す"""
        results: list[dict[str, Any]] = []
        for node in self.graph.nodes:
            if not _is_go_node(node):
                continue
            ext_keys = node.properties.get(EXT_KEYS_FIELD)
            has_inline = isinstance(node.properties.get(x_key), list)
            if not has_inline and not (isinstance(ext_keys, list) and x_key in ext_keys):
                continue
            props = self._resolve_node_properties(node)
            x_vals = props.get(x_key)
            y_vals = props.get(y_key)
            if not isinstance(x_vals, list) or not isinstance(y_vals, list):
                continue
            if len(x_vals) != len(y_vals):
                continue
            row = self._node_to_row(node)
            if filters and not self._matches_filters(row, filters):
                continue
            results.append(
                {
                    "node_id": node.id,
                    "name": node.name,
                    "display_name": self._get_display_name(node),
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

    # ---- データ供給 内部ヘルパー（vocab/units/verbose_name） ----

    def _node_to_row(self, node: Node) -> dict[str, Any]:
        """Node を行 dict に変換し verbose_name を付与する。"""
        row = self.nodes_to_rows([node])[0]
        row[self._verbose_name_key] = self._get_display_name(node)
        return row

    def _matches_filters(self, row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """行がフィルタ条件に一致するか判定（vocab マッピング込み）。"""
        mapped = self._get_vocab_mapped_filters(filters)
        if mapped is None:
            return True
        return self._match_row(row, mapped)

    def _get_vocab_mapped_filters(self, filters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """filters のキーを生キーに正規化する"""
        if filters is None:
            return filters
        from modules.vocab_display import reverse_vocab

        rev = reverse_vocab(self.vocab)
        return {rev.get(k, k): v for k, v in filters.items()}

    def _get_display_name(self, node: Node) -> str:
        """ノードの表示名（verbose_name プロパティ参照、なければ node.name）"""
        display = node.properties.get(self._verbose_name_key)
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

    # ---- image extraction (gallery 系のうち純グラフ情報からの抽出) ----

    @staticmethod
    def extract_image_paths(
        results: list[dict[str, Any]],
        node: Node,
        display_name: str,
        key: str,
        value: Any,
        go_props: dict[str, Any],
        image_extensions: set[str],
    ) -> None:
        """値から画像パスを抽出して results に追加する。"""
        candidates: list[str] = []
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [v for v in value if isinstance(v, str)]

        for candidate in candidates:
            if "." not in candidate:
                continue
            ext = candidate.rsplit(".", 1)[-1].lower()
            if ext in image_extensions:
                results.append(
                    {
                        "go_node_id": node.id,
                        "go_node_name": node.name,
                        "display_name": display_name,
                        "property_key": key,
                        "image_path": candidate,
                        "image_format": ext,
                        "go_properties": go_props,
                    }
                )

    @staticmethod
    def extract_daily_note_images(
        results: list[dict[str, Any]],
        node: Node,
        display_name: str,
        daily_notes: dict[str, Any],
        go_props: dict[str, Any],
        image_extensions: set[str],
        daily_notes_dir: str,
    ) -> None:
        """daily_notes dict 内から画像パスを抽出する。"""
        for date_key, props in daily_notes.items():
            if not isinstance(props, dict):
                continue
            for key, value in props.items():
                candidates: list[str] = []
                if isinstance(value, str):
                    candidates = [value]
                elif isinstance(value, list):
                    candidates = [v for v in value if isinstance(v, str)]

                for candidate in candidates:
                    if "." not in candidate:
                        continue
                    ext = candidate.rsplit(".", 1)[-1].lower()
                    if ext in image_extensions:
                        resolved = posixpath.normpath(posixpath.join(daily_notes_dir, candidate))
                        results.append(
                            {
                                "go_node_id": node.id,
                                "go_node_name": node.name,
                                "display_name": display_name,
                                "property_key": f"daily:{date_key}:{key}",
                                "image_path": resolved,
                                "image_format": ext,
                                "go_properties": go_props,
                            }
                        )
