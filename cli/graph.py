"""jj graph コマンド: グラフデータの管理

このモジュールはCLI層のみを担当し、ビジネスロジックはservicesから呼び出します。

サブコマンド（トップレベル）:
- jj init: 設定ファイルを初期化
- jj parse: プロジェクトをスキャンしてグラフデータを生成・保存
- jj show: 保存されたグラフデータを表示
- jj export: グラフデータをObsidian等にエクスポート
- jj export --parse: parseしてからexport
- jj info <ファイル名>: ファイルのproperty/relationを表示

旧コマンド（互換性維持）:
- jj g init / jj g parse / jj g show / jj g export

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from services.graph import GraphService
from services.connectors.obsidian import ObsidianConnector
from config import init_graph_config


def _add_init_args(parser: argparse.ArgumentParser) -> None:
    """initコマンドの引数を追加"""
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存の設定ファイルを上書き",
    )


def _add_parse_args(parser: argparse.ArgumentParser) -> None:
    """parseコマンドの引数を追加"""
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="出力ファイル名（デフォルト: graph.yaml）",
    )
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="出力フォーマット（デフォルト: yaml）",
    )


def _add_show_args(parser: argparse.ArgumentParser) -> None:
    """showコマンドの引数を追加"""
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むファイル名",
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        help="表示するノードタイプでフィルタリング",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="サマリーのみ表示",
    )


def _add_export_args(parser: argparse.ArgumentParser) -> None:
    """exportコマンドの引数を追加"""
    parser.add_argument(
        "--target",
        choices=["obsidian"],
        default="obsidian",
        help="エクスポート先（デフォルト: obsidian）",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むグラフファイル名",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存ファイルを上書き",
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help="エクスポート前にparseを実行",
    )


def _add_info_args(parser: argparse.ArgumentParser) -> None:
    """infoコマンドの引数を追加"""
    parser.add_argument(
        "filename",
        type=str,
        help="表示するファイル名",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むグラフファイル名",
    )


def add_top_level_graph_commands(subparsers: argparse._SubParsersAction) -> None:
    """トップレベルのグラフサブコマンドを追加（jj init, jj parse等）"""
    # jj init
    init_parser = subparsers.add_parser(
        "init",
        help="設定ファイルを初期化（デフォルト設定をコピー）",
    )
    _add_init_args(init_parser)

    # jj parse
    parse_parser = subparsers.add_parser(
        "parse",
        help="プロジェクトをスキャンしてグラフデータを生成",
    )
    _add_parse_args(parse_parser)

    # jj show
    show_parser = subparsers.add_parser(
        "show",
        help="グラフデータを表示",
    )
    _add_show_args(show_parser)

    # jj export
    export_parser = subparsers.add_parser(
        "export",
        help="グラフデータをエクスポート",
    )
    _add_export_args(export_parser)

    # jj info
    info_parser = subparsers.add_parser(
        "info",
        help="ファイルのproperty/relationを表示",
    )
    _add_info_args(info_parser)


def add_graph_parser(subparsers: argparse._SubParsersAction) -> None:
    """graphサブコマンドをパーサーに追加（jj g互換）"""
    graph_parser = subparsers.add_parser(
        "g",
        aliases=["graph"],
        help="グラフデータの管理",
        description="プロジェクトのグラフデータを管理します",
    )

    graph_subparsers = graph_parser.add_subparsers(
        dest="graph_command",
        help="グラフサブコマンド",
    )

    # jj g init
    init_parser = graph_subparsers.add_parser(
        "init",
        help="設定ファイルを初期化（デフォルト設定をコピー）",
    )
    _add_init_args(init_parser)

    # jj g parse
    parse_parser = graph_subparsers.add_parser(
        "parse",
        help="プロジェクトをスキャンしてグラフデータを生成",
    )
    _add_parse_args(parse_parser)

    # jj g show
    show_parser = graph_subparsers.add_parser(
        "show",
        help="グラフデータを表示",
    )
    _add_show_args(show_parser)

    # jj g export
    export_parser = graph_subparsers.add_parser(
        "export",
        help="グラフデータをエクスポート",
    )
    _add_export_args(export_parser)

    # jj g info
    info_parser = graph_subparsers.add_parser(
        "info",
        help="ファイルのproperty/relationを表示",
    )
    _add_info_args(info_parser)



def run_graph_command(args: argparse.Namespace) -> int:
    """graphコマンドを実行（jj g経由）"""
    graph_command = getattr(args, "graph_command", None)

    if graph_command is None:
        print("使用方法: jj g <サブコマンド>")
        print("サブコマンド: init, parse, show, export, info")
        print("詳細: jj g --help")
        return 1

    project_root = Path.cwd()

    if graph_command == "init":
        return _run_init(project_root, args)
    elif graph_command == "parse":
        return _run_parse(project_root, args)
    elif graph_command == "show":
        return _run_show(project_root, args)
    elif graph_command == "export":
        return _run_export(project_root, args)
    elif graph_command == "info":
        return _run_info(project_root, args)
    else:
        print(f"不明なサブコマンド: {graph_command}")
        return 1


def run_top_level_graph_command(cmd: str, args: argparse.Namespace) -> int:
    """トップレベルのグラフコマンドを実行（jj init/parse/show/export/info）"""
    project_root = Path.cwd()

    if cmd == "init":
        return _run_init(project_root, args)
    elif cmd == "parse":
        return _run_parse(project_root, args)
    elif cmd == "show":
        return _run_show(project_root, args)
    elif cmd == "export":
        return _run_export(project_root, args)
    elif cmd == "info":
        return _run_info(project_root, args)
    else:
        print(f"不明なコマンド: {cmd}")
        return 1


def _run_init(project_root: Path, args: argparse.Namespace) -> int:
    """initサブコマンドを実行"""
    overwrite = getattr(args, "overwrite", False)

    try:
        config_path = init_graph_config(base_dir=project_root, overwrite=overwrite)
        print(f"設定ファイルを初期化しました: {config_path}")
        if overwrite:
            print("（既存ファイルを上書きしました）")
        return 0
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_parse(project_root: Path, args: argparse.Namespace) -> int:
    """parseサブコマンドを実行"""
    service = GraphService(project_root=project_root)

    # 出力ファイル名を決定
    output_file = args.output
    if output_file is None:
        output_file = f"graph.{args.format}"

    print(f"プロジェクトをスキャン中: {project_root}")

    try:
        graph, save_path = service.parse_and_save(filename=output_file)
        summary = service.summary(graph)

        print(f"\n=== スキャン完了 ===")
        print(f"ノード数: {summary['total_nodes']}")
        print(f"リレーション数: {summary['total_relations']}")
        print(f"\nノードタイプ別:")
        for node_type, count in summary["nodes_by_type"].items():
            print(f"  {node_type}: {count}")
        print(f"\n保存先: {save_path}")
        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_show(project_root: Path, args: argparse.Namespace) -> int:
    """showサブコマンドを実行"""
    service = GraphService(project_root=project_root)

    try:
        graph = service.load(filename=args.file)

        if not graph.nodes and not graph.relations:
            print("グラフデータが見つかりません。")
            print("まず 'jj g parse' を実行してください。")
            return 1

        if args.summary:
            summary = service.summary(graph)
            print("=== グラフサマリー ===")
            print(f"ノード数: {summary['total_nodes']}")
            print(f"リレーション数: {summary['total_relations']}")
            print(f"\nノードタイプ別:")
            for node_type, count in summary["nodes_by_type"].items():
                print(f"  {node_type}: {count}")
            return 0

        # フィルタリング
        nodes = graph.nodes
        if args.type:
            nodes = service.get_nodes_by_type(graph, args.type)

        print(f"=== ノード一覧 ({len(nodes)}件) ===\n")
        for node in nodes:
            print(f"[{node.id}] {node.name}")
            print(f"    タイプ: {node.type}")
            print(f"    フォーマット: {node.format}")
            path = node.properties.get("path", "")
            if path:
                print(f"    パス: {path}")
            print()

        if graph.relations:
            print(f"=== リレーション ({len(graph.relations)}件) ===\n")
            for rel in graph.relations:
                print(f"[{rel.id}] {rel.node1_id} --{rel.label}--> {rel.node2_id}")

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_export(project_root: Path, args: argparse.Namespace) -> int:
    """exportサブコマンドを実行

    --parse オプションが指定された場合、エクスポート前にparseを実行する。
    """
    service = GraphService(project_root=project_root)

    try:
        # --parse オプション: エクスポート前にparseを実行
        if getattr(args, "parse", False):
            print(f"プロジェクトをスキャン中: {project_root}")
            graph, save_path = service.parse_and_save()
            summary = service.summary(graph)
            print(f"スキャン完了: ノード {summary['total_nodes']}件、リレーション {summary['total_relations']}件")
            print(f"保存先: {save_path}")
        else:
            graph = service.load(filename=getattr(args, "file", None))

        if not graph.nodes:
            print("グラフデータが見つかりません。")
            print("'jj parse' または 'jj export --parse' を実行してください。")
            return 1

        target = getattr(args, "target", "obsidian")
        if target == "obsidian":
            connector = ObsidianConnector(project_root=project_root)
            print(f"Obsidianにエクスポート中...")
            written = connector.export_graph(graph, overwrite=getattr(args, "overwrite", False))

            print(f"\n=== エクスポート完了 ===")
            print(f"書き込みファイル数: {len(written)}")
            if written:
                print("\n書き込んだファイル:")
                for path in written[:10]:  # 最初の10件のみ表示
                    rel_path = path.relative_to(project_root)
                    print(f"  {rel_path}")
                if len(written) > 10:
                    print(f"  ... 他 {len(written) - 10} 件")
            return 0
        else:
            print(f"未対応のエクスポート先: {target}")
            return 1

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_info(project_root: Path, args: argparse.Namespace) -> int:
    """infoサブコマンドを実行 - ファイルのproperty/relationを表示"""
    service = GraphService(project_root=project_root)
    filename = getattr(args, "filename", "")

    try:
        graph = service.load(filename=getattr(args, "file", None))

        if not graph.nodes:
            print("グラフデータが見つかりません。")
            print("まず 'jj parse' を実行してください。")
            return 1

        # ファイル名でノードを検索（部分一致）
        matched_nodes = []
        for node in graph.nodes:
            node_path = node.properties.get("path", "")
            node_file = Path(node_path).name if node_path else ""
            # 完全一致 or 部分一致
            if (
                node.name == filename
                or node_file == filename
                or node_path == filename
                or filename in node.name
                or filename in node_path
            ):
                matched_nodes.append(node)

        if not matched_nodes:
            print(f"ファイル '{filename}' に一致するノードが見つかりません。")
            return 1

        # ノードIDからノードへのマッピング
        node_by_id = {node.id: node for node in graph.nodes}

        for node in matched_nodes:
            print(f"\n=== {node.name} ===")
            print(f"  ID: {node.id}")
            print(f"  タイプ: {node.type}")
            print(f"  フォーマット: {node.format}")

            # プロパティ表示
            print(f"\n  プロパティ:")
            for key, value in sorted(node.properties.items()):
                if isinstance(value, list) and len(value) > 5:
                    print(f"    {key}: [{len(value)} items]")
                elif isinstance(value, dict):
                    print(f"    {key}: {{{len(value)} keys}}")
                else:
                    print(f"    {key}: {value}")

            # リレーション表示
            rels = service.get_relations_for_node(graph, node.id)
            if rels:
                print(f"\n  リレーション ({len(rels)}件):")
                for rel in rels:
                    if rel.node1_id == node.id:
                        target = node_by_id.get(rel.node2_id)
                        target_name = target.name if target else f"ID:{rel.node2_id}"
                        print(f"    --{rel.label}--> {target_name}")
                    else:
                        source = node_by_id.get(rel.node1_id)
                        source_name = source.name if source else f"ID:{rel.node1_id}"
                        print(f"    <--{rel.label}-- {source_name}")

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


