# status-052

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

JsonPropertyParserのJSON内キー使用を検証するテスト追加、`-Infinity`のJSONサニタイズ処理順序バグの修正、
ロードマップへの新テスト要件追加（go_inp element/elsetノード化、隣接バージョンdiff差分）。

## 実装内容

### 1. JsonPropertyParser単体テスト追加（test_parser_units.py）

go_inpに紐づくJSONからプロパティを読み取る際、キー名がJSON内のキーであること（ファイル名ではないこと）を明示的にテスト。

追加テスト5件:
- **test_flat_json_keys_used_as_property_keys**: `{key1: value}` → `key1: value`（ファイル名プレフィックスなし）
- **test_nested_json_keys_flattened_with_dot**: `{key1: {key2: v}, key3: v}` → `key1.key2: v, key3: v`
- **test_multiple_json_files_merge_keys**: 複数JSONからのキーマージ
- **test_nan_infinity_replaced_with_null**: NaN/Infinity/−Infinityのnull変換
- **test_odb_json_excluded**: `.odb.json`ファイルの除外

### 2. `-Infinity` JSONサニタイズ処理順序バグ修正（json_property_parser.py）

**原因**: `\bInfinity\b` の置換が `-Infinity` 内の `Infinity` を先に `null` に変換し、`-null` という不正JSONが残る
**修正**: `-Infinity` → `Infinity` の順に置換するよう順序を入れ替え

```python
# 修正前（バグ）
content = re.sub(r'\bNaN\b', 'null', content)
content = re.sub(r'\bInfinity\b', 'null', content)    # -Infinity内のInfinityも置換→-null
content = re.sub(r'\b-Infinity\b', 'null', content)

# 修正後
content = re.sub(r'\bNaN\b', 'null', content)
content = re.sub(r'-Infinity\b', 'null', content)     # -Infinityを先に処理
content = re.sub(r'\bInfinity\b', 'null', content)
```

### 3. ロードマップ更新（roadmap.md）

Phase 2-2（Abaqusコネクターの追加機能）に以下の要件を追加:

#### go_inp element/elsetのabaqus_elsetノード化
- go_inpで定義されたelement・elsetをabaqus_elsetノードとして生成
- volumeなどのelement_qualityを個々のelsetごとに評価しproperty化
- 材料定義を個々のelsetに紐づけてproperty化
- **テスト要件**: goで定義されたelement・elsetがgraph.yamlに書き出されていること

#### 隣接バージョンdiff差分のプロパティ付加
- versionが複数あるgoのプロパティにdiff情報が付加されていることのテスト追加
- node/nsetブロック: 接点数を差分評価対象にする
- element/elsetブロック: 要素数・要素品質を差分評価対象にする
- **テスト要件**: node,nset,element,elsetブロックの接点数・要素数・要素品質が差分プロパティに含まれること

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/parsers/json_property_parser.py` | `-Infinity`サニタイズ処理順序修正 |
| `tests/test_parser_units.py` | JsonPropertyParser単体テスト5件追加 |
| `docs/roadmap.md` | Phase 2-2にelement/elsetノード化、diff差分テスト要件追加 |
| `docs/status/status-052.md` | 本ステータスファイル |

## テスト結果

```
test_parser_units.py: 31 passed (新規5件追加)
test_parser_pipeline.py: 31 passed
合計: 62 passed
```

## パーサー実行順（更新なし）

| priority | パーサー | 備考 |
|----------|---------|------|
| 20 | VersionRelationParser | |
| 30 | ResultRelationParser | |
| 31 | AssetRelationParser | |
| 32 | OutputRelationParser | |
| 33 | JsonPropertyParser | **テスト追加**: JSON内キー使用、ファイル名非使用の検証 |
| 40 | IncludesRelationParser | |
| 50 | DirectoryRelationParser | |
| 60 | AbaqusInpParser | |
| 80 | AbaqusMeshParser | requires_full=True |
| 81 | MeshInheritParser | |
| 85 | AbaqusMaterialAssignmentParser | |
| 86 | AbaqusResultRelationParser | |
| 90 | AbaqusDiffParser | |
| 95 | ObsidianDailyParser | |
| 98 | AbaqusElsetParser / RootDirectoryParser | |
| 99 | EnrichmentOnlyFilter | |
| 100 | VocabFinalizer | |

## 確認事項・TODO

- [x] JSONプロパティのキー名はJSON内キーを使用（ファイル名サフィックスは不使用）→ テスト追加で確認済み
- [x] `-Infinity`のJSONサニタイズ順序バグ修正
- [ ] go_inp element/elsetのabaqus_elsetノード化（ロードマップ2-2に追加済み、未実装）
- [ ] 隣接バージョンdiff差分にnode/nset/element/elsetの接点数・要素数・要素品質を含める（ロードマップ2-2に追加済み、未実装）
