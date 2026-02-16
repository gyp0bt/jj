"""ダッシュボード クエリ・フィルタ・ソートロジック

汎用のフィルタ/ソートロジックは services/query/ に昇格済み。
本モジュールはダッシュボード固有の関数（graph.yaml検知、
画像ギャラリーユーティリティ）を保持しつつ、
services/query からの再エクスポートにより後方互換性を維持する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ==================================================================
# services/query からの再エクスポート（後方互換）
# ==================================================================
from services.query.filters import (  # noqa: F401
    apply_filters,
    apply_saved_view_filters,
    is_truthy,
    saved_view_filters_to_provider_filters,
)
from services.query.sort import (  # noqa: F401
    select_table_columns,
    sort_columns_by_vocab,
)

# ====================================================================
# graph.yaml 検知ユーティリティ（dashboard固有）
# ====================================================================

_GRAPH_EXTENSIONS = ("yaml", "yml", "json")


def find_graph_path(project_root: Path) -> Path | None:
    """graph.yamlの実パスを検出

    Args:
        project_root: プロジェクトルート

    Returns:
        graph.yamlのパス。見つからない場合はNone。
    """
    storage_dir = project_root / ".jj" / "storage"
    for ext in _GRAPH_EXTENSIONS:
        p = storage_dir / f"graph.{ext}"
        if p.exists():
            return p
    return None


def get_graph_mtime(project_root: Path) -> float:
    """graph.yamlの更新時刻を取得

    Args:
        project_root: プロジェクトルート

    Returns:
        更新時刻（epoch秒）。ファイルが存在しない場合は0.0。
    """
    graph_path = find_graph_path(project_root)
    if graph_path is not None:
        return graph_path.stat().st_mtime
    return 0.0


# ====================================================================
# 画像ギャラリー ユーティリティ（dashboard固有）
# ====================================================================


def normalize_group_key(key: str) -> str:
    """グループキーを正規化（daily:日付:キー -> キー部分のみ）

    property_keyが "daily:2026-01-15:screenshot" の場合、
    グルーピング用に "screenshot" に正規化する。

    Args:
        key: 生のグループキー

    Returns:
        正規化されたキー
    """
    if key.startswith("daily:"):
        parts = key.split(":", 2)
        if len(parts) >= 3:
            return parts[2]
    return key


def collect_group_keys(images: list[dict[str, Any]], source: str) -> list[str]:
    """画像リストからグループ化に利用できるキーを収集

    Args:
        images: 画像情報のリスト
        source: "output" or "property"

    Returns:
        グループ化に利用可能なキーのリスト
    """
    keys: set[str] = set()
    for img in images:
        props = img.get("go_properties", {})
        for k in props:
            if k not in ("path", "include_properties"):
                keys.add(k)
    result = sorted(keys)
    # propertyソースの場合はproperty_keyでのグルーピングも追加
    if source == "property":
        result = ["property_key", *result]
    return result
