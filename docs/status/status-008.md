[← README.md](../../README.md)

# status-008 — results/サブディレクトリのメタデータ抽出パーサー

| 項目 | 内容 |
|------|------|
| 日付 | 2026-02-16 |
| マイルストーン | M2 |
| ブランチ | claude/extract-results-metadata-ILTKn |
| 作業者 | Claude |

---

## 概要

results/ディレクトリのサブディレクトリ内にある結果可視化画像（.png等）から
メタデータを抽出し、対応するgo_*.inpノードにプロパティとして割り当てる機能を実装。

## 変更内容

### 1. EnrichmentOnlyFilterの修正

- **ファイル**: `jj/services/parse/parsers/enrichment_filter.py`
- **変更**: `_is_in_info_only_directory()` のロジックを修正
  - 変更前: results/配下の全ファイルを除外
  - 変更後: results/直下のファイルのみ除外、サブディレクトリ内のファイルはノードとして残す
- results/直下のJSON（go_*_stress.json等）は引き続きinfo-onlyとして除外

### 2. ResultsMetadataParserの新規作成

- **ファイル**: `jj/services/parse/parsers/results_metadata_parser.py`
- **priority**: 34（OutputRelationParser=32, JsonPropertyParser=33の直後）
- **機能**:
  1. results/サブディレクトリ内のファイルノードを検出
  2. ディレクトリ名からメタデータ抽出（例: `step0_frame10` → step=0, frame=10）
  3. ファイル名から結果キーとパラメータ抽出（例: `go_idx1.v1_S-S33_vmax10.0_vmin5.0.png` → S-S33, vmax=10.0, vmin=5.0）
  4. ファイルノードにstep/frame/vmax/vmin等のプロパティを付与
  5. 対応するgo_*.inpノードに`results.{result_key}`キーでリスト形式のエントリを追加

### 3. データ構造

go_*.inpノードのプロパティ例:
```yaml
results.S-S33:
  - path: results/step0_frame10/go_idx1.v1_S-S33_vmax10.0_vmin5.0.png
    step: "0"
    frame: "10"
    vmax: "10.0"
    vmin: "5.0"
  - path: results/step1_frame20/go_idx1.v1_S-S33_vmax15.0_vmin3.0.png
    step: "1"
    frame: "20"
    vmax: "15.0"
    vmin: "3.0"
```

同じresult_keyでstep/frame/vmin/vmax違いがあれば別エントリとして格納。
異なるresult_key（S-S33, U-U3等）は別プロパティキーとして格納。

### 4. テスト

- **単体テスト**: 6テスト（TestResultsMetadataParser）
- **ヘルパー関数テスト**: 7テスト（TestResultsMetadataParserHelpers）
- **実データテスト**: 3テスト（TestResultsMetadataParserRealData）
- **EnrichmentOnlyFilter更新テスト**: 既存2テスト修正 + 2テスト追加
- **統合テスト**: 既存1テスト修正 + 2テスト追加
- **テストデータ**: `shared/tests/test_asset1/results/` にサブディレクトリとPNGファイル追加

### 5. テストアセット追加

```
shared/tests/test_asset1/results/
├── step0_frame10/
│   ├── go_idx1.v3_S-S33_vmax10.0_vmin5.0.png
│   └── go_idx1.v3_U-U3_vmax1.0_vmin0.5.png
└── step1_frame20/
    └── go_idx1.v3_S-S33_vmax15.0_vmin3.0.png
```

## テスト結果

- ユニットテスト: 24/24 通過（EnrichmentOnlyFilter + ResultsMetadataParser関連）
- 統合テスト: 52/52 通過（test_parser_pipeline.py）
- lint: ruff check 通過
- format: ruff format 通過

## 設計上の補足

- `_parse_result_filename()` は既知のgo_*.inp basename集合から最長一致でbasenameを特定
- result_keyは `_RESULT_KEY_PATTERN` で判定（S-S33, U-U3, PEEQ等に対応）
- パラメータ値は浮動小数点対応（`vmax10.0`のような `[A-Za-z]+\d+(\.\d+)?` パターン）
- `vmin_5.0`のように値が別トークンの場合にも対応
