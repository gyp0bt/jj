[READMEへ戻る](../../README.md)

# status-032: CLIコマンド省略、info/diff/include伝搬/daily解析、Obsidianエクスポート強化

**日付**: 2026-02-06

## 概要

5つの大きな機能を実装:
1. CLIコマンドの省略化（`jj g` → `jj`）
2. `jj info` コマンドの追加
3. includeファイルのproperty伝搬
4. 前バージョンとのキーワードブロック差分
5. notes/daily日報解析によるグラフ拡張
6. Obsidianエクスポートのwarning/差分表示強化

## 変更内容

### 1. CLIコマンド省略化
- `jj g init` → `jj init` に省略可能
- `jj g parse` → `jj parse`
- `jj g show` → `jj show`
- `jj g export` → `jj export`
- `jj export --parse`: parseしてからexportする統合コマンド
- `jj g` も互換性のため維持

**変更ファイル**:
- `cli/graph.py`: `add_top_level_graph_commands()`, `run_top_level_graph_command()` 追加
- `cli/__init__.py`: トップレベルコマンドのルーティング追加

### 2. `jj info` コマンド
- `jj info <ファイル名>`: ファイルのproperty/relationを表示
- 完全一致・部分一致検索対応
- プロパティ一覧とリレーション一覧を表示

**変更ファイル**:
- `cli/graph.py`: `_run_info()`, `_add_info_args()` 追加

### 3. includeファイルのproperty伝搬
- go_*.inpが*INCLUDEするmesh/materialファイルのpropertyを親ノードに集約
- 伝搬されるプロパティ: mesh統計(mesh_node_count等)、warning/error、materialキーワード
- `include_properties`として辞書形式で親ノードに格納

**変更ファイル**:
- `services/graph/__init__.py`: `_enrich_include_properties()` 追加

### 4. 前バージョンとのキーワードブロック差分
- 同一type+indexの.inpファイルをバージョン順に並べ、隣接バージョン間で差分計算
- 差分は`diff_from`, `diff_summary`, `diff_details` としてpropertyに追加
- `abaqus_connector.py`の`_serialize_component()`でReadProcedureのprocedure_keywordも比較対象に含めるよう修正

**変更ファイル**:
- `services/graph/__init__.py`: `_enrich_version_diff()` 追加
- `services/parse/abaqus_connector.py`: `_serialize_component()`でprocedure_keyword追加

### 5. notes/daily日報解析
- `notes/daily/`ディレクトリ内の日報（Obsidian dailyノート）を解析
- ファイル参照の検出パターン:
  - リスト項目: `- go_idx1.inp`
  - プロパティ付き: `go_idx1.inp: 備考: 最終版`
  - Obsidianリンク: `[[go_idx1.inp]]`
- セクション名・タグの検出
- `daily_note`ノードの生成と`mentioned_in`関係の構築
- 日報のプロパティを対象ファイルノードに反映（`daily_notes`, `daily_sections`）

**新規ファイル**:
- `services/connectors/daily_connector.py`: 日報解析コネクタ

### 6. Obsidianエクスポートのwarning/差分表示強化
- frontmatterのpropertyに加え、markdown本文にも記載（視認性向上）
- `## 警告・エラー`セクション: sta_warnings, sta_errors, msg_warnings, msg_errors
- `## 前バージョンとの差分`セクション: diff_from, diff_summary, diff_details

**変更ファイル**:
- `services/connectors/obsidian.py`: `_format_md()`拡張

## テスト結果

- **260件パス**（+18件）、8件スキップ（CLI環境依存テスト）
- 新規テストクラス:
  - `TestCliTopLevelCommands`: CLIトップレベルコマンドの引数定義テスト（6件）
  - `TestInfoCommand`: infoコマンドのノード検索テスト（2件）
  - `TestIncludePropertyPropagation`: includeプロパティ伝搬テスト（2件）
  - `TestVersionDiff`: バージョン差分テスト（3件）
  - `TestObsidianWarningDisplay`: Obsidian warning/diff表示テスト（3件）
  - `TestDailyNotesParsing`: daily解析テスト（7件）
  - `TestExportParse`: export --parseフラグテスト（2件）

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `cli/__init__.py` | 変更: トップレベルコマンドルーティング追加 |
| `cli/graph.py` | 変更: コマンド引数関数分離、info/export --parse追加 |
| `services/graph/__init__.py` | 変更: include伝搬、version diff、daily解析統合 |
| `services/parse/abaqus_connector.py` | 変更: procedure_keyword比較対象追加 |
| `services/connectors/obsidian.py` | 変更: warning/diff markdown本文出力 |
| `services/connectors/daily_connector.py` | 新規: 日報解析コネクタ |
| `tests/test_graph_feature.py` | 変更: 25件のテスト追加 |

## TODO / 次のステップ

- [ ] `jj info` のJSON出力オプション（`--json`）
- [ ] daily解析の Obsidianリンク検出の高度化（ディスプレイ名対応）
- [ ] version diff をincludeされたファイル（mesh, material）の変更にも対応
- [ ] `jj export --parse` のプログレスバー表示
- [ ] 大量のdailyノートに対するパフォーマンス検証
- [ ] CLI環境テストの独立化（SSH依存の解消）
