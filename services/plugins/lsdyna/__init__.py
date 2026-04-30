"""LS-DYNAプラグイン: キーワード解析・結果ファイル解析

LS-DYNA固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| LsDynaKeywordParser | 60 | .k/.key/.datキーワードカード解析 |

## ファイル構造

- .k/.key/.dat: インプット（キーワードカード形式）
- d3plot: バイナリ結果（拡張子なし）
- d3hsp/glstat/matsum/messag: テキストログ/統計
- ソース単位: ディレクトリ（1フォルダ=1計算ケース）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """LS-DYNAプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    # import services.parse.connectors.lsdyna.keyword_parser  # noqa: F401

    # logger.debug("LS-DYNAプラグインを登録完了")


# モジュールインポート時に自動登録
register()
