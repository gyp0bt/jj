[← README.md](../../README.md)

# status-065: T5 リモートジョブ実行基盤 Phase 5-1/5-2/5-6

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-l1Idi

## 実施内容

### T5-1: フォルダマッピングConfig拡張

SSHConfigに`folder_mappings`フィールドを追加し、ローカル⇔リモートのディレクトリペアを定義可能にした。

- `FolderMapping`データクラス新設（`config/__init__.py`）
- `SSHConfig.from_dict()`でYAMLの`FOLDER_MAPPINGS`リストを読み込み
- `resolve_remote_path()` / `resolve_local_path()`メソッド追加
- Windowsバックスラッシュの自動正規化
- 従来の`linux_local_basedirpath`/`remote_basedirpath`方式との互換性維持

### T5-2: JobStateモデル + ストレージ

リモートジョブのライフサイクルを管理するデータモデルとYAMLストレージを実装。

- `services/job/models.py`: `JobState` Pydanticモデル + `JobStatus` Enum
  - 状態遷移: submitted → running → completed → collected / failed
  - `mark_running()` / `mark_completed()` / `mark_collected()` / `mark_failed()` メソッド
- `services/job/storage.py`: `JobStorage` CRUD操作
  - `.j2/storage/jobs/job-{id}.yaml`に永続化
  - `list_jobs()`でステータスフィルタ対応
  - `generate_job_id()`でタイムスタンプ付きID生成

### T5-6: jj job status CLIコマンド

CLIにjob管理コマンドを追加。

- `jj job status [--filter <status>]`: 投入済みジョブの一覧表示（テーブル形式）
- `jj job show <job_id>`: ジョブ詳細表示
- `services/job/service.py`: `JobService`クラス（submit/collect/list_jobsのビジネスロジック）
  - `_resolve_remote_dir()`: folder_mappingsとbasedirpathの二段階解決
  - SSH操作は`modules/pyssh`に委譲（paramiko未インストール時はgraceful error）

### テスト

14件のユニットテスト新規追加（全パス）:
- `TestJobState`: モデル生成、状態遷移、失敗マーク、シリアライゼーション（4件）
- `TestJobStorage`: CRUD操作、フィルタ、削除（5件）
- `TestFolderMapping`: SSHConfig拡張、パス解決、Windows互換（5件）

## ファイル構成

```
config/__init__.py                  # FolderMapping + SSHConfig拡張
services/job/__init__.py            # [NEW] ジョブ管理パッケージ
services/job/models.py              # [NEW] JobState / JobStatus
services/job/storage.py             # [NEW] JobStorage YAML永続化
services/job/service.py             # [NEW] JobService ビジネスロジック
services/cli/__init__.py            # jj job status/show CLIコマンド追加
tests/test_job_service.py           # [NEW] 14件のユニットテスト
docs/status/status-065.md           # [NEW] 本status
```

## 設計判断

### folder_mappings vs 従来basedirpath
- folder_mappingsを優先し、未設定時は従来方式にフォールバック
- 後方互換を100%維持（既存の.pyssh.yamlに変更不要）
- 複数マッピング対応（例: F:/active → /usr2/work, D:/archive → /usr2/archive）

### ストレージ形式
- 1ジョブ = 1 YAMLファイル（`job-{id}.yaml`）
- 既存のGraphStorageパターンに統一
- ジョブ数が増えた場合もファイル単位で管理可能

## TODO

### T5 残フェーズ（次セッション以降）
- [ ] T5-3: `jj submit` — ファイル転送 + リモート実行 + State記録（SSH統合テスト）
- [ ] T5-4: `jj watch` — SSHストリーミング + 完了検知
- [ ] T5-5: `jj collect` — 結果ダウンロード + parse統合
- [ ] T5-7: バッチ投入（複数target展開）
- [ ] T5-8: ダッシュボードJob Monitorページ
- [ ] T5-9: Prefect統合

### ワークトラック（継続）
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理

## 確認事項

- SSH接続を伴うテスト（submit/collect/watch）はモック化またはSSH環境準備後に実施
- `jj submit`の旧CLI（凍結）は変更せず、新しい`jj job`名前空間に実装
- folder_mappingsのYAML書式は大文字キー`FOLDER_MAPPINGS`と小文字キー`folder_mappings`の両方をサポート
