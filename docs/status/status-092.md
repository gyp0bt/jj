[← status-index.md](status-index.md)

# status-092 — jj jobs コマンド追加（軸B 第一歩・CLIで「軽い一覧」）

- **日付**: 2026-06-04
- **ブランチ**: claude/jj-jobs-cli-A8iQ9
- **バージョン**: 0.2.1

---

## 概要

ダッシュボードという退路を断った（status-091）後の最初の一歩。
**「CLIに留まる価値」＝息を吐くように業務をこなす口** を作る軸B
（汎用レポジトリ＋一覧）の第一歩として、ワークスペース内の
RUN（ジョブ）一覧を表示する `jj jobs` を最小実装した。

ロジックは既に揃っていた（`RunQueryService.get_runs()`・`NodeCategory.RUN`・
`get_nodes_by_category()`）。不足していたのは「息を吐く口」＝薄いCLIコマンド
だけ、という前セッションの見立て通り、新しい抽象化はゼロで実装できた。

`jj show` と完全に同じ三層構造（CLI解析 → GraphCommandService → RunQueryService）
に乗せ、CLI層は argparse 解析と出力整形のみに責務を限定した。

---

## 追加したもの

### サービス層（`services/service/graph_command.py`）
- `JobsResult` dataclass（`jobs: list[Node]`, `empty: bool`）— 既存の `ShowResult` 等に倣う
- `GraphCommandService.jobs(run_type, run_status, graph_filename)`
  - グラフをロードし、空なら `empty=True`
  - `RunQueryService(graph).get_runs(run_type, run_status)` に委譲して返すだけ

### CLI層（`services/cli/graph.py`・`services/cli/__init__.py`）
- トップレベルコマンド `jj jobs` を追加
  - `--type`（run_type 絞り込み）/ `--status`（run_status 絞り込み）/ `-f`（グラフファイル指定）
- `_run_jobs()` ハンドラ — 一覧を `[id] name` ＋ `type/status/started_at` の2行で整形出力
- `dispatch` 分岐タプル・ルートヘルプに `jobs` を追加

### 出力例

```
=== ジョブ一覧 (1件) ===

[3] s.py
    type: script  status: completed  started: 2026-06-04T12:14:30+00:00
```

絞り込み 0 件時・空グラフ時はそれぞれ案内メッセージを出す。

---

## テスト（先行）

`tests/test_jobs_command.py` を新規作成（計11件）:

- **サービス層 6件**: 全件 / run_type / run_status / AND複合 / 空グラフ（empty=True）/ RUNノード無し
- **CLI層 5件**: jobs解析 / --type・--status・-f 解析 / 一覧出力 / 空グラフ案内 / 0件案内

検証結果:
- `pytest`: **1180 passed / 15 skipped / 0 failed**（旧1169 → +11）
- `ruff check` / `ruff format --check`: clean
- CLIスモーク: `jj r python s.py` → `jj jobs` でRUNノードが一覧表示、`--type`/`--status` 絞り込みも動作確認

---

## 設計判断

- **「ジョブ＝RUNノード」**: `jj_types` docstring は REPOSITORY を「集合体」と説明するが、
  ワークスペース内のジョブの実体は RUN ノード（`get_runs` が返す対象）。
  軸Bの第一歩としては RUN 一覧が最小かつ正解。
- **新抽象化ゼロ**: 1コマンドのために専用ヘルパーやレジストリは作らず、
  既存の三層構造にそのまま乗せた（CLAUDE.md「過度な抽象化の回避」に従う）。
- **コミット粒度**: サービス層 / CLI層 の2コミットに分割。

---

## TODO（次パス候補）

- [ ] **J-1**: `jj jobs` の出力拡充（入力/出力ファイル数・duration・exit_code 列、`--detail`）
- [ ] **J-2**: ソート順の制御（started_at 降順デフォルト・`--sort`）
- [ ] **J-3**: 軸B 本丸 = `NodeCategory.REPOSITORY` を使った汎用レポジトリ一覧
- [ ] **DR-5**（status-091 継続）: `config.DashboardConfig` / `SavedViewConfig` の刈り取り
- [ ] **DR-6**（status-091 継続）: `docs/specs` ダッシュボード仕様書の扱い
