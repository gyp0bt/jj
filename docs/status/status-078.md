[← README.md](../../README.md) | [← status-index](status-index.md)

# status-078 — PPTX/XLSX連携プラグイン実装（W-1〜W-5）

**日付**: 2026-03-14
**ブランチ**: claude/pptx-xlsx-integration-PQbpD
**作業者**: Claude Code

---

## 概要

windows-integration.md仕様書に基づき、Office連携プラグイン（PPTX/XLSX）をフル実装。
パーサー（メタデータ抽出）、エクスポーター（書式付き出力）、ダッシュボード統合（ダウンロードボタン）の3層を構築。

## 実施内容

### 1. Officeプラグイン基盤

**場所**: `services/plugins/office/__init__.py`

- `register()` 関数でパーサー・エクスポーターを遅延登録
- python-pptx / openpyxl の有無に応じてgraceful degradation
- `pyproject.toml` に entry_point `office` を追加

### 2. PPTXメタデータパーサー（priority=35）

**場所**: `services/parse/connectors/office/pptx_parser.py`

- .pptxファイルからスライド数・テキスト長・画像数・タイトル一覧・コアプロパティを抽出
- プロパティキー: `pptx.slide_count`, `pptx.image_count`, `pptx.slide_titles`, `pptx.author` 等
- python-pptx未インストール時は静かにスキップ

### 3. XLSXメタデータパーサー（priority=35）

**場所**: `services/parse/connectors/office/xlsx_parser.py`

- .xlsxファイルからシート数・シート名・行列数・コアプロパティを抽出
- read_only=True + data_only=True で高速読み込み
- プロパティキー: `xlsx.sheet_count`, `xlsx.sheet_names`, `xlsx.total_rows`, `xlsx.sheet_dimensions` 等

### 4. Excel書式付きエクスポーター（W-1/W-2）

**場所**: `services/export/connectors/excel_export.py`

- **W-1: テーブルデータ書き出し**
  - メイリオ10ptフォント統一
  - ヘッダー行: 太字・背景色#4472C4・白文字
  - 列幅自動調整（日本語2文字幅換算）
  - ウィンドウ枠固定（ヘッダー行）
  - `export_table_to_excel()` / `export_table_to_excel_bytes()`

- **W-2: 配列データ書き出し**
  - Summaryシート + ノードごとのデータシート
  - メタデータヘッダー + X/Yデータ列
  - `export_array_data_to_excel()` / `export_array_data_to_excel_bytes()`

- **AbstractExporter サブクラス** `ExcelExporter`（format="xlsx", priority=12）

### 5. PPTXエクスポーター（W-3/W-4）

**場所**: `services/export/connectors/pptx_export.py`

- **W-3: ギャラリーグリッド → PPTスライド**
  - NxMグリッドレイアウト（マージン・パディング計算）
  - アスペクト比保持・中央寄せ配置
  - 画像数超過時の自動スライド分割
  - `export_gallery_to_pptx()` / `export_gallery_to_pptx_bytes()`

- **W-4: プロット画像 → PPTスライド**
  - 1図/スライド、全幅レイアウト
  - Plotly figure → PNG → PPTX 変換ユーティリティ
  - `export_plots_to_pptx()` / `plotly_fig_to_pptx_bytes()`

- **AbstractExporter サブクラス** `PptxExporter`（format="pptx", priority=13）

### 6. ダッシュボード統合（W-5）

**場所**: `services/dashboard/widgets.py`

- `render_excel_download()` を書式付きExcel版に拡張（フォールバック付き）
- `render_pptx_gallery_download()` 新規: ギャラリー画像のPPTXダウンロード
- `render_pptx_plot_download()` 新規: PlotlyプロットのPPTXダウンロード
- `render_array_excel_download()` 新規: 配列データの書式付きExcelダウンロード

### 7. テスト

**場所**: `tests/test_office_integration.py` — 21テスト（18 passed, 3 skipped）

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| TestPptxMetadataParser | 4 | パーサー登録・メタデータ抽出・フォーマットスキップ |
| TestXlsxMetadataParser | 3 | パーサー登録・メタデータ抽出・フォーマットスキップ |
| TestExcelExporter | 5 | 登録・テーブル出力・バイト列変換・配列出力・シート名サニタイズ・列幅 |
| TestPptxExporter | 5 | 登録・ギャラリー生成・複数スライド・バイト列・プロット・エラー |
| TestOfficePluginRegistration | 2 | インポート・冪等性 |

skipped: pandas未インストール環境でのDataFrame系テスト2件 + 非有効PPTXフィクスチャ1件

## 修正ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/plugins/office/__init__.py` | 新規: Officeプラグイン登録 |
| `services/parse/connectors/office/__init__.py` | 新規: パッケージ初期化 |
| `services/parse/connectors/office/pptx_parser.py` | 新規: PPTXメタデータパーサー |
| `services/parse/connectors/office/xlsx_parser.py` | 新規: XLSXメタデータパーサー |
| `services/export/connectors/excel_export.py` | 新規: Excel書式付きエクスポーター |
| `services/export/connectors/pptx_export.py` | 新規: PPTXエクスポーター |
| `services/dashboard/widgets.py` | 改修: 書式付きExcel + PPTX/配列ダウンロードボタン |
| `tests/test_office_integration.py` | 新規: 21テスト |
| `pyproject.toml` | office依存・entry_point追加 |

## アーキテクチャ

```
services/plugins/office/
├── __init__.py            # register() + graceful degradation

services/parse/connectors/office/
├── __init__.py
├── pptx_parser.py         # PptxMetadataParser (priority=35)
└── xlsx_parser.py         # XlsxMetadataParser (priority=35)

services/export/connectors/
├── excel_export.py        # ExcelExporter (format="xlsx", priority=12)
└── pptx_export.py         # PptxExporter (format="pptx", priority=13)
```

## 確認事項・TODO

- [ ] Windows実環境でのPPTX/XLSXエクスポート動作確認
- [ ] Win32 COM連携（アクティブPPTへの貼り付け）は未実装。windows-integration.md Phase W-3の後半に相当
- [ ] ダッシュボードの各ページコンポーネントへのPPTX/Excelボタン統合は関数を提供済み。各ページで `render_pptx_gallery_download()` 等を呼び出すだけで有効化できる
- [ ] kaleido未インストール時のPlotly→PNG変換はスキップされる。`pip install kaleido` が必要
- [ ] config.yaml の `dashboard.windows` セクション（フォント名・色等のカスタマイズ）は未実装

## 設計懸念

- PPTXエクスポーターは `PIL.Image` に依存してアスペクト比を計算している。PILが未インストールの場合はフォールバックで画像をそのまま配置する
- `export_table_to_excel_bytes()` は openpyxl のWorkbookをメモリ上で生成するため、大量データ（10万行超）の場合はメモリ消費に注意
- Win32 COM連携は `services/plugins/windows/` として別プラグインにする設計（windows-integration.md準拠）を推奨。現在の `services/plugins/office/` はクロスプラットフォーム部分のみ
