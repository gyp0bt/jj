[READMEへ戻る](../../../README.md)

# status-061: パーサーキャッシュ拡張 & タイムスタンプ差分パース

**日付**: 2026-02-11
**担当**: Claude Code

---

## 概要

パーサーキャッシュを全パーサーに展開し、タイムスタンプ差分による増分パースを実装した。
重い処理（read_inp、pymesh等）の重複実行を排除し、変更のないファイルのパースをスキップする。

---

## 実装内容

### 1. ABQDataキャッシュの全パーサー展開

| パーサー | 変更前 | 変更後 |
|---|---|---|
| AbaqusDiffParser | ✅ キャッシュ使用（status-060で実装済み） | タイムスタンプチェック追加 |
| AbaqusMeshParser | 毎回read_inp()実行 | ✅ キャッシュ使用 + タイムスタンプスキップ |
| AbaqusInpParser | 軽量パーサー（影響小） | 変更なし |
| IncludesRelationParser | テキストスキャンのみ | 変更なし（軽量のためスキップ不要） |

#### AbaqusMeshParser のキャッシュ化
- `_get_or_parse_inp()` メソッドを追加（AbaqusDiffParserと同じパターン）
- `extract_mesh_stats()` に `cached_abq_data` パラメータを追加
- `modules/pymesh/mesh/__init__.py` の `mesher()` 関数に `cached_abq_data` パラメータを追加
- AbaqusDiffParserで先にキャッシュされたABQDataをAbaqusMeshParserで再利用可能

#### キャッシュヒット効果
例: 3バージョンのINPファイル（v1, v2, v3）
- DiffParser: 3回のread_inp()（v1, v2, v3 各1回、v2はキャッシュヒット）
- MeshParser: 0回のread_inp()（全てDiffParserのキャッシュヒット）
- **合計: 4回→3回→3回（キャッシュなしの7回から57%削減）**

### 2. タイムスタンプ差分による増分パース

#### 概念
```
前回パース時のタイムスタンプ (.j2/storage/parse_timestamps.json)
    ↓ 比較
現在のファイルmtime
    ↓
変更ファイルのみを重い処理の対象にする
```

#### 実装箇所

| ファイル | 変更内容 |
|---|---|
| `services/graph/project_graph.py` | `_file_timestamps`, `_prev_timestamps` フィールド追加、`is_file_modified()`, `record_file_timestamp()`, `collect_file_timestamps()` メソッド追加 |
| `services/graph/storage/__init__.py` | `load_timestamps()`, `save_timestamps()` メソッド追加（`parse_timestamps.json`永続化） |
| `services/graph/__init__.py` | `parse_project()` でタイムスタンプのロード・比較・保存を統合 |
| `services/parse/connectors/abaqus/mesh_parser.py` | `is_file_modified()` チェック追加（未変更ファイルをスキップ） |
| `services/parse/connectors/abaqus/diff_parser.py` | `_pair_needs_diff()` メソッド追加（未変更ペアのdiff計算をスキップ） |

#### データフロー
1. `parse_project()` で前回の `parse_timestamps.json` を読み込み
2. スキャンした各ファイルの現在のmtimeを取得
3. `ProjectGraph._prev_timestamps` に前回データを設定
4. 各パーサーが `graph.is_file_modified(path)` で判定:
   - True → パース実行
   - False → スキップ
5. パース完了後に新しいタイムスタンプを保存

### 3. pymeshテスト（modules/pymesh使用）

- `mesher()` の `cached_abq_data` パラメータのテスト追加
- `extract_mesh_stats()` のキャッシュ経由テスト追加
- pymeshインポートテスト通過確認（scipy依存解決後）

---

## テスト結果

- **641テストパス、21スキップ**（前回: 628テストパス、21スキップ）
- 新規追加テスト: **13件**
  - `TestTimestampCache`: 5件（is_file_modified、record_file_timestamp）
  - `TestTimestampPersistence`: 2件（save/load_timestamps）
  - `TestMeshParserCache`: 2件（キャッシュヒット、タイムスタンプスキップ）
  - `TestDiffParserTimestamp`: 2件（未変更ペアスキップ、変更ペアdiff実行）
  - `TestPymeshWithModules`: 2件（cached_abq_data経由mesher、extract_mesh_stats）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/graph/project_graph.py` | タイムスタンプフィールド・メソッド追加 |
| `services/graph/storage/__init__.py` | タイムスタンプ永続化メソッド追加 |
| `services/graph/__init__.py` | parse_project()にタイムスタンプ統合 |
| `services/parse/connectors/abaqus/mesh_parser.py` | キャッシュ・タイムスタンプ統合 |
| `services/parse/connectors/abaqus/diff_parser.py` | タイムスタンプスキップ追加 |
| `services/parse/connectors/abaqus/mesh.py` | cached_abq_dataパラメータ追加 |
| `modules/pymesh/mesh/__init__.py` | cached_abq_dataパラメータ追加 |
| `tests/test_parser_units.py` | 13件のテスト追加 |

---

## TODO（次回への引き継ぎ）

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] 個々のElsetごとの品質統計
- [ ] config-driven include search depth
- [ ] Version diff & elset relation visualization in Obsidian
- [ ] タイムスタンプ差分パースの最適化: 軽量パーサーにも展開検討
- [ ] ABQDataの永続化キャッシュ（pickle等でディスクに保存し、再起動後も再利用可能にする）

---

## 設計上の懸念

- タイムスタンプ差分は **重いパーサー（requires_full=True）のみ** に適用。軽量パーサーはグラフ構造の決定に関わるためスキップすると不整合が生じる可能性がある。
- ABQDataキャッシュはメモリ上のみ。大量のINPファイルを持つプロジェクトではメモリ消費が増える可能性がある。将来的にはディスクキャッシュを検討。
