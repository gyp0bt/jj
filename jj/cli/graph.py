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
from typing import Any, Optional, Sequence

from services.graph import GraphService
from services.connectors.obsidian import ObsidianConnector
from services.parse.abaqus_connector import (
    read_inp as abq_read_inp,
    diff_abq_blocks,
    format_diff_summary_table,
    format_diff_blocks_markdown,
)
from services.credentials import (
    save_credentials,
    load_credentials,
    mask_value,
)
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
        choices=["obsidian", "csv", "json", "neo4j", "cypher"],
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
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="出力ファイル名（CSV/JSON出力時に使用）",
    )
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        help="エクスポートするノードタイプでフィルタリング",
    )
    parser.add_argument(
        "--select",
        type=str,
        nargs="*",
        default=None,
        help="エクスポートするファイル名を指定（複数可）",
    )
    # Neo4j固有オプション
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Neo4jエクスポート時、既存のプロジェクトデータを削除してから投入",
    )
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default=None,
        help="Neo4j接続URI（デフォルト: bolt://localhost:7687）",
    )
    parser.add_argument(
        "--neo4j-user",
        type=str,
        default=None,
        help="Neo4jユーザー名（デフォルト: neo4j）",
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        default=None,
        help="Neo4jパスワード（デフォルト: password）",
    )


def _add_info_args(parser: argparse.ArgumentParser) -> None:
    """infoコマンドの引数を追加"""
    parser.add_argument(
        "filename",
        type=str,
        nargs="*",
        default=[],
        help="表示するファイル名（複数指定可）",
    )
    parser.add_argument(
        "-id",
        "--index",
        type=str,
        nargs="*",
        default=None,
        help="インデックスで指定（例: -id 1 2）",
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        nargs="*",
        default=None,
        help="バージョンで指定（例: -v 1 2）",
    )
    parser.add_argument(
        "-props",
        "--props-only",
        action="store_true",
        help="プロパティのみ表示",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help="読み込むグラフファイル名",
    )


def _add_diff_args(parser: argparse.ArgumentParser) -> None:
    """diffコマンドの引数を追加"""
    parser.add_argument(
        "file1",
        type=str,
        help="比較元ファイル（パスまたはファイル名）",
    )
    parser.add_argument(
        "file2",
        type=str,
        help="比較先ファイル（パスまたはファイル名）",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="詳細な差分を表示",
    )


