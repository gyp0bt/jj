[← status-index.md](status-index.md) | [← README.md](../../../README.md)

# status-052: M7完了 — バッチ俯瞰Run統合・Run比較ダッシュボード・Neo4j Run Node対応

- **日付**: 2026-03-06
- **マイルストーン**: M7（Run中心スキーマ再設計）完了
- **ブランチ**: `claude/execute-status-todos-h9bRM`

---

## 概要

status-051のTODO4件を全て実行し、M7マイルストーンを完了:

1. **バッチ俯瞰のHTML生成にRunバッジ情報を反映**
2. **Runノードのプロパティをバッチ俯瞰の詳細ビューで展開表示**
3. **M7 Phase 5: Run比較ダッシュボード（RunQueryServiceとの統合）**
4. **M7 Phase 6: Neo4j Run Node対応**

## 変更内容

### 1. バッチ俯瞰HTML生成のRunバッジ・サマリー反映

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/batch_overview.py` | `_generate_batch_html`にrun_map構築・各ブロックへのRunバッジHTML・Runサマリー追加 |
| `services/dashboard/components/batch_overview.py` | `_generate_run_summary_html`関数を新規追加（スタティックHTML用） |

### 2. Runノードプロパティの詳細展開表示

| ファイル | 変更 |
|---------|------|
| `services/dashboard/data_provider.py` | `get_run_for_node`にhost, user, exit_code, finished_atを追加 |
| `services/dashboard/components/batch_overview.py` | `_render_run_details_expander`: Streamlit expanderでRunプロパティ一覧表示（タイプ・ステータス・コマンド・開始/終了・実行時間・終了コード・ホスト・ユーザー） |
| `services/dashboard/components/batch_overview.py` | `_render_single_block`/`_render_version_blocks`からexpander呼び出し |

### 3. M7 Phase 5: Run比較ダッシュボード

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/run_comparison.py` | 新規作成。`RunComparisonPage`/`RunComparisonViewConfig`（PageComponent自動登録パターン） |

**機能**:
- Run一覧テーブル（run_type フィルタ付き）
- 2Run比較（RunQueryService.diff_runs活用）: 入出力差分・プロパティ差分テーブル
- 比較グループ探索（find_comparable_runs）: INPUT軸/MEDIA軸
- HTML生成: Run一覧テーブルのスタティック出力

### 4. M7 Phase 6: Neo4j Run Node対応

| ファイル | 変更 |
|---------|------|
| `shared/neo4j_schema.py` | `RelType`: RUN_INPUT, RUN_OUTPUT, RUN_MEDIA追加 |
| `shared/neo4j_schema.py` | `LABEL_TO_RELTYPE`: run_input/output/mediaマッピング追加 |
| `services/export/connectors/neo4j.py` | `_build_node_properties`: categoryフィールドをNeo4jプロパティに含める |

### 5. テスト追加

| ファイル | 追加テスト数 |
|---------|-------------|
| `tests/test_dashboard.py` | 9件（HTML Run Badge 3件、Run Details 2件、Run Comparison 4件） |
| `tests/test_neo4j_connector.py` | 6件（ラベルマッピング3件、プロパティ2件、Cypher出力1件） |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 214 files already formatted
- **pytest**: 1592 passed, 97 skipped（新規15件追加）

## M7マイルストーン完了サマリー

| Phase | タスク | 状態 |
|-------|--------|------|
| 1 | コアモデル拡張（NodeCategory, RunQueryService） | 完了 |
| 2 | CAE Run発見（CaeRunDiscoverer） | 完了 |
| 3 | ML Run発見（MlTrainingRunDiscoverer） | 完了 |
| 4 | RunService統合・Parse-Run統合 | 完了 |
| 4.5 | バッチ俯瞰Run統合（バッジ・サマリー・詳細展開） | 完了 |
| 5 | Run比較ダッシュボード（RunComparisonPage） | 完了 |
| 6 | Neo4j Run Node対応（リレーション・カテゴリマッピング） | 完了 |

## TODO

- [ ] Run比較ダッシュボードの高度な機能: Run DAG可視化（networkxベースのフロー図）
- [ ] Run比較結果のHTMLエクスポート（diff_runsの差分テーブルHTML化）
- [ ] Runフィルタの保存対応（SavedViewConfigへの統合）
- [ ] GalleryDefaults二重構造の解消（status-050から据え置き）

## 確認事項・懸念

- Run比較ダッシュボードは`provider.graph`経由でRunQueryServiceを構築している。大規模グラフでの走査パフォーマンスに注意
- Neo4j categoryプロパティの追加により既存のNeo4jデータとの互換性に注意（新規プロパティ追加なので破壊的変更なし）
- M7マイルストーンは機能的に完了だが、Run DAG可視化やRun履歴管理は将来的な拡張として残す
