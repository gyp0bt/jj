[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-053: 中期計画v0.3統合・Phase A基盤整理開始

- **日付**: 2026-03-07
- **マイルストーン**: v0.3.0 Phase A（T1, T4, T6-1）
- **ブランチ**: `claude/integrate-midterm-plan-j9Zm2`

---

## 概要

中期計画v0.3（midterm-plan-v0.3.md）をroadmapとstatus-indexに統合し、Phase A（基盤整理）のタスクを実施:

1. **roadmap・status-index統合**: v0.3.0ワークトラック（T1-T8）をroadmap.mdに追加、status-indexにv0.3.0進捗表追加
2. **T4: Deprecation Warning調査**: 問題なし。全APIがモダン版を使用（st.rerun, plotly express, st_aggrid 1.0+）
3. **GalleryDefaults二重構造解消**: DashboardConfigからlegacy fields（gallery_columns/rows/max_image_bytes）を削除し、GalleryDefaultsに一本化
4. **T1 #3: active判定config化**: ハードコード`parent_dir=="old"`を削除、path-property-map経由に統一
5. **T1 #4: DEFAULT_EXTENSIONS定義**: default-config.yamlにdefault-extensionsセクション追加（T2完了後にConfigLoader経由取得に移行）
6. **T6-1: Re-parseボタン**: ダッシュボードサイドバーにRe-parseボタンを追加

## 変更内容

### 1. ドキュメント統合

| ファイル | 変更 |
|---------|------|
| `docs/roadmap.md` | v0.3.0セクション追加（T1-T8ワークトラック概要・依存関係・進捗表・実施ロードマップ）、v0.2.0をアーカイブセクション化 |
| `docs/status/status-index.md` | v0.3.0ワークトラック進捗表追加、v0.2.0マイルストーン状態を最終更新 |
| `README.md` | ドキュメント表のroadmapリンクを更新 |

### 2. GalleryDefaults二重構造解消

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | DashboardConfigから`gallery_columns`, `gallery_rows`, `gallery_max_image_bytes`削除。パースロジックをGalleryDefaultsに統合（YAML後方互換維持） |
| `services/dashboard/components/gallery.py` | `_get_gallery_settings()`をシンプル化、`gallery_max_image_bytes`直接参照削除 |
| `services/dashboard/html_export.py` | `gallery_columns`→`gallery_defaults.columns`参照に変更 |
| `tests/test_dashboard.py` | legacy field参照を`gallery_defaults`経由に更新 |

### 3. T1 #3: active判定config化

| ファイル | 変更 |
|---------|------|
| `services/graph/__init__.py` | `parent_dir == "old"`ハードコード削除、`active: "true"`をデフォルトとしpath-property-mapで上書き |
| `tests/test_graph_feature.py` | TestActiveAttributeフィクスチャにpath-property-map追加 |
| `tests/test_parser_pipeline.py` | configフィクスチャにpath-property-map追加 |

### 4. T1 #4: DEFAULT_EXTENSIONS定義

| ファイル | 変更 |
|---------|------|
| `shared/assets/default-config.yaml` | `default-extensions`セクション追加（20拡張子） |
| `services/parse/file_parse.py` | TODOコメントをT2連動メモに更新 |

### 5. T6-1: Re-parseボタン

| ファイル | 変更 |
|---------|------|
| `services/dashboard/app.py` | サイドバーに「Re-parse」ボタン追加。GraphService.parse_and_save()呼び出し |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 214 files already formatted
- **pytest**: 1602 passed, 97 skipped

## v0.3.0 ワークトラック進捗

| トラック | 状態 | 今回の進捗 |
|---------|------|-----------|
| **T1: コードベースTODO解消** | 進行中 | #3（active判定）, #4（DEFAULT_EXTENSIONS定義）完了 |
| **T2: Config二層分離** | 未着手 | — |
| **T3: M6 Phase 5 MLダッシュボード** | 未着手 | — |
| **T4: Deprecation Warning修正** | 完了 | 問題なし。全APIモダン版使用確認 |
| **T5: リモートジョブ実行基盤** | 未着手 | — |
| **T6: ダッシュボード高度化** | 進行中 | T6-1（Re-parseボタン）完了 |
| **T7: Ollama AI連携** | 未着手 | — |
| **T8: 汎用データ管理** | 未着手 | — |

## TODO

- [ ] T1 #1: ソートロジックの関数化（table.py:77 → query.pyへ抽出）
- [ ] T1 #2: list[str]パースのconfig対応+関数化（T2と連動）
- [ ] T1 #5: Abaqus parameter式評価（仕様確認後実装）
- [ ] T1 #6: Abaqus収束情報の収集
- [ ] T1 #13: GalleryDefaults二重構造 → **完了**
- [ ] T2: Config二層分離（Phase A最重要基盤、次のセッションで着手推奨）
- [ ] T6-2: AgGridフィルタ共有
- [ ] T6-3: グラフ可視化美化
- [ ] T6-4: GalleryDefaults二重構造解消 → **完了**
- [ ] status-052 TODO: Run DAG可視化, Run比較HTMLエクスポート, Runフィルタ保存 → T6と連動

## 確認事項・懸念

- T1 #4 のDEFAULT_EXTENSIONS完全移行はT2（Config二層分離）に依存。現時点ではdefault-config.yamlに定義追加のみ。ConfigLoader側の読み取りはT2で実装
- T4は問題なしだが、`st.components.v1.html`（自動リフレッシュ用JS注入）は将来のStreamlitバージョンで非推奨になる可能性あり
- Re-parseボタンはGraphServiceを直接instantiateしている。大規模プロジェクトではparse時間が長くなる可能性あり（progressbar検討）
- T2（Config二層分離）が次のセッションの最優先タスク。多くのTODOがT2に依存している

## 開発運用メモ

- **効果的**: midterm-plan-v0.3.mdの事前策定により、roadmap統合がスムーズだった。依存関係が明確で作業順序を迷わない
- **改善点**: configのpath-property-mapに依存するテストが散在しており、ハードコード削除時にテスト修正が必要。共通configフィクスチャの標準化が望ましい
