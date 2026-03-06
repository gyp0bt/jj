[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-048: Config classification実装・vocab_display UI統合

- **日付**: 2026-03-06
- **マイルストーン**: M2（マルチソルバー基盤）
- **ブランチ**: `claude/execute-status-todos-oFw3W`

---

## 概要

status-047のTODOを実行:

1. **Config classification実装**: ハードコードされた設定値を明示的なconfigクラスに集約
2. **vocab_displayユーティリティのダッシュボードUI統合**: テーブルヘッダーにvocab変換を適用
3. **配列プロットsaved-viewクロスグループ対応**: 既に対応済みであることを確認

## 変更内容

### 1. Config classification（Phase 1-2）

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | `PlotStyleDefaults`（マーカー/線幅/フォントサイズの範囲・デフォルト）、`GalleryDefaults`（カラム/行/画像サイズ上限）、`ParseDefaults`（除外ディレクトリfrozenset）dataclass追加。DashboardConfigに`plot_style_defaults`/`gallery_defaults`、GraphConfigに`parse_defaults`フィールド追加。`from_dict()`でYAMLからの読み込みに対応 |
| `services/dashboard/components/plot.py` | スライダー範囲をPlotStyleDefaults参照に変更 |
| `services/dashboard/components/array_plot.py` | スライダー範囲をPlotStyleDefaults参照に変更 |
| `services/graph/__init__.py` | 除外ディレクトリをParseDefaults参照に変更（TODOコメント解消） |
| `services/parse/parsers/directory_parser.py` | 除外ディレクトリをParseDefaults参照に変更 |

**config.yaml 設定例**:
```yaml
dashboard:
  plot-style-defaults:
    marker-size-min: 2
    marker-size-max: 80
    line-width-default: 3
  gallery-defaults:
    columns: 3
    rows: 6
    max-image-bytes: 10485760
parse-defaults:
  exclude-dirs:
    - .git
    - .j2
    - build
```

### 2. vocab_display UI統合

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/table.py` | `render_page`/`render_saved_view`: DataFrameカラム名をvocab変換して表示 |
| `services/dashboard/html_export.py` | `generate_table_html`: HTMLテーブルヘッダーもvocab変換 |

### 3. テスト追加

| ファイル | 変更 |
|---------|------|
| `tests/test_dashboard.py` | `TestPlotStyleDefaults`(4件)、`TestGalleryDefaults`(3件)、`TestParseDefaults`(4件)、`TestVocabDisplay`(5件) = 計16件追加 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 212 files already formatted
- **pytest**: 全件通過（16テスト増加）

## TODO

- [ ] Run-PropertyトレーサビリティCLI対応（`jj run --show-properties`）
- [ ] M7 Phase 5: Run比較ダッシュボード
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] プロット軸ラベルへのvocab変換適用（現在はテーブルヘッダーのみ）
- [ ] GalleryDefaults.columns/rowsをギャラリーコンポーネントで参照（現在はDashboardConfig.gallery_columns/rowsを直接参照）

## 確認事項・懸念

- `services/run/__init__.py`のignore_namesは独自セット（`.pytest_cache`含む、`node_modules`なし）のため、ParseDefaults参照にせず独自のまま維持
- 配列プロットsaved-viewのクロスグループ対応は`render_add_form`でクロスグループ選択→x/y自由指定→configに保存の流れが既に完成しており、追加対応不要であることを確認
- GitHub Actionsへのアクセスが制限されているため、ローカルでのテスト実行で代替
