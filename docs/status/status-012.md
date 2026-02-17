[← README.md](../../README.md) | [← status-index](status-index.md)

# status-012 — PageComponent[ViewConfig]パターン導入・グリッドビュー廃止・ギャラリーキーフィルタ

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/fix-iteration-logic-REVGc

---

## 実施内容

### 1. PageComponent[ViewConfig]パターン導入

status-011のTODO「ViewConfigComponentサブクラス化」を実施。

- `services/dashboard/components/__init__.py` に基底クラスを新規作成
  - `ViewConfig`: ビュー設定コンポーネント基底クラス（`__init_subclass__`で`_registry`に自動登録）
  - `PageComponent[VC]`: ページコンポーネント基底クラス（`Generic[VC]`でViewConfigと型関連付け、`__init_subclass__`で`_registry`に自動登録）
  - レジストリアクセス関数: `get_page_labels()`, `get_page_component()`, `get_page_component_by_label()`, `get_view_config()`, `get_view_type_options()`

- 6つのビュータイプごとにサブクラスを作成
  - `components/table.py`: `TableViewConfig` + `TablePage(PageComponent[TableViewConfig])`
  - `components/card.py`: `CardViewConfig` + `CardPage(PageComponent[CardViewConfig])`
  - `components/plot.py`: `PlotViewConfig` + `PlotPage(PageComponent[PlotViewConfig])`
  - `components/array_plot.py`: `ArrayPlotViewConfig` + `ArrayPlotPage(PageComponent[ArrayPlotViewConfig])`
  - `components/status.py`: `StatusViewConfig` + `StatusPage(PageComponent[StatusViewConfig])`
  - `components/gallery.py`: `GalleryViewConfig` + `GalleryPage(PageComponent[GalleryViewConfig])`

- `app.py`をリファクタリング
  - ページ選択: ハードコード`page_options`リスト → `get_page_labels()`レジストリベース
  - ページディスパッチ: if/elif 6分岐 → `get_page_component_by_label()`レジストリルックアップ
  - 保存済みビューディスパッチ: if/elif 6分岐 → `get_page_component(view.view_type)`レジストリルックアップ
  - ビュー追加フォーム: ハードコードUI → `get_view_type_options()` + `vc.render_add_form()`レジストリベース

### 2. プロット・配列プロットのグリッドビュー廃止

status-011のTODO「プロット・配列プロットのグリッドビュー廃止」を実施。

- プロットビュー: 「グリッドモード（スクリーンショット用）」チェックボックスと`_render_plot_grid()`関数を削除
- 配列プロットビュー:
  - 表示モードから「グリッド比較」を削除（「全条件比較」「個別ノード」の2択に変更）
  - `_render_array_grid()`関数を削除
  - 保存済みビューのgridモードはoverlay（全条件比較）にフォールバック

### 3. ギャラリービューのフィルターロジックにキー名リスト指定を追加

status-011のTODO「ギャラリービューのフィルターロジックにキー名のリスト指定を追加」を実施。

- `query.py`に`filter_images_by_keys()`関数を新規追加
  - outputソース: `_extract_result_key_from_path()`でresult_keyを抽出し、許可リストと照合
  - propertyソース: `normalize_group_key()`でキー名を正規化し、許可リストと照合
- has_output画像ギャラリー: サイドバーにresult_keyフィルター（multiselect）を追加
- プロパティ画像ギャラリー: プロパティキーフィルターをselectbox→multiselect形式に拡張

---

## テスト結果

- **全テスト**: 278 passed, 38 skipped（+16件追加）
- **既存テスト**: 262件のパス継続（破壊なし）
- **新規テスト**: 16件追加
  - `TestPageComponentRegistry` (7件): PageComponentの__init_subclass__レジストリ動作検証
  - `TestViewConfigRegistry` (4件): ViewConfigの__init_subclass__レジストリ動作検証
  - `TestFilterImagesByKeys` (5件): キー名リストフィルタリング検証

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/dashboard/components/__init__.py` | 新規 | PageComponent[VC]/ViewConfig基底クラスとレジストリ |
| `services/dashboard/components/table.py` | 新規 | テーブルビューコンポーネント |
| `services/dashboard/components/card.py` | 新規 | カードビューコンポーネント |
| `services/dashboard/components/plot.py` | 新規 | プロットビューコンポーネント |
| `services/dashboard/components/array_plot.py` | 新規 | 配列プロットビューコンポーネント |
| `services/dashboard/components/status.py` | 新規 | ステータスビューコンポーネント |
| `services/dashboard/components/gallery.py` | 新規 | ギャラリービューコンポーネント |
| `services/dashboard/app.py` | 修正 | レジストリベースディスパッチ、グリッドビュー廃止、キーフィルタUI |
| `services/dashboard/query.py` | 修正 | `filter_images_by_keys()`追加 |
| `tests/test_dashboard.py` | 修正 | 新規テスト16件追加 |

---

## 設計メモ

### PageComponent[ViewConfig]パターン

```
ViewConfig (基底)
  ├── __init_subclass__() で _registry に自動登録
  ├── view_type: str で識別
  └── render_add_form() でビュータイプ固有の設定UI描画

VC = TypeVar("VC", bound=ViewConfig)

PageComponent[VC] (Generic基底)
  ├── __init_subclass__() で _registry に自動登録
  ├── page_key: str で識別 (= SavedViewConfigのview_type)
  ├── page_label: str でUI表示
  ├── get_view_config() → VC で対応するViewConfigを取得
  ├── render_page() でスタンドアロンページ描画
  └── render_saved_view() で保存済みビュー描画

登録例:
  class PlotViewConfig(ViewConfig):
      view_type = "plot"
  class PlotPage(PageComponent[PlotViewConfig]):
      page_key = "plot"
      page_label = "プロット"
```

### 後方互換性

- 保存済みビューの`mode: "grid"`設定は`overlay`にフォールバック
- SavedViewConfigの`view_type`バリデーションは変更なし
- DashboardPageConnector（コネクターページ）は従来通り独立して動作

---

## 次回TODO

- [ ] 描画ロジック移動: 現在PageComponentのrender_page()はapp.pyの_render_*関数を呼び出すブリッジ実装。段階的にロジックをPageComponentに移動してapp.pyを薄くする
- [ ] HTMLエクスポート: PageComponentレジストリを活用したHTMLエクスポートの統合
- [ ] プラグインパッケージ: PageComponent/ViewConfigのエントリーポイント登録対応
