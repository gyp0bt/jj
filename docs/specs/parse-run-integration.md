[← README.md](../../README.md) | [← run-centric-schema.md](run-centric-schema.md)

# 仕様書: Parse-Run統合

> M7 Phase 4.5: parseコマンドをRunフレームワークに統合する

---

## 1. 概要

`jj parse` と `jj run` を統合し、以下を実現する:

1. **Parse as Run**: `jj parse` 実行時に parse 操作自体を Run Node（`run_type="parse"`）としてグラフに記録
2. **Run triggers Parse**: `jj run` 実行後にparseパイプラインを自動実行し、グラフを最新化
3. **統一フロー**: parse と run の結果が同一の Run Node 構造で記録される

---

## 2. 設計

### 2.1 Parse as Run

`jj parse` 実行時のフロー:

```
jj parse
  → GraphCommandService.parse()
    → GraphService.parse_and_save()    # 既存のパース処理
    → _record_parse_run()              # 新規: parse操作をRun Nodeとして記録
```

**Run Node プロパティ**:

```python
{
    "run_type": "parse",
    "run_status": "completed",
    "discovery": "runtime",
    "started_at": "<ISO8601>",
    "finished_at": "<ISO8601>",
    "duration_seconds": <float>,
    "full_mode": "<bool>",
    "node_count": <int>,
    "relation_count": <int>,
}
```

**リレーション**:
- `run_output`: 生成された graph.yaml ファイル（存在する場合）

### 2.2 Run triggers Parse

`jj run` 実行後のフロー:

```
jj run python train.py
  → RunService.execute()               # 既存のコマンド実行
  → GraphService.parse_and_save()      # 新規: parse自動実行
  → _update_graph_storage()            # 既存: Run Node記録（parse後のグラフに対して実行）
```

変更点:
- `RunService._update_graph_storage()` で既存グラフをロードする代わりに、`parse_and_save()` で最新グラフを生成
- trace_files の node は parse が作成したものを参照（重複作成を防止）

### 2.3 CLIオプション

`jj run` に `--no-parse` オプションを追加:

```bash
jj run python train.py             # 実行後にparse自動実行（デフォルト）
jj run --no-parse python train.py  # parse をスキップ（高速実行）
```

---

## 3. 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/service/graph_command.py` | `parse()` に Run Node 記録を追加 |
| `services/run/__init__.py` | `execute()` 後に parse_and_save() を呼出、`--no-parse` 対応 |
| `services/service/run_command.py` | `--no-parse` パラメータ受け渡し |
| `services/cli/__init__.py` | `--no-parse` CLI引数追加 |
| `tests/test_parse_run_integration.py` | 統合テスト |

---

## 4. 後方互換性

- 既存の `jj parse` の出力・動作に変更なし（Run Node 記録が追加されるのみ）
- 既存の `jj run` の動作に変更なし（parse 自動実行が追加されるが `--no-parse` でスキップ可能）
- 既存テストは全て通過する

---

## 5. 関連ドキュメント

- [Run中心スキーマ仕様書](run-centric-schema.md)
- [MLタスクロードマップ](ml-task-roadmap.md)
- [status-045](../status/status-045.md)
