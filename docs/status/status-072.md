[← README.md](../../README.md)

# status-072: T8 Phase 8-3/8-4/8-5 — プラグインガイド・Config汎用化・Run比較汎用化

- 日付: 2026-03-10
- ブランチ: claude/execute-status-todos-zTTaN

## 実施内容

### pyproject.toml: experiment プラグインentry_points追加

- `[project.entry-points."jj.plugins"]` に `experiment` エントリ追加
- `[project.optional-dependencies]` に `experiment = []` 追加
- `all` グループに `experiment` 追加

### T8 Phase 8-3: プラグイン開発ガイド

- **`docs/specs/plugin-development-guide.md`**: [NEW] プラグイン開発ガイド
  - クイックスタート（ディレクトリ構成・register関数・パーサー実装・pyproject.toml登録）
  - priority ガイドライン（10-19: 前処理、50-59: データ抽出、60-69: 構造解析、70-79: Run発見、80-99: 後処理）
  - RunDiscoveryMixin 使用パターン（Run情報辞書構造、ユーティリティ関数一覧）
  - テスト作成ガイド（テンプレート、実行方法）
  - 実装例として物理実験プラグインを参照

### T8 Phase 8-4: Config分類の汎用化

- **`config/__init__.py`**: [MOD] ExtensionsConfig拡張
  - `custom_categories: dict[str, list[str]]` フィールド追加（frozenデータクラス）
  - `get_category(name)`: 組み込み・カスタム両対応のカテゴリ取得メソッド
  - `all_categories()`: 全カテゴリ（組み込み + カスタム）一覧取得メソッド
  - `from_dict()`: 既知キー以外を自動的にcustom_categoriesに収集
- **`config/__init__.py`**: [MOD] DEFAULT_EXTENSIONS拡張
  - `experiment_data: [".csv", ".tsv"]` 追加
  - `ml_model: [".pt", ".pth", ".ckpt", ".pkl", ".joblib"]` 追加
  - `ml_config: [".yaml", ".json", ".toml"]` 追加
- **`shared/assets/default-config.yaml`**: [MOD] `domain-classification` セクション追加
  - experiment / ml / cae ドメインの分類テンプレート（コメントアウト）
  - `run-discovery` モード（metadata / directory / auto）

### T8 Phase 8-5: Run比較ダッシュボードの汎用化

- **`services/dashboard/components/run_comparison.py`**: [MOD] ドメイン非依存化
  - `RUN_STATUS_COLORS` 定数に統合（3箇所のハードコード `status_colors` を除去）
  - `_BASE_TABLE_COLUMNS`: 基本カラム定義（ID, 名前, タイプ, ステータスのみ）
  - `_HIDDEN_PROPERTIES`: テーブル非表示プロパティ（run_type, run_status）
  - `_render_run_table()`: ハードコードカラムから動的カラム生成に変更
    - 全RunのプロパティキーをScan → 自動でテーブルカラムに反映
    - CAE/ML/実験どのドメインでも適切なカラムが表示される
  - HTML生成も同様に動的カラム対応

### テスト

合計20件追加（既存テスト全パス）:
- `tests/config/test_config_loader.py`: 4件追加（custom_categories, get_category, all_categories）
- `tests/test_run_comparison_generic.py`: [NEW] 11件（ステータスカラー、テーブルカラム定義、動的カラム生成、HTML生成）

### T8設計仕様書更新

- **`docs/specs/t8-generic-data-management.md`**: [MOD] Phase 8-3/8-4/8-5の実装内容を反映

## ファイル構成

```
pyproject.toml                                      # [MOD] experiment entry_points
docs/specs/plugin-development-guide.md              # [NEW] プラグイン開発ガイド
config/__init__.py                                  # [MOD] ExtensionsConfig汎用化
shared/assets/default-config.yaml                   # [MOD] domain-classification
services/dashboard/components/run_comparison.py     # [MOD] ドメイン非依存化
tests/config/test_config_loader.py                  # [MOD] 4件追加
tests/test_run_comparison_generic.py                # [NEW] 11件
docs/specs/t8-generic-data-management.md            # [MOD] 実装状況反映
docs/status/status-072.md                           # [NEW] 本status
```

## TODO

### T8 完了確認
- [x] Phase 8-1: Run Discovery標準化
- [x] Phase 8-2: 物理実験プラグイン
- [x] Phase 8-3: プラグイン開発ガイド
- [x] Phase 8-4: Config分類汎用化
- [x] Phase 8-5: Run比較汎用化
- [x] pyproject.toml experiment entry_points

### ワークトラック（継続）
- [ ] T7 ダッシュボードAIアシスタントの実運用テスト（Ollama接続時の動作確認）
- [ ] T3改善候補（モデルレジストリ、Optuna詳細、TensorBoard連携）
- [ ] M2: マルチソルバー検証（検証環境確保後）

## 確認事項・懸念

- ExtensionsConfig の `custom_categories` はfrozen dataclassのため不変。`from_dict()` 時に全カテゴリが確定する設計。
- `domain-classification` はdefault-config.yamlにテンプレートとして追加（コメントアウト状態）。ユーザーが必要に応じて有効化する方式。まだコアの読み込みロジックは未実装で、プラグイン側が直接参照する想定。
- Run比較テーブルの動的カラム生成は、プロパティキーの出現順（最初のRunから順に収集）でカラム順序が決まる。vocabによる表示名変換は現時点では未適用（将来的に検討）。

## 開発運用メモ

- 環境のpytestがインストール先のPythonと不一致だった（`python -m pytest` で解消）。CIでは問題なし。
- GitHub Actions: 直近10件のrunに失敗なし。
