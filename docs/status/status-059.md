[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-059: Run DAG可視化の実装

- **日付**: 2026-03-09
- **マイルストーン**: v0.3.0 T6（ダッシュボード高度化）
- **ブランチ**: `claude/execute-status-todos-LGHaP`

---

## 概要

status-058のTODOから、実行可能な「Run DAG可視化」（status-052 TODO）を実装:

1. **Run DAG可視化**: RunComparisonPageにDAGセクションを追加。Run間のデータ依存関係（Run A の出力 → Run B の入力）を検出し、データフローグラフとして可視化
2. **streamlit-agraph / graphviz 二重フォールバック**: batch_overview.pyと同じパターンを適用
3. **HTML DAG生成**: Run DAGの依存関係テーブルをスタティックHTML出力に対応
4. **テスト4件追加**: 依存関係なし/あり/空/graphvizフォールバックのテスト

## 変更内容

### 1. Run DAG可視化（run_comparison.py）

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/run_comparison.py` | `_render_run_dag()`: DAG描画のオーケストレーション関数 |
| `services/dashboard/components/run_comparison.py` | `_try_render_run_dag_agraph()`: streamlit-agraphによるDAG描画 |
| `services/dashboard/components/run_comparison.py` | `_try_render_run_dag_graphviz()`: graphvizフォールバック |
| `services/dashboard/components/run_comparison.py` | `_generate_run_dag_html()`: スタティックHTML生成 |
| `services/dashboard/components/run_comparison.py` | `render_page()`: DAGセクション追加 |
| `services/dashboard/components/run_comparison.py` | `generate_html()`: DAG HTML統合 |

### DAG描画のロジック

- **データ依存関係の検出**: 各Runの入出力を解析し、Run A の `run_output` が Run B の `run_input` に含まれる場合にA → Bのデータフローエッジを構築
- **共有ノード表示**: 複数のRunに関わるファイルノードのみを小さい楕円ノードとして表示（DAGの可読性向上）
- **ノード色分け**: Runステータスに応じた色分け（completed=緑, failed=赤, running=黄, latent=紫）
- **エッジ色分け**: 入力=青, 出力=緑, 媒体=紫点線

### 2. テスト追加

| ファイル | 追加テスト数 |
|---------|-------------|
| `tests/test_dashboard.py` | 4件（DAG依存なし、DAG依存あり、DAG空、graphvizフォールバック） |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 217 files already formatted
- **pytest**: 実行中（前回: 412 passed, 64 skipped + 新規4件）

## TODO

- [ ] T3: M6 Phase 5 MLダッシュボード（MLOverviewPage, 三層データフロー可視化）
- [ ] T5: リモートジョブ実行基盤（jj submit/watch/collect）
- [ ] T7: Ollama AI連携（AIProviderプロトコル, 要約, RAG, tips）
- [ ] T8: 汎用データ管理（Run中心プラットフォームへの昇華）
- [ ] streamlit-agraphの本番環境でのテスト
- [ ] Abaqus Explicit形式の.staファイル対応（サンプル入手後）
- [ ] Run比較結果のHTMLエクスポート（diff_runsの差分テーブルHTML化）
- [ ] Runフィルタの保存対応（SavedViewConfigへの統合）
- [ ] CIが正常にジョブ実行されることをpush後に確認

## 確認事項・懸念

- streamlit-agraphは`hierarchical=True`でDAGレイアウトを使用。大量のRunがある場合はphysics設定の調整が必要になる可能性あり
- 共有ノード検出は全Run のI/Oを走査するため、大規模グラフでは`O(R*N)`の計算コスト。現状のユースケースでは問題なし

## 開発運用メモ

- **効果的**: batch_overview.pyの既存agraph/graphvizフォールバックパターンを再利用することで、実装時間を短縮できた
- **効果的**: RunQueryServiceのget_run_io()がDAG構築に必要な情報を全て提供しており、新たなクエリメソッド追加は不要だった
