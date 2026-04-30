"""HFSSプラグイン（Ansys Electronics Desktop）: .aedtファイル部分解析・実行ログ解析

HFSS固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| HfssAedtParser | 60 | .aedtファイルの部分テキスト領域解析 |

## ファイル構造

- .aedt: プロジェクトファイル（バイナリ、部分的にテキスト埋め込み）
- .aedt.batchinfo/: 計算実行ログディレクトリ
- .aedtresults/: 結果ディレクトリ
- .csv: GUI上でエクスポートした波形・レポートデータ
- .s2p: Touchstoneフォーマット（Sパラメータ等、GUIエクスポート）
- ソース単位: ファイル（.aedtが主インプット）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """HFSSプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    # import services.parse.connectors.hfss.aedt_parser  # noqa: F401

    # logger.debug("HFSSプラグインを登録完了")


# モジュールインポート時に自動登録
register()
