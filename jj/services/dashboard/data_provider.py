"""ダッシュボード向けデータ供給クラス（汎用）

GraphModelを受け取り、テーブル/カード/プロット/ステータスの
各ビュー向けデータ構造に変換する。
ソフトウェア固有のデータ供給（例: Abaqus物性テーブル）は
services/dashboard/connectors/ のコネクターに移動済み。
float値は桁数が大きい場合に指数表示（小数2桁）でフォーマットする。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch
import math
from datetime import datetime, timezone
from typing import Any

from jj_types import GraphModel, Node, Relation


def format_float_value(value: float) -> str | float:
    """float値を表示用にフォーマット

    絶対値が1e4以上または1e-2未満（0を除く）の場合、
    指数表示で小数2桁にフォーマットする。
    それ以外はそのまま返す。

    Args:
        value: フォーマット対象のfloat値

    Returns:
        フォーマット済み文字列 or 元の値
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


class DashboardDataProvider:
    """ダッシュボード向けデータ供給

    GraphModelを受け取り、各ビューに最適化したデータ構造を返す。

    表示名（verbose_name）はparse時にDisplayNameParserが生成・格納済みのため、
    ダッシュボード側ではverbose_nameプロパティを参照するだけでよい。

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
    ) -> None:
        self.graph = graph
        self.vocab = vocab or {}
        self.units = units or {}
        self._verbose_name_format = verbose_name_format  # 後方互換のため保持
        self._global_columns = global_columns
        self._node_by_id: dict[int, Node] = {n.id: n for n in graph.nodes}
        self._relations_by_node: dict[int, list[Relation]] = {}
        for r in graph.relations:
            self._relations_by_node.setdefault(r.node1_id, []).append(r)
            self._relations_by_node.setdefault(r.node2_id, []).append(r)

        # verbose_nameのvocab変換後キー名を特定（例: "表示名"）
        self._verbose_name_key = self.vocab.get("verbose_name", "verbose_name")

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
        """プロット用データ（数値プロパティのみ）

        Args:
            x_key: X軸プロパティキー
            y_key: Y軸プロパティキー
            color_key: 色分けプロパティキー
            extra_keys: 追加で含めるプロパティキー（グループ結線キー等）

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
                self._verbose_name_key: self._get_display_name(node),
                "id": node.id,
                x_key: x_num,
                y_key: y_num,
            }

            if color_key:
                point[color_key] = node.properties.get(color_key, "")

            # 追加キー（グループ結線キー等）をデータに含める
            if extra_keys:
                for ek in extra_keys:
                    if ek not in point:
                        point[ek] = node.properties.get(ek, "")

            points.append(point)

        return points

    def get_property_keys(self) -> list[str]:
        """利用可能なプロパティキー一覧（vocab順）

        go_ノードのプロパティキーを集約して返す。
        vocab辞書の値の定義順序で優先的にソートし、
        vocabに含まれないキーは文字列昇順で後に配置する。

        Returns:
            vocab順→文字列昇順のキーリスト
        """
        keys: set[str] = set()
        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue
            keys.update(node.properties.keys())

        # 内部キー（path等）は除外
        internal_keys = {"path"}
        keys -= internal_keys

        return self._sort_by_vocab(keys)

    def _sort_by_vocab(self, keys: set[str] | list[str]) -> list[str]:
        """vocab順でキーをソート

        vocab辞書の値（日本語表記）の出現順を優先し、
        vocabに含まれないキーは文字列昇順で後に配置する。

        Args:
            keys: ソート対象のキー集合

        Returns:
            vocab順→文字列昇順のリスト
        """
        # vocabの値（翻訳後キー名）の順序マップを構築
        vocab_order: dict[str, int] = {}
        for idx, v in enumerate(self.vocab.values()):
            if v not in vocab_order:
                vocab_order[v] = idx
        # vocabのキー（翻訳前）も順序に含める
        for idx, k in enumerate(self.vocab.keys()):
            if k not in vocab_order:
                vocab_order[k] = len(self.vocab) + idx

        in_vocab = [k for k in keys if k in vocab_order]
        not_in_vocab = [k for k in keys if k not in vocab_order]

        in_vocab.sort(key=lambda k: vocab_order[k])
        not_in_vocab.sort()

        return in_vocab + not_in_vocab

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
        """プロパティに画像ファイルパスを持つノードの画像情報を取得

        Obsidianのdaily note経由でプロパティに画像ファイルパスが
        割り当てられたノードを検出し、画像情報を返す。
        daily_notes dict内の画像パスはdaily_notes_dir基準の相対パスとして
        解釈し、プロジェクトルート基準のパスに変換して返す。

        Args:
            daily_notes_dir: daily noteディレクトリ（プロジェクトルート基準）

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

            go_props = {k: v for k, v in node.properties.items() if k != "path"}
            display_name = self._get_display_name(node)

            for key, value in node.properties.items():
                if key == "path":
                    continue
                # daily_notes dict内の画像パスを探索
                if key == "daily_notes" and isinstance(value, dict):
                    self._extract_daily_note_images(
                        results,
                        node,
                        display_name,
                        value,
                        go_props,
                        image_extensions,
                        daily_notes_dir,
                    )
                    continue
                self._extract_image_paths(results, node, display_name, key, value, go_props, image_extensions)

        return results

    @staticmethod
    def _extract_daily_note_images(
        results: list[dict[str, Any]],
        node: Node,
        display_name: str,
        daily_notes: dict[str, Any],
        go_props: dict[str, Any],
        image_extensions: set[str],
        daily_notes_dir: str,
    ) -> None:
        """daily_notes dict内から画像パスを抽出

        daily_notes構造: {date: {key: value, ...}, ...}
        画像パスはdaily note基準の相対パスとして扱い、
        daily_notes_dirを付加してプロジェクトルート基準に変換する。
        """
        import posixpath

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
                        # daily note基準の相対パスをプロジェクトルート基準に変換
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

    @staticmethod
    def _extract_image_paths(
        results: list[dict[str, Any]],
        node: Node,
        display_name: str,
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

    def get_array_property_keys(self) -> list[str]:
        """go_ノードの配列型プロパティキーを返す

        「PREFIX.列名」形式（例: RF.time, RF.RF3）のプロパティキーを
        抽出してソート済みリストで返す。

        Returns:
            ソート済みの配列プロパティキーリスト
        """
        keys: set[str] = set()
        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue
            for key, value in node.properties.items():
                if "." in key and isinstance(value, list):
                    keys.add(key)
        return sorted(keys)

    def get_array_plot_data(
        self,
        node_id: int,
        x_key: str,
        y_keys: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """特定ノードの配列プロパティをプロット用データに変換

        Args:
            node_id: GOノードID
            x_key: X軸の配列プロパティキー（例: "RF.time"）
            y_keys: Y軸の配列プロパティキー群（例: ["RF.RF1", "RF.RF3"]）
                    省略時はx_keyと同じ接頭辞の全列を使用

        Returns:
            {
                "name": str,
                "x_key": str,
                "x_values": list[float],
                "series": [{"key": str, "values": list[float]}, ...],
            }
            ノードが見つからない場合はNone
        """
        node = self._node_by_id.get(node_id)
        if node is None:
            return None

        x_values = node.properties.get(x_key)
        if not isinstance(x_values, list):
            return None

        # y_keysが未指定の場合、x_keyと同じ接頭辞の全キーを使用
        if y_keys is None:
            prefix = x_key.split(".")[0] + "."
            y_keys = sorted(
                k
                for k in node.properties
                if k.startswith(prefix) and k != x_key and isinstance(node.properties[k], list)
            )

        series = []
        for y_key in y_keys:
            y_values = node.properties.get(y_key)
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
        """全GOノードの配列プロパティをグリッドプロット用に返す

        indexごとに配列データを収集し、グリッド配置で並べるためのリストを返す。

        Args:
            x_key: X軸配列キー
            y_key: Y軸配列キー
            filters: フィルタ条件

        Returns:
            [{
                "node_id": int,
                "name": str,
                "index": str,
                "x_values": list[float],
                "y_values": list[float],
                "properties": dict,
            }, ...]
        """
        results: list[dict[str, Any]] = []

        for node in self.graph.nodes:
            name_lower = node.name.lower()
            if not (name_lower.startswith("go_") or name_lower == "go"):
                continue

            x_vals = node.properties.get(x_key)
            y_vals = node.properties.get(y_key)
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
                    "index": node.properties.get("index", ""),
                    "version": node.properties.get("version", ""),
                    "x_values": x_vals,
                    "y_values": y_vals,
                    "properties": {
                        k: v
                        for k, v in node.properties.items()
                        if k != "path" and not (isinstance(v, list) and "." in k)
                    },
                }
            )

        return results

    # ---- private ----

    def _get_display_name(self, node: Node) -> str:
        """ノードの表示名を取得

        parse時にDisplayNameParserが生成したverbose_nameプロパティを参照する。
        優先順位:
        1. verbose_nameプロパティ（vocab変換後キー → 変換前キー）
        2. node.name

        Args:
            node: 対象ノード

        Returns:
            表示用の名前文字列
        """
        # vocab変換後のキー（例: "表示名"）で検索
        display = node.properties.get(self._verbose_name_key)
        if display:
            return str(display)
        # 変換前のキーでフォールバック
        display = node.properties.get("verbose_name")
        if display:
            return str(display)
        return node.name

    def get_filtered_property_keys(self) -> list[str]:
        """グローバルカラム設定でフィルタされたプロパティキー一覧

        global_columnsが設定されている場合はglobパターンでフィルタした結果を返す。
        未設定の場合はget_property_keys()と同じ結果を返す。

        Returns:
            フィルタ済みキーリスト
        """
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

    def _node_to_row(self, node: Node) -> dict[str, Any]:
        """ノードをテーブル行に変換（プロパティ展開、float指数表示対応）"""
        row: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
            self._verbose_name_key: self._get_display_name(node),
            "type": node.type,
            "format": node.format,
        }

        for key, value in node.properties.items():
            if key == "path":
                continue
            row[key] = format_float_value(value) if isinstance(value, float) else value

        # 関連ファイル情報を追加
        related = []
        for rel in self._relations_by_node.get(node.id, []):
            if rel.node1_id != node.id:
                continue
            other = self._node_by_id.get(rel.node2_id)
            if other:
                related.append(
                    {
                        "name": other.name,
                        "relation": rel.label,
                    }
                )
        if related:
            row["related_files"] = related

        return row

    @staticmethod
    def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        """行がフィルタ条件に一致するか判定

        bool値はYAML由来(True/False)と文字列("true"/"false")の両方に対応。
        """
        for key, value in filters.items():
            row_value = row.get(key)
            if row_value is None:
                return False
            if isinstance(value, list):
                if row_value not in value:
                    return False
            elif isinstance(value, bool) or (isinstance(value, str) and value.strip().lower() in ("true", "false")):
                # bool/bool文字列の比較は正規化して行う
                def _to_bool(v: Any) -> bool:
                    if isinstance(v, bool):
                        return v
                    if isinstance(v, str):
                        return v.strip().lower() == "true"
                    return bool(v)

                if _to_bool(row_value) != _to_bool(value):
                    return False
            elif row_value != value:
                return False
        return True

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
