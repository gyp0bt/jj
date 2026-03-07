[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-056: T1完了(#5,#6)・T6-2,3実装・pymesh依存修正

- **日付**: 2026-03-07
- **マイルストーン**: v0.3.0 Phase A/C（T1完了, T6進行）
- **ブランチ**: `claude/execute-status-todos-dwEdz`

---

## 概要

status-055のTODOを全件実行。T1のコードベースTODO（#5, #6）を完了し、T6のダッシュボード高度化（T6-2, T6-3）を実装:

1. **pymesh optional依存修正**: pyproject.tomlにscipy/plotlyを追加、テストスキップ条件更新
2. **T1 #5: パラメータ式評価改善**: `_resolve_param_references`関数追加（`<param>`形式+識別子形式）、pending_lineバッファによるinclude間伝搬修正
3. **T1 #6: 収束情報パーサー**: `_parse_convergence_info`でAbaqus Standard .staファイルのインクリメント行を解析、カットバック・イテレーション情報を抽出
4. **T6-2: AgGridフィルタ共有**: フィルタ共有ON/OFFトグル、AgGridフィルタ変更イベントキャプチャ、session_state経由の共有
5. **T6-3: グラフ可視化**: バッチ俯瞰に「グラフビュー」追加。streamlit-agraph→graphvizフォールバック

## 変更内容

### 1. pymesh optional依存修正

| ファイル | 変更 |
|---------|------|
| `pyproject.toml` | pymesh optional-dependenciesにscipy/plotly追加 |
| `tests/test_encoding_optimization.py` | plotly importorskip追加 |
| `tests/test_graph_feature.py` | pymeshインポートテストにscipy/plotlyスキップ条件追加 |

### 2. T1 #5: パラメータ式評価改善

| ファイル | 変更 |
|---------|------|
| `services/parse/connectors/abaqus/parameter_parser.py` | `_resolve_param_references()`追加、`<param>`形式対応、pending_lineバッファ、循環include検出改善 |
| `tests/test_parameter_expression.py` | 新規: 19テスト（単体テスト11件+統合テスト8件） |

### 3. T1 #6: 収束情報パーサー

| ファイル | 変更 |
|---------|------|
| `services/parse/connectors/abaqus/result_parser.py` | `_parse_convergence_info()`追加、`parse_sta_file()`に収束情報統合、`_enrich_sta_status()`で収束propsをノードに付与 |
| `tests/test_convergence_info.py` | 新規: 10テスト（単体テスト5件+ファイルテスト4件+統合テスト1件） |

### 4. T6-2: AgGridフィルタ共有

| ファイル | 変更 |
|---------|------|
| `services/dashboard/widgets.py` | `try_render_aggrid`にフィルタ共有機能追加、`grid_key`パラメータ、フィルタ共有ON/OFFトグル、クリアボタン |

### 5. T6-3: グラフ可視化

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/batch_overview.py` | 「グラフビュー」表示モード追加、streamlit-agraph描画、graphvizフォールバック |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: All files formatted
- **pytest**: 1657 passed, 101 skipped（+29件増加）
- **新規テスト**: +29件（パラメータ式19件 + 収束情報10件）

## v0.3.0 ワークトラック進捗

| トラック | 状態 | 今回の進捗 |
|---------|------|-----------|
| **T1: コードベースTODO解消** | **完了** | #5(パラメータ式評価), #6(収束情報パーサー)完了。#7-12はM2依存で据え置き |
| **T2: Config二層分離** | 完了 | — |
| **T3: M6 Phase 5 MLダッシュボード** | 未着手 | — |
| **T4: Deprecation Warning修正** | 完了 | — |
| **T5: リモートジョブ実行基盤** | 未着手 | — |
| **T6: ダッシュボード高度化** | 進行中 | T6-2(AgGridフィルタ共有), T6-3(グラフ可視化)完了。残: T6-4 |
| **T7: Ollama AI連携** | 未着手 | — |
| **T8: 汎用データ管理** | 未着手 | — |

## TODO

- [ ] T6-4: GalleryDefaults二重構造の解消
- [ ] T3: M6 Phase 5 MLダッシュボード（MLOverviewPage, 三層データフロー可視化）
- [ ] T5: リモートジョブ実行基盤（jj submit/watch/collect）
- [ ] streamlit-agraphの本番環境でのテスト（`pip install streamlit-agraph`が必要）
- [ ] Abaqus Explicit形式の.staファイル対応（サンプル入手後）
- [ ] status-052 TODO: Run DAG可視化（T6-3のグラフビューを拡張）

## 確認事項・懸念

- `_resolve_param_references`は大文字小文字を区別しないパラメータ参照解決を行う。Abaqus仕様に準拠
- `_parse_convergence_info`はAbaqus Standard形式のみ対応。Explicit形式はサンプル入手後に追加対応が必要
- T6-2のAgGridフィルタ共有は`grid_options_state.filterModel`に依存。streamlit-aggridのバージョンによってAPIが異なる可能性あり
- T6-3のstreamlit-agraphはこの環境では動作確認できていない。graphvizフォールバックは動作確認済み

## 開発運用メモ

- **効果的**: status-055のTODOを上から順に全件実行する方式で、漏れなく作業を進められた
- **効果的**: featureごとにコミットを分離することで、レビュー粒度が明確
- **注意点**: ダッシュボード系のUI変更はStreamlit環境がないと動作確認できない。テスト可能なロジック部分を先に実装し、UI部分は別途確認が望ましい
