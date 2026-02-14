[READMEへ戻る](../../README.md)

# status-047: 共通選択コマンド・jj info拡張・CSVエクスポート改善・vocab一括置換

**日付**: 2026-02-10

## 概要

4つの機能追加・改善を実施:
1. **共通ファイル選択コマンド**: `-id 1..3`の範囲展開ユーティリティ（`expand_ranges()`）
2. **jj info拡張**: `-all`（全ノード選択）、`-prop`（プロパティフィルタ）、`-type`（タイプフィルタ）引数追加
3. **CSVエクスポート改善**: ネスト辞書の"."区切り平坦化、`-prop`によるカラム絞り込み、共通選択オプション対応
4. **vocab一括置換**: `VocabFinalizer`パーサー(priority=100)で全パーサー実行後にvocab置換を一括適用し、置換漏れを解消

テスト467件パス（前回比+23件）、0件失敗、20スキップ。

## 変更内容

### 1. 共通ファイル選択コマンド（範囲展開）

**背景**: `-id 1 2 3`のように複数指定が冗長。`1..3`で範囲展開できると便利。

**実装**:
- `services/lib/selection.py`: `expand_ranges()`関数を新規作成
  - `1..3` → `["1", "2", "3"]`
  - `3..1` → `["3", "2", "1"]`（逆順対応）
  - 数値以外はそのまま通過
- CLI層（`_run_info`, `_run_export_data`）で`-id`/`-v`引数に`expand_ranges()`を適用

**使用例**:
```bash
jj info -id 1..5 -v 1..3    # id=1〜5、version=1〜3に展開
jj export --target csv -id 1..3 -type Abaqusインプット
```

### 2. jj info拡張（-all, -prop, -type）

**背景**: 特定プロパティを持つノードのみ出力したい。全ノード対象で`-prop 応力`のような使い方を可能にする。

**実装**:
- `_add_info_args()`: `-all`、`-prop`、`-type`引数を追加
- `InfoService.search_nodes()`: `all_nodes`、`type_filter`パラメータ追加
- `_run_info()`: `-prop`指定時は該当プロパティを持つノードのみ表示し、その値だけを出力

**使用例**:
```bash
jj info -all -prop 応力           # 応力プロパティを持つ全ノードとその応力値を出力
jj info -all -type Abaqusインプット  # 全Abaqusインプットノードを表示
jj info -id 1..3 -prop 応力 変位   # id=1〜3で応力・変位プロパティ表示
```

### 3. CSVエクスポート改善

**背景**: `mesh_quality`やJSONから読んだ階層データがCSVでは`json.dumps`文字列として出力されていた。"."区切りで平坦化してCSVカラムとして展開する。

**実装**:
- `_flatten_properties()`: ネスト辞書を再帰的に平坦化
  - `{"mesh_quality": {"aspect_ratio": {"min": 0.5}}}` → `{"mesh_quality.aspect_ratio.min": 0.5}`
  - リストは展開せずそのまま保持
- `export_data()`: `prop_filters`、`nodes`パラメータ追加
- `_add_export_args()`: `-id`、`-v`、`-all`、`-prop`引数追加
- `_run_export_data()`: 共通選択オプション（`-id`, `-v`, `-all`）でノード事前絞り込み

**使用例**:
```bash
jj export --target csv -all -type Abaqusインプット -prop 応力 -o stress.csv
jj export --target csv -id 1..3 -v 1 -o results.csv
```

### 4. vocab一括置換（VocabFinalizer）

**背景**: `file_to_node()`でのvocab置換はファイル名由来のプロパティのみ対象。パーサーパイプライン（JsonPropertyParser, ResultParser, MeshParser等）が追加するプロパティはvocab置換を経由せず、設定した翻訳が反映されない問題があった。

**実装**:
- `services/parse/parsers/vocab_finalizer.py`: `VocabFinalizer`クラスを新規作成
  - priority=100（全パーサーの最後に実行）
  - 全ノードのpropertiesを走査し、キーと文字列値にvocabを適用
  - ネスト辞書のキーも再帰的に変換
  - 既に変換済みのキー/値は二重変換されない（vocab辞書にないためそのまま通過）

**対象パーサー（vocab漏れ解消）**:
- `JsonPropertyParser` (priority=33): JSONファイルのサフィックスキー
- `AbaqusResultParser` (priority=70): analysis_status, cpu_time等
- `AbaqusMeshParser` (priority=80): mesh_node_count等
- `AbaqusDiffParser` (priority=90): diff_from, diff_summary等
- `AbaqusIncludePropertyParser` (priority=86): include_properties

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/lib/selection.py` | 新規: expand_ranges()範囲展開ユーティリティ |
| `services/parse/parsers/vocab_finalizer.py` | 新規: VocabFinalizer最終パスパーサー |
| `services/parse/parsers/__init__.py` | 変更: VocabFinalizerのimport追加 |
| `services/cli/graph.py` | 変更: info/exportコマンドの引数追加、_run_info/_run_export_data改修 |
| `services/service/info.py` | 変更: search_nodesにall_nodes/type_filter追加、export_dataに平坦化・prop_filters追加、_flatten_properties新規 |
| `tests/test_selection_and_export.py` | 新規: 23件のテスト追加 |

## テスト結果

```
467 passed, 0 failed, 20 skipped
```

- 新規テスト23件: expand_ranges(8件)、search_nodes拡張(4件)、平坦化(5件)、VocabFinalizer(6件)
- 既存テスト444件: 全パス（VocabFinalizer追加によるリグレッションなし）

## TODO / 次のステップ

- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤
- [ ] vocab置換をGUI/ダッシュボードからプレビューできる機能
- [ ] CSVエクスポートのカラム順序カスタマイズ
- [ ] results/以外のinfo-onlyディレクトリの設定化

## 確認事項

- VocabFinalizerはpriority=100で全パーサーの後に実行される。EnrichmentOnlyFilter(priority=99)でノード除去後に実行されるため、除去されたノードへの不要な処理は発生しない。
- `file_to_node()`の既存vocab置換は維持（verbose_name生成に必要）。VocabFinalizerは二重変換を防ぐ設計（vocabマップにない値はそのまま通過）。
- `-prop`フィルタはAND条件（全指定プロパティを持つノードのみ対象）。
