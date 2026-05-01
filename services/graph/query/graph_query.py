"""GraphQuery: GraphModel に対する汎用クエリクラス

dashboard / api 共通の薄い問い合わせ層。vocab/units/verbose_name は持たず、
プレゼンテーション層 (DashboardDataProvider) で適用する。

公開メソッド:
    query_nodes(filters)         — Node 単位の絞り込み
    query_relations(node_id, ..) — リレーション抽出 (方向指定可)
    nodes_to_rows(nodes, ..)     — Node → 行 dict 変換 (固定列+properties展開+
                                    related_files 付与+外部化プロパティ解決)
    apply_view(rows, ..)         — 保存ビュー filters + (idx,ver) ソート適用

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import math
import posixpath
from pathlib import Path
from typing import Any

from jj_types import GraphModel, Node, Relation
from services.graph.query.filters import apply_saved_view_filters
from services.graph.query.sort import sort_rows_by_index

EXT_KEYS_FIELD = "_ext_keys"


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
    """GraphModel への問い合わせ + 行整形 (vocab非依存)

    Args:
        graph: 対象 GraphModel
        storage: 外部化プロパティ解決用 (CacheProvider / GraphStorage)。
                 None の場合は外部化解決をスキップ。
        project_root: storage が解決パスを必要とする場合に使用。
    """

    def __init__(
        self,
        graph: GraphModel,
        storage: Any | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.graph = graph
        self._storage = storage
        self._project_root = project_root
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

        DashboardDataProvider._matches_filters の vocab マッピングを除いた
        中核ロジック。bool/bool 文字列値は truthy 正規化、list 値は in 判定。
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
