"""Abaqusプラグイン: INP解析・結果ファイル解析・メッシュ統計・差分比較・ジョブ投入

Abaqus固有のパーサー・ジョブ投入サービスを集約するプラグインパッケージ。
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

## サービス

- SubmitService: Abaqusジョブ投入・ターゲット解決・ファイル操作

## コアモジュール（plugins.abaqus.parse）

- ABQData: INP解析結果データ構造
- read_inp(): INPファイル読み込み
- diff_abq_blocks(): ブロック差分比較
- mesh.py: pymeshメッシュ品質統計

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

import logging

from services.sdk.plugin_manifest import PluginManifest

logger = logging.getLogger(__name__)

_registered = False


def register() -> PluginManifest | None:
    """Abaqusプラグインの全コンポーネントを登録する

    __init_subclass__パターンにより、モジュールをimportするだけで
    各パーサー・コネクターがレジストリに自動登録される。
    PluginManifest を返すことで PluginManager がメタデータを管理する。
    """
    global _registered
    if _registered:
        return None
    _registered = True

    # パーサーのインポート（自動登録が発動）
    import plugins.abaqus.parse.diff_parser
    import plugins.abaqus.parse.inp_parser
    import plugins.abaqus.parse.inp_parser_base
    import plugins.abaqus.parse.mesh_inherit_parser
    import plugins.abaqus.parse.mesh_parser
    import plugins.abaqus.parse.parameter_parser
    import plugins.abaqus.parse.result_parser  # noqa: F401

    logger.debug("Abaqusプラグインを登録完了")

    return PluginManifest(
        name="abaqus",
        version="0.2.1",
        description="Abaqus INP解析・結果ファイル解析・メッシュ統計・差分比較・ジョブ投入",
        parsers=[
            "plugins.abaqus.parse.parameter_parser",
            "plugins.abaqus.parse.inp_parser_base",
            "plugins.abaqus.parse.result_parser",
            "plugins.abaqus.parse.inp_parser",
            "plugins.abaqus.parse.mesh_parser",
            "plugins.abaqus.parse.mesh_inherit_parser",
            "plugins.abaqus.parse.diff_parser",
        ],
        optional_dependencies={
            "pymesh": "pymesh（メッシュ統計）",
        },
    )


# モジュールインポート時に自動登録
register()
