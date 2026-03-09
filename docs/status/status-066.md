[← README.md](../../README.md)

# status-066: T5 リモートジョブ実行基盤 Phase 5-3/5-4/5-5

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-l1Idi

## 実施内容

### T5-3: `jj job submit` コマンド

CLIから直接ジョブを投入可能にした。

- `jj job submit <targets...> [--command <template>] [--host-name <host>]`
- コマンドテンプレートで`{target}`プレースホルダをサポート
- ファイル転送 → リモート実行 → State記録の一連フローを実装
- 複数ターゲットの一括投入対応（各targetに個別JobState生成）
- コマンド未指定時はファイル転送のみ（status=submitted）

### T5-4: `jj job watch` コマンド

ジョブの完了を定期監視するコマンドを実装。

- `jj job watch [job_ids...] [--interval <sec>] [--timeout <sec>] [--check-command <cmd>]`
- SSHでリモートの`.lck`ファイル消失を検知するデフォルト完了判定
- カスタム完了チェックコマンド対応（`{job_id}`プレースホルダ）
- タイムアウト対応（0で無制限、Ctrl+Cで中断可能）
- 状態変化コールバックによるリアルタイム通知

### T5-5: `jj job collect` コマンド

完了ジョブの結果ファイルを回収するコマンドを実装。

- `jj job collect [job_ids...] [--completed-only] [--output-patterns <patterns...>]`
- 指定IDまたは全完了ジョブの一括回収
- `output_patterns`による出力ファイル指定（ジョブに未設定時）
- リモートディレクトリからの自動出力ファイル検出（`_detect_output_files`）
- エラー時のgraceful処理（propertiesにcollect_errorを記録、他ジョブの回収は継続）

### テスト

11件のユニットテスト新規追加（全25件パス）:
- `TestJobServiceSubmit`: ジョブ投入、コマンドなし投入、複数ターゲット（3件）
- `TestJobServiceWatch`: 完了検知、タイムアウト、空ジョブ、コールバック（4件）
- `TestJobServiceCollect`: 完了ジョブ回収、パターン指定、エラーハンドリング、非完了スキップ（4件）

全体テスト: 1733 passed, 102 skipped（リグレッションなし）

## ファイル構成

```
services/job/service.py             # [MOD] watch/collect拡張、_check_job_completion、_detect_output_files追加
services/cli/__init__.py            # [MOD] jj job submit/watch/collect サブコマンド追加
tests/test_job_service.py           # [MOD] 11件のテスト追加（計25件）
docs/status/status-066.md           # [NEW] 本status
```

## 設計判断

### 完了検知戦略
- デフォルト: `.lck`ファイルの消失で完了判定（CAEソルバー共通パターン）
- カスタム: `--check-command`で任意の完了チェックコマンドを指定可能
- 汎用性を優先し、特定ソルバーへのハードコード依存を回避

### collectのエラーハンドリング
- 1ジョブの回収失敗が他ジョブに影響しないよう、ジョブ単位でtry/except
- エラー情報はJobState.propertiesに記録し、後から確認可能
- 回収成功したジョブのみcollectedステータスに遷移

### CLIコマンド名前空間
- 全て`jj job`名前空間に統一（凍結中の旧`jj submit`とは独立）
- submit/watch/collectの3コマンドでジョブライフサイクル全体をカバー

## TODO

### T5 残フェーズ（次セッション以降）
- [ ] T5-7: バッチ投入（複数target展開）
- [ ] T5-8: ダッシュボードJob Monitorページ
- [ ] T5-9: Prefect統合

### ワークトラック（継続）
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理
