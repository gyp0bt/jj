"""ダッシュボード クエリ・フィルタ・ソートロジック（純粋関数）

app.pyから抽出した、Streamlitに依存しない純粋なデータ操作ロジック。
カラムソート、テーブルカラム選択、フィルタ適用、truthy判定、
画像グループキー収集、graph.yaml検知などを提供する。

jj-dashboardの分離を見据え、描画層（app.py）から
クエリ/フィルタ層を独立させることで、テスト容易性と
将来のパッケージ分離を実現する。

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any


# ====================================================================
# graph.yaml 検知ユーティリティ
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
# truthy判定
# ====================================================================


def is_truthy(value: Any) -> bool:
    """bool/文字列両方に対応したtruthy判定

    YAML経由の値はbool True/Falseだが、GraphService.file_to_node()では
    文字列 "true"/"false" として格納される。両方を正しく扱う。

    Args:
        value: チェック対象の値

    Returns:
        True と見なせる場合 True
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


# ====================================================================
# カラムソート・選択
# ====================================================================


def sort_columns_by_vocab(
    columns: list[str], vocab: dict[str, str]
) -> list[str]:
    """vocab順でカラムをソート

    vocab辞書の値（日本語表記）の出現順を優先し、
    vocabに含まれないカラムは文字列昇順で後に配置する。

    Args:
        columns: ソート対象のカラムリスト
        vocab: vocabマッピング

    Returns:
        vocab順 -> 文字列昇順のリスト
    """
    vocab_order: dict[str, int] = {}
    for idx, v in enumerate(vocab.values()):
        if v not in vocab_order:
            vocab_order[v] = idx
    for idx, k in enumerate(vocab.keys()):
        if k not in vocab_order:
            vocab_order[k] = len(vocab) + idx

    in_vocab = [c for c in columns if c in vocab_order]
    not_in_vocab = [c for c in columns if c not in vocab_order]
    in_vocab.sort(key=lambda c: vocab_order[c])
    not_in_vocab.sort()
    return in_vocab + not_in_vocab


def select_table_columns(
    all_columns: list[str],
    table_columns: list[str] | None,
    vocab: dict[str, str] | None = None,
) -> list[str]:
    """config指定に基づいてテーブルカラムをフィルタ・並べ替え

    table_columnsが指定されていない場合はvocab順でソートして返す。

    Args:
        all_columns: DataFrameの全カラム名
        table_columns: config.dashboard.table-columns（globパターン対応）
        vocab: vocabマッピング（vocab順ソート用）

    Returns:
        表示するカラムのリスト（順序付き）
    """
    # 固定カラム（常に先頭に表示）
    fixed = ["name", "type", "format"]

    if table_columns is None:
        # table-columns未指定の場合: 固定カラム + vocab順でソート
        remaining = [c for c in all_columns if c not in fixed]
        if vocab:
            remaining = sort_columns_by_vocab(remaining, vocab)
        result = [c for c in fixed if c in all_columns] + remaining
        return result

    ordered: list[str] = []
    seen: set[str] = set(fixed)

    for pattern in table_columns:
        for col in all_columns:
            if col in seen:
                continue
            if fnmatch.fnmatch(col, pattern) or col == pattern:
                ordered.append(col)
                seen.add(col)

    # 固定カラム（存在するもののみ） + 指定カラム
    result = [c for c in fixed if c in all_columns] + ordered
    return result


# ====================================================================
# フィルタ適用（セッション非依存の純粋関数版）
# ====================================================================


def apply_filters(
    rows: list[dict[str, Any]],
    type_filter: str | None = None,
    status_filter: str | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """汎用フィルタを適用

    Args:
        rows: フィルタ対象の全行データ
        type_filter: タイプフィルタ（Noneまたは"すべて"で無効）
        status_filter: ステータスフィルタ（Noneまたは"すべて"で無効）
        active_only: Trueの場合activeのみ

    Returns:
        フィルタ適用後の行データ
    """
    filtered = rows
    if type_filter and type_filter != "すべて":
        filtered = [r for r in filtered if r.get("type") == type_filter]
    if status_filter and status_filter != "すべて":
        filtered = [
            r for r in filtered if r.get("analysis_status") == status_filter
        ]
    if active_only:
        filtered = [r for r in filtered if is_truthy(r.get("active"))]
    return filtered


def apply_saved_view_filters(
    rows: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """保存済みビューのフィルタを適用

    Args:
        rows: フィルタ対象の全行データ
        filters: 保存済みフィルタ条件

    Returns:
        フィルタ適用後の行データ
    """
    if not filters:
        return rows

    filtered = rows
    for key, value in filters.items():
        if key == "active":
            if is_truthy(value):
                filtered = [r for r in filtered if is_truthy(r.get("active"))]
            else:
                filtered = [
                    r for r in filtered if not is_truthy(r.get("active"))
                ]
        elif key == "type" and value != "すべて":
            filtered = [r for r in filtered if r.get("type") == value]
        elif key == "analysis_status" and value != "すべて":
            filtered = [
                r for r in filtered if r.get("analysis_status") == value
            ]
        else:
            filtered = [r for r in filtered if r.get(key) == value]

    return filtered


def saved_view_filters_to_provider_filters(
    filters: dict[str, Any],
) -> dict[str, Any]:
    """保存済みビューのフィルタをDashboardDataProvider.get_*のfilters形式に変換"""
    result: dict[str, Any] = {}
    for key, value in filters.items():
        result[key] = value
    return result


# ====================================================================
# 画像ギャラリー ユーティリティ
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


def collect_group_keys(
    images: list[dict[str, Any]], source: str
) -> list[str]:
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
        result = ["property_key"] + result
    return result
