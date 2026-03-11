[← README.md](../../README.md)

# Windows連携プラグイン仕様書

> PowerPoint / Excel への直接出力機能

---

## 1. 概要

ダッシュボードのテーブル・ギャラリー・プロットデータを、Windows上で開いている
PowerPointやExcelに直接書き出す機能。Win32 COM (comtypes/win32com) を使用し、
Windows環境限定のオプショナルプラグインとして提供する。

## 2. ユースケース

| # | ユースケース | 入力 | 出力先 |
|---|-------------|------|--------|
| U1 | ギャラリー画像をPPTスライドに貼り付け | ギャラリーグリッド（NxM画像） | アクティブPPTの新規スライド |
| U2 | テーブルデータをExcelに書き出し | テーブルビューのDataFrame | 新規Excelファイル |
| U3 | 配列プロットデータをExcelに書き出し | 配列プロットのデータ | 新規Excelファイル |
| U4 | プロット画像をPPTに貼り付け | plotly/matplotlib図 | アクティブPPTの新規スライド |

## 3. アーキテクチャ

```
services/plugins/windows/
├── __init__.py            # register() + 環境検出
├── com_bridge.py          # Win32 COM共通ユーティリティ
├── pptx_export.py         # PowerPoint出力ロジック
├── excel_export.py        # Excel出力ロジック
└── dashboard_buttons.py   # Streamlitボタンコンポーネント
```

### プラグイン登録

```toml
# pyproject.toml
[project.entry-points."jj.plugins"]
windows = "services.plugins.windows:register"

[project.optional-dependencies]
windows = ["pywin32>=306"]
```

`register()` はプラットフォーム判定（`sys.platform == "win32"`）を行い、
非Windows環境では何もしない（silent skip）。

## 4. PowerPoint連携（pptx_export）

### 4.1 プレゼンテーション選択戦略

Win32 COMの `Application.ActivePresentation` は「最後にフォーカスが当たったPPT」を返す。
しかしStreamlitのボタンクリック時にブラウザにフォーカスが移るため、
**アクティブなプレゼンテーションが変わる可能性がある**。

**採用方針: プレゼンテーション一覧ドロップダウン + 新規作成オプション**

```python
def list_open_presentations() -> list[dict[str, str]]:
    """開いているプレゼンテーション一覧を取得

    Returns:
        [{"name": "報告書.pptx", "path": "C:\\...\\報告書.pptx"}, ...]
    """
    app = win32com.client.GetActiveObject("PowerPoint.Application")
    return [
        {"name": p.Name, "path": p.FullName}
        for p in app.Presentations
    ]
```

UIフロー:
1. 「PPTに貼り付け」ボタン押下
2. ドロップダウンに開いているPPT一覧 + 「新規作成」を表示
3. 選択されたPPTの末尾に新規スライドを追加して画像を配置

PowerPointが起動していない場合は新規作成を自動選択。

### 4.2 ギャラリー → PPTスライド

グリッドレイアウトを保ったまま、スライド上に画像を配置する。

```python
def export_gallery_to_ppt(
    images: list[Path],
    cols: int,
    rows: int,
    presentation_index: int | None = None,  # None = 新規作成
    slide_layout: int = 6,  # ppLayoutBlank
) -> None:
    """ギャラリー画像をPPTスライドにグリッド配置

    スライドサイズ（デフォルト: 13.333 x 7.5 inch = 33.867 x 19.05 cm）から
    マージンを引いた領域をcols x rowsに分割し、各セルに画像を配置。
    """
```

**レイアウト計算:**
```
slide_width  = 13.333 inch (= 33.867 cm)
slide_height =  7.5   inch (= 19.05  cm)
margin       =  0.5   inch (上下左右)
title_height =  0.8   inch (タイトル行)

usable_width  = slide_width - 2 * margin = 12.333 inch
usable_height = slide_height - 2 * margin - title_height = 5.7 inch

cell_width  = usable_width / cols
cell_height = usable_height / rows
padding     = 0.1 inch (セル間)

image_max_w = cell_width - 2 * padding
image_max_h = cell_height - 2 * padding
```

各画像はアスペクト比を保ったまま `image_max_w x image_max_h` に収まるようリサイズ。
画像が `cols * rows` を超える場合は複数スライドに分割。

### 4.3 プロット → PPTスライド

plotly図をPNG画像として一時ファイルに書き出し、スライドに配置。

```python
def export_plot_to_ppt(
    fig,  # plotly.graph_objects.Figure
    title: str = "",
    presentation_index: int | None = None,
) -> None:
    """plotly図をPPTスライドに貼り付け（1図/スライド、全幅）"""
```

## 5. Excel連携（excel_export）

### 5.1 基本方針