def _add_credential_args(parser: argparse.ArgumentParser) -> None:
    """credentialコマンドの引数を追加"""
    cred_sub = parser.add_subparsers(dest="credential_command", help="クレデンシャル操作")

    # jj credential set
    set_parser = cred_sub.add_parser(
        "set",
        help="クレデンシャルを暗号化して保存",
    )
    set_parser.add_argument(
        "--service",
        type=str,
        default="neo4j",
        help="サービス名（デフォルト: neo4j）",
    )
    set_parser.add_argument("--uri", type=str, help="接続URI")
    set_parser.add_argument("--user", type=str, help="ユーザー名")
    set_parser.add_argument("--password", type=str, help="パスワード")
    set_parser.add_argument("--database", type=str, help="データベース名")

    # jj credential show
    show_parser = cred_sub.add_parser(
        "show",
        help="保存済みクレデンシャルを表示（マスキング付き）",
    )
    show_parser.add_argument(
        "--service",
        type=str,
        default="neo4j",
        help="サービス名（デフォルト: neo4j）",
    )
    show_parser.add_argument(
        "--unmask",
        action="store_true",
        help="マスキングせずに表示",
    )

    # jj credential delete
    del_parser = cred_sub.add_parser(
        "delete",
        help="保存済みクレデンシャルを削除",
    )
    del_parser.add_argument(
        "--service",
        type=str,
        default="neo4j",
        help="サービス名（デフォルト: neo4j）",
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

    # jj diff
    diff_parser = subparsers.add_parser(
        "diff",
        help="2つのファイル間のAbaqusキーワードブロック差分を表示",
    )
    _add_diff_args(diff_parser)

    # jj credential
    cred_parser = subparsers.add_parser(
        "credential",
        help="クレデンシャル（認証情報）の管理",
    )
    _add_credential_args(cred_parser)


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

    # jj g diff
    diff_parser = graph_subparsers.add_parser(
        "diff",
        help="2つのファイル間のAbaqusキーワードブロック差分を表示",
    )
    _add_diff_args(diff_parser)


def run_graph_command(args: argparse.Namespace) -> int:
    """graphコマンドを実行（jj g経由）"""
    graph_command = getattr(args, "graph_command", None)

    if graph_command is None:
        print("使用方法: jj g <サブコマンド>")
        print("サブコマンド: init, parse, show, export, info, diff")
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
    elif graph_command == "diff":
        return _run_diff(project_root, args)
    else:
        print(f"不明なサブコマンド: {graph_command}")
        return 1


def run_top_level_graph_command(cmd: str, args: argparse.Namespace) -> int:
    """トップレベルのグラフコマンドを実行（jj init/parse/show/export/info/diff/credential）"""
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
    elif cmd == "diff":
        return _run_diff(project_root, args)
    elif cmd == "credential":
        return _run_credential(project_root, args)
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
    --target csv/json の場合、ノード属性をCSV/JSON形式で書き出す。
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
                for path in written[:10]:
                    rel_path = path.relative_to(project_root)
                    print(f"  {rel_path}")
                if len(written) > 10:
                    print(f"  ... 他 {len(written) - 10} 件")
            return 0

        elif target in ("csv", "json"):
            return _run_export_data(
                project_root, graph, service, target, args
            )

        elif target == "neo4j":
            return _run_export_neo4j(
                project_root, graph, args, direct=True
            )

        elif target == "cypher":
            return _run_export_neo4j(
                project_root, graph, args, direct=False
            )

        else:
            print(f"未対応のエクスポート先: {target}")
            return 1

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_export_data(
    project_root: Path,
    graph: "GraphModel",
    service: GraphService,
    target: str,
    args: argparse.Namespace,
) -> int:
    """CSV/JSONデータエクスポートを実行

    選択したノードのプロパティを全キーのAND（積集合ではなく和集合）で
    null埋めしてCSV/JSON形式で書き出す。
    """
    import csv
    import json as json_mod

    # ノードのフィルタリング
    nodes = list(graph.nodes)
    type_filter = getattr(args, "type", None)
    select_filter = getattr(args, "select", None)

    if type_filter:
        nodes = [n for n in nodes if n.type == type_filter]
    if select_filter:
        filtered = []
        for n in nodes:
            name_with_ext = f"{n.name}.{n.format}" if n.format else n.name
            for sel in select_filter:
                if n.name == sel or name_with_ext == sel or sel in n.name:
                    filtered.append(n)
                    break
        nodes = filtered

    if not nodes:
        print("対象ノードが見つかりません。")
        return 1

    # 全キーの和集合を収集
    all_keys: list[str] = []
    seen_keys: set[str] = set()
    # 基本属性キー
    base_keys = ["name", "type", "format"]
    for k in base_keys:
        all_keys.append(k)
        seen_keys.add(k)

    for node in nodes:
        for key in node.properties:
            if key not in seen_keys:
                all_keys.append(key)
                seen_keys.add(key)

    # 行データの構築（null埋め）
    rows: list[dict[str, Any]] = []
    for node in nodes:
        row: dict[str, Any] = {
            "name": node.name,
            "type": node.type,
            "format": node.format,
        }
        for key in all_keys:
            if key in row:
                continue
            value = node.properties.get(key)
            if value is None:
                row[key] = None
            elif isinstance(value, (list, dict)):
                row[key] = json_mod.dumps(value, ensure_ascii=False)
            else:
                row[key] = value
        rows.append(row)

    # 出力ファイル名の決定
    output_file = getattr(args, "output", None)
    if output_file is None:
        output_file = f"export.{target}"
    output_path = project_root / output_file

    if target == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSVエクスポート完了: {output_path} ({len(rows)}件)")
    elif target == "json":
        with output_path.open("w", encoding="utf-8") as f:
            json_mod.dump(rows, f, ensure_ascii=False, indent=2, default=str)
        print(f"JSONエクスポート完了: {output_path} ({len(rows)}件)")

    return 0


def _run_export_neo4j(
    project_root: Path,
    graph: "GraphModel",
    args: argparse.Namespace,
    direct: bool = True,
) -> int:
    """Neo4j/Cypherエクスポートを実行

    Args:
        project_root: プロジェクトルート
        graph: エクスポート対象のグラフ
        args: CLIの引数
        direct: Trueの場合Neo4jに直接書き込み、Falseの場合Cypherファイル出力
    """
    from services.connectors.neo4j import Neo4jConnector
    from shared.config import Neo4jConfig

    clear_project = getattr(args, "clear", False)

    # Neo4j接続設定の構築
    neo4j_config = Neo4jConfig.from_jj_config(project_root)
    # CLIオプションで上書き
    uri = getattr(args, "neo4j_uri", None)
    user = getattr(args, "neo4j_user", None)
    password = getattr(args, "neo4j_password", None)
    if uri:
        neo4j_config.uri = uri
    if user:
        neo4j_config.user = user
    if password:
        neo4j_config.password = password

    connector = Neo4jConnector(project_root=project_root, config=neo4j_config)

    try:
        if direct:
            # Neo4jに直接書き込み
            print(f"Neo4jにエクスポート中... ({neo4j_config.uri})")
            stats = connector.export_graph(
                graph, clear_project=clear_project
            )
            print(f"\n=== Neo4jエクスポート完了 ===")
            print(f"ノード: {stats['nodes_created']}件")
            print(f"リレーション: {stats['relations_created']}件")
            if clear_project:
                print("（既存プロジェクトデータを削除後に投入）")
        else:
            # Cypherファイルとしてエクスポート
            output_file = getattr(args, "output", None)
            output_path = connector.export_cypher(
                graph,
                output_path=output_file,
                clear_project=clear_project,
            )
            rel_path = output_path.relative_to(project_root)
            print(f"Cypherエクスポート完了: {rel_path}")
            print(f"ノード: {len(graph.nodes)}件、リレーション: {len(graph.relations)}件")

        return 0

    except ImportError as e:
        print(f"エラー: {e}", file=sys.stderr)
        print("Neo4jへの直接接続が不要な場合は --target cypher を使用してください。")
        return 1
    except Exception as e:
        print(f"Neo4jエクスポートエラー: {e}", file=sys.stderr)
        return 1
    finally:
        connector.close()


def _print_mesh_stats_section(node: "Node") -> None:
    """メッシュ統計情報の専用セクションを表示

    mesh_node_count, mesh_element_count 等のプロパティが存在する場合に
    見やすく整形して出力する。
    """
    props = node.properties
    has_mesh = any(
        k.startswith("mesh_") for k in props
    )
    if not has_mesh:
        return

    print(f"\n  メッシュ統計:")
    if "mesh_node_count" in props:
        print(f"    節点数: {props['mesh_node_count']}")
    if "mesh_element_count" in props:
        print(f"    要素数: {props['mesh_element_count']}")

    elem_types = props.get("mesh_element_types")
    if isinstance(elem_types, dict) and elem_types:
        print(f"    要素タイプ:")
        for etype, count in elem_types.items():
            print(f"      {etype}: {count}")

    elset_summary = props.get("mesh_elset_summary")
    if isinstance(elset_summary, dict) and elset_summary:
        print(f"    Elset:")
        for eset, count in elset_summary.items():
            print(f"      {eset}: {count}")

    quality = props.get("mesh_quality")
    if isinstance(quality, dict) and quality:
        print(f"    品質統計:")
        for metric, stats in quality.items():
            if isinstance(stats, dict):
                parts = ", ".join(f"{sk}: {sv:.4g}" if isinstance(sv, float) else f"{sk}: {sv}" for sk, sv in stats.items())
                print(f"      {metric}: {parts}")
            else:
                print(f"      {metric}: {stats}")


def _run_info(project_root: Path, args: argparse.Namespace) -> int:
    """infoサブコマンドを実行 - ファイルのproperty/relationを表示

    指定方法:
    - ファイル名直打ち（複数可）: jj info go_idx1.inp mesh.inp
    - インデックス指定: jj info -id 1 2
    - バージョン指定: jj info -v 1 2
    - プロパティのみ表示: jj info -props go_idx1.inp
    """
    service = GraphService(project_root=project_root)
    filenames = getattr(args, "filename", []) or []
    index_filters = getattr(args, "index", None)
    version_filters = getattr(args, "version", None)
    props_only = getattr(args, "props_only", False)

    try:
        graph = service.load(filename=getattr(args, "file", None))

        if not graph.nodes:
            print("グラフデータが見つかりません。")
            print("まず 'jj parse' を実行してください。")
            return 1

        matched_nodes = []

        # ファイル名で検索（部分一致）
        # Windows環境でパス込み指定された場合、バックスラッシュをスラッシュに
        # 正規化し、basename抽出もPureWindowsPathで対応する。
        for filename in filenames:
            # パスの正規化: バックスラッシュ→スラッシュ
            normalized = filename.replace("\\", "/")
            # basename抽出（Windowsパスでもバックスラッシュ分割できるようPurePosixPathも利用）
            from pathlib import PurePosixPath, PureWindowsPath
            basename = PurePosixPath(normalized).name
            # Windows形式のバックスラッシュ区切りもfallback
            if basename == filename and "\\" in filename:
                basename = PureWindowsPath(filename).name

            for node in graph.nodes:
                if node in matched_nodes:
                    continue
                node_path = node.properties.get("path", "").replace("\\", "/")
                node_file = PurePosixPath(node_path).name if node_path else ""
                if (
                    node.name == basename
                    or node_file == basename
                    or node_path == normalized
                    or basename in node.name
                    or normalized in node_path
                    # 元のファイル名指定でも検索
                    or node.name == filename
                    or node_file == filename
                    or filename in node.name
                ):
                    matched_nodes.append(node)

        # インデックスで検索
        if index_filters is not None:
            for node in graph.nodes:
                if node in matched_nodes:
                    continue
                node_index = str(node.properties.get("index", ""))
                if node_index and node_index in index_filters:
                    matched_nodes.append(node)

        # バージョンで検索
        if version_filters is not None:
            # バージョンフィルタはマッチ済みノードに対して絞り込み、
            # または他の条件と組み合わせて使う
            if filenames or index_filters is not None:
                # 既存のマッチ結果から絞り込み
                matched_nodes = [
                    n for n in matched_nodes
                    if str(n.properties.get("version", "")) in version_filters
                ]
            else:
                # バージョンのみ指定の場合は全ノードから検索
                for node in graph.nodes:
                    node_ver = str(node.properties.get("version", ""))
                    if node_ver and node_ver in version_filters:
                        matched_nodes.append(node)

        # 何も指定がない場合
        if not filenames and index_filters is None and version_filters is None:
            print("ファイル名、-id、-v のいずれかを指定してください。")
            return 1

        if not matched_nodes:
            criteria = []
            if filenames:
                criteria.append(f"ファイル名: {', '.join(filenames)}")
            if index_filters:
                criteria.append(f"index: {', '.join(index_filters)}")
            if version_filters:
                criteria.append(f"version: {', '.join(version_filters)}")
            print(f"条件 ({'; '.join(criteria)}) に一致するノードが見つかりません。")
            return 1

        # ノードIDからノードへのマッピング
        node_by_id = {node.id: node for node in graph.nodes}

        for node in matched_nodes:
            print(f"\n=== {node.name} ===")
            if not props_only:
                print(f"  ID: {node.id}")
                print(f"  タイプ: {node.type}")
                print(f"  フォーマット: {node.format}")
                verbose_name = node.properties.get("verbose_name", "")
                if verbose_name:
                    print(f"  表示名: {verbose_name}")

            # プロパティ表示
            print(f"\n  プロパティ:")
            for key, value in sorted(node.properties.items()):
                if isinstance(value, list) and len(value) > 5:
                    print(f"    {key}: [{len(value)} items]")
                elif isinstance(value, dict):
                    print(f"    {key}:")
                    for dk, dv in value.items():
                        if isinstance(dv, dict):
                            # ネストされたdict（例: mesh_quality の各指標）
                            parts = ", ".join(f"{sk}: {sv}" for sk, sv in dv.items())
                            print(f"      {dk}: {{{parts}}}")
                        else:
                            print(f"      {dk}: {dv}")
                else:
                    print(f"    {key}: {value}")

            # メッシュ統計セクション
            _print_mesh_stats_section(node)

            # リレーション表示（-propsでない場合のみ）
            if not props_only:
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


def _run_credential(project_root: Path, args: argparse.Namespace) -> int:
    """credentialサブコマンドを実行 - 認証情報の暗号化保存・表示・削除"""
    cred_cmd = getattr(args, "credential_command", None)

    if cred_cmd is None:
        print("使用方法: jj credential <set|show|delete>")
        print("  set    : クレデンシャルを暗号化して保存")
        print("  show   : 保存済みクレデンシャルを表示")
        print("  delete : クレデンシャルを削除")
        return 1

    service = getattr(args, "service", "neo4j")

    if cred_cmd == "set":
        import getpass

        uri = getattr(args, "uri", None)
        user = getattr(args, "user", None)
        password = getattr(args, "password", None)
        database = getattr(args, "database", None)

        # 未指定の場合はインタラクティブに入力
        if uri is None:
            uri = input(f"URI [bolt://localhost:7687]: ").strip()
            if not uri:
                uri = "bolt://localhost:7687"
        if user is None:
            user = input(f"ユーザー名 [neo4j]: ").strip()
            if not user:
                user = "neo4j"
        if password is None:
            password = getpass.getpass("パスワード: ")
        if database is None:
            database = input(f"データベース名 [neo4j]: ").strip()
            if not database:
                database = "neo4j"

        creds = {
            "uri": uri,
            "user": user,
            "password": password,
            "database": database,
        }
        path = save_credentials(project_root, service, creds)
        print(f"クレデンシャルを暗号化して保存しました: {path}")
        print("※ .gitignoreに .jj/config/.credentials を追加することを推奨します")
        return 0

    elif cred_cmd == "show":
        unmask = getattr(args, "unmask", False)
        creds = load_credentials(project_root, service)

        if creds is None:
            print(f"サービス '{service}' のクレデンシャルが見つかりません。")
            print(f"'jj credential set --service {service}' で設定してください。")
            return 1

        print(f"=== {service} クレデンシャル ===")
        for key, value in creds.items():
            if unmask:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {mask_value(value)}")
        return 0

    elif cred_cmd == "delete":
        from services.credentials import _get_credentials_path
        import json as json_mod

        cred_path = _get_credentials_path(project_root)
        if not cred_path.exists():
            print(f"クレデンシャルファイルが見つかりません。")
            return 1

        try:
            all_creds = json_mod.loads(cred_path.read_text(encoding="utf-8"))
            if service in all_creds:
                del all_creds[service]
                cred_path.write_text(
                    json_mod.dumps(all_creds, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                print(f"サービス '{service}' のクレデンシャルを削除しました。")
            else:
                print(f"サービス '{service}' のクレデンシャルが見つかりません。")
        except Exception as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1
        return 0

    else:
        print(f"不明なサブコマンド: {cred_cmd}")
        return 1


def _resolve_file_path(project_root: Path, filename: str) -> Path | None:
    """ファイル名からファイルパスを解決

    直接パス指定、プロジェクトルート相対パス、再帰検索の順に試行する。
    """
    direct = Path(filename)
    if direct.exists():
        return direct
    relative = project_root / filename
    if relative.exists():
        return relative
    for found in project_root.rglob(filename):
        return found
    return None


def _run_diff(project_root: Path, args: argparse.Namespace) -> int:
    """diffサブコマンドを実行 - 2つのファイル間の差分を表示"""
    file1_arg = getattr(args, "file1", "")
    file2_arg = getattr(args, "file2", "")
    show_detail = getattr(args, "detail", False)

    try:
        file1 = _resolve_file_path(project_root, file1_arg)
        if file1 is None:
            print(f"ファイルが見つかりません: {file1_arg}", file=sys.stderr)
            return 1

        file2 = _resolve_file_path(project_root, file2_arg)
        if file2 is None:
            print(f"ファイルが見つかりません: {file2_arg}", file=sys.stderr)
            return 1

        print(f"比較: {file1.name} ← → {file2.name}")
        print()

        if file1.suffix.lower() == ".inp" and file2.suffix.lower() == ".inp":
            left_abq = abq_read_inp(str(file1), verbose=False)
            right_abq = abq_read_inp(str(file2), verbose=False)
            diffs = diff_abq_blocks(left_abq, right_abq)

            if not diffs:
                print("差分はありません。")
                return 0

            summary = format_diff_summary_table(diffs)
            print("=== サマリー ===")
            print(summary)

            if show_detail:
                details = format_diff_blocks_markdown(diffs)
                print("\n=== 詳細 ===")
                print(details)
        else:
            import difflib

            try:
                text1 = file1.read_text(encoding="utf-8", errors="ignore").splitlines()
                text2 = file2.read_text(encoding="utf-8", errors="ignore").splitlines()
            except (OSError, IOError) as e:
                print(f"ファイル読み込みエラー: {e}", file=sys.stderr)
                return 1

            diff = difflib.unified_diff(
                text1, text2,
                fromfile=str(file1.name),
                tofile=str(file2.name),
                lineterm="",
            )
            diff_lines = list(diff)
            if not diff_lines:
                print("差分はありません。")
                return 0

            for line in diff_lines:
                print(line)

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
