[← status-index.md](status-index.md)

# status-091 — ダッシュボード層の全削除（CLIファースト回帰）

- **日付**: 2026-06-04
- **ブランチ**: claude/jj-cli-workspace-ypjUt
- **バージョン**: 0.2.1

---

## 概要

jjは「Streamlitダッシュボード」をターゲットに設計の重心がGUIへ引っ張られ、
CLIで息を吐くように業務をこなすという本来の喜びから乖離していた（キメラ化）。
本作業では**ダッシュボード／GUIサーバー層をコードベースから丸ごと切除**し、
CLI・グラフ・パーサー・エクスポーターという健全な胴体だけを残した。

`jj parse` の起動コスト計測でも、CLI起動（~100ms）は streamlit/plotly/pandas を
一切 eager-import しておらず、ダッシュボードは「胴体に縫い付けられた帽子」であることを確認。
帽子を脱がせても中核は崩れない、という前提で切除を行った。

### 切除の効果

| 指標 | Before | After |
|------|--------|-------|
| 変更ファイル | — | 58（削除27・修正31） |
| 行数 | — | **+30 / −19,815**（約20k行削除） |
| ruff format 対象 | 223 | 197（−26ファイル） |
| テスト | 1644 passed / 113 skipped | 1169 passed / 15 skipped / **0 failed** |

> テスト数の減少（−475 passed / −98 skipped）は、丸ごと削除した
> `test_dashboard.py` / `test_dashboard_e2e.py`（巨大ファイル＋streamlit未導入でskipされていた多数）に
> 完全に一致し、機能回帰は無い。

---

## 削除したもの（丸ごと）

### GUI／サーバー本体
- `services/dashboard/`（Streamlitダッシュボード一式・7,095行）
- `services/cli/launchers.py`（`jj dashboard` / `jj serve` ランチャー。`serve` は参照先 `services/api/` が既に存在せず死んでいた）
- `services/service/api_service.py`（REST API向けサービス。`services/api/` 消失により孤児化）
- `services/export/connectors/dashboard_json.py`（DashboardJsonExporter）
- `plugins/base/dashboard.py`（`DashboardPageConnector` 基底）
- `plugins/abaqus/dashboard.py`（Abaqus物性ページコネクター）
- `tests/test_dashboard.py`, `tests/test_dashboard_e2e.py`
- `examples/jj-plugin-example/.../dashboard.py`（外部プラグイン例のコネクター）

### CLIコマンド
- `jj dashboard`（Streamlit起動）
- `jj serve`（FastAPI REST、既に死んでいた）
- `jj export --target dashboard-json`

### SDK／プラグイン基盤からの概念除去
- `PluginManifest.dashboard_pages` フィールド
- `Capability.DASHBOARD_PAGE`
- `jj.dashboard_connectors` entry_pointグループの発見処理
- `JJApp.get_dashboard_pages()` / `get_dashboard_page_data()`
- `services.sdk` / `plugins` / `plugins.base` からの `DashboardPageConnector` および
  connector系ヘルパ（`generate_connector_pages_html` 等）の re-export

### 依存・ドキュメント
- `pyproject.toml`: `[project.optional-dependencies] dashboard`（streamlit/aggrid/plotly）を削除、`all` から除外
- `CLAUDE.md` / `README.md` / `docs` / example: ダッシュボード記述を除去

---

## 残したもの（意図的に据え置き）

- **`config.DashboardConfig` / `SavedViewConfig`**: GUIを一切importしない純粋な設定スキーマで、
  起動コストもパース重さも増やさない。一方 `GraphConfig` に深く編み込まれ多数の後方互換分岐と
  テストを持つため、ここを切るとコア設定パスを壊すリスクが高く喜びへの寄与はゼロ。
  → 今回は触らず、次パスの刈り取り候補とする。
- **`services/graph/query/` の `saved_view` 系フィルタ関数**: dictベースで config クラスにも
  GUIにも依存しない純関数。query層の安定を優先して据え置き（docstringの歴史的言及のみ整理）。
- **`services/api/` の entry（`get_api_routes` 等のSDKプラグイン汎用配管）**: dashboardとは別概念のため非対象。
  ただし `jj serve` コマンド自体は削除済み。

---

## 検証結果

```
ruff check .          # All checks passed!
ruff format --check . # 197 files already formatted
pytest                # 1169 passed, 15 skipped, 0 failed
```

### CLI動作確認（temp project）

| コマンド | 結果 |
|----------|------|
| `jj`（ヘルプ） | dashboard/serve が消え、init/parse/show/export/info/diff/run/config のみ表示 |
| `jj parse` | グラフ生成OK（ノード・リレーション生成） |
| `jj show --summary` | サマリー表示OK |

---

## TODO（次パス候補）

- [ ] `config.DashboardConfig` / `SavedViewConfig` の刈り取り（GraphConfig依存の慎重な切り離し）
- [ ] `services/graph/query/` の `saved_view` フィルタ関数の要否判断（dashboard消失後の利用実態確認）
- [ ] `docs/specs/09-dashboard.md` ほかダッシュボード仕様書の扱い（アーカイブ移動 or 削除）
- [ ] アイデア軸B（汎用 `RepositoryNode` への "ポイポイ放り込み＋一覧"、`jj jobs`、tips/物性配信）の着手
