[READMEへ戻る](../../README.md)

# status-044: NO_NODE_EXTENSIONS、materialパーサーvocab対応、ディレクトリ階層relation、JSONプロパティパーサー

**日付**: 2026-02-10

## 概要

5つの機能追加・改善を実施:
1. `.odb`/`.odb.json`をNO_NODE_EXTENSIONS（スキャンするがNode化しない拡張子）に追加
2. materialパーサーにvocab/token-key-mapによる置換ロジックを追加
3. ProjectGraph.iterate_directories()でnon_file_nodesを反映
4. ディレクトリツリーの親子階層構造をcontains relationとして追加
5. go_*.inpに紐づくJSONファイルの第一階層key-valueをプロパティとして割り当てるJsonPropertyParserを新規追加

テスト439件パス、4件失敗（既存の不整合、今回変更と無関係）、20スキップ。パイプラインテスト29件全パス。

## 変更内容

### 1. NO_NODE_EXTENSIONS（.odb, .odb.json）

`.odb`と`.odb.json`はスキャンされるがNodeの実体を作らない拡張子として定義。

**定義場所**: `services/parse/file_parse.py`、`services/parse/base.py`

```python
NO_NODE_EXTENSIONS: tuple[str, ...] = (
    ".odb.json",  # ODBメタデータ（長い拡張子を先に評価）
    ".odb",       # Abaqus ODBバイナリ
)
```

**フィルタリング**: `services/graph/__init__.py` の `parse_project()` でファイル名末尾チェックによりNode生成をスキップ。

### 2. materialパーサーにvocab/token-key-map置換ロジック追加

`AbaqusInpParser._build_material_nodes()` を拡張:
- 材料名（例: `steel_iso`）を`_`でトークン分割
- 各トークンにtoken-key-mapを適用（指定キーへのマッピング）
- vocabでpropsのキー・値を変換
- verbose_name構築（token-key-map適用キーは値のみ含める）
- verbose_nameの各パーツをタグに追加

材料ノードは実ファイルを持たないため、`source_file`プロパティで元ファイルのパスを保持する。

### 3. ProjectGraph.iterate_directories()でnon_file_nodesを反映

`iterate_directories()`に、実ファイルを持たないノード（material, elset等）を`ProjectDirectory.non_file_nodes`に配置するロジックを追加:
- `path`プロパティがなく`format != "directory"`のノードを対象
- `source_file`からディレクトリを特定し、該当ディレクトリの`non_file_nodes`に`ProjectNonFileNode`として追加

### 4. ディレクトリ階層構造のcontains relation

**DirectoryRelationParser** (priority=50):
- 全ディレクトリノード作成後、パスの親子関係からディレクトリ間のcontains関係を構築
- 例: `results/sub/` → `results/` contains `results/sub/`

**RootDirectoryParser** (priority=98):
- ルート直下のディレクトリノードもcontainsでリンク
- 例: root contains `results/`, root contains `tools/`

### 5. JsonPropertyParser（新規パーサー）

go_*.inpに紐づく`.json`ファイル（`.odb.json`除外）の第一階層key-valueを、go_*.inpノードのプロパティに割り当てる。

**ファイル**: `services/parse/parsers/json_property_parser.py`
**priority**: 33（OutputRelationParser直後）

**動作**:
1. go_*.inpノードとjsonノードをbasenameプレフィックスでマッチ
2. JSONファイルを読み込み（NaN/Infinity→null変換対応）
3. ファイル名のサフィックスをキー、JSON内容を値としてpropertyに格納

**例**:
- `results/go_idx0.v29_stress.json` → `go_idx0.v29.inp` の `stress` プロパティに `{"0(center)": 0.25, "1": null, "2(edge)": null}` を割り当て

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/parse/file_parse.py` | 変更: NO_NODE_EXTENSIONS定義追加 |
| `services/parse/base.py` | 変更: NO_NODE_EXTENSIONS定義追加 |
| `services/graph/__init__.py` | 変更: parse_projectでNO_NODE_EXTENSIONSフィルタリング |
| `services/parse/connectors/abaqus/inp_parser.py` | 変更: materialパーサーにvocab/token-key-map対応 |
| `services/graph/project_graph.py` | 変更: iterate_directoriesでnon_file_nodes反映 |
| `services/parse/parsers/directory_parser.py` | 変更: ディレクトリ階層contains関係、ルート直下ディレクトリリンク |
| `services/parse/parsers/json_property_parser.py` | 新規: JsonPropertyParser |
| `services/parse/parsers/__init__.py` | 変更: JsonPropertyParser import追加 |
| `tests/test_graph_feature.py` | 変更: .odbノード非生成・ディレクトリ階層に対応したテスト更新 |
| `tests/test_parser_units.py` | 変更: RootDirectoryParserのcontains期待値更新 |

## テスト結果

```
439 passed, 4 failed, 20 skipped in 494.36s
```

- パイプラインテスト: 29件全パス
- ユニットテスト: 18件全パス
- グラフ機能テスト: 191件パス、18スキップ
- 4件失敗はObsidianConnectorのvocabテスト（`idx→番号` vs `idx→条件`の不整合、今回変更と無関係・既存バグ）

## TODO / 次のステップ

- [ ] services/cliのロジックをservices/serviceに切り出す
- [ ] ObsidianConnectorのvocabテスト不整合修正（`番号` → `条件`に統一）
- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤

## 確認事項

- NO_NODE_EXTENSIONSはハードコード定数として定義。将来的にconfig.yamlで設定可能にすることも検討。
- materialのvocab/token-key-map適用は、ファイル名パース（file_to_node）と同様のパターンに従う。
- ディレクトリ階層のcontains関係は、ignore設定で除外されたディレクトリには適用されない。
