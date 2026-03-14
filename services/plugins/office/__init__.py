"""Officeプラグイン: PPTX/XLSXファイル解析・エクスポート

Office系ファイル（PowerPoint, Excel）のメタデータ抽出と
書式付きエクスポート機能を提供するプラグインパッケージ。

## 登録されるパーサー（AbstractFileParserサブクラス）

| パーサー | priority | 説明 |
|----------|----------|------|
| PptxMetadataParser | 35 | .pptxファイルのメタデータ抽出（スライド数・テキスト・画像数） |
| XlsxMetadataParser | 35 | .xlsxファイルのメタデータ抽出（シート名・行列数） |

## 登録されるエクスポーター（AbstractExporterサブクラス）

| エクスポーター | format | 説明 |
|---------------|--------|------|
| ExcelExporter | xlsx | 書式付きExcelファイル出力（メイリオ・ヘッダー色付き） |
| PptxExporter | pptx | PowerPointファイル出力（ギャラリー・プロット画像埋め込み） |

## 依存パッケージ

- python-pptx>=0.6.21（オプション: PPTXパーサー/エクスポーター）
- openpyxl>=3.0.0（オプション: XLSXパーサー/エクスポーター）

[READMEへ戻る](../../../../README.md)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register() -> None:
    """Officeプラグインの全コンポーネントを登録する

    python-pptx / openpyxl が利用可能な場合のみ対応パーサー・エクスポーターを登録する。
    """
    global _registered
    if _registered:
        return
    _registered = True

    # PPTX パーサー（python-pptx がなくても基本メタデータは抽出可能）
    try:
        import services.parse.connectors.office.pptx_parser

        logger.debug("PPTX パーサーを登録")
    except ImportError:
        logger.debug("PPTX パーサーのロードをスキップ（python-pptx 不足）")

    # XLSX パーサー（openpyxl がなくても基本メタデータは抽出可能）
    try:
        import services.parse.connectors.office.xlsx_parser

        logger.debug("XLSX パーサーを登録")
    except ImportError:
        logger.debug("XLSX パーサーのロードをスキップ（openpyxl 不足）")

    # Excel エクスポーター
    try:
        import services.export.connectors.excel_export

        logger.debug("Excel エクスポーターを登録")
    except ImportError:
        logger.debug("Excel エクスポーターのロードをスキップ（openpyxl 不足）")

    # PPTX エクスポーター
    try:
        import services.export.connectors.pptx_export  # noqa: F401

        logger.debug("PPTX エクスポーターを登録")
    except ImportError:
        logger.debug("PPTX エクスポーターのロードをスキップ（python-pptx 不足）")

    logger.debug("Officeプラグインを登録完了")


# モジュールインポート時に自動登録
register()
