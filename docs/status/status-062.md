[← README.md](../../README.md)

# status-062: T3 MLダッシュボード Phase 5 実装・ML使用マニュアル作成

- 日付: 2026-03-09
- ブランチ: claude/t3-tasks-ml-manual-HDXK8

## 実施内容

### T3: M6 Phase 5 MLダッシュボード

1. **MLOverviewPageConnector（ML概要ページ）**
   - `services/dashboard/connectors/ml.py` に実装
   - サマリーメトリクス（6カテゴリのノード件数）
   - 6タブ構成: 実験メトリクス、データセット、モデル、スクリプト、最適化、リレーション
   - DashboardPageConnectorパターンに準拠（`__init_subclass__`で自動登録）
   - `is_available()`: MLノードが存在する場合のみサイドバーに表示

2. **MLDataFlowPageConnector（MLデータフローページ）**
   - 三層データフロー可視化: Layer 1(CAE/青), Layer 2(ML/緑), Layer 3(最適化/橙)
   - `streamlit-agraph`がインストールされている場合はインタラクティブグラフ表示
   - 未インストール時はテーブル形式にフォールバック
   - 層間リレーションテーブル表示（extracted_from, surrogate_of, optimizes等）

3. **ml_query.py（クエリ層）**
   - Streamlit非依存の純粋なクエリ関数群
   - `get_ml_summary()`, `get_experiment_table()`, `get_dataset_table()`, `get_model_table()`
   - `get_script_table()`, `get_optimization_table()`, `get_ml_relations()`
   - `get_dataflow_graph_data()`: 三層グラフデータ構築
   - `get_node_layer()`: ノードのレイヤー判定ロジック

4. **HTMLエクスポート対応**
   - `_generate_overview_html()`: ML概要のHTML断片生成
   - `_generate_dataflow_html()`: 三層データフローのHTML断片生成

5. **app.py統合**
   - MLコネクターのimport追加（`__init_subclass__`で自動登録）

### ML使用マニュアル

6. **docs/ml-usage-guide.md**
   - 機械学習プロジェクト向け実践ガイド
   - PyTorch/scikit-learn/Optuna対応
   - 典型ディレクトリ構成、パース手順、ダッシュボード操作
   - 三層データフロー解説、CAE-ML連携シナリオ
   - ノードプロパティ一覧、設定カスタマイズ、トラブルシューティング

## ファイル構成

```
services/dashboard/connectors/ml.py       # [NEW] MLダッシュボードコネクター
services/dashboard/connectors/ml_query.py # [NEW] MLクエリ関数群
services/dashboard/app.py                 # MLコネクターimport追加
tests/test_ml_dashboard.py                # [NEW] テスト33件
docs/ml-usage-guide.md                    # [NEW] ML使用マニュアル
docs/README.md                            # MLマニュアルリンク追加
docs/status/status-062.md                 # [NEW] 本status
docs/status/status-index.md               # status-062追加、T3完了
```

## テスト

- ruff check / ruff format: パス
- pytest: 1693 passed, 102 skipped（全テスト通過、+33件）

## TODO

### ワークトラック（継続）

- [ ] T5: リモートジョブ実行基盤
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理

### T3関連の改善候補

- [ ] メトリクス比較プロット（実験間のloss曲線比較）
- [ ] モデルレジストリ詳細ページ（チェックポイント選択・比較UI）
- [ ] Optuna試行詳細表示（パラメータ重要度、パレートフロント）
- [ ] TensorBoard/MLflow連携パーサー（Phase 4相当）
- [ ] ビュー保存・コネクターconfig連携

## 確認事項・懸念

- streamlit-agraphはoptional依存。CIにはインストールされないため、テストはクエリ層のみ対象
- `optimization_config`ノードは`ML_CONFIG_TYPES`にも`ML_OPTIMIZATION_TYPES`にも含まれるが、`get_ml_summary()`の分類はelifの順序で`configs`にカウントされる。意図通りだが、将来的に混乱の元になる可能性あり
- 三層データフローグラフの自動レイアウトは、ノード数が多い場合に視認性が下がる可能性。ノード数上限やクラスタリングの検討が必要

## 開発運用メモ

- T3（MLダッシュボード）はPhase 4までのパーサー基盤の上に、ダッシュボードコネクターパターンで自然に実装できた
- abaqus.pyの実装をリファレンスとして使用。クエリ層分離パターン（*_query.py）は再利用性が高い
