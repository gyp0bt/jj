"""Abaqusプラグイン: INP解析・結果ファイル解析・メッシュ統計・差分比較・ジョブ投入

Abaqus固有のパーサー・ダッシュボードコネクター・ジョブ投入サービスを集約するプラグインパッケージ。
このモジュールをインポートすると、以下のコンポーネントが自動登録される:

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| AbaqusParameterParser | 15 | *PARAMETER/**propsプロパティ抽出 |
| AbaqusInpParser | 60 | material.inp解析、材料ノード生成 |
| AbaqusResultParser | 70 | .sta/.msg/.dat解析 |
| AbaqusMeshParser | 80 | pymeshメッシュ品質統計（requires_full） |
| MeshInheritParser | 81 | includeプロパティ継承（競合時は接頭辞エスケープ） |
| AbaqusMaterialAssignmentParser | 85 | 材料割り当て |
| AbaqusDiffParser | 90 | バージョン間diff |
| AbaqusElsetParser | 98 | elsetノード化 |

## 登録されるダッシュボードコネクター

| コネクター | page_label | 説明 |
|------------|------------|------|
| AbaqusMaterialPageConnector | 物性一覧 | 材料テーブル・プロパティカーブ表示 |

## サービス

- SubmitService: Abaqusジョブ投入・ターゲット解決・ファイル操作

## コアモジュール（services.parse.connectors.abaqus）

- ABQData: INP解析結果データ構造
- read_inp(): INPファイル読み込み
- diff_abq_blocks(): ブロック差分比較
- mesh.py: pymeshメッシュ品質統計

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """Abaqusプラグインの全コンポーネントを登録する

    __init_subclass__パターンにより、モジュールをimportするだけで
    各パーサー・コネクターがレジストリに自動登録される。
    """
    global _registered
    if _registered:
        return
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import services.parse.connectors.abaqus.diff_parser
    import services.parse.connectors.abaqus.inp_parser

    # import services.parse.connectors.abaqus.mesh_inherit_parser
    import services.parse.connectors.abaqus.mesh_parser
    import services.parse.connectors.abaqus.parameter_parser
    import services.parse.connectors.abaqus.result_parser

    # ダッシュボードコネクターのインポート（自動登録が発動）
    try:
        import services.dashboard.connectors.abaqus  # noqa: F401
    except ImportError:
        logger.debug("Abaqusダッシュボードコネクターのロードをスキップ（依存パッケージ不足）")

    logger.debug("Abaqusプラグインを登録完了")


# モジュールインポート時に自動登録
register()
