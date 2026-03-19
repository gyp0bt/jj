[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-014 — バグ修正4件: verbose_name・浮動小数点表記・動的ビュー入力・メッシュ継承

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/execute-status-todos-CISAk

---

## 実施内容

status-013の追加TODO 4件を実施。

### 1. materialテーブルのverbose_name列が空になる問題を修正

**原因**: `abaqus_query.py`の`get_material_table()`で`node.properties.get("verbose_name", "")`を使用していたが、VocabFinalizerがキー名を変換（例: `"verbose_name"` → `"表示名"`）した後では取得できなくなっていた。

**修正**:
- `provider._verbose_name_key`（vocab変換後のキー名）で検索し、変換前のキーにフォールバック
- 除外キーリストにもvocab変換後のキーを追加して重複列を防止
- テスト3件追加（vocab変換後取得・フォールバック・重複防止）

### 2. テーブルビューの浮動小数点を指数表記に修正

**原因**: `get_material_table()`のスカラfloat値に`format_float_value()`が未適用。テーブルビューの`display_rows`構築時にもフォーマットが欠落。

**修正**:
- `abaqus_query.py`: スカラfloat値に`format_float_value()`を適用（`isinstance(value, float)`チェック追加）
- `components/table.py`: `render_page()`と`render_saved_view()`のdisplay_rowsループでfloat値フォーマットを追加

### 3. 動的ビューの入力項目をページビューと一致させる

**原因**: 動的ビューの追加フォーム（`render_add_form()`）がページビュー（`render_page()`）に比べて設定項目が不足。

**修正**:
- `PlotViewConfig.render_add_form()`: 色分けキー（`color`）選択を追加。4カラムレイアウトに変更
- `GalleryViewConfig.render_add_form()`: propertyソース時のプロパティキー（`property_key`）選択を追加。3カラムレイアウトに変更
- テスト2件追加（色分けキー付きplot、property_key付きgallery）
- **備考**: 軸範囲・スタイル設定はインタラクティブ操作向けのため動的ビューフォームには含めない判断

### 4. MeshInheritParserで複数include先のメッシュ辞書プロパティをマージ

**原因**: `MeshInheritParser`の`if key not in node.properties`ガードにより、複数のmeshファイルをincludeする場合に最初のinclude先のメッシュ統計のみが継承され、後続のinclude先のデータが無視されていた。

**修正**:
- `_MERGE_DICT_KEYS`定数を導入（`mesh_elset_summary`, `mesh_elset_quality`, `mesh_element_types`）
- マージ対象の辞書型プロパティは複数include先からシャロウマージ
- テスト1件追加（3つのelsetが2つのmeshファイルから正しくマージされることを検証）

### 5. lint修正（既存エラー解消）

- `parsers/__init__.py`: `DisplayNameParser`のimportをソート済み位置に移動し`__all__`に追加
- `widgets.py`: 冗長な`int(round())`を`round()`に簡素化（RUF046）

---

## テスト結果

- **全テスト**: 1122 passed, 59 skipped, 3 failed（pymesh/scipy依存の既存テスト）
- **新規テスト**: 6件追加
  - verbose_nameのvocab変換後取得: 1件
  - verbose_nameのフォールバック: 1件
  - verbose_nameの重複列防止: 1件
  - 動的ビューplot色分け: 1件
  - 動的ビューgallery property_key: 1件
  - MeshInheritParser辞書マージ: 1件
- ruff lint: All checks passed
- ruff format: 166 files already formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/dashboard/connectors/abaqus_query.py` | 修正 | verbose_name vocab対応、float値フォーマット適用 |
| `services/dashboard/components/table.py` | 修正 | display_rowsのfloat値フォーマット追加 |
| `services/dashboard/components/plot.py` | 修正 | render_add_formに色分けキー追加 |
| `services/dashboard/components/gallery.py` | 修正 | render_add_formにproperty_key追加 |
| `services/parse/connectors/abaqus/mesh_inherit_parser.py` | 修正 | _MERGE_DICT_KEYS導入、辞書マージロジック |
| `services/parse/parsers/__init__.py` | 修正 | DisplayNameParser import整列・__all__追加 |
| `services/dashboard/widgets.py` | 修正 | int(round())→round() lint修正 |
| `tests/test_dashboard.py` | 修正 | テスト5件追加、既存テスト期待値更新 |
| `tests/test_parser_units.py` | 修正 | MeshInheritParserマージテスト1件追加 |

---

## 次回TODO

- [ ] メッシュ品質の残課題: `get_element_node_coord_array(allow_polymorphism=False)`で要素タイプ混在時に品質計算が失敗する問題。pymesh側でelset別に分離して計算する方式への変更が必要
- [ ] DashboardPageConnector（ソルバー別コネクターページ）のPageComponentパターン統合検討
- [ ] ダッシュボードのE2Eテスト追加（Streamlit TestRunnerの導入検討）
- [ ] 外部プラグインパッケージの実例作成（pyproject.toml + entry_points設定のサンプル）
- [ ] 解析結果の保存構造見直し: `results/go_idx1_v1/` ディレクトリ方式への変更

---

## 設計上の判断

- **動的ビューフォームの範囲**: 軸範囲・スタイル設定（マーカーサイズ等）はインタラクティブ操作向けのため、動的ビューの追加フォームには含めないと判断。ページビューのサイドバーで調整するのが自然なUXフロー
- **メッシュ辞書マージ**: シャロウマージ（後勝ち）で実装。同名elsetが複数meshファイルに存在する場合は後のincludeが優先される。深いマージが必要な場合は今後検討
