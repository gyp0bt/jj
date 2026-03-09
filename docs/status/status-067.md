[← README.md](../../README.md)

# status-067: T5 リモートジョブ実行基盤 Phase 5-7/5-8

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-l1Idi

## 実施内容

### T5-7: バッチ投入（複数target展開）

`jj job submit`にバッチモード（`--batch`/`-b`）を追加。

- **ブレース展開**: `go_sample_{1..5}.inp` → 5ファイルに展開
- **カンマ展開**: `test_{a,b,c}.inp` → 3ファイルに展開
- **逆順範囲**: `model_{3..1}.inp` → 降順展開
- **glob展開**: `*.inp` → ローカルファイルマッチング
- **混合パターン**: 通常ファイル名とパターンの混在をサポート
- **重複除去**: 展開結果の重複を順序保持で排除
- CLI: 展開プレビュー表示（投入前にターゲット一覧を確認可能）

### T5-8: ダッシュボードJob Monitorページ

Streamlitダッシュボードに「Job Monitor」ページを追加。

- `DashboardPageConnector`サブクラスとして実装（`__init_subclass__`自動登録）
- **ステータス集計**: submitted/running/completed/collected/failed別のメトリクス表示
- **ジョブテーブル**: フィルタ付き一覧表示（dataframe）
- **ジョブ詳細**: セレクトボックスで選択→詳細情報を2カラムで表示
- **HTMLエクスポート**: `generate_html()`でHTMLテーブル出力対応
- **自動可用性判定**: `.j2/storage/jobs/`にジョブファイルが存在する場合のみ表示

### テスト

9件のユニットテスト新規追加（計34件パス）:
- `TestExpandTargets`: ブレース展開、カンマ展開、逆順、glob、混合、重複除去、バッチ投入統合（9件）

## ファイル構成

```
services/job/service.py                          # [MOD] expand_targets/\u005F expand_braces追加、submitにbatchフラグ
services/cli/__init__.py                         # [MOD] --batch/-bフラグ、展開プレビュー
services/dashboard/connectors/job_monitor.py     # [NEW] Job Monitorダッシュボードページ
services/dashboard/app.py                        # [MOD] job_monitorインポート追加
tests/test_job_service.py                        # [MOD] TestExpandTargets 9件追加
docs/status/status-067.md                        # [NEW] 本status
```

## 設計判断

### バッチ展開の設計
- `--batch`フラグによるオプトイン方式（意図しない展開を防止）
- シェルのブレース展開と同じ構文を採用（学習コスト最小化）
- `expand_targets()`を独立関数として実装（テスタビリティ確保）
- glob展開はcwd相対パスで解決

### Job Monitor配置
- `DashboardPageConnector`パターンに従い、既存アーキテクチャに自然統合
- Streamlit依存はrender_page内に局所化（import遅延）
- ジョブファイルが存在しない場合はページ自体を非表示

## TODO

### T5 残フェーズ
- [ ] T5-9: Prefect統合

### ワークトラック（継続）
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理
