"""jj Python API — スクリプトからプロジェクトグラフにアクセスするためのパブリックAPI

使用例::

    import jj

    # プロジェクトのグラフをロード（カレントディレクトリから探索）
    graph = jj.load()

    # パスでノードを取得
    node = jj.get_node("go_case01.inp")

    # ノードのプロパティを取得
    props = jj.get_properties("go_case01.inp")

    # 特定プロパティの値を取得
    value = jj.get_property("go_case01.inp", "analysis_status")

[READMEへ戻る](../README.md)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "get_node",
    "get_nodes",
    "get_properties",
    "get_property",
    "load",
]


def _find_project_root(start: Path | None = None) -> Path:
    """カレントディレクトリから上方向に.j2ディレクトリを探索してプロジェクトルートを返す"""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".j2").is_dir():
            return parent
    return current


def load(project_root: str | Path | None = None) -> Any:
    """プロジェクトのGraphModelをロードする

    Args:
        project_root: プロジェクトルートのパス。省略時はカレントディレクトリから探索。

    Returns:
        GraphModel インスタンス
    """
    from services.graph import GraphService

    root = Path(project_root) if project_root else _find_project_root()
    svc = GraphService(project_root=root)
    return svc.load()


def get_nodes(
    project_root: str | Path | None = None,
    *,
    type_filter: str | None = None,
    name_filter: str | None = None,
) -> list[Any]:
    """プロジェクト内のノード一覧を取得する

    Args:
        project_root: プロジェクトルート
        type_filter: ノードタイプでフィルタ（例: "file"）
        name_filter: ノード名の部分一致フィルタ

    Returns:
        Nodeのリスト
    """
    graph = load(project_root)
    nodes = list(graph.nodes)
    if type_filter:
        nodes = [n for n in nodes if n.type == type_filter]
    if name_filter:
        nodes = [n for n in nodes if name_filter.lower() in n.name.lower()]
    return nodes


def get_node(name_or_path: str, project_root: str | Path | None = None) -> Any | None:
    """名前またはパスでノードを取得する

    Args:
        name_or_path: ノード名またはproperties.pathの値
        project_root: プロジェクトルート

    Returns:
        一致するNode、見つからない場合はNone
    """
    graph = load(project_root)
    # 名前で完全一致
    for node in graph.nodes:
        if node.name == name_or_path:
            return node
    # パスで一致
    for node in graph.nodes:
        if node.properties.get("path") == name_or_path:
            return node
    # 名前の部分一致（ファイル名のみ）
    target_name = Path(name_or_path).stem
    for node in graph.nodes:
        if node.name == target_name:
            return node
    return None


def get_properties(name_or_path: str, project_root: str | Path | None = None) -> dict[str, Any]:
    """ノードのプロパティを辞書で取得する

    Args:
        name_or_path: ノード名またはパス
        project_root: プロジェクトルート

    Returns:
        プロパティの辞書。ノードが見つからない場合は空辞書。
    """
    node = get_node(name_or_path, project_root)
    if node is None:
        return {}
    return dict(node.properties)


def get_property(
    name_or_path: str,
    property_key: str,
    project_root: str | Path | None = None,
    default: Any = None,
) -> Any:
    """ノードの特定プロパティを取得する

    Args:
        name_or_path: ノード名またはパス
        property_key: プロパティキー
        project_root: プロジェクトルート
        default: ノードが見つからないかキーがない場合のデフォルト値

    Returns:
        プロパティの値
    """
    props = get_properties(name_or_path, project_root)
    return props.get(property_key, default)
