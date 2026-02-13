[READMEへ戻る](../../README.md)

# status-083: テストインポート移行 + app.pyラッパー関数削除

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-082のTODO（Phase B / Phase C）を実施:

1. **Phase B: テストインポート更新** — テストが `app.*` ラッパー経由でインポートしていた箇所を、`query.*` / `html_export.*` への直接インポートに移行
2. **Phase C: app.pyラッパー関数削除** — query/html_export層への単純委譲ラッパー8関数をapp.pyから削除

---

## 1. Phase B: テストインポート更新

### 変更したテストクラス

| テストクラス | 変更前のインポート | 変更後のインポート | streamlitスキップ |
|---|---|---|---|
| TestGraphChangeDetection | `app._find_graph_path` | `query.find_graph_path` | 不要（元から無し） |
| TestGraphChangeDetection | `app._get_graph_mtime` | `query.get_graph_mtime` | 不要（元から無し） |
| TestSelectTableColumns | `app._select_table_columns` | `query.select_table_columns` | **除去** |
| TestIsTruthy | `app._is_truthy` | `query.is_truthy` | **除去** |
| TestNormalizeGroupKey | `app._normalize_group_key` | `query.normalize_group_key` | **除去** |
| TestSortColumnsByVocab | `app._sort_columns_by_vocab` | `query.sort_columns_by_vocab` | **除去** |
| TestHtmlExport | `app._generate_table_html` | `html_export.generate_table_html` | 不要 |
| TestHtmlExport | `app._generate_status_html` | `html_export.generate_status_html` | 不要 |
| TestHtmlExport | `app._generate_plot_html` | `html_export.generate_plot_html` | 不要 |
| TestHtmlExport | `app._generate_card_html` | `html_export.generate_card_html` | 不要 |
| TestHtmlExport | `app._generate_saved_views_html` | `html_export.generate_saved_views_html` | 不要 |

### 効果

- **TestGraphChangeDetection**: 以前は `app._find_graph_path` のラッパーが既に削除済みでインポートエラーだった → **5件復活（PASSED）**
- **TestSelectTableColumns / TestIsTruthy / TestNormalizeGroupKey / TestSortColumnsByVocab**: streamlit未インストール環境でスキップされていた → **16件がスキップ不要に（常にPASSED）**

---

## 2. Phase C: app.pyラッパー関数削除

### 削除したラッパー関数（8関数）

| 削除関数 | 委譲先 | 置換方法 |
|---|---|---|
| `_sort_columns_by_vocab()` | `query.sort_columns_by_vocab` | ラッパー削除のみ（外部呼び出し無し） |
| `_select_table_columns()` | `query.select_table_columns` | app.py内呼び出しを `select_table_columns()` に直接置換 |
| `_is_truthy()` | `query.is_truthy` | ラッパー削除のみ（app.py内では `is_truthy()` を直接使用済み） |
| `_apply_shared_filters()` | `query.apply_filters` | session_stateからの読み出しをインラインで展開 |
| `_add_ng_regions()` | `html_export._add_ng_regions_to_fig` | app.py内呼び出しを `_add_ng_regions_to_fig()` に直接置換 |
| `_add_group_lines()` | `html_export._add_group_lines_to_fig` | app.py内呼び出しを `_add_group_lines_to_fig()` に直接置換 |
| `_normalize_group_key()` | `query.normalize_group_key` | app.py内呼び出しを `normalize_group_key()` に直接置換 |
| `_collect_group_keys()` | `query.collect_group_keys` | app.py内呼び出しを `collect_group_keys()` に直接置換 |

### 残存するapp.py固有関数（非削除対象）

| 関数 | 理由 |
|---|---|
| `_try_render_aggrid()` | widgets.pyへの委譲（UI固有） |
| `_estimate_column_width()` | widgets.pyへの委譲（UI固有） |
| `_get_active_filters()` | session_state → provider用フィルタ辞書変換（app固有ロジック） |
| `_render_*()` | Streamlit UI描画関数（app.pyの本来の責務） |

---

## テスト結果

```
222 passed, 38 skipped, 30 failed
```

- **passed 222件**: 変更前比 +5件（TestGraphChangeDetection復活）
- **skipped 38件**: 変更前比 −17件（streamlitスキップ除去分がpassedに移行）
- **failed 30件**: chardet/fastapi/pandas未インストール（本変更と無関係、status-082時点と同等）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `tests/test_dashboard.py` | テストインポート更新（app.* → query.*/html_export.*）、streamlitスキップ除去 |
| `services/dashboard/app.py` | ラッパー関数8件削除、呼び出し箇所を直接呼び出しに置換 |
| `docs/status/status-083.md` | 本ステータスファイル（新規） |

---

## TODO / 次回引き継ぎ事項

### 過去status引き継ぎ（status-082から継続）
- [ ] services/query パッケージの実装（status-082 設計検討セクション参照）
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV・ヘッダーなしCSV対応
- [ ] ダッシュボード: Excelダウンロード機能・UIからの動的ビュー保存
- [ ] REST API拡張（POST parse, クエリフィルター）
- [ ] プラグイン化Phase 1-3（jj-sdk定義、CacheProvider抽象化、entry_points動的発見）

---

## 設計上の懸念

- [ ] services/queryの粒度: REST APIのprops条件式フィルタを汎用層に含めるかAPI固有にするか（status-082から継続）
- [ ] プラグイン化Phase 1（jj-sdk）との設計整合性（status-082から継続）
- [ ] `_try_render_aggrid` / `_estimate_column_width` は widgets.py への委譲ラッパーとして残存。widgets.py自体がStreamlit依存のため、テスト移行はStreamlitモック or 統合テストが必要
