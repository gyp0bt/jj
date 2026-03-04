"""jj外部プラグインの実例パッケージ

このパッケージは、jjの外部プラグインシステムを使って
独自のソルバー対応を追加する方法を示すサンプルです。

## プラグインの仕組み

1. pyproject.tomlの[project.entry-points]でエントリーポイントを登録
2. jjの起動時にentry_points経由でregister()が呼ばれる
3. register()内でパーサー/エクスポーター/コネクターをインポート
4. __init_subclass__により各コンポーネントが自動登録される

## 使い方

    # 開発モードでインストール
    pip install -e .

    # jjのプラグインとして自動検出される
    jj parse /path/to/project

[← README.md](../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """プラグインの全コンポーネントを登録する

    jj.pluginsエントリーポイント経由で呼び出される。
    idempotent（2回目以降の呼び出しはスキップ）。
    """
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（__init_subclass__で自動登録）
    import jj_plugin_example.parser

    # ダッシュボードコネクターのインポート（optional）
    try:
        import jj_plugin_example.dashboard  # noqa: F401
    except ImportError:
        logger.debug("Dashboard connector skipped (streamlit not available)")

    logger.debug("example_solverプラグインを登録完了")


# モジュールインポート時にも自動登録
register()
