"""jj graph コマンド: グラフデータの管理

このモジュールはCLI層のみを担当し、ビジネスロジックはservices.serviceから呼び出します。

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
from typing import Any

import yaml

from services.lib.selection import expand_ranges
from services.service.graph_command import GraphCommandService


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
    parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="全パーサーを実行（pymeshメッシュ統計等の重い処理を含む）",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="ディレクトリ階層の最大深さ（デフォルト: 無制限＝最終階層まで）",
    )
    parser.add_argument(
        "-debug",
        "--debug",
        action="store_true",
        default=False,
        help="デバッグモード: パーサーでエラーが発生した場合に例外をraiseする",
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
        "--full",
        action="store_true",
        default=False,
        help="--parse時に全パーサーを実行（pymeshメッシュ統計等の重い処理を含む）",
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
    parser.add_argument(
        "-id",
        "--index",
        type=str,
        nargs="*",
        default=None,
        help="インデックスで選択（例: -id 1 2、1..3で範囲展開）",
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        nargs="*",
        default=None,
        help="バージョンで選択（例: -v 1 2、1..3で範囲展開）",
    )
    parser.add_argument(
        "-all",
        "--all-nodes",
        action="store_true",
        help="全ノードを選択",
    )
    parser.add_argument(
        "-prop",
        "--prop",
        type=str,
        nargs="*",
        default=None,
        help="プロパティキーで絞り込み（AND条件）",
    )
    parser.add_argument(
        "-active",
        "--active",
        action="store_true",
        help="activeがtrueのノードのみエクスポート",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        default=False,
        help="JSONエクスポート時にプロパティを平坦化する（CSVは常に平坦化）",
    )
    parser.add_argument(
        "--unit-format",
        choices=["header", "row"],
        default=None,
        help="CSV単位表示形式: header={column}[{unit}]、row=2行目に単位行（デフォルト: config設定）",
    )
    parser.add_argument(
        "--columns",
        type=str,
        nargs="*",
        default=None,
        help="CSVエクスポートするカラム名を指定（globパターン対応: stress* mesh_*等。config設定を上書き）",
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
        help="インデックスで指定（例: -id 1 2、1..3で範囲展開）",
    )
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        nargs="*",
        default=None,
        help="バージョンで指定（例: -v 1 2、1..3で範囲展開）",
    )
    parser.add_argument(
        "-type",
        "--type",
        type=str,
        default=None,
        help="ノードタイプでフィルタリング（例: -type Abaqusインプット）",
    )
    parser.add_argument(
        "-all",
        "--all-nodes",
        action="store_true",
        help="全ノードを選択",
    )
    parser.add_argument(
        "-prop",
        "--prop",
        type=str,
        nargs="*",
        default=None,
        help="指定プロパティを持つノードのみ表示し、そのプロパティ値を出力",
    )
    parser.add_argument(
        "-active",
        "--active",
        action="store_true",
        help="activeがtrueのノードのみ表示",
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
    cred_sub = parser.add_subparsers(
        dest="credential_command", help="クレデンシャル操作"
    )

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


# =========
# 各コマンド実行（CLI層：出力整形のみ）
# =========


def _run_init(project_root: Path, args: argparse.Namespace) -> int:
    """initサブコマンドを実行"""
    overwrite = getattr(args, "overwrite", False)
    service = GraphCommandService(project_root)

    try:
        config_path = service.init_config(overwrite=overwrite)
        print(f"設定ファイルを初期化しました: {config_path}")
        if overwrite:
            print("（既存ファイルを上書きしました）")
        return 0
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_parse(project_root: Path, args: argparse.Namespace) -> int:
    """parseサブコマンドを実行"""
    service = GraphCommandService(project_root)

    output_file = getattr(args, "output", None)
    fmt = getattr(args, "format", "yaml")
    full_mode = getattr(args, "full", False)
    max_depth = getattr(args, "max_depth", None)
    debug = getattr(args, "debug", False)

    mode_label = "full" if full_mode else "lite"
    print(f"プロジェクトをスキャン中 ({mode_label}): {project_root}")

    try:
        result = service.parse(
            output_file=output_file,
            format=fmt,
            full_mode=full_mode,
            max_depth=max_depth,
            debug=debug,
        )

        print(f"\n=== スキャン完了 ===")
        print(f"ノード数: {result.summary['total_nodes']}")
        print(f"リレーション数: {result.summary['total_relations']}")
        print(f"\nノードタイプ別:")
        for node_type, count in result.summary["nodes_by_type"].items():
            print(f"  {node_type}: {count}")
        print(f"\n保存先: {result.save_path}")
        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_show(project_root: Path, args: argparse.Namespace) -> int:
    """showサブコマンドを実行"""
    service = GraphCommandService(project_root)

    try:
        result = service.show(
            filename=getattr(args, "file", None),
            type_filter=getattr(args, "type", None),
            summary_only=getattr(args, "summary", False),
        )

        if result.empty:
            print("グラフデータが見つかりません。")
            print("まず 'jj g parse' を実行してください。")
            return 1

        if result.summary:
            print("=== グラフサマリー ===")
            print(f"ノード数: {result.summary['total_nodes']}")
            print(f"リレーション数: {result.summary['total_relations']}")
            print(f"\nノードタイプ別:")
            for node_type, count in result.summary["nodes_by_type"].items():
                print(f"  {node_type}: {count}")
            return 0

        print(f"=== ノード一覧 ({len(result.nodes)}件) ===\n")
        for node in result.nodes:
            print(f"[{node.id}] {node.name}")
            print(f"    タイプ: {node.type}")
            print(f"    フォーマット: {node.format}")
            path = node.properties.get("path", "")
            if path:
                print(f"    パス: {path}")
            print()

        if result.relations:
            print(f"=== リレーション ({len(result.relations)}件) ===\n")
            for rel in result.relations:
                print(f"[{rel.id}] {rel.node1_id} --{rel.label}--> {rel.node2_id}")

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _run_export(project_root: Path, args: argparse.Namespace) -> int:
    """exportサブコマンドを実行"""
    service = GraphCommandService(project_root)

    try:
        # グラフデータのロード（--parse オプションで事前parse可能）
        do_parse = getattr(args, "parse", False)
        full_mode = getattr(args, "full", False)

        graph, parse_result = service.load_or_parse(
            filename=getattr(args, "file", None),
            do_parse=do_parse,
            full_mode=full_mode,
        )

        if parse_result:
            mode_label = "full" if full_mode else "lite"
            print(f"プロジェクトをスキャン中 ({mode_label}): {project_root}")
            print(
                f"スキャン完了: ノード {parse_result.summary['total_nodes']}件、"
                f"リレーション {parse_result.summary['total_relations']}件"
            )
            print(f"保存先: {parse_result.save_path}")

        if not graph.nodes:
            print("グラフデータが見つかりません。")
            print("'jj parse' または 'jj export --parse' を実行してください。")
            return 1

        target = getattr(args, "target", "obsidian")

        if target == "obsidian":
            return _print_export_obsidian(service, graph, project_root, args)
        elif target in ("csv", "json"):
            return _print_export_data(service, graph, target, args)
        elif target == "neo4j":
            return _print_export_neo4j(service, graph, args, direct=True)
        elif target == "cypher":
            return _print_export_neo4j(service, graph, args, direct=False)
        else:
            print(f"未対応のエクスポート先: {target}")
            return 1

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _print_export_obsidian(
    service: GraphCommandService,
    graph: "GraphModel",
    project_root: Path,
    args: argparse.Namespace,
) -> int:
    """Obsidianエクスポートの出力整形"""
    print(f"Obsidianにエクスポート中...")
    result = service.export_obsidian(
        graph, overwrite=getattr(args, "overwrite", False)
    )

    print(f"\n=== エクスポート完了 ===")
    print(f"書き込みファイル数: {len(result.written_paths)}")
    if result.written_paths:
        print("\n書き込んだファイル:")
        for path in result.written_paths[:10]:
            rel_path = path.relative_to(project_root)
            print(f"  {rel_path}")
        if len(result.written_paths) > 10:
            print(f"  ... 他 {len(result.written_paths) - 10} 件")
    return 0


def _print_export_data(
    service: GraphCommandService,
    graph: "GraphModel",
    target: str,
    args: argparse.Namespace,
) -> int:
    """CSV/JSONエクスポートの出力整形"""
    try:
        result = service.export_data(
            graph,
            target,
            type_filter=getattr(args, "type", None),
            select_filter=getattr(args, "select", None),
            output_file=getattr(args, "output", None),
            index_filters=expand_ranges(getattr(args, "index", None)),
            version_filters=expand_ranges(getattr(args, "version", None)),
            all_nodes=getattr(args, "all_nodes", False),
            prop_filters=getattr(args, "prop", None),
            flatten=getattr(args, "flatten", False),
            active_only=getattr(args, "active", False),
            unit_format=getattr(args, "unit_format", None),
            columns=getattr(args, "columns", None),
        )
        label = "CSV" if target == "csv" else "JSON"
        print(f"{label}エクスポート完了: {result.output_path} ({result.count}件)")
        return 0
    except ValueError as e:
        print(str(e))
        return 1


def _print_export_neo4j(
    service: GraphCommandService,
    graph: "GraphModel",
    args: argparse.Namespace,
    direct: bool = True,
) -> int:
    """Neo4j/Cypherエクスポートの出力整形"""
    try:
        result = service.export_neo4j(
            graph,
            direct=direct,
            clear_project=getattr(args, "clear", False),
            neo4j_uri=getattr(args, "neo4j_uri", None),
            neo4j_user=getattr(args, "neo4j_user", None),
            neo4j_password=getattr(args, "neo4j_password", None),
            output_file=getattr(args, "output", None),
        )

        if result.direct:
            print(f"Neo4jにエクスポート中... ({result.uri})")
            print(f"\n=== Neo4jエクスポート完了 ===")
            print(f"ノード: {result.node_count}件")
            print(f"リレーション: {result.relation_count}件")
            if result.clear_project:
                print("（既存プロジェクトデータを削除後に投入）")
        else:
            if result.output_path:
                try:
                    rel_path = result.output_path.relative_to(service.project_root)
                except ValueError:
                    rel_path = result.output_path
                print(f"Cypherエクスポート完了: {rel_path}")
            print(
                f"ノード: {result.node_count}件、"
                f"リレーション: {result.relation_count}件"
            )

        return 0

    except ImportError as e:
        print(f"エラー: {e}", file=sys.stderr)
        print("Neo4jへの直接接続が不要な場合は --target cypher を使用してください。")
        return 1
    except Exception as e:
        print(f"Neo4jエクスポートエラー: {e}", file=sys.stderr)
        return 1


def _run_info(project_root: Path, args: argparse.Namespace) -> int:
    """infoサブコマンドを実行 - ファイルのproperty/relationを表示"""
    service = GraphCommandService(project_root)

    filenames = getattr(args, "filename", []) or []
    index_filters = expand_ranges(getattr(args, "index", None))
    version_filters = expand_ranges(getattr(args, "version", None))
    type_filter = getattr(args, "type", None)
    all_nodes = getattr(args, "all_nodes", False)
    prop_filters = getattr(args, "prop", None)
    props_only = getattr(args, "props_only", False)
    active_only = getattr(args, "active", False)

    try:
        result = service.info(
            filenames=filenames or None,
            index_filters=index_filters,
            version_filters=version_filters,
            type_filter=type_filter,
            all_nodes=all_nodes,
            prop_filters=prop_filters,
            active_only=active_only,
            graph_filename=getattr(args, "file", None),
        )

        if result.empty:
            print("グラフデータが見つかりません。")
            print("まず 'jj parse' を実行してください。")
            return 1

        if result.no_criteria:
            print("ファイル名、-id、-v、-all のいずれかを指定してください。")
            return 1

        if not result.nodes:
            criteria = []
            if filenames:
                criteria.append(f"ファイル名: {', '.join(filenames)}")
            if index_filters:
                criteria.append(f"index: {', '.join(index_filters)}")
            if version_filters:
                criteria.append(f"version: {', '.join(version_filters)}")
            if type_filter:
                criteria.append(f"type: {type_filter}")
            if all_nodes:
                criteria.append("all")
            if prop_filters:
                criteria.append(f"prop: {', '.join(prop_filters)}")
            print(f"条件 ({'; '.join(criteria)}) に一致するノードが見つかりません。")
            return 1

        # ノードIDからノードへのマッピング
        node_by_id = {node.id: node for node in result.graph.nodes}

        for node in result.nodes:
            print(f"\n=== {node.name} ===")
            if not props_only and not prop_filters:
                print(f"  ID: {node.id}")
                print(f"  タイプ: {node.type}")
                print(f"  フォーマット: {node.format}")
                verbose_name = node.properties.get("verbose_name", "")
                if verbose_name:
                    print(f"  表示名: {verbose_name}")

            if prop_filters:
                # -prop指定時: 指定プロパティのみ表示
                for prop_key in prop_filters:
                    value = node.properties.get(prop_key)
                    if value is not None:
                        print(f"  {prop_key}: {_format_prop_value(value)}")
            else:
                # プロパティ表示（yamlソースをありのまま出力）
                print(f"\n  プロパティ:")
                props_yaml = yaml.safe_dump(
                    dict(sorted(node.properties.items())),
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
                for line in props_yaml.rstrip("\n").split("\n"):
                    print(f"    {line}")

            # リレーション表示（-propsでない場合のみ、-prop指定時は非表示）
            if not props_only and not prop_filters:
                rels = service.get_relations_for_node(result.graph, node.id)
                if rels:
                    print(f"\n  リレーション ({len(rels)}件):")
                    for rel in rels:
                        if rel.node1_id == node.id:
                            target = node_by_id.get(rel.node2_id)
                            target_name = (
                                target.name if target else f"ID:{rel.node2_id}"
                            )
                            print(f"    --{rel.label}--> {target_name}")
                        else:
                            source = node_by_id.get(rel.node1_id)
                            source_name = (
                                source.name if source else f"ID:{rel.node1_id}"
                            )
                            print(f"    <--{rel.label}-- {source_name}")

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


def _format_prop_value(value: Any) -> str:
    """プロパティ値を表示用にフォーマット"""
    if isinstance(value, dict):
        return yaml.safe_dump(
            value, allow_unicode=True, default_flow_style=False
        ).rstrip("\n")
    if isinstance(value, list):
        return yaml.safe_dump(
            value, allow_unicode=True, default_flow_style=False
        ).rstrip("\n")
    return str(value)


def _run_credential(project_root: Path, args: argparse.Namespace) -> int:
    """credentialサブコマンドを実行 - 認証情報の暗号化保存・表示・削除"""
    cred_cmd = getattr(args, "credential_command", None)

    if cred_cmd is None:
        print("使用方法: jj credential <set|show|delete>")
        print("  set    : クレデンシャルを暗号化して保存")
        print("  show   : 保存済みクレデンシャルを表示")
        print("  delete : クレデンシャルを削除")
        return 1

    service_name = getattr(args, "service", "neo4j")
    service = GraphCommandService(project_root)

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
        path = service.credential_set(service_name, creds)
        print(f"クレデンシャルを暗号化して保存しました: {path}")
        print("※ .gitignoreに .jj/config/.credentials を追加することを推奨します")
        return 0

    elif cred_cmd == "show":
        unmask = getattr(args, "unmask", False)
        result = service.credential_show(service_name, unmask=unmask)

        if not result.found:
            print(f"サービス '{service_name}' のクレデンシャルが見つかりません。")
            print(f"'jj credential set --service {service_name}' で設定してください。")
            return 1

        print(f"=== {service_name} クレデンシャル ===")
        if result.credentials:
            for key, value in result.credentials.items():
                print(f"  {key}: {value}")
        return 0

    elif cred_cmd == "delete":
        deleted = service.credential_delete(service_name)

        if not deleted:
            print(f"サービス '{service_name}' のクレデンシャルが見つかりません。")
            return 1

        print(f"サービス '{service_name}' のクレデンシャルを削除しました。")
        return 0

    else:
        print(f"不明なサブコマンド: {cred_cmd}")
        return 1


def _run_diff(project_root: Path, args: argparse.Namespace) -> int:
    """diffサブコマンドを実行 - 2つのファイル間の差分を表示"""
    service = GraphCommandService(project_root)

    file1_arg = getattr(args, "file1", "")
    file2_arg = getattr(args, "file2", "")
    show_detail = getattr(args, "detail", False)

    try:
        result = service.diff(file1_arg, file2_arg, show_detail=show_detail)

        if result.error:
            print(result.error, file=sys.stderr)
            return 1

        print(f"比較: {result.file1.name} ← → {result.file2.name}")
        print()

        if not result.has_diffs:
            print("差分はありません。")
            return 0

        if result.is_inp:
            if result.summary_table:
                print("=== サマリー ===")
                print(result.summary_table)

            if result.detail_markdown:
                print("\n=== 詳細 ===")
                print(result.detail_markdown)
        else:
            for line in result.unified_diff_lines:
                print(line)

        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
