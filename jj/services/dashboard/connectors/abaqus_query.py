"""Abaqus物性データ クエリ関数

Abaqus固有のダッシュボードデータ取得ロジック。
Streamlitに依存しない純粋なクエリ関数群を提供する。

abaqus_materialノードの物性テーブル、テーブル型プロパティ、
カーブプロット軸、物性使用関係の取得を担う。

描画ロジック（abaqus.py）から分離して、テスト容易性と
将来のプラグインパッケージ化を実現する。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider


# ====================================================================
# 物性テーブル クエリ
# ====================================================================


def get_material_table(provider: "DashboardDataProvider") -> list[dict[str, Any]]:
    """abaqus_materialノードの物性テーブルデータ

    全abaqus_materialノードの非テーブル型プロパティを
    フラットなテーブル行として返す。テーブル型データ（list[list]）は
    列名だけを表示用に含める。

    Args:
        provider: DashboardDataProvider

    Returns:
        行データのリスト
    """
    rows: list[dict[str, Any]] = []

    for node in provider.graph.nodes:
        if node.type != "abaqus_material":
            continue

        row: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
        }

        for key, value in node.properties.items():
            if key in ("path", "include_properties", "source_file"):
                continue
            # テーブル型データ（list[list]）はサマリのみ
            if isinstance(value, list) and value and isinstance(value[0], list):
                row[key] = f"[{len(value)}行]"
            elif isinstance(value, (dict, list)):
                row[key] = str(value)
            else:
                row[key] = value

        rows.append(row)

    return rows


def get_material_table_data(
    provider: "DashboardDataProvider",
    node_id: int,
    property_key: str,
) -> dict[str, Any] | None:
    """materialノードのテーブル型プロパティデータを取得

    plastic, elastic等のテーブル型データ（list[list[float]]）を返す。

    Args:
        provider: DashboardDataProvider
        node_id: materialノードID
        property_key: プロパティキー（例: "plastic", "elastic"）

    Returns:
        {
            "name": str,
            "property_key": str,
            "data": list[list[float]],
            "keywords": list[str],
        }
        見つからない場合はNone
    """
    node = provider._node_by_id.get(node_id)
    if node is None or node.type != "abaqus_material":
        return None

    value = node.properties.get(property_key)
    if not isinstance(value, list) or not value:
        return None

    # テーブル型（list[list]）かチェック
    if not isinstance(value[0], list):
        return None

    return {
        "name": node.name,
        "property_key": property_key,
        "data": value,
        "keywords": node.properties.get("keywords", []),
    }


def get_material_table_keys(
    provider: "DashboardDataProvider",
    node_id: int,
) -> list[str]:
    """materialノードのテーブル型プロパティキーを返す

    Args:
        provider: DashboardDataProvider
        node_id: materialノードID

    Returns:
        テーブル型プロパティキーのソート済みリスト
    """
    node = provider._node_by_id.get(node_id)
    if node is None or node.type != "abaqus_material":
        return []

    keys: list[str] = []
    for key, value in node.properties.items():
        if isinstance(value, list) and value and isinstance(value[0], list):
            keys.append(key)
    return sorted(keys)


# ====================================================================
# 物性カーブヘルパー
# ====================================================================


def guess_table_column_names(
    property_key: str,
    num_cols: int,
    material_curve_columns: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """テーブル型プロパティの列名をconfig設定から取得

    config.dashboard.material-curve-columnsに定義された列名を使用する。
    configにマッチしない場合はcol_0, col_1, ... で補完する。

    Args:
        property_key: プロパティキー（plastic, elastic等）
        num_cols: 列数
        material_curve_columns: config.dashboard.material-curve-columns

    Returns:
        列名のリスト
    """
    names: list[str] = []
    if material_curve_columns and property_key in material_curve_columns:
        entry = material_curve_columns[property_key]
        names = list(entry.get("columns", []))
    # 不足分はcol_Nで補完
    while len(names) < num_cols:
        names.append(f"col_{len(names)}")
    return names[:num_cols]


def get_curve_plot_axes(
    property_key: str,
    num_cols: int,
    material_curve_columns: dict[str, dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """物性カーブのプロットX/Y軸インデックスをconfigから取得

    configにx/yが指定されている場合はそれを使用。
    未指定の場合はデフォルト（x=0, y=1）を返す。

    Args:
        property_key: プロパティキー
        num_cols: 列数
        material_curve_columns: config.dashboard.material-curve-columns

    Returns:
        (x_index, y_index) タプル
    """
    x_idx = 0
    y_idx = min(1, num_cols - 1)
    if material_curve_columns and property_key in material_curve_columns:
        entry = material_curve_columns[property_key]
        if "x" in entry:
            x_idx = min(int(entry["x"]), num_cols - 1)
        if "y" in entry:
            y_idx = min(int(entry["y"]), num_cols - 1)
    return x_idx, y_idx


def parse_material_curve_columns(
    raw_mcc: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """material-curve-columns設定を正規化

    config.yamlのconnectors.abaqus.material-curve-columnsセクションを
    {property_key: {columns: [...], x: int, y: int}} 形式に正規化する。

    Args:
        raw_mcc: 生の設定辞書

    Returns:
        正規化された設定辞書
    """
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_mcc, dict):
        return result
    for key, val in raw_mcc.items():
        if isinstance(val, dict):
            entry: dict[str, Any] = {}
            cols = val.get("columns", [])
            if isinstance(cols, list):
                entry["columns"] = [str(c) for c in cols]
            else:
                entry["columns"] = []
            if "x" in val:
                entry["x"] = int(val["x"])
            if "y" in val:
                entry["y"] = int(val["y"])
            result[str(key)] = entry
        elif isinstance(val, list):
            # 簡略形式: property_key: [col1, col2]
            result[str(key)] = {
                "columns": [str(c) for c in val],
            }
    return result


# ====================================================================
# 物性-GOノード使用関係
# ====================================================================


def get_material_usage(
    provider: "DashboardDataProvider",
) -> list[dict[str, Any]]:
    """materialノードとgo_ノードの使用関係を取得

    uses_material関係をたどり、各materialがどのgo_ノードで使われているかを返す。

    Returns:
        [{"material_name": str, "material_id": int,
          "go_nodes": [{"name": str, "id": int}, ...]}]
    """
    results: list[dict[str, Any]] = []

    for node in provider.graph.nodes:
        if node.type != "abaqus_material":
            continue

        go_nodes: list[dict[str, Any]] = []
        for rel in provider._relations_by_node.get(node.id, []):
            if rel.label != "uses_material":
                continue
            # uses_material: go_node -> material_node (node1 -> node2)
            go_id = rel.node1_id if rel.node2_id == node.id else rel.node2_id
            if go_id == node.id:
                continue
            go_node = provider._node_by_id.get(go_id)
            if go_node is None:
                continue
            name_lower = go_node.name.lower()
            if name_lower.startswith("go_") or name_lower == "go":
                go_nodes.append({"name": go_node.name, "id": go_node.id})

        results.append({
            "material_name": node.name,
            "material_id": node.id,
            "go_nodes": go_nodes,
        })

    return results
