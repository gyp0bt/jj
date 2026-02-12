"""ダッシュボード向けデータ供給クラス

GraphModelを受け取り、テーブル/カード/プロット/ステータスの
各ビュー向けデータ構造に変換する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from jj_types import GraphModel, Node, Relation


class DashboardDataProvider:
    """ダッシュボード向けデータ供給

    GraphModelを受け取り、各ビューに最適化したデータ構造を返す。

    Args:
        graph: 対象のGraphModel
        vocab: config.vocabマッピング（キー/値の翻訳用）
        units: config.export.unitsマッピング（カラム名への単位付加用）
    """

    def __init__(
        self,
        graph: GraphModel,
        vocab: dict[str, str] | None = None,
        units: dict[str, str] | None = None,
    ) -> None:
        self.graph = graph
        self.vocab = vocab or {}
        self.units = units or {}
        self._node_by_id: dict[int, Node] = {n.id: n for n in graph.nodes}
        self._relations_by_node: dict[int, list[Relation]] = {}
        for r in graph.relations:
            self._relations_by_node.setdefault(r.node1_id, []).append(r)
            self._relations_by_node.setdefault(r.node2_id, []).append(r)

    def get_go_table(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """go_ファイルのテーブルデータ（プロパティ展開済み）

        Args:
            filters: フィルタ条件 {"type": "go", "active": True, ...}

        Returns:
            行データのリスト。各行は展開済みプロパティを含むdict。
        """
        rows: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            row = self._node_to_row(node)

            if filters and not self._matches_filters(row, filters):
                continue

            rows.append(row)

        return rows

    def get_node_card(self, node_id: int) -> dict[str, Any] | None:
        """ノード詳細カード（関連ノード含む）

        Args:
            node_id: 対象ノードのID

        Returns:
            ノード詳細の辞書。ノードが見つからない場合はNone。
        """
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

        for rel in self._relations_by_node.get(node_id, []):
            other_id = rel.node2_id if rel.node1_id == node_id else rel.node1_id
            other_node = self._node_by_id.get(other_id)
            card["relations"].append({
                "label": rel.label,
                "direction": "outgoing" if rel.node1_id == node_id else "incoming",
                "node_id": other_id,
                "node_name": other_node.name if other_node else str(other_id),
                "node_type": other_node.type if other_node else "unknown",
            })

        return card

    def get_plot_data(
        self,
        x_key: str,
        y_key: str,
        color_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """プロット用データ（数値プロパティのみ）

        Args:
            x_key: X軸プロパティキー
            y_key: Y軸プロパティキー
            color_key: 色分けプロパティキー

        Returns:
            プロット用データポイントのリスト
        """
        points: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
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
                "id": node.id,
                x_key: x_num,
                y_key: y_num,
            }

            if color_key:
                point[color_key] = node.properties.get(color_key, "")

            points.append(point)

        return points

    def get_property_keys(self) -> list[str]:
        """利用可能なプロパティキー一覧

        go_ノードのプロパティキーを集約して返す。

        Returns:
            ソート済みキーリスト
        """
        keys: set[str] = set()
        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue
            keys.update(node.properties.keys())

        # 内部キー（path等）は除外
        internal_keys = {"path", "include_properties"}
        keys -= internal_keys

        return sorted(keys)

    def get_status_summary(self) -> dict[str, Any]:
        """実行ステータスサマリー

        Returns:
            {
                "total": int,
                "completed": int,
                "failed": int,
                "running": int,
                "unknown": int,
                "items": [{"name": str, "status": str, ...}, ...]
            }
        """
        total = 0
        completed = 0
        failed = 0
        unknown = 0
        items: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
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
            if "sta_errors" in node.properties:
                item["errors"] = node.properties["sta_errors"]
            if "sta_warnings" in node.properties:
                item["warnings"] = node.properties["sta_warnings"]

            items.append(item)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "unknown": unknown,
            "items": items,
        }

    def get_related_files(
        self,
        node_id: int,
        label: str | None = None,
    ) -> list[dict[str, Any]]:
        """関連ファイル一覧

        Args:
            node_id: 対象ノードのID
            label: リレーションラベルでフィルタ（省略時は全件）

        Returns:
            関連ノード情報のリスト
        """
        related: list[dict[str, Any]] = []

        for rel in self._relations_by_node.get(node_id, []):
            if label and rel.label != label:
                continue

            other_id = rel.node2_id if rel.node1_id == node_id else rel.node1_id
            other_node = self._node_by_id.get(other_id)
            if other_node is None:
                continue

            related.append({
                "id": other_node.id,
                "name": other_node.name,
                "type": other_node.type,
                "format": other_node.format,
                "label": rel.label,
                "direction": "outgoing" if rel.node1_id == node_id else "incoming",
            })

        return related

    def to_dashboard_json(self, project_name: str = "") -> dict[str, Any]:
        """dashboard-json形式のエクスポートデータを生成

        テーブルビューに最適化したフラットなJSON構造を返す。

        Args:
            project_name: プロジェクト名

        Returns:
            dashboard-json形式の辞書
        """
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
        """画像出力ファイル一覧（has_output関係から取得）

        has_output関係で結ばれたノードのうち、画像フォーマット
        （png, gif, jpg, jpeg, bmp, svg, tiff）のものを返す。

        Args:
            node_id: 対象go_ノードID（省略時は全go_ノード）

        Returns:
            画像情報のリスト。各要素:
            {
                "go_node_id": int,
                "go_node_name": str,
                "image_node_id": int,
                "image_name": str,
                "image_path": str,
                "image_format": str,
                "go_properties": dict,
            }
        """
        image_formats = {"png", "gif", "jpg", "jpeg", "bmp", "svg", "tiff"}
        results: list[dict[str, Any]] = []

        target_nodes: list[Node] = []
        if node_id is not None:
            node = self._node_by_id.get(node_id)
            if node is not None:
                target_nodes = [node]
        else:
            for n in self.graph.nodes:
                name_lower = n.name.lower()
                if name_lower.startswith("go_") or name_lower == "go":
                    target_nodes.append(n)

        for go_node in target_nodes:
            for rel in self._relations_by_node.get(go_node.id, []):
                if rel.label != "has_output":
                    continue
                if rel.node1_id != go_node.id:
                    continue

                output_node = self._node_by_id.get(rel.node2_id)
                if output_node is None:
                    continue

                # フォーマットまたはパス拡張子で画像判定
                fmt = output_node.format.lower() if output_node.format else ""
                path_str = output_node.properties.get("path", "")
                ext = path_str.rsplit(".", 1)[-1].lower() if "." in path_str else ""

                if fmt not in image_formats and ext not in image_formats:
                    continue

                results.append({
                    "go_node_id": go_node.id,
                    "go_node_name": go_node.name,
                    "image_node_id": output_node.id,
                    "image_name": output_node.name,
                    "image_path": path_str,
                    "image_format": fmt or ext,
                    "go_properties": {
                        k: v
                        for k, v in go_node.properties.items()
                        if k not in ("path", "include_properties")
                    },
                })

        return results

    def get_property_images(self) -> list[dict[str, Any]]:
        """プロパティに画像ファイルパスを持つノードの画像情報を取得

        Obsidianのdaily note経由でプロパティに画像ファイルパスが
        割り当てられたノードを検出し、画像情報を返す。

        Returns:
            画像情報のリスト。各要素:
            {
                "go_node_id": int,
                "go_node_name": str,
                "property_key": str,
                "image_path": str,
                "image_format": str,
                "go_properties": dict,
            }
        """
        image_extensions = {"png", "gif", "jpg", "jpeg", "bmp", "svg", "tiff"}
        results: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            go_props = {
                k: v
                for k, v in node.properties.items()
                if k not in ("path", "include_properties")
            }

            for key, value in node.properties.items():
                if key in ("path", "include_properties"):
                    continue
                self._extract_image_paths(
                    results, node, key, value, go_props, image_extensions
                )

        return results

    @staticmethod
    def _extract_image_paths(
        results: list[dict[str, Any]],
        node: Node,
        key: str,
        value: Any,
        go_props: dict[str, Any],
        image_extensions: set[str],
    ) -> None:
        """値から画像パスを抽出してresultsに追加"""
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
                results.append({
                    "go_node_id": node.id,
                    "go_node_name": node.name,
                    "property_key": key,
                    "image_path": candidate,
                    "image_format": ext,
                    "go_properties": go_props,
                })

    # ---- private ----

    def _node_to_row(self, node: Node) -> dict[str, Any]:
        """ノードをテーブル行に変換（プロパティ展開）"""
        row: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
            "type": node.type,
            "format": node.format,
        }

        for key, value in node.properties.items():
            if key == "path":
                continue
            if key == "include_properties":
                continue
            row[key] = value

        # 関連ファイル情報を追加
        related = []
        for rel in self._relations_by_node.get(node.id, []):
            if rel.node1_id != node.id:
                continue
            other = self._node_by_id.get(rel.node2_id)
            if other:
                related.append({
                    "name": other.name,
                    "relation": rel.label,
                })
        if related:
            row["related_files"] = related

        return row

    @staticmethod
    def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """行がフィルタ条件に一致するか判定"""
        for key, value in filters.items():
            row_value = row.get(key)
            if row_value is None:
                return False
            if isinstance(value, list):
                if row_value not in value:
                    return False
            elif row_value != value:
                return False
        return True

    @staticmethod
    def _collect_columns(rows: list[dict[str, Any]]) -> list[str]:
        """行データからカラムリストを収集"""
        fixed = ["id", "name", "type", "format"]
        dynamic: list[str] = []
        seen: set[str] = set(fixed)

        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    dynamic.append(key)

        return fixed + sorted(dynamic)
