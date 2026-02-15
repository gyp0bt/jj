"""CalculiXプラグイン: Abaqusサブセット.inp解析・結果ファイル解析

CalculiX固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| CalculixInpParser | 60 | Abaqusサブセットの.inp解析（CalculiX固有拡張検出） |

## ファイル構造

- .inp: インプット（Abaqusサブセット形式）
- .frd: 結果ファイル
- .sta: ステータス（Abaqusと同名）
- .dat: 結果データ（Abaqusと同名）
- .cvg: 収束情報
- ソース単位: ファイル（Abaqusに近い）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """CalculiXプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import services.parse.connectors.calculix.inp_parser  # noqa: F401

    logger.debug("CalculiXプラグインを登録完了")


# モジュールインポート時に自動登録
register()
