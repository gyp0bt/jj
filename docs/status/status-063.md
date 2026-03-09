[← README.md](../../README.md)

# status-063: T3改善 メトリクス比較プロット・ビュー保存連携

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-6wBmM

## 実施内容

### メトリクス比較プロット

1. **ml_query.py: クエリ関数追加**
   - `get_experiment_metric_keys()`: 全実験メトリクスノードから利用可能なメトリクスキーを出現頻度順に収集
   - `get_experiment_comparison_data()`: 実験間メトリクス比較データを構築（メトリクスキー/実験IDフィルタ対応）

2. **ml.py: 比較プロットUI**
   - 実験メトリクスタブに比較プロットセクションを追加（実験2件以上時に表示）
   - plotly利用可能時: グループ化棒グラフで実験間メトリクス比較
   - plotly未使用時: テーブル形式にフォールバック
   - メトリクス選択UI（`st.multiselect`）

3. **HTMLエクスポート対応**
   - `_generate_comparison_html()`: メトリクス比較テーブルのHTML断片生成

### ビュー保存・コネクターconfig連携

4. **MLOverviewPageConnector拡張**
   - `render_saved_view()`: connector_configからtab/metric_keys/experiment_idsを読み取り
   - `generate_saved_view_html()`: comparison tab時の比較HTML生成
   - `get_connector_config_schema()`: tab, metric_keys, experiment_idsの3フィールド
   - 対応tab: experiment/dataset/model/script/optimization/relation/comparison

5. **MLDataFlowPageConnector拡張**
   - `render_saved_view()`: connector_configからlayer_filterを読み取り（レイヤー指定表示）
   - `get_connector_config_schema()`: layer_filterフィールド追加

## ファイル構成

```
services/dashboard/connectors/ml_query.py # メトリクス比較クエリ関数追加
services/dashboard/connectors/ml.py       # 比較プロットUI・ビュー保存連携
tests/test_ml_dashboard.py                # テスト14件追加（33→47件）
docs/status/status-063.md                 # [NEW] 本status
docs/status/status-index.md              # status-063追加
```

## テスト

- ruff check / ruff format: パス
- pytest tests/test_ml_dashboard.py: 47 passed（+14件）
- 新規テストクラス:
  - `TestExperimentMetricKeys`: メトリクスキー収集（3件）
  - `TestExperimentComparisonData`: 比較データ構築（6件）
  - `TestMLOverviewConnectorConfig`: connector_configスキーマ（2件）
  - `TestMLDataFlowConnectorConfig`: connector_configスキーマ（1件）
  - `TestComparisonHTML`: 比較HTML生成（3件）

## TODO

### ワークトラック（継続）

- [ ] T5: リモートジョブ実行基盤
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理

### T3関連の改善候補（残）

- [ ] モデルレジストリ詳細ページ（チェックポイント選択・比較UI）
- [ ] Optuna試行詳細表示（パラメータ重要度、パレートフロント）
- [ ] TensorBoard/MLflow連携パーサー（Phase 4相当）

## 確認事項・懸念

- plotlyはoptional依存。CIにはインストールされないため、テストはクエリ層のみ対象。棒グラフ描画は手動確認が必要
- comparison tabのHTMLエクスポートはテーブル形式のみ（plotlyグラフの静的出力には`kaleido`が必要）
- `render_saved_view()`で`view.name`を参照しているが、`SavedViewConfig`の実装に依存。属性が存在しない場合は`view.connector_config`のhasattrチェックと同様のガードが必要になる可能性

## 開発運用メモ

- abaqus.pyのconnector_config実装パターンをそのまま踏襲。render_saved_view + generate_saved_view_html + get_connector_config_schemaの3点セット
- MLDataFlowPageConnectorのlayer_filterは簡易だが、ビュー保存で特定レイヤーのみ表示する用途に有用
