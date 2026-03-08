[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-057: CI修正・status-056 TODO確認

- **日付**: 2026-03-07
- **マイルストーン**: v0.3.0 インフラ整備
- **ブランチ**: `claude/execute-status-todos-WMTsa`

---

## 概要

status-056のTODOを確認し、実行可能なものを処理:

1. **CI修正**: ワークフローのトリガーブランチが`main`になっていたが、リポジトリのデフォルトブランチは`master`。これにより全CIジョブが空のジョブリストで失敗していた。`master`に修正
2. **T6-4確認**: GalleryDefaults二重構造はstatus-053で既に解消済み。TODOから削除

## 変更内容

### 1. CI修正

| ファイル | 変更 |
|---------|------|
| `.github/workflows/ci.yml` | `branches: [main]` → `branches: [master]` (push/PR両方) |

### 2. TODO消化状況

| TODO | 状態 | 備考 |
|------|------|------|
| T6-4: GalleryDefaults二重構造の解消 | **完了済み** | status-053で解消。後方互換YAML parsingは意図的に残存 |
| T3: M6 Phase 5 MLダッシュボード | 未着手 | 大規模feature。別セッションで実施 |
| T5: リモートジョブ実行基盤 | 未着手 | 大規模feature。別セッションで実施 |
| streamlit-agraph本番テスト | 保留 | Streamlit環境がないため検証不可 |
| Abaqus Explicit .sta対応 | 保留 | サンプルファイル未入手 |
| Run DAG可視化 | 保留 | T6-3グラフビューの拡張として後日対応 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 217 files already formatted
- **pytest**: 1657 passed, 101 skipped

## v0.3.0 ワークトラック進捗

| トラック | 状態 | 今回の進捗 |
|---------|------|-----------|
| **T1: コードベースTODO解消** | **完了** | — |
| **T2: Config二層分離** | **完了** | — |
| **T3: M6 Phase 5 MLダッシュボード** | 未着手 | — |
| **T4: Deprecation Warning修正** | **完了** | — |
| **T5: リモートジョブ実行基盤** | 未着手 | — |
| **T6: ダッシュボード高度化** | **T6-4完了** | T6-4はstatus-053で解消済みを確認。T6全完了 |
| **T7: Ollama AI連携** | 未着手 | — |
| **T8: 汎用データ管理** | 未着手 | — |

## TODO

- [ ] T3: M6 Phase 5 MLダッシュボード（MLOverviewPage, 三層データフロー可視化）
- [ ] T5: リモートジョブ実行基盤（jj submit/watch/collect）
- [ ] T7: Ollama AI連携（AIProviderプロトコル, 要約, RAG, tips）
- [ ] T8: 汎用データ管理（Run中心プラットフォームへの昇華）
- [ ] streamlit-agraphの本番環境でのテスト
- [ ] Abaqus Explicit形式の.staファイル対応（サンプル入手後）
- [ ] status-052 TODO: Run DAG可視化（T6-3のグラフビューを拡張）

## 確認事項・懸念

- CIが`main`ブランチをトリガーにしていたのは初期設定時のミスと思われる。masterへのpush/PRで正しくジョブが実行されるようになる
- T6は全サブタスク（T6-1〜T6-4）が完了。status-indexの状態を「完了」に更新

## 開発運用メモ

- **効果的**: `gh api`でCI実行履歴を確認し、ジョブが0件であることからワークフロー設定の問題を特定できた
- **注意点**: `pytest`コマンド単体ではモジュールが見つからないが、`python -m pytest`では正常動作する。pip install -eの環境とpytestのPATHの不一致が原因
