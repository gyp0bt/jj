[← README.md](../../README.md)

# status-071: T7-6 AIアシスタントパネル / T8 汎用データ管理基盤

- 日付: 2026-03-10
- ブランチ: claude/execute-status-todos-2xvZf

## 実施内容

### T7-6: ダッシュボードAIアシスタントパネル

DashboardPageConnectorパターンを使用してAI機能をダッシュボードに統合。

- **`services/dashboard/connectors/ai_assistant.py`**: [NEW] AIAssistantPageConnector
  - page_label = "AIアシスタント", connector_key = "ai"
  - **Tipsタブ**: TipsStore読み込み、キーワード検索、ページネーション、expander表示
  - **RAG検索タブ**: インデックス状態表示（エントリ数/ファイル数）、質問→RAG回答UI
  - **チャットタブ**: session_state管理のチャット履歴、chat_input、履歴クリア
  - HTMLエクスポート対応（Tips一覧テーブル）
  - _is_ai_configured() / _init_provider() でconfig.yamlからの遅延初期化
- **`services/dashboard/app.py`**: [MOD] ai_assistantコネクターインポート追加

### T8: 汎用データ管理基盤（Phase 8-1, 8-2）

#### Phase 8-1: Run Discovery標準化

- **`services/parse/run_discovery.py`**: [NEW] Run発見ユーティリティ
  - `RunDiscoveryMixin`: discover_runs() / register_run() のMixin
  - `find_input_output_pairs()`: 同一ディレクトリ内の入出力ファイルペア発見
  - `detect_run_status()`: 出力ノードプロパティからのステータス推定
  - `extract_run_properties()`: ノード群からの共通プロパティ抽出
  - ステータス定数: RUN_STATUS_COMPLETED/FAILED/RUNNING/UNKNOWN

#### Phase 8-2: 物理実験プラグインスケルトン

- **`services/plugins/experiment/__init__.py`**: [NEW] プラグインエントリ
- **`services/parse/connectors/experiment/data_parser.py`**: [NEW]
  - `ExperimentDataParser` (priority=56): CSV/TSVヘッダ抽出・行数カウント
    - .meta.yaml メタデータ読み込み（experiment_name, operator, conditions等）
  - `ExperimentRunDiscoverer` (priority=76): RunDiscoveryMixin使用
    - メタデータ付きCSVディレクトリからのRun自動発見・登録

#### 設計仕様書

- **`docs/specs/t8-generic-data-management.md`**: [NEW] T8設計仕様書
  - Phase 8-1〜8-5の段階的実装計画
  - Run = 第一級オブジェクト原則の定義

### テスト

合計41件追加（既存テスト97件全パス）:
- `test_ai_assistant_connector.py`: 16件（登録・可用性・設定・Tips/RAG読込・HTML生成）
- `test_run_discovery.py`: 14件（Mixin・ペア発見・ステータス判定・プロパティ抽出）
- `test_experiment_plugin.py`: 11件（CSVヘッダ・行数・メタデータ・Run発見・登録）

## ファイル構成

```
services/dashboard/connectors/ai_assistant.py    # [NEW] AIアシスタントページ
services/dashboard/app.py                        # [MOD] インポート追加
services/parse/run_discovery.py                  # [NEW] Run Discoveryユーティリティ
services/parse/connectors/experiment/__init__.py # [NEW]
services/parse/connectors/experiment/data_parser.py # [NEW] 実験データパーサー
services/plugins/experiment/__init__.py          # [NEW] 物理実験プラグイン
docs/specs/t8-generic-data-management.md         # [NEW] T8設計仕様書
tests/test_ai_assistant_connector.py             # [NEW] 16件
tests/test_run_discovery.py                      # [NEW] 14件
tests/test_experiment_plugin.py                  # [NEW] 11件
docs/status/status-071.md                        # [NEW] 本status
```

## TODO

### T7 継続
- [ ] T7 ダッシュボードAIアシスタントの実運用テスト（Ollama接続時の動作確認）

### T8 継続
- [ ] T8 Phase 8-3: プラグイン開発ガイド更新
- [ ] T8 Phase 8-4: Config分類の汎用化
- [ ] T8 Phase 8-5: Run比較ダッシュボードの汎用化
- [ ] pyproject.toml に experiment プラグインのentry_pointsを追加

### ワークトラック（継続）
- [ ] T3改善候補（モデルレジストリ、Optuna詳細、TensorBoard連携）
- [ ] M2: マルチソルバー検証（検証環境確保後）

## 確認事項・懸念

- 物理実験プラグインのメタデータ形式（.meta.yaml）はv1仕様。利用者フィードバックに応じてフィールドの追加を検討。
- ExperimentRunDiscovererはメタデータ付きCSVのみをRun化する保守的な実装。将来的にはディレクトリ構造ベースの推定も検討。
- AIアシスタントパネルはOllama非稼働環境では「AIアシスタント」ページ自体が非表示になる（is_availableがconfig.yamlの設定で判定）。
