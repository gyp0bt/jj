[READMEへ戻る](../../../README.md)

# status-062: Elset品質統計・ABQDataキャッシュ永続化・設定駆動include探索

**日付**: 2026-02-11
**担当**: Claude Code

---

## 概要

5つの機能を実装: (1) Elsetごとの品質統計、(2) config-driven include search depth、(3) Version diff & elset relation Obsidian可視化、(4) 軽量パーサーへのタイムスタンプ差分展開、(5) ABQDataのpickle永続化キャッシュ。

---

## 実装内容

### 1. 個々のElsetごとの品質統計

**概要**: Elsetに属する要素だけを対象にメッシュ品質メトリクスを計算し、elsetノードに付与する。

| ファイル | 変更内容 |
|---|---|
| `services/parse/connectors/abaqus/mesh.py` | `extract_elset_quality_stats()` 新規追加。Elsetごとに要素をフィルタして品質計算 |
| `services/parse/connectors/abaqus/mesh_parser.py` | `apply()` で `extract_elset_quality_stats()` を呼び出し、`mesh_elset_quality` プロパティを付与 |
| `services/parse/connectors/abaqus/inp_parser.py` | `AbaqusElsetParser` で `mesh_elset_quality` を統合し、各elsetノードに `quality` プロパティを付与 |

**データフロー**:
```
.inpファイル → pymesh品質計算（全要素一括） → Elset別インデックスフィルタ
    → mesh_elset_quality = {ELSET名: {element_count, quality: {volume/detJ/aspect/skewness}}}
    → AbaqusElsetParser → Node(abaqus_elset).properties["quality"]
```

### 2. Config-driven include search depth

**概要**: `*INCLUDE`ディレクティブの探索階層数を設定ファイルで制御可能にする。

| ファイル | 変更内容 |
|---|---|
| `config/__init__.py` | `GraphConfig.include_search_depth` フィールド追加（デフォルト5） |
| `shared/assets/default-config.yaml` | `include-search-depth` 設定項目追加（コメントアウト） |
| `services/parse/connectors/abaqus/__init__.py` | `read_inp()`, `read_files_with_unknown_encoding()` に `include_max_depth` パラメータ追加 |
| `services/parse/connectors/abaqus/mesh_parser.py` | `_get_or_parse_inp()` で `graph.config.include_search_depth` を渡す |
| `services/parse/connectors/abaqus/diff_parser.py` | 同上 |

**設定例**:
```yaml
# .j2/config/config.yaml
include-search-depth: 10  # デフォルト: 5
```

### 3. Version diff & elset relation visualization in Obsidian

**概要**: Obsidianエクスポートでversion_diffノードとabaqus_elsetノードの可視化を改善。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | `_format_md()` に version_diff 専用セクション（比較元/先リンク、差分有無）と abaqus_elset 専用セクション（要素数、材料、品質統計テーブル）を追加 |

**version_diffノード出力例**:
```markdown
## バージョン比較
- 旧バージョン: [[O-go_idx1_v1.inp]]
- 新バージョン: [[O-go_idx1_v2.inp]]
- 差分有無: あり
```

**abaqus_elsetノード出力例**:
```markdown
## Elset情報
- 要素数: 100
- 割り当て材料: Steel_S235
- ソースファイル: [[O-go_idx1.inp]]

### メッシュ品質
| メトリクス | min | max | mean |
|-----------|-----|-----|------|
| volume | 0.1 | 1.0 | 0.5 |
```

### 4. タイムスタンプ差分パースの最適化: 軽量パーサーにも展開

**概要**: ファイルI/Oを行う軽量パーサーにもキャッシュを適用し、未変更ファイルのディスク読み取りを回避。

| パーサー | 変更前 | 変更後 |
|---|---|---|
| IncludesRelationParser | 毎回.inpファイルを全行スキャン | `_parser_cache` にincludeパスをキャッシュ。未変更ファイルはキャッシュから取得 |
| JsonPropertyParser | 毎回.jsonファイルを読み込み | `_parser_cache` にJSON dictをキャッシュ。未変更ファイルはキャッシュから取得 |

