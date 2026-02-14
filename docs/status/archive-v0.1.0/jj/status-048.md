[READMEへ戻る](../../README.md)

# status-048: vocab統合修正・エクスポート改善・info -active・parse --full/--lite

**日付**: 2026-02-10

## 概要

7つの機能修正・追加を実施:
1. **vocab.yamlマージ修正**: `vocab.yaml`の`mapping`を`GraphConfig.vocab`にマージし、JSONから読み取ったキーのvocab置換が正しく動作するよう修正
2. **-id/-v vocab対応**: vocab変換後のキー（例: "条件"/"バージョン"）でも`-id`/`-v`検索が機能するよう修正
3. **Obsidian frontmatter修正**: vocab変換後にindex/version値が消失するバグを修正
4. **CSV UTF-8 BOM**: CSVエクスポート時にUTF-8 BOMを付与し、Excelでの日本語文字化けを防止
5. **JSONエクスポート平坦化オプション**: `--flatten`フラグ追加。JSONはデフォルト非平坦化、CSVは常に平坦化
6. **info -active**: `active == "true"`のノードのみ表示するフィルタオプション追加
7. **parse --full/--lite**: 重いパーサー（pymeshメッシュ統計等）を`--full`時のみ実行。1ファイルあたり1秒超の処理は警告出力

テスト480件パス（前回比+13件）、0件失敗（既存pymesh環境依存1件除く）、20スキップ。

## 変更内容

### 1. vocab.yamlマージ修正（JSON keyのvocab置換）

**背景**: `JsonPropertyParser`が追加するプロパティキー（例: "stress-result"）がvocab置換されない問題。原因は`GraphConfig.vocab`が`config.yaml`のvocabセクションのみ読み込み、`vocab.yaml`のmappingをマージしていなかったこと。

**実装**:
- `config/__init__.py`: `GraphConfig.load()`で`vocab.yaml`のmappingも読み込み、`config.yaml`のvocabとマージ（vocab.yamlが優先）

### 2. -id/-v検索のvocab対応

**背景**: `file_to_node()`でvocab（`idx: 条件`, `v: バージョン`）が適用されると、ノードのプロパティキーが"index"→"条件"、"version"→"バージョン"に変換される。しかし`search_nodes()`は"index"/"version"キーのみ参照するため、vocab使用時に`-id`/`-v`検索が機能しなかった。

**実装**:
- `services/service/info.py`: `search_nodes()`でvocab変換後のキー名も参照するよう修正
- `InfoService.__init__()`で`self._vocab`を保持

### 3. Obsidian frontmatterのvocab値消失バグ修正

**背景**: `node_to_frontmatter()`で`props.pop("index", "")`を先に実行するが、vocab変換後は"index"キーが存在しない。その後のバリアント除去処理でvocab変換後キー（"条件"等）の値が失われていた。

**実装**:
- `services/export/connectors/obsidian/__init__.py`: rawキー（"index"/"version"）を優先した順序付き探索に変更。全バリアントキーを収集して値を取得してから除去
- `_get_node_index()`/`_get_node_version()`ヘルパーを追加し、`_build_version_groups`等でも使用

### 4. CSVエクスポート UTF-8 BOM追加

**背景**: UTF-8エンコーディングのCSVファイルをExcel（特にWindows）で開くと日本語が文字化けする問題。

**実装**:
- `services/service/info.py`: `export_data()`のCSV出力で`encoding="utf-8-sig"`を使用（BOM付きUTF-8）

### 5. JSONエクスポート平坦化オプション

**背景**: JSONエクスポート時にネスト辞書が平坦化されると構造情報が失われる。JSONでは階層構造を維持し、必要時のみ平坦化できるようにする。

**実装**:
- `services/service/info.py`: `export_data()`に`flatten`パラメータ追加（CSV: デフォルトTrue, JSON: デフォルトFalse）
- `services/cli/graph.py`: exportコマンドに`--flatten`フラグ追加

### 6. info -active オプション

**背景**: old/フォルダ等の非アクティブノードを除外して表示したいケースが多い。

**実装**:
- `services/service/info.py`: `search_nodes()`に`active_only`パラメータ追加
- `services/cli/graph.py`: info/exportコマンドに`-active`フラグ追加

### 7. parse --full / --lite オプション

**背景**: pymeshによる.inp全読み込みは1ファイルあたり数秒かかるため、通常のパースでは不要。

**実装**:
- `services/parse/base.py`: `AbstractFileParser`に`requires_full`属性追加（デフォルトFalse）
- `parse()`関数に`full_mode`パラメータ追加。`requires_full=True`のパーサーは`full_mode`時のみ実行
- `--full`未指定で1ファイルあたり1秒超のパーサーはstderrに警告出力
- `services/parse/connectors/abaqus/mesh_parser.py`: `AbaqusMeshParser`に`requires_full = True`設定
- `services/graph/__init__.py`: `parse_project()`/`parse_and_save()`に`full_mode`パラメータ追加
- `services/cli/graph.py`: parse/exportコマンドに`--full`フラグ追加

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `config/__init__.py` | 変更: GraphConfig.load()でvocab.yamlのmappingをマージ |
| `services/service/info.py` | 変更: search_nodesのvocab対応・active_only追加、export_dataのflatten・BOM対応 |
| `services/export/connectors/obsidian/__init__.py` | 変更: frontmatterのvocab値消失バグ修正、_get_node_index/version追加 |
| `services/parse/base.py` | 変更: AbstractFileParser.requires_full追加、parse()にfull_mode・時間警告 |
| `services/parse/connectors/abaqus/mesh_parser.py` | 変更: requires_full = True設定 |
| `services/graph/__init__.py` | 変更: parse_project/parse_and_saveにfull_mode追加 |
| `services/cli/graph.py` | 変更: -active, --flatten, --fullフラグ追加 |
| `tests/test_selection_and_export.py` | 変更: 13件のテスト追加 |

## テスト結果

```
480 passed, 0 failed (pymesh環境依存1件除く), 20 skipped
```

- 新規テスト13件: vocab検索(3件)、active_only(2件)、CSV BOM(1件)、JSON平坦化(3件)、parse full_mode(3件)、vocabマージ(1件)
- 既存テスト467件: 全パス

## 使用例

```bash
# vocab変換後キーで検索
jj info -id 1 -v 3                    # "条件"/"バージョン"キーでも検索可

# activeフィルタ
jj info -all -active                   # active=trueのノードのみ
jj export --target csv -all -active    # activeのみCSVエクスポート

# JSON平坦化オプション
jj export --target json -all -o data.json          # ネスト維持（デフォルト）
jj export --target json -all --flatten -o flat.json # 平坦化

# parse full/lite
jj parse                               # lite（pymeshメッシュ統計スキップ）
jj parse --full                        # full（pymeshメッシュ統計含む）
jj export --parse --full --target obsidian  # fullパース後エクスポート
```

## TODO / 次のステップ

- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤
- [ ] vocab置換をGUI/ダッシュボードからプレビューできる機能
- [ ] CSVエクスポートのカラム順序カスタマイズ

## 確認事項

- `vocab.yaml`のmappingと`config.yaml`のvocabセクションはマージされる。`vocab.yaml`のmappingが同一キーの場合優先される。
- `-active`フィルタは`active`プロパティが文字列`"true"`（大文字小文字不問）のノードのみ通過する。
- `--full`未指定時、`AbaqusMeshParser`は実行されない。1ファイルあたり1秒超の処理時間を検出した場合はstderrに警告を出力する。
