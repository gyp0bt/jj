[← status-index.md](status-index.md) | [← README.md](../../../README.md)

# status-051: 配列プロット凡例vocab変換・バッチ俯瞰Runノード統合

- **日付**: 2026-03-06
- **マイルストーン**: M2（基盤改善）/ M7（Run中心スキーマ）
- **ブランチ**: `claude/execute-status-todos-h9bRM`

---

## 概要

status-050のTODOから3件を実行:

1. **配列プロットの凡例名へのvocab変換適用**: `_render_array_single`、`render_saved_view`のsingleモード凡例名にvocab変換を追加
2. **generate_array_plot_htmlのモード別vocab対応確認・修正**: gridモードの凡例名(`y_key`)にtranslate_key適用
3. **バッチ俯瞰ページでRunノード（NodeCategory.RUN）との統合表示**: DashboardDataProviderにRun取得メソッド追加、バッチ俯瞰にRunバッジ表示

## 変更内容

### 1. 配列プロット凡例名へのvocab変換

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/array_plot.py` | `_render_array_single`のtraceのname引数を`translate_key(s["key"].split(".")[-1], v)`に変更。`render_saved_view`のsingleモードも同様にvocab変換を適用 |

**変換ロジック**:
- `s["key"]`の末尾部分（例: `RF.force` → `force`）をvocab辞書でtranslate
- vocab未指定時は従来通り生キーを使用

### 2. generate_array_plot_htmlのgridモード凡例vocab対応

| ファイル | 変更 |
|---------|------|
| `services/dashboard/html_export.py` | gridモードの個別グラフの凡例名 `y_key` → `translate_key(y_key, v)` に変更 |

### 3. バッチ俯瞰ページのRunノード統合表示

| ファイル | 変更 |
|---------|------|
| `services/dashboard/data_provider.py` | `get_run_nodes()`: Runノード一覧（入出力ID含む）を返すメソッド追加。`get_run_for_node(node_id)`: 指定ノードを出力に持つRunを逆引きするメソッド追加 |
| `services/dashboard/components/batch_overview.py` | `_build_run_map()`: 各go_ノードのRun紐付け情報を収集。`_render_run_summary()`: Runサマリー（件数・タイプ・ステータス別）表示。`_format_run_badge()`: Runタイプ別カラーバッジHTML生成。グリッド俯瞰・詳細ブロック図の各ブロックにRunバッジ表示 |

**設計**:
- `_build_run_map(provider, rows)` → `{node_id: run_info}` マッピングを構築
- `run_output`リレーション経由で逆引き（Run→出力ノード方向）
- タイプ別カラー: cae_job=青、ml_training=紫、script=黄
- バッジ表示: タイプ / ステータス / 実行時間(秒)

### 4. テスト追加

| ファイル | 変更 |
|---------|------|
| `tests/test_dashboard.py` | `TestArrayPlotLegendVocab`(3件)、`TestBatchOverviewRunIntegration`(6件) = 計9件追加 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 213 files already formatted
- **pytest**: 1587 passed, 97 skipped（新規7件pass + 2件skip含む）

## TODO

- [ ] M7 Phase 5: Run比較ダッシュボード（RunQueryServiceとの統合）
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] バッチ俯瞰のHTML生成にもRunバッジ情報を反映
- [ ] Runノードのプロパティ（command, host等）をバッチ俯瞰の詳細ビューで展開表示

## 確認事項・懸念

- `get_run_for_node`は全リレーションを走査するため、大規模グラフではインデックス化が望ましい
- Runノードが複数ある場合（再実行等）、最初に見つかったRunのみを返す仕様。将来的には全Runの履歴表示が有用
- GalleryDefaults二重構造（status-050で指摘）は今回は据え置き
