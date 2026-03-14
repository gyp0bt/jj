[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-017 — ビュー保存/HTMLエクスポート横断対応・フィルター階層化

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/view-save-html-export-zhqFA

---

## 実施内容

### 1. ロードマップ更新: ダッシュボード横断要件の追加

**背景**: コネクターページを含む全ページにビュー保存/HTMLエクスポート機能を持たせる要件、およびフィルターロジックのグローバル+ローカル階層化要件が未定義だった。

**変更**:
- `docs/roadmap.md` のM2ダッシュボードアーキテクチャセクションに「ダッシュボード横断要件」を追加
- ビュー保存/HTMLエクスポートの原則: 全ページ（PageComponent + DashboardPageConnector）が対応すること
- フィルター階層化の原則: グローバルフィルター + オプショナルなローカルフィルター

### 2. SavedViewConfigのコネクタービュータイプ拡張

**背景**: `SavedViewConfig.view_type`がビルトインタイプ（table, plot等）のみに限定されていた。

**変更**:
- `view_type`に`connector:{page_label}`形式を追加（例: `connector:物性一覧`）
- `is_connector_view`プロパティ: コネクタービューかを判定
- `connector_page_label`プロパティ: コネクターのページラベルを取得
- `local_filters`フィールド追加: ページ/ビュー固有のローカルフィルター
- `connector_config`フィールド追加: コネクター固有の設定

### 3. DashboardPageConnectorのsaved view対応

**背景**: DashboardPageConnectorはrender_page()とgenerate_html()のみで、保存済みビューとしての利用に非対応だった。

**変更**:
- `render_saved_view()`: 保存済みビューとして描画（デフォルトはrender_page()に委譲）
- `generate_saved_view_html()`: 保存済みビューのHTML生成（デフォルトはgenerate_html()に委譲）
- `render_connector_saved_view()`: ページラベルで保存済みビューをレンダリング
- `generate_connector_saved_view_html()`: ページラベルで保存済みビューHTMLを生成
- `get_connector_view_type_options()`: 利用可能なコネクターview_type一覧を返す

### 4. app.pyのコネクター保存ビュー統合

**変更**:
- 保存済みビューページでコネクタービュー（`connector:*`）のディスパッチを追加
- ビュー追加フォームにコネクタービュータイプの選択肢を追加
- ローカルフィルタ入力フォームを追加

### 5. html_export.pyのコネクタービュー対応

**変更**:
- `generate_view_html()`がコネクタービューを検出し、コネクターレジストリにディスパッチ

### 6. フィルター階層化（グローバル+ローカル）

**背景**: フィルターロジックがグローバルフィルターのみで、ページ/ビュー固有のローカルフィルターに非対応だった。

**変更**:
- `merge_filters()`: グローバル+ローカルフィルタのマージ関数
- `apply_chained_filters()`: グローバル→ローカルの順でフィルタを適用する関数
- dashboard/query.pyにre-export追加

---

## テスト結果

- **既存テスト**: 296 passed → 314 passed（退行なし）
- **新規テスト**: 18件追加
  - SavedViewConfigコネクタータイプ: 6件（connector:*受入、ビルトイン判定、不正型エラー、local_filters解析、デフォルト空、connector_config解析）
  - ローカルフィルターチェーン: 5件（merge_filters 3件、apply_chained_filters 2件）
  - コネクター保存ビューHTML: 7件（HTML生成、未登録、利用不可、generate_view_htmlディスパッチ、view_typeオプション、委譲テスト2件）
- ruff lint: All checks passed
- ruff format: All files formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `docs/roadmap.md` | 修正 | ダッシュボード横断要件（ビュー保存/HTMLエクスポート原則、フィルター階層化原則）を追加 |
| `config/__init__.py` | 修正 | SavedViewConfigにconnector:*タイプ、local_filters、connector_configフィールド追加 |
| `services/dashboard/connectors/__init__.py` | 修正 | render_saved_view/generate_saved_view_html/レジストリ関数追加 |
| `services/dashboard/app.py` | 修正 | 保存済みビューページのコネクターディスパッチ、追加フォーム拡張 |
| `services/dashboard/html_export.py` | 修正 | generate_view_htmlのコネクタービューディスパッチ |
| `services/query/filters.py` | 修正 | merge_filters/apply_chained_filters追加 |
| `services/dashboard/query.py` | 修正 | merge_filters/apply_chained_filtersのre-export |
| `tests/test_dashboard.py` | 修正 | テスト18件追加（3テストクラス） |

---

## 次回TODO

- [ ] 解析結果の保存構造見直し: `results/go_idx1_v1/`ディレクトリ方式への変更（設計先行）
- [ ] コネクターページのrender_saved_view個別実装（物性一覧: 選択物性のカーブ表示等）
- [ ] ローカルフィルターのUI拡張: 複数キー/値ペアの追加・削除
- [ ] E2Eテストの拡充: ページ遷移テスト、フィルタ操作テスト、コネクター保存ビューE2E
- [ ] 外部プラグインのCI統合テスト（pip install -e → jj parse で動作確認）

---

## 設計メモ

### コネクタービュータイプの設計判断

`connector:{page_label}` プレフィックス方式を採用した理由:
- ビルトインタイプとの名前空間衝突を回避
- ページラベルがそのままview_typeに埋め込まれるため、レジストリ検索が直接的
- 外部プラグインが追加するコネクターも自動的にview_type候補に含まれる

### フィルター階層の適用順

グローバル → ローカルのAND結合方式を採用:
- グローバルフィルタで大まかに絞り込み、ローカルフィルタで追加条件を適用
- ローカルフィルタの同一キーはグローバルを上書き（merge_filtersの仕様）
- ローカルフィルタが空の場合は完全にスキップ（パフォーマンス考慮）

### render_saved_view()のデフォルト委譲

基底クラスの`render_saved_view()`はデフォルトでrender_page()に委譲する:
- 既存のコネクターはオーバーライド不要で保存ビュー対応が完了
- 特定の表示カスタマイズが必要な場合のみサブクラスでオーバーライド
- generate_saved_view_html()も同様にgenerate_html()に委譲
