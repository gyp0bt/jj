"""OpenFOAMプラグイン: ケースディレクトリ解析・辞書ファイル解析

OpenFOAM固有のパーサーを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| OpenFoamCaseParser | 60 | ケースディレクトリ構造の検出・controlDict解析 |

## ファイル構造

- system/controlDict, fvSchemes, fvSolution: ソルバー設定
- constant/: 定数定義（transportProperties等）
- 0/: 初期条件（U, p, T等）
- 100/, 200/, ...: タイムステップ結果ディレクトリ
- postProcessing/: 後処理結果
- ソース単位: ディレクトリ（ケース=system+constant+0+結果）
- filename-pattern: none（拡張子なし、ディレクトリ構造が意味を持つ）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """OpenFOAMプラグインの全コンポーネントを登録する"""
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    # import services.parse.connectors.openfoam.case_parser  # noqa: F401

    # logger.debug("OpenFOAMプラグインを登録完了")


# モジュールインポート時に自動登録
register()
