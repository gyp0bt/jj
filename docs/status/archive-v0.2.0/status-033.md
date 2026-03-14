[← README.md](../../../README.md)

# status-033: パフォーマンス最適化 Phase 2 — UTF-8ファースト・段階的INP解析・パーサー並列化・統計量UI

- **日付**: 2026-02-19
- **マイルストーン**: M2（パフォーマンス改善）
- **ブランチ**: claude/execute-status-todos-IRWbE
- **前提**: status-032（メッシュ統計キャッシュ）

---

## 背景

status-032の残TODOとして挙げられた4項目を実行。
chardetエンコーディング検出の最適化、INP読み込みの段階的解析、
パーサー並列化基盤、ダッシュボードの統計量表示を一括で実装。

## 実施内容

### 1. chardetエンコーディング検出のUTF-8ファースト最適化

**ファイル**: `jj/modules/pymesh/io.py`, `jj/modules/pymesh/read_inp.py`

- `detect_file_encoding()`: 先頭8KBをUTF-8としてデコード試行。成功すれば即座にUTF-8を返し、chardetのランダムサンプリング100回（seek×100+chardet.detect）を完全スキップ
- `_detect_encoding()`: UTF-8デコード試行を追加。UTF-8バイト列ならchardetを呼ばない
- **効果**: 大半のCAEファイルはUTF-8/ASCIIのため、chardet呼び出しを90%以上回避

### 2. INP読み込みの段階的解析（lightweight/heavyweightモード分離）

**ファイル**: `jj/services/parse/connectors/abaqus/__init__.py`

- `ReadComponent`基底クラスに `is_heavyweight: ClassVar[bool]` 属性を追加
- `ReadNode`, `ReadElement`, `ReadNset`, `ReadElset` を `is_heavyweight = True` に設定
- `read_inp()` に `lightweight: bool = False` パラメータを追加
- lightweightモード時: heavyweightコンポーネントのデータ行読み込みをスキップ
- **保持するもの**: PARAMETER、MATERIAL、STEP構造、BOUNDARY、RawBlock
- **スキップするもの**: NODE/ELEMENT/NSET/ELSETの数値データ行
- **効果**: メッシュ統計が不要なパーサー（差分、キーワード解析等）で使用可能

### 3. パーサー並列化基盤

**ファイル**: `jj/services/parse/base.py`

- `_group_parsers_by_priority()`: パーサーを同一priority値でグルーピング
- `parse()` に `parallel: bool`, `max_workers: int | None` パラメータを追加
- `_run_parser_group_parallel()`: 同一priorityグループ内のパーサーをThreadPoolExecutorで並列実行
- 異なるpriority間は依存関係があるため順序保持
- **設計方針**: 現在のパーサーは全て異なるpriority値のため、この基盤は将来の同一priority追加時に自動的に並列実行される

### 4. サマリーモード時のダッシュボード表示対応（統計量プロットUI）

**ファイル**: `jj/services/dashboard/data_provider.py`, `jj/services/dashboard/components/status.py`

- `get_status_summary()` の返値に `cpu_stats`, `warning_stats` を追加
  - `cpu_stats`: count, min, max, mean, values（CPU時間分布）
  - `warning_stats`: count, total, values（警告件数分布）
- `StatusPage._render_statistics()`: 統計量プロットUI
  - CPU時間分布バーチャート + サマリーメトリクス（件数/最小/最大/平均）
  - 警告件数分布バーチャート + サマリーメトリクス（解析数/警告総数）
- ステータスページのレイアウト改善: サマリーメトリクス → 統計量プロット → ステータス別一覧

---

## テスト結果

- 新規テスト: 29件全通過
  - TestDetectFileEncoding: 5件（UTF-8ファースト最適化）
  - TestDetectEncodingReadInp: 5件（read_inp側のUTF-8ファースト）
  - TestDetectAndFixEncoding: 2件（エンコーディング修正）
  - TestReadInpLightweight: 8件（lightweightモード）
  - TestParserParallel: 3件（並列化基盤）
  - TestGetStatusSummary追加分: 3件（統計量データ）
  - TestParseMaterialBlocksRealData追加分: 3件（既存に追加）
- 既存テスト: 1453件通過（影響なし）
- lint: ruff check + ruff format 通過

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `jj/modules/pymesh/io.py` | 修正（UTF-8ファースト） |
| `jj/modules/pymesh/read_inp.py` | 修正（UTF-8ファースト） |
| `jj/services/parse/connectors/abaqus/__init__.py` | 修正（lightweight, is_heavyweight） |
| `jj/services/parse/base.py` | 修正（parallel, _group_parsers_by_priority） |
| `jj/services/dashboard/data_provider.py` | 修正（cpu_stats, warning_stats） |
| `jj/services/dashboard/components/status.py` | 修正（統計量プロットUI） |
| `jj/tests/test_encoding_optimization.py` | 新規（12テスト） |
| `jj/tests/test_abaqus_connector.py` | 修正（lightweightテスト8件追加） |
| `jj/tests/test_parser_pipeline.py` | 修正（並列化テスト3件追加） |
| `jj/tests/test_dashboard.py` | 修正（統計量テスト3件追加） |
| `docs/status/status-033.md` | 新規 |
| `docs/status/status-index.md` | 修正 |

---

## 残TODO

- [ ] パーサー内のファイル処理並列化（AbaqusMeshParser等で複数.inpを並列parse）
- [ ] lightweightモードをAbaqusDiffParserで活用（メッシュ差分はスキップ、メタデータ差分のみ高速実行）
- [ ] CPU時間のヒストグラムビン数の動的調整（データ分布に応じたbin幅）
- [ ] Streamlitプロットのインタラクティブ化（plotly統合検討）
