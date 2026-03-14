[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-035 — status-034 TODO実行: lightweight最適化・ワーカーチューニング・plotlyテーマ・ホバー表示

**日付**: 2026-02-19
**マイルストーン**: M2
**ブランチ**: claude/execute-status-todos-7XXco

---

## 概要

status-034のTODO4件を実行。AbaqusDiffParserへのlightweight最適化導入、
並列プリフェッチのワーカー数チューニング、plotlyグラフのテーマ統一、
ヒストグラムのホバーテキストによるビン範囲表示を実装。

---

## 実施内容

### 1. AbaqusDiffParser.apply()でのlightweight活用

**ファイル**: `services/parse/connectors/abaqus/diff_parser.py`

- `_mesh_hashes_match()` staticmethod追加:
  - `_compute_mesh_content_hash()`を両ファイルに適用
  - ハッシュが一致する場合Trueを返す（メッシュ同一判定）
- `apply()`にlightweight最適化を導入:
  - メッシュハッシュが同一のファイルペアでは `lightweight=True` でパース
  - メッシュデータ（NODE/ELEMENT等）のパースをスキップし、STEP/材料/境界条件のみ差分計算
  - diffノードに `mesh_identical` フラグを追加（メッシュ同一性の記録）
- **設計判断**: `diff_abq_blocks`自体は変更せず、パース段階で最適化する。
  メッシュが異なるペアにはフルモードを維持し、正確なメッシュ差分を保証。
- モジュールレベルの`_logger`に統一（`_get_or_parse_inp`内のローカルimport削除）

### 2. 並列プリフェッチのワーカー数チューニング

**ファイル**: `services/parse/connectors/abaqus/mesh_parser.py`

- `_compute_optimal_workers()` staticmethod追加:
  - CPU数の2倍を基本値（I/O+CPU混合処理の最適値）
  - 上限16（過剰なスレッドによるGIL競合回避）
  - ファイル数で制限（1ファイルなら1ワーカー）
  - 最小1を保証
- `_prefetch_inp_parallel()`を更新:
  - `max_workers=None`時に`_compute_optimal_workers()`で自動決定
  - デバッグログにワーカー数を出力

### 3. plotlyグラフのテーマ統一

**ファイル**: `services/dashboard/components/status.py`

- CPU時間ヒストグラム: `template="plotly_white"`を追加
- 警告件数ヒストグラム: `template="plotly_white"`を追加
- **設計判断**: Streamlitのライトテーマ（デフォルト）と整合させるため、
  plotlyのデフォルトテンプレート（青背景）から白背景テンプレートに変更。

### 4. ヒストグラムのビン幅表示

**ファイル**: `services/dashboard/components/status.py`

- CPU時間ヒストグラム: `hovertemplate`でビン範囲と件数を表示
- 警告件数ヒストグラム: 同様の`hovertemplate`を設定
- ホバー時に「範囲: X, 件数: Y」形式で表示
- `<extra></extra>`でplotlyデフォルトのtrace名を非表示化

---

## テスト結果

- 新規テスト: 7件追加（全通過）
  - `TestComputeOptimalWorkers`: 4件（ワーカー数計算ロジック）
  - `TestMeshHashesMatch`: 3件（メッシュハッシュ一致判定）
- 既存テスト: 1445件通過、71件スキップ（pymesh/scipy環境依存のみ）
- ruff check/format: クリーン

---

## TODO

- [ ] ProcessPoolExecutorへの切り替え検討（CPU-bound部分の並列化）
- [ ] plotlyテーマのダークモード自動切替（Streamlitテーマ設定連動）
- [ ] diff_abq_blocksのメッシュ差分とメタデータ差分の完全分離（将来的なlightweight拡張）

---

## 確認事項・懸念

- `_mesh_hashes_match`はファイルを2回読む（ハッシュ計算）ため、非常に大きなファイルではオーバーヘッドとなる可能性がある。ただし、ハッシュ計算はメッシュ定義行のみをストリーム処理するため、フルパースと比較して十分軽量。
- `_compute_optimal_workers`は`os.cpu_count()`がNoneを返す環境で4をフォールバック値として使用。コンテナ環境等で期待通り動作する。
