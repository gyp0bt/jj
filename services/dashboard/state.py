"""ダッシュボード固有のグラフファイル検知ユーティリティ

graph.yaml のパス検出と更新時刻取得。`services.dashboard.app` での
mtime ベース変更検知と、HTML エクスポートでのパス解決に使用される。
graph 層には依存せず、純粋なファイルシステム操作のみ。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

from pathlib import Path

_GRAPH_EXTENSIONS = ("yaml", "yml", "json")


def find_graph_path(project_root: Path) -> Path | None:
    """graph.yaml の実パスを検出する。見つからない場合は None。"""
    storage_dir = project_root / ".j2" / "storage"
    for ext in _GRAPH_EXTENSIONS:
        p = storage_dir / f"graph.{ext}"
        if p.exists():
            return p
    return None


def get_graph_mtime(project_root: Path) -> float:
    """graph.yaml の更新時刻 (epoch 秒) を返す。存在しない場合は 0.0。"""
    graph_path = find_graph_path(project_root)
    if graph_path is not None:
        return graph_path.stat().st_mtime
    return 0.0
