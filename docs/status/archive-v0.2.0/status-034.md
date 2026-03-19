[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-034 — パフォーマンス最適化Phase3: 並列プリフェッチ・lightweight対応・plotly統合

**日付**: 2026-02-19
**マイルストーン**: M2
**ブランチ**: claude/execute-status-todos-pK7Ih

---

## 概要

status-033のTODO4件を実行。AbaqusMeshParserの並列ファイルプリフェッチ、
AbaqusDiffParserのlightweightモード対応、ヒストグラムビン数の動的調整、
Streamlitプロットのplotly統合を実装。

---

## 実施内容

### 1. パーサー内のファイル処理並列化

**ファイル**: `services/parse/connectors/abaqus/mesh_parser.py`

- `AbaqusMeshParser.apply()`を3フェーズ構成にリファクタリング:
  - Phase 1: ノード分類（キャッシュヒット vs 要parse）
  - Phase 1.5: キャッシュヒットノードへの即時適用
  - Phase 2: `_prefetch_inp_parallel()`で複数.inpを`ThreadPoolExecutor`で並列パース
  - Phase 3: メッシュ統計を順次抽出・適用
- `_prefetch_inp_parallel()` staticmethod追加:
  - 同一パスの重複parseを自動回避（dict一意化）
  - インメモリキャッシュ済みファイルのスキップ
  - read_inp()結果をインメモリキャッシュにプリフェッチ

### 2. lightweightモードをAbaqusDiffParserで活用

**ファイル**: `services/parse/connectors/abaqus/diff_parser.py`

- `_get_or_parse_inp()`にlightweightパラメータを追加:
  - フルデータキャッシュがあればlightweight要求でもフルデータを返す
  - lightweightキャッシュキーの分離（`{path}::lightweight`形式）
  - ディスクキャッシュはフルパースのみ（lightweight結果は保存しない）
- `apply()`ではフルモードを維持（diff_abq_blocksがメッシュサマリーを比較するため）
- **設計判断**: diff_abq_blocksはnode_count等のメッシュ要約を比較に使うため、
  DiffParser自身のapply()ではlightweightを使わず、_get_or_parse_inpのAPI拡張のみ
  実施。将来のキーワード専用パーサーでのlightweight活用基盤として機能する。

### 3. CPU時間のヒストグラムビン数の動的調整

**ファイル**: `services/dashboard/data_provider.py`

- `_compute_histogram_bins()` ヘルパー関数追加:
  - Sturges則（ceil(log2(n) + 1)）をベース
  - n<=5: bin=n, n>5: 最小10〜最大50
- `_percentile()` ヘルパー関数追加（線形補間方式）
- `get_status_summary()` 拡張:
  - cpu_stats に `nbins`, `median`, `q1`, `q3`, `std` を追加
  - warning_stats に `nbins`, `min`, `max` を追加

### 4. Streamlitプロットのインタラクティブ化（plotly統合）

**ファイル**: `services/dashboard/components/status.py`

- `_render_statistics()` をplotly.expressベースに書き換え:
  - `px.histogram()` でインタラクティブヒストグラム（ホバー、ズーム対応）
  - nbinsパラメータでdata_providerの動的ビン数を使用
  - CPU時間サマリーに中央値・標準偏差を追加表示
  - 警告サマリーに最小/最大を追加表示
- plotly未インストール時はst.bar_chartにフォールバック

---

## テスト結果

- 新規テスト: 18件追加（全通過）
  - `TestComputeHistogramBins`: 5件（ビン数計算ロジック）
  - `TestPercentile`: 4件（パーセンタイル計算）
  - `TestStatusSummaryEnhanced`: 3件（拡張統計テスト）
  - `TestMeshParserPrefetch`: 3件（並列プリフェッチ）
  - `TestDiffParserLightweight`: 3件（lightweightモード）
- 既存テスト: 1450件通過、71件スキップ（pymesh/scipy環境依存のみ）
- ruff check/format: クリーン

---

## TODO

- [ ] AbaqusDiffParser.apply()でのlightweight活用検討（diff_abq_blocksの分離: メタデータ差分 vs メッシュ差分）
- [ ] 並列プリフェッチのワーカー数チューニング（CPU数ベースの最適値検証）
- [ ] plotlyグラフのテーマ統一（ライトテーマ設定との整合）
- [ ] ヒストグラムのビン幅表示（各ビンの範囲をホバーテキストで表示）

---

## 確認事項・懸念

- diff_abq_blocks()はメッシュサマリー（node_count等）を比較対象に含むため、DiffParserでlightweightを使うとメッシュ差分が「差分なし」になる。設計上のトレードオフとして、apply()ではフルモードを維持した。
- 並列プリフェッチはGIL影響を受けるが、read_inp()のI/O待ち部分で効果が出る想定。CPU-bound部分の並列化にはProcessPoolExecutorへの変更が必要。
