[← README.md](../../README.md)

# Config Classification仕様書

## 概要

ダッシュボード・パーサー・グラフサービス全体にハードコードされている設定値を、
明示的なconfigクラスに集約する。現在40+箇所に散在するマジックナンバーや
デフォルト値を発見・変更しやすくする。

## 設計方針

### 現在の課題

1. **ギャラリー設定**: `5x4`グリッド、`12px`ギャップ等がコンポーネント内にハードコード
2. **プロットスタイル**: marker size(1-50)、line width(1-20)、font size(6-48)の範囲がコンポーネント内に散在
3. **パーサー設定**: DEFAULT_EXTENSIONS、NO_NODE_EXTENSIONS、FILE_TYPE_PREFIXES等がfile_parse.pyにハードコード
4. **除外ディレクトリ**: `.git`, `.j2`, `__pycache__`等が複数箇所に重複定義
5. **キャッシュ設定**: search-depth=5, max-age-days=30, max-count=100がconfig.pyに直書き

### アプローチ: DashboardConfig拡張

既存の`DashboardConfig`（config/__init__.py）を拡張し、新しいサブ設定クラスを追加する。

```python
@dataclass
class PlotStyleDefaults:
    """プロットスタイルのデフォルト値"""
    marker_size_min: int = 1
    marker_size_max: int = 50
    marker_size_default: int = 16
    line_width_min: int = 1
    line_width_max: int = 20
    line_width_default: int = 2
    font_size_min: int = 6
    font_size_max: int = 48
    font_size_default: int = 20


@dataclass
class GalleryDefaults:
    """ギャラリーのデフォルト値"""
    columns: int = 5
    rows: int = 4
    max_image_bytes: int = 5 * 1024 * 1024


@dataclass
class ParseDefaults:
    """パーサーのデフォルト値"""
    exclude_dirs: frozenset[str] = frozenset({".git", ".j2", "__pycache__", "node_modules", ".venv"})
```

## 実装計画

### Phase 1: 設定クラス定義
- config/__init__.pyに上記dataclassを追加
- DashboardConfigに`plot_style_defaults`、`gallery_defaults`フィールドを追加
- GraphConfigに`parse_defaults`フィールドを追加

### Phase 2: ハードコード置換
- dashboard/components/plot.py、array_plot.pyのスライダー範囲をconfig参照に変更
- dashboard/components/gallery.pyのグリッド設定をconfig参照に変更
- services/graph/__init__.pyの除外ディレクトリをconfig参照に変更
- services/parse/parsers/directory_parser.pyの除外ディレクトリをconfig参照に変更

## 優先度

| 優先度 | カテゴリ | 影響箇所 |
|--------|---------|----------|
| 高 | 除外ディレクトリ | 3箇所に重複 |
| 高 | プロットスタイル範囲 | 4箇所に重複 |
| 中 | ギャラリー設定 | 4箇所に重複 |
| 低 | HTML/CSSスタイル | テーマ化は後回し |