**設計判断**: 軽量パーサーはグラフ構造に関わるためパーサー自体はスキップせず、ファイルI/Oのみをキャッシュで回避する方針。リレーション作成やプロパティ付与は毎回実行される。

### 5. ABQDataの永続化キャッシュ（pickle）

**概要**: `read_inp()` のパース結果をpickleでディスクに永続化し、プロセス再起動後も再利用可能にする。

| ファイル | 変更内容 |
|---|---|
| `services/graph/storage/__init__.py` | `save_abq_data()`, `load_abq_data()`, `clear_abq_cache()` メソッド追加 |
| `services/parse/connectors/abaqus/mesh_parser.py` | `_get_or_parse_inp()` で3段階キャッシュ（メモリ→ディスク→新規パース） |
| `services/parse/connectors/abaqus/diff_parser.py` | 同上 |

**キャッシュ探索順序**:
```
1. インメモリキャッシュ（_parser_cache）→ ヒットなら即座に返す
2. ディスクキャッシュ（.j2/storage/abq_cache/*.pickle）→ mtime一致なら返す
3. キャッシュなし → read_inp()で新規パース → 両キャッシュに保存
```

**永続化形式**: pickle (protocol=HIGHEST_PROTOCOL)
- ファイル名: パスのSHA256ハッシュ先頭16文字 + `.pickle`
- 検証: source_path + mtime の一致でキャッシュ有効性を判定
- 保存先: `.j2/storage/abq_cache/`

---

## テスト結果

- **649テストパス、21スキップ**（前回: 641テストパス、21スキップ）
- 新規追加テスト: **11件**
  - `TestABQDataDiskCache`: 4件（save/load、mtime不一致、nonexistent、clear）
  - `TestIncludeSearchDepthConfig`: 4件（デフォルト値、カスタム値、0、負の値エラー）
  - `TestElsetQualityStats`: 2件（品質統計付与、include先からの統合）
  - `TestIncludesParserCache`: 1件（キャッシュ保存確認）
- 既存テスト修正: `counting_read_inp` のシグネチャを `include_max_depth` パラメータに対応

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `include_search_depth` フィールド追加 |
| `shared/assets/default-config.yaml` | `include-search-depth` 設定項目追加 |
| `services/graph/storage/__init__.py` | ABQData永続化キャッシュメソッド追加 |
| `services/parse/connectors/abaqus/__init__.py` | `include_max_depth` パラメータ追加 |
| `services/parse/connectors/abaqus/mesh.py` | `extract_elset_quality_stats()` 新規追加 |
| `services/parse/connectors/abaqus/mesh_parser.py` | 3段階キャッシュ + elset品質統計 |
| `services/parse/connectors/abaqus/diff_parser.py` | 3段階キャッシュ |
| `services/parse/connectors/abaqus/inp_parser.py` | elset品質統計統合 |
| `services/parse/parsers/output_parser.py` | IncludesRelationParser キャッシュ対応 |
| `services/parse/parsers/json_property_parser.py` | JsonPropertyParser キャッシュ対応 |
| `services/export/connectors/obsidian/__init__.py` | version_diff/elset可視化追加 |
| `tests/test_parser_units.py` | 11件のテスト追加 + 既存テスト修正 |

---

## TODO（次回への引き継ぎ）

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] ABQData永続化キャッシュの自動クリーンアップ（古いキャッシュの削除ポリシー）
- [ ] Elset品質統計のCSVエクスポート対応
- [ ] ObsidianでElsetと材料の関係グラフ（Dataview/Obsidian Canvas対応）

---

## 設計上の懸念

- ABQDataのpickleキャッシュはPythonバージョン間での互換性が保証されない。バージョンアップ時はキャッシュクリアが必要。
- Elset品質統計は全要素の品質を一括計算後にフィルタする方式のため、elset数が極めて多い場合のメモリ消費に注意。
- 軽量パーサーのキャッシュはインメモリのみ（`_parser_cache`）。プロセス間では共有されない。
