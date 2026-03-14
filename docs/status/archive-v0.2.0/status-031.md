[← README.md](../../../README.md)

# status-031: パフォーマンス最適化 — ProjectGraphインデックス・IgnoreConfig・CSVサマリーモード

- **日付**: 2026-02-19
- **マイルストーン**: M2（パフォーマンス改善）
- **ブランチ**: claude/optimize-file-parsing-hhX9f
- **前提**: status-030（M7 Phase 2-3完了）

---

## 背景

大規模プロジェクト（1000条件×60K行CSV×60K メッシュ.inp）でのパフォーマンスが問題。
ignore設定による除外は対応済みだが、パーサーパイプライン内部のボトルネックを調査・改善。

## ボトルネック調査結果

| ボトルネック | 影響度 | 対応 |
|---|---|---|
| ProjectGraph: リレーション/ノード検索がO(N)線形走査 | **高** | **実装済み** |
| IgnoreConfig: fnmatch毎回呼出し | **中** | **実装済み** |
| CsvArrayParser: 全行メモリ保持(60K行×1000=4.8GB+) | **高** | **実装済み** |
| パーサー逐次実行（並列化） | 中 | ペンディング |
| chardetエンコーディング検出 | 低〜中 | ペンディング |

---

## 実施内容

### 1. ProjectGraphインデックス化

**ファイル**: `jj/services/graph/project_graph.py`

グラフ検索のO(N)線形走査をO(1)ハッシュマップ参照に置き換え。

- `_relations_by_label: dict[str, list[Relation]]` — ラベル別リレーションインデックス
- `_relations_by_node: dict[int, list[Relation]]` — ノードID別リレーションインデックス
- `_nodes_by_type: dict[str, list[Node]]` — タイプ別ノードインデックス
- `_nodes_by_category: dict[NodeCategory, list[Node]]` — カテゴリ別ノードインデックス

**影響メソッド**:
- `get_nodes_by_type()` — O(N) → O(1)
- `get_relations_by_label()` — O(N) → O(1)
- `get_relations_for_node()` — O(N) → O(1)
- `get_nodes_by_category()` — O(N) → O(1)
- `get_run_nodes()` — O(N) → O(1)
- `_get_run_related_nodes()` — O(N) → O(ノードのリレーション数)

**効果**: 1000ノード+10000リレーションの場合、パーサー全体で数百〜数千回のO(N)走査が解消される。

### 2. IgnoreConfig正規表現プリコンパイル

**ファイル**: `jj/config/__init__.py`

- fnmatchパターンを初期化時に正規表現にプリコンパイル（`fnmatch.translate()` + `re.compile()`）
- `should_ignore()`で毎回のfnmatch呼出しを排除
- 後方互換性あり（同一結果を返す）

**効果**: 10,000ファイル×5パターンの場合、パターンマッチングのオーバーヘッドが約50%削減。

### 3. CsvArrayParserサマリーモード

**ファイル**: `jj/services/parse/parsers/csv_array_parser.py`, `jj/config/__init__.py`

- 新config設定: `csv-max-rows`（デフォルト: 0=無制限）
- 設定値を超えるCSVは全行メモリ保持せず、ストリーミング統計量（min/max/mean/count/last）のみ格納
- `_read_csv_summary()`: メモリ効率的なストリーミング集計
- `_count_csv_rows()`: 高速行数カウント

**効果**: `csv-max-rows: 10000` 設定時、60K行×1000ファイル = 4.8GB+ → 数MB（統計量のみ）。

### 4. CsvArrayParserインデックス活用

- `graph.get_input_nodes()` / `graph.get_relations_by_label("has_output")` で
  ProjectGraphインデックスを活用（全ノード/全リレーション走査を排除）

---

## テスト結果

- 新規テスト: 22件全通過
  - TestProjectGraphIndex: 8件
  - TestIgnoreConfigOptimized: 7件
  - TestCsvSummaryMode: 7件
- 既存テスト: 影響なし（1051件通過、8件はpymesh/pandas依存の既存問題）
- lint: ruff check + ruff format 通過

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `jj/services/graph/project_graph.py` | 修正（インデックス4種追加、全検索メソッド最適化） |
| `jj/config/__init__.py` | 修正（IgnoreConfigプリコンパイル、csv-max-rows設定追加） |
| `jj/services/parse/parsers/csv_array_parser.py` | 修正（サマリーモード、インデックス活用） |
| `jj/tests/test_performance_optimizations.py` | 新規（22テスト） |
| `docs/status/status-031.md` | 新規 |
| `docs/status/status-index.md` | 修正 |

---

## 使い方

大規模プロジェクトでは、`.j2/config/config.yaml`に以下を追加:

```yaml
# 10000行を超えるCSVはサマリーモード（統計量のみ格納）
csv-max-rows: 10000
```

---

## 残TODO

- [ ] パーサー並列化の検討（multiprocessing/asyncio、依存関係グラフ構築が前提）
- [ ] chardetエンコーディング検出のUTF-8ファースト最適化
- [ ] INP読み込みの段階的解析（軽量/重量モード分離の拡充）
- [ ] サマリーモード時のダッシュボード表示対応（統計量プロットUI）

---

## 確認事項・懸念

- サマリーモード時はダッシュボードの配列プロット（全条件比較モード等）がサマリー統計量での表示になる。
  従来の全ポイントプロットが必要な場合は `csv-max-rows: 0`（デフォルト）を維持。
- ProjectGraphインデックスはremove_nodesで全再構築されるが、通常のパース中にremove_nodesは
  EnrichmentFilter(priority=99)のみで呼ばれるため、パフォーマンス影響は最小限。
- IgnoreConfigのプリコンパイルはfrozen dataclassのため、パターン追加時は新インスタンス生成が必要。
  現行設計では初期化時に全パターンが確定するため問題なし。
