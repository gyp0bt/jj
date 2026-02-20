[← README.md](../../README.md) | [← status-index](status-index.md)

# status-036 — status-035 TODO実行: ProcessPool並列化・plotlyダークモード・diff分離

**日付**: 2026-02-19
**マイルストーン**: M2
**ブランチ**: claude/execute-status-todos-11ExX

---

## 概要

status-035のTODO3件を実行。ProcessPoolExecutorによる真の並列化対応、
plotlyテーマのStreamlitダークモード連動、diff_abq_blocksのメッシュ差分と
メタデータ差分の完全分離を実装。

---

## 実施内容

### 1. ProcessPoolExecutorへの切り替え（CPU-bound部分の並列化）

**ファイル**: `services/parse/connectors/abaqus/mesh_parser.py`

- `_parse_inp_worker()` モジュールレベル関数を追加:
  - ProcessPoolExecutorで使用するためpickle可能な設計
  - 子プロセスで`read_inp()`を独立実行
- `_compute_optimal_workers()` に `use_processes` パラメータ追加:
  - `use_processes=True`: CPU数を上限（GIL回避の真の並列化）
  - `use_processes=False`: CPU数×2を上限（I/O待ち隠蔽、従来動作）
- `_prefetch_inp_parallel()` に `use_processes` パラメータ追加:
  - `None`（デフォルト）: ファイル数 >= 3でProcessPool、それ未満でThreadPool
  - `True`/`False`: 強制指定
  - ProcessPoolExecutor起動失敗時はThreadPoolExecutorに自動フォールバック
- `_PROCESS_POOL_THRESHOLD = 3` クラス定数追加:
  - プロセス起動オーバーヘッドが支配的にならない閾値

**設計判断**: ファイル数が少ない場合はプロセス起動コストが支配的になるため、
ハイブリッド戦略を採用。3ファイル以上でProcessPool、それ以下でThreadPoolに自動切替。
ProcessPoolが利用不可の環境ではThreadPoolにフォールバック。

### 2. plotlyテーマのダークモード自動切替

**ファイル**: `services/dashboard/widgets.py`, `services/dashboard/components/status.py`

- `get_plotly_template()` 関数を `widgets.py` に追加:
  - `st.get_option("theme.base")` でStreamlitテーマを検出
  - ダークテーマ → `"plotly_dark"`、それ以外 → `"plotly_white"`
  - Streamlit未インストール・テーマ未設定時は `"plotly_white"` にフォールバック
- `status.py` のCPU時間・警告件数ヒストグラム:
  - ハードコードの `template="plotly_white"` を `get_plotly_template()` に置換

**設計判断**: テーマ検出関数を `widgets.py`（プロットスタイルヘルパーセクション）に
配置し、将来的に他のダッシュボードコンポーネントからも利用可能にした。

### 3. diff_abq_blocksのメッシュ差分とメタデータ差分の完全分離

**ファイル**: `services/parse/connectors/abaqus/__init__.py`, `services/parse/connectors/abaqus/diff_parser.py`

- `diff_abq_mesh_blocks()` 関数を新規追加:
  - トップレベルのメッシュデータ（nodes/elements/nsets/elsets）の差分のみ抽出
  - STEP/raw_blocksは比較しない
- `diff_abq_metadata_blocks()` 関数を新規追加:
  - STEP配下のblocks + STEP外のraw_blocksの差分のみ抽出
  - メッシュデータは比較しない
- `diff_abq_blocks()` を統合ラッパーに変更:
  - `diff_abq_mesh_blocks()` + `diff_abq_metadata_blocks()` の結果を連結
  - 後方互換を完全に維持
- `AbaqusDiffParser.apply()` を最適化:
  - `mesh_identical=True` の場合、`diff_abq_metadata_blocks()` のみを呼び出し
  - メッシュ同一ペアでの不要なメッシュ比較を完全スキップ

**設計判断**: 既存の`diff_abq_blocks()`は後方互換ラッパーとして維持。
新規関数を追加する形で分離し、呼び出し側が用途に応じて選択可能にした。

---

## テスト結果

- 新規テスト: 14件追加（全通過）
  - `TestComputeOptimalWorkersProcessMode`: 4件（プロセスモードワーカー数計算）
  - `TestProcessPoolThreshold`: 1件（閾値定数）
  - `TestGetPlotlyTemplate`: 4件（テーマ検出：light/dark/None/ImportError）
  - `TestDiffSeparation`: 5件（mesh/metadata分離・統合一致性）
- 既存テスト: 206件通過（関連テスト）、1件スキップ（pymesh環境依存）
- ruff check/format: クリーン

---

## TODO

- [ ] `get_plotly_template()` を他のplotly使用コンポーネント（array_plot/plot/abaqus connector等）にも適用
- [ ] ProcessPoolExecutorの実ファイル大量パース時のベンチマーク（Thread vs Process比較）
- [ ] diff_abq_metadata_blocksのraw_blocksからメッシュ関連キーワードを除外するフィルタ追加

---

## 確認事項・懸念

- ProcessPoolExecutorでは`ABQData`がpickleシリアライゼーションされるため、非常に大規模なメッシュ（数百万ノード）ではシリアライゼーションオーバーヘッドが無視できない可能性がある。自動閾値（3ファイル以上）とフォールバック機構で緩和。
- `diff_abq_metadata_blocks`は`_build_nodes_lookup`を構築しているが、lightweight版ABQDataでは`nodes`が空になるため実質的にオーバーヘッドはゼロ。
