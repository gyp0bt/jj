"""ランチャーモジュール: dashboard / serve の起動ロジック

CLIのgraph.pyからdashboard・serveの起動ロジックを分離し、
それぞれのオプショナル依存関係を明確化する。

依存関係:
  dashboard: streamlit, plotly（オプショナル）
  serve: fastapi, uvicorn（オプショナル）
  → いずれも未インストールでもCLI自体は起動可能

[READMEへ戻る](../../../README.md)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def add_dashboard_args(parser: argparse.ArgumentParser) -> None:
    """dashboardコマンドの引数を追加"""
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Streamlitサーバーのポート番号（デフォルト: 8501）",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="ブラウザを自動で開かない",
    )


def add_serve_args(parser: argparse.ArgumentParser) -> None:
    """serveコマンドの引数を追加"""
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="APIサーバーのポート番号（デフォルト: 8080）",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="バインドするホスト（デフォルト: 127.0.0.1）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="ファイル変更時に自動リロード（開発用）",
    )


def run_dashboard(project_root: Path, args: argparse.Namespace) -> int:
    """dashboardサブコマンドを実行 - Streamlitダッシュボードを起動

    Streamlitがインストールされていない場合はエラーメッセージを表示して終了する。
    ダッシュボードはサブプロセスとして起動されるため、services/dashboard/の
    インポートはここでは発生しない（Streamlitプロセス内で行われる）。

    Args:
        project_root: jjプロジェクトのルートパス
        args: コマンドライン引数

    Returns:
        終了コード
    """
    port = getattr(args, "port", 8501)
    no_browser = getattr(args, "no_browser", False)

    try:
        import streamlit  # noqa: F401
    except ImportError:
        print(
            "エラー: streamlitがインストールされていません。",
            file=sys.stderr,
        )
        print("  pip install streamlit plotly", file=sys.stderr)
        return 1

    import os
    import subprocess

    # Streamlitアプリのパスを取得
    app_path = Path(__file__).parent.parent / "dashboard" / "app.py"
    if not app_path.exists():
        print(f"エラー: ダッシュボードアプリが見つかりません: {app_path}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["JJ_PROJECT_ROOT"] = str(project_root)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
    ]

    if no_browser:
        cmd.extend(["--server.headless", "true"])

    print(f"ダッシュボードを起動します: http://localhost:{port}")
    print("終了するには Ctrl+C を押してください。")

    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except KeyboardInterrupt:
        print("\nダッシュボードを終了しました。")
        return 0


def run_serve(project_root: Path, args: argparse.Namespace) -> int:
    """serveサブコマンドを実行 - FastAPI REST APIサーバーを起動

    FastAPI/uvicornがインストールされていない場合はエラーメッセージを表示して終了する。
    APIモジュール（services/api/）は遅延インポートされるため、
    FastAPI未インストール環境でもCLI自体は起動可能。

    Args:
        project_root: jjプロジェクトのルートパス
        args: コマンドライン引数

    Returns:
        終了コード
    """
    port = getattr(args, "port", 8080)
    host = getattr(args, "host", "127.0.0.1")

    try:
        import uvicorn
    except ImportError:
        print(
            "エラー: uvicornがインストールされていません。",
            file=sys.stderr,
        )
        print("  pip install fastapi uvicorn", file=sys.stderr)
        return 1

    try:
        import fastapi  # noqa: F401
    except ImportError:
        print(
            "エラー: fastapiがインストールされていません。",
            file=sys.stderr,
        )
        print("  pip install fastapi uvicorn", file=sys.stderr)
        return 1

    import os

    os.environ["JJ_PROJECT_ROOT"] = str(project_root)

    print(f"APIサーバーを起動します: http://{host}:{port}")
    print(f"APIドキュメント: http://{host}:{port}/docs")
    print("終了するには Ctrl+C を押してください。")

    try:
        from services.api.routes import create_app

        app = create_app(project_root)
        uvicorn.run(app, host=host, port=port)
        return 0
    except KeyboardInterrupt:
        print("\nAPIサーバーを終了しました。")
        return 0