- **常に新規ファイル** — 上書きによるデータ消失を防止
- フォント: **メイリオ**（全セル統一）
- ファイル名: `{prefix}_{YYYYMMDD_HHMMSS}.xlsx`
- 出力先: プロジェクトの `.j2/exports/` ディレクトリ

### 5.2 テーブルデータ書き出し

```python
def export_table_to_excel(
    df: pd.DataFrame,
    output_dir: Path,
    filename_prefix: str = "table",
    sheet_name: str = "Data",
    freeze_panes: tuple[int, int] = (1, 0),  # ヘッダー固定
) -> Path:
    """DataFrameをExcelファイルに書き出し

    Features:
    - フォント: メイリオ 10pt
    - ヘッダー行: 太字、背景色 #4472C4、文字色 白
    - 列幅: 内容に基づく自動調整（日本語は2文字幅換算）
    - 数値列: 桁区切り / 有効数字自動フォーマット
    - ウィンドウ枠固定: ヘッダー行

    Returns:
        出力ファイルパス
    """
```

### 5.3 配列プロットデータ書き出し

配列プロットはノードごとに複数系列（x, y配列）を持つ。

```python
def export_array_data_to_excel(
    array_data: list[dict],  # [{name, x, y, props}, ...]
    output_dir: Path,
    filename_prefix: str = "array_data",
) -> Path:
    """配列データをExcelに書き出し

    シート構成:
    - "Summary" シート: ノード名、プロパティ一覧
    - 各ノードごとにシート: x, y 列 + メタデータヘッダー
    """
```

### 5.4 openpyxlによる書式設定

```python
from openpyxl.styles import Font, PatternFill, Alignment

MEIRYO_FONT = Font(name="メイリオ", size=10)
HEADER_FONT = Font(name="メイリオ", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
```

Win32 COMは不要 — openpyxlで新規ファイルを生成し、Streamlitのダウンロードボタンで提供。
ユーザーの要望でExcelアプリで直接開きたい場合のみ `os.startfile()` を追加検討。

## 6. ダッシュボード統合

### 6.1 エクスポートボタンの配置

各ページコンポーネントにエクスポートボタンを配置する。

```
テーブルページ:
  [テーブル表示]
  [Excelダウンロード ▼] [PPTに貼り付け]  ← 既存のExcelダウンロード横にPPTボタン追加

ギャラリーページ:
  [ギャラリーグリッド]
  [PPTに貼り付け] [HTML保存]  ← ギャラリー下部

プロットページ:
  [プロット表示]
  [PPTに貼り付け] [Excelダウンロード]  ← プロット下部

配列プロットページ:
  [配列プロット表示]
  [PPTに貼り付け] [Excelダウンロード]  ← 配列プロット下部
```

### 6.2 Windows環境検出

```python
def is_windows_com_available() -> bool:
    """Win32 COM が利用可能かチェック"""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client
        return True
    except ImportError:
        return False
```

非Windows環境ではPPTボタンを非表示にする。Excelダウンロードは環境問わず利用可能
（openpyxlベース）。

## 7. 実装フェーズ

| Phase | 内容 | 見積 |
|-------|------|------|
| W-1 | Excel新規ファイル出力（テーブル + メイリオ書式） | 小 |
| W-2 | Excel配列データ出力（複数シート） | 小 |
| W-3 | PPTギャラリーグリッド貼り付け | 中 |
| W-4 | PPTプロット貼り付け | 小 |
| W-5 | ダッシュボードUI統合 | 小 |

## 8. 設定（config.yaml）

```yaml
dashboard:
  windows:
    excel-font: "メイリオ"
    excel-font-size: 10
    excel-header-color: "4472C4"
    ppt-margin-inch: 0.5
    ppt-title-height-inch: 0.8
    ppt-cell-padding-inch: 0.1
    export-dir: ".j2/exports"  # デフォルト出力先
```

## 9. 依存関係

| パッケージ | 用途 | 必須/オプション |
|-----------|------|---------------|
| openpyxl | Excel書式付き出力 | オプション（既存） |
| pywin32 | Win32 COM (PPT連携) | オプション（Windows限定） |
| kaleido | plotly→PNG変換 | オプション（PPTプロット用） |

---

## 10. 制約・注意事項

- Win32 COMはメインスレッドでのみ動作（CoInitialize問題）
  → Streamlitのメインスレッドから呼び出す（ワーカースレッド不可）
- PowerPointが応答なし状態の場合、COMタイムアウトが発生する
  → try/except + ユーザーへの明示的エラーメッセージ
- 大量画像のPPT貼り付けはメモリ消費に注意
  → サムネイル化オプション（既存の `_generate_thumbnail` 流用）
