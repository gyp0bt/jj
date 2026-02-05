"""jj g (graph) コマンド: グラフデータの管理

このモジュールはCLI層のみを担当し、ビジネスロジックはservicesから呼び出します。

サブコマンド:
- jj g parse: プロジェクトをスキャンしてグラフデータを生成・保存
- jj g show: 保存されたグラフデータを表示
- jj g export: グラフデータをObsidian等にエクスポート

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


def add_graph_parser(subparsers: argparse._SubParsersAction) -> None:
    """graphサブコマンドをパーサーに追加"""
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
    init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存の設定ファイルを上書き",
    )

    # jj g parse
    parse_parser = graph_subparsers.add_parser(
        "parse",
        help="プロジェクトをスキャンしてグラフデータを生成",
    )
    parse_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="出力ファイル名（デフォルト: graph.yaml）",
    )
    parse_parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="出力フォーマット（デフォルト: yaml）",
    )

    # jj g show
    show_parser = graph_subparsers.add_parser(
        "show",
        help="グラフデータを表示",
    )
    show_parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むファイル名",
    )
    show_parser.add_argument(
        "--type",
        type=str,
        default=None,
        help="表示するノードタイプでフィルタリング",
    )
    show_parser.add_argument(
        "--summary",
        action="store_true",
        help="サマリーのみ表示",
    )

    # jj g export
    export_parser = graph_subparsers.add_parser(
        "export",
        help="グラフデータをエクスポート",
    )
    export_parser.add_argument(
        "--target",
        choices=["obsidian"],
        default="obsidian",
        help="エクスポート先（デフォルト: obsidian）",
    )
    export_parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むグラフファイル名",
    )
    export_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="既存ファイルを上書き",
    )


def run_graph_command(args: argparse.Namespace) -> int:
    """graphコマンドを実行"""
    graph_command = getattr(args, "graph_command", None)

    if graph_command is None:
        print("使用方法: jj g <サブコマンド>")
        print("サブコマンド: init, parse, show, export")
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
    else:
        print(f"不明なサブコマンド: {graph_command}")
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
    """exportサブコマンドを実行"""
    service = GraphService(project_root=project_root)

    try:
        graph = service.load(filename=args.file)

        if not graph.nodes:
            print("グラフデータが見つかりません。")
            print("まず 'jj g parse' を実行してください。")
            return 1

        if args.target == "obsidian":
            connector = ObsidianConnector(project_root=project_root)
            print(f"Obsidianにエクスポート中...")
            written = connector.export_graph(graph, overwrite=args.overwrite)

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
            print(f"未対応のエクスポート先: {args.target}")
            return 1

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
