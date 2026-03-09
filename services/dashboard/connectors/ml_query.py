"""MLダッシュボード クエリ関数

ML固有のダッシュボードデータ取得ロジック。
Streamlitに依存しない純粋なクエリ関数群を提供する。

描画ロジック（ml.py）から分離してテスト容易性を確保。

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.dashboard.data_provider import DashboardDataProvider

# ====================================================================
# ノードタイプ定数
# ====================================================================

ML_DATASET_TYPES = {"dataset"}
ML_MODEL_TYPES = {"model_checkpoint", "serialized_model"}
ML_SCRIPT_TYPES = {"training_script"}
ML_CONFIG_TYPES = {"experiment_config", "optimization_config"}
ML_METRICS_TYPES = {"experiment_metrics"}
ML_OPTIMIZATION_TYPES = {"optimization_study", "optimization_config", "trial_history"}

ML_ALL_TYPES = (
    ML_DATASET_TYPES | ML_MODEL_TYPES | ML_SCRIPT_TYPES | ML_CONFIG_TYPES | ML_METRICS_TYPES | ML_OPTIMIZATION_TYPES
)

# レイヤー定義
CAE_NODE_TYPES = {"calculation_input", "result", "mesh", "output", "asset"}
CAE_FORMATS = {"inp", "odb", "dat", "sta", "msg", "cae", "cas", "msh", "jou", "sif"}


def get_node_layer(node: Any) -> int | None:
    """ノードの所属レイヤーを判定

    Returns:
        1: CAE, 2: ML, 3: Optimization, None: 不明
    """
    if node.type in CAE_NODE_TYPES or node.format in CAE_FORMATS:
        return 1
    if node.type in ML_DATASET_TYPES | ML_MODEL_TYPES | ML_SCRIPT_TYPES | ML_METRICS_TYPES:
        return 2
    if node.type in ML_CONFIG_TYPES and not node.properties.get("ml_optimization"):
        return 2
    if node.type in ML_OPTIMIZATION_TYPES or node.properties.get("ml_optimization"):
        return 3
    return None


# ====================================================================
# ML概要テーブル
# ====================================================================


def has_ml_nodes(provider: DashboardDataProvider) -> bool:
    """MLノードが1つ以上存在するか"""
    return any(node.type in ML_ALL_TYPES for node in provider.graph.nodes)


def get_ml_summary(provider: DashboardDataProvider) -> dict[str, int]:
    """ML関連ノードのサマリーカウント"""
    counts: dict[str, int] = {
        "datasets": 0,
        "models": 0,
        "scripts": 0,
        "configs": 0,
        "metrics": 0,
        "optimizations": 0,
    }
    for node in provider.graph.nodes:
        if node.type in ML_DATASET_TYPES:
            counts["datasets"] += 1
        elif node.type in ML_MODEL_TYPES:
            counts["models"] += 1
        elif node.type in ML_SCRIPT_TYPES:
            counts["scripts"] += 1
        elif node.type in ML_CONFIG_TYPES:
            counts["configs"] += 1
        elif node.type in ML_METRICS_TYPES:
            counts["metrics"] += 1
        elif node.type in ML_OPTIMIZATION_TYPES:
            counts["optimizations"] += 1
    return counts


def get_experiment_table(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """実験メトリクスのテーブルデータを取得"""
    rows: list[dict[str, Any]] = []
    for node in provider.graph.nodes:
        if node.type not in ML_METRICS_TYPES:
            continue
        row: dict[str, Any] = {
            "名前": node.name,
            "実験ID": node.properties.get("experiment_id", ""),
            "実験ディレクトリ": node.properties.get("experiment_dir", ""),
            "パス": node.properties.get("path", ""),
        }
        # キーメトリクスを展開
        key_metrics = node.properties.get("ml_key_metrics", {})
        for k, v in key_metrics.items():
            row[k] = v
        rows.append(row)
    return rows


def get_dataset_table(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """データセットのテーブルデータを取得"""
    rows: list[dict[str, Any]] = []
    for node in provider.graph.nodes:
        if node.type not in ML_DATASET_TYPES:
            continue
        row: dict[str, Any] = {
            "名前": node.name,
            "形式": node.format,
            "分割": node.properties.get("split", ""),
            "行数": node.properties.get("n_rows", ""),
            "列数": node.properties.get("n_columns", ""),
            "パス": node.properties.get("path", ""),
        }
        # カラム名があれば追加
        columns = node.properties.get("columns")
        if columns:
            row["カラム"] = ", ".join(columns[:10])
            if len(columns) > 10:
                row["カラム"] += f" ... (+{len(columns) - 10})"
        rows.append(row)
    return rows


def get_model_table(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """モデルのテーブルデータを取得"""
    rows: list[dict[str, Any]] = []
    for node in provider.graph.nodes:
        if node.type not in ML_MODEL_TYPES:
            continue
        row: dict[str, Any] = {
            "名前": node.name,
            "タイプ": node.type,
            "形式": node.format,
            "パス": node.properties.get("path", ""),
        }
        # チェックポイント固有
        if node.type == "model_checkpoint":
            row["エポック"] = node.properties.get("epoch", "")
            row["ステップ"] = node.properties.get("step", "")
            row["ベスト"] = "✓" if node.properties.get("is_best") else ""
        # scikit-learn固有
        if node.type == "serialized_model":
            row["モデル種別"] = node.properties.get("model_type", "")
            row["ベスト"] = "✓" if node.properties.get("is_best") else ""
        # ファイルサイズ
        size = node.properties.get("file_size_bytes")
        if size is not None:
            row["サイズ"] = _format_file_size(size)
        rows.append(row)
    return rows


def get_script_table(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """スクリプトのテーブルデータを取得"""
    rows: list[dict[str, Any]] = []
    for node in provider.graph.nodes:
        if node.type not in ML_SCRIPT_TYPES:
            continue
        row: dict[str, Any] = {
            "名前": node.name,
            "フレームワーク": ", ".join(node.properties.get("ml_frameworks", [])),
            "役割": node.properties.get("ml_role", ""),
            "パス": node.properties.get("path", ""),
        }
        rows.append(row)
    return rows


def get_optimization_table(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """最適化スタディのテーブルデータを取得"""
    rows: list[dict[str, Any]] = []
    for node in provider.graph.nodes:
        if node.type not in ML_OPTIMIZATION_TYPES:
            continue
        row: dict[str, Any] = {
            "名前": node.name,
            "タイプ": node.type,
            "形式": node.format,
            "パス": node.properties.get("path", ""),
        }
        if node.type == "optimization_study":
            row["フレームワーク"] = node.properties.get("optimization_framework", "")
            row["スタディ名"] = node.properties.get("study_name", "")
            row["試行数"] = node.properties.get("n_trials_completed", "")
            row["方向"] = node.properties.get("direction", "")
        elif node.type == "optimization_config":
            params = node.properties.get("optimization_params", {})
            row["目的関数"] = params.get("objective", "")
            row["試行数"] = params.get("n_trials", "")
        rows.append(row)
    return rows


# ====================================================================
# 三層データフローグラフ
# ====================================================================


def get_dataflow_graph_data(
    provider: DashboardDataProvider,
) -> dict[str, Any]:
    """三層データフロー可視化用のデータを構築

    Returns:
        {
            "nodes": [{"id": int, "name": str, "type": str, "layer": int, "path": str}],
            "edges": [{"source": int, "target": int, "label": str, "cross_layer": bool}],
            "layer_counts": {1: int, 2: int, 3: int},
        }
    """
    nodes: list[dict[str, Any]] = []
    node_ids: set[int] = set()
    layer_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}

    for node in provider.graph.nodes:
        layer = get_node_layer(node)
        if layer is None:
            continue
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "type": node.type,
                "layer": layer,
                "path": node.properties.get("path", ""),
            }
        )
        node_ids.add(node.id)
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    # リレーションからエッジ構築
    edges: list[dict[str, Any]] = []
    node_layer_map = {n["id"]: n["layer"] for n in nodes}

    for rel in provider.graph.relations:
        if rel.node1_id not in node_ids or rel.node2_id not in node_ids:
            continue
        src_layer = node_layer_map.get(rel.node1_id)
        tgt_layer = node_layer_map.get(rel.node2_id)
        cross_layer = src_layer != tgt_layer if src_layer and tgt_layer else False
        edges.append(
            {
                "source": rel.node1_id,
                "target": rel.node2_id,
                "label": rel.label,
                "cross_layer": cross_layer,
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "layer_counts": layer_counts,
    }


def get_ml_relations(provider: DashboardDataProvider) -> list[dict[str, Any]]:
    """ML関連リレーションのテーブルデータを取得"""
    ml_labels = {
        "trains_with",
        "produces_model",
        "configured_by",
        "logs_to",
        "evaluated_on",
        "extracted_from",
        "surrogate_of",
        "optimizes",
        "uses_objective",
    }
    node_map = {n.id: n for n in provider.graph.nodes}
    rows: list[dict[str, Any]] = []
    for rel in provider.graph.relations:
        if rel.label not in ml_labels:
            continue
        src = node_map.get(rel.node1_id)
        tgt = node_map.get(rel.node2_id)
        if src is None or tgt is None:
            continue
        rows.append(
            {
                "リレーション": rel.label,
                "始点": src.name,
                "始点タイプ": src.type,
                "終点": tgt.name,
                "終点タイプ": tgt.type,
            }
        )
    return rows


# ====================================================================
# ヘルパー
# ====================================================================


def _format_file_size(size_bytes: int) -> str:
    """ファイルサイズを人間可読な形式に変換"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _short_path(path_str: str) -> str:
    """パスを短縮表示"""
    parts = PurePosixPath(path_str).parts
    if len(parts) <= 3:
        return path_str
    return str(PurePosixPath(*parts[-3:]))
