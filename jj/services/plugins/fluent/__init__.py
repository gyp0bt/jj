"""Fluentプラグイン: ジャーナルファイル解析・結果データ認識

Fluent固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| FluentJournalParser | 60 | .jouジャーナルファイルのテキスト解析 |

## ファイル構造

- .cas.h5: ケースファイル（HDF5バイナリ、インプット）
- .dat.h5: 結果データ（HDF5バイナリ）
- .jou: ジャーナルファイル（バッチ実行用、独自記法テキスト）
- .out: テーブル形式リザルトデータ
- .xy: テーブル形式リザルトデータ（XYプロット）
- .msh: メッシュファイル
- ソース単位: ファイル

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """Fluentプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import services.parse.connectors.fluent.journal_parser  # noqa: F401

    logger.debug("Fluentプラグインを登録完了")


# モジュールインポート時に自動登録
register()
