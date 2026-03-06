[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-049: Activeフィルタ全ページ適用・バッチ俯瞰ページ追加

- **日付**: 2026-03-06
- **マイルストーン**: M7（Run中心スキーマ再設計）Phase 5準備
- **ブランチ**: `claude/batch-run-visualization-iOJAa`

---

## 概要

1. **Activeフィルタの全ページ適用**: 従来TableとArrayPlotのみだった共有フィルタ（active/type/status）をPlot/Gallery/Card/Statusの全4ページにも適用
2. **バッチ俯瞰ページ新設**: 同一indexのバージョン違いをブロック図+スタイルドテキストで俯瞰表示する新しいPageComponent

## 変更内容

### 1. Activeフィルタ全ページ適用

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/plot.py` | `render_page`に`render_shared_filters`+`get_active_filters`追加。フィルタ適用後のgo_table名でplot dataをフィルタリング |
| `services/dashboard/components/gallery.py` | `render_page`に共有フィルタ追加。`_render_gallery_output_images`・`_render_gallery_property_images`に`active_filters`引数追加。go_node_nameベースでフィルタリング |
| `services/dashboard/components/card.py` | `render_page`に共有フィルタ追加。フィルタ適用済みrowsからノード選択 |
| `services/dashboard/components/status.py` | `render_page`に共有フィルタ追加。`_render_status`にフィルタ適用ロジック追加（itemsをフィルタ後にサマリー再計算） |

**フィルタ適用パターン**: 各ページでは`provider.get_go_table(filters=active_filters)`でフィルタ済み名前セットを取得し、各データソース（plot_data, images, status items）を名前ベースでフィルタリングする方式を採用。

### 2. バッチ俯瞰ページ（batch_overview）

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/batch_overview.py` | 新規作成。`BatchOverviewPage` PageComponent |
| `services/dashboard/app.py` | `batch_overview`コンポーネントのimport追加 |

**機能**:
- go_ノードを`index`プロパティでグルーピング
- 2つの表示モード:
  - **グリッド俯瞰**: 全indexを行、バージョンを列とするマトリクス表示。ステータス色分けブロック+差分プロパティ要約
  - **詳細ブロック図**: index別にバージョンブロックを横並び表示+差分プロパティテーブル
- indexの複数選択フィルタ
- 共有フィルタ（active/type/status）対応
- saved-view対応
- HTMLエクスポート対応

### 3. テスト追加

| ファイル | 変更 |
|---------|------|
| `tests/test_dashboard.py` | `TestBatchOverviewGrouping`(3件)、`TestBatchOverviewVaryingKeys`(2件)、`TestBatchOverviewHtml`(2件)、`TestSharedFiltersOnAllPages`(4件) = 計11件追加 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 213 files already formatted
- **pytest**: 新規11テスト全件通過

## TODO

- [ ] Run-PropertyトレーサビリティCLI対応（`jj run --show-properties`）
- [ ] M7 Phase 5: Run比較ダッシュボード（RunQueryServiceとの統合）
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] プロット軸ラベルへのvocab変換適用
- [ ] GalleryDefaults.columns/rowsをギャラリーコンポーネントで参照
- [ ] バッチ俯瞰ページでRunノード（NodeCategory.RUN）との統合表示

## 確認事項・懸念

- Gallery/Plot/Statusのフィルタ適用は「go_table → 名前セット → データフィルタ」の間接方式。直接的にproviderメソッドにフィルタを渡す方式がより効率的だが、既存APIとの互換性を優先して間接方式を採用
- バッチ俯瞰のブロック図はStreamlitのmarkdown+unsafe_allow_html方式。より高度なインタラクティブ表示にはplotly/pyvisなどの検討が必要
- `_render_shared_filters`は最初にレンダリングされたページのrowsでオプションを初期化するため、ページ遷移時にフィルタ選択肢が更新されない場合がある（既知のStreamlit session_state制約）
