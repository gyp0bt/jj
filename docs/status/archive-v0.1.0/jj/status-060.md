[READMEへ戻る](../../README.md)

# status-060: パーサーキャッシュ実装 & ダッシュボードプロジェクト開始

**日付**: 2026-02-11
**作業者**: Claude Code
**ブランチ**: `claude/parser-cache-dashboard-WzUNB`

---

## 実施内容

### 1. パーサーキャッシュ機構の実装

#### 背景
`AbaqusDiffParser`が`read_inp()`を多数回呼び出す際、同一ファイルの重複パースが発生していた。
例: バージョンv1, v2, v3が存在する場合、v2は(v1,v2)と(v2,v3)の2回パースされていた。

#### 実装内容
- **`ProjectGraph._parser_cache`**: 汎用パーサー間キャッシュを追加（`dict[str, Any]`）
  - `get_cache(key)` / `set_cache(key, value)`: 汎用キャッシュAPI
  - `get_cached_abq_data(file_path)` / `set_cached_abq_data(file_path, data)`: ABQData専用API
- **`AbaqusDiffParser._get_or_parse_inp()`**: キャッシュ経由で`read_inp()`を呼ぶヘルパー
  - キャッシュヒット時はI/Oとパースをスキップ
  - キャッシュミス時は`read_inp()`を実行しキャッシュに保存

#### 変更ファイル
- `services/graph/project_graph.py`: `_parser_cache`フィールドと4つのキャッシュAPIを追加
- `services/parse/connectors/abaqus/diff_parser.py`: `_get_or_parse_inp()`導入

#### テスト
- `tests/test_parser_units.py::TestParserCache`: 4テスト追加
  - `test_cache_set_and_get`: 汎用キャッシュの基本動作
  - `test_abq_cache_set_and_get`: ABQData専用キャッシュの基本動作
  - `test_diff_parser_uses_cache`: 3バージョン時にread_inpが3回のみ（キャッシュなし4回）
  - `test_diff_parser_populates_cache`: DiffParser実行後にキャッシュが populated

### 2. ダッシュボードプロジェクト開始（Phase 2.5 D1完了）

#### 実装内容
- **`services/dashboard/__init__.py`**: DashboardDataProvider公開モジュール
- **`services/dashboard/data_provider.py`**: メインクラス
  - `get_go_table(filters=None)`: go_ノードのテーブルデータ（プロパティ展開、フィルタ対応）
  - `get_node_card(node_id)`: ノード詳細カード（関連ノード含む）
  - `get_plot_data(x_key, y_key, color_key=None)`: プロット用数値データ
  - `get_property_keys()`: 利用可能プロパティキー一覧
  - `get_status_summary()`: 実行ステータスサマリー（completed/failed/unknownカウント）
  - `get_related_files(node_id, label=None)`: 関連ファイル一覧
  - `to_dashboard_json(project_name="")`: dashboard-json形式エクスポート

#### CLIコマンド統合
- `jj export --target dashboard-json` を追加
- `services/cli/graph.py`: `_print_export_dashboard_json()`ハンドラ追加
- `services/service/graph_command.py`:
  - `ExportDashboardJsonResult`データクラス追加
  - `export_dashboard_json()`メソッド追加
  - 出力先: `.j2/storage/dashboard.json`（デフォルト）

#### テスト
- `tests/test_dashboard.py`: 24テスト追加
  - `TestGetGoTable`: 6テスト（フィルタ、プロパティ展開、関連ファイル）
  - `TestGetNodeCard`: 3テスト（取得、存在しないID、リレーション）
  - `TestGetPlotData`: 3テスト（数値データ、カラーキー、欠落プロパティ）
  - `TestGetPropertyKeys`: 3テスト（ソート順、内部キー除外、キー含有）
  - `TestGetStatusSummary`: 3テスト（カウント、ステータス情報、エラー/警告）
  - `TestGetRelatedFiles`: 2テスト（全件取得、ラベルフィルタ）
  - `TestToDashboardJson`: 4テスト（メタデータ、行データ、カラム、グラフ）

---

## テスト結果

```
tests/test_parser_units.py: 66 passed (キャッシュ4件含む)
tests/test_dashboard.py: 24 passed
全テスト（pymesh除く）: 622 passed, 21 skipped
```

---

## ロードマップ更新

- Phase 2.5 D1（DashboardDataProvider）: **完了**
- roadmap.md: D1チェック済み、アーキテクチャ図にdashboard/追加
- 次ステップ: Phase 2.5 D2（Streamlitダッシュボード）

---

## TODO / 次の作業者への引き継ぎ

- [ ] Phase 2.5 D2: Streamlitダッシュボード実装
  - `jj dashboard`コマンド追加
  - テーブル/カード/プロット/ステータスの4ビュー
- [ ] Phase 2.5 D3: REST API (`jj serve`)
- [ ] パーサーキャッシュの他パーサーへの展開（mesh_parserなど重い処理）
- [ ] pymeshテスト（環境依存で現在1件skip）
