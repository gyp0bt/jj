"""Flow-3Dプラグイン: prepinファイル解析・結果ファイル認識

Flow-3D固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| Flow3dPrepinParser | 60 | prepin.*ファイルのパラメータ解析 |

## ファイル構造

- prepin.*: インプット（出力種類.ジョブ名の逆転形式）
- flsgrf.*/flsprt.*/prpgrf.*: 結果ファイル（バイナリ）
- report.*: レポート
- ソース単位: ディレクトリ
- filename-pattern: reversed（basename=出力種類、拡張子=ジョブ名）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """Flow-3Dプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import services.parse.connectors.flow3d.prepin_parser  # noqa: F401

    logger.debug("Flow-3Dプラグインを登録完了")


# モジュールインポート時に自動登録
register()
