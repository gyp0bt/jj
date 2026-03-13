[← README.md](../../README.md)

# status-076: Windows共有フォルダ同期 + GitLab連携 (T9)

**日付**: 2026-03-13
**ブランチ**: claude/windows-folder-sync-SOkr8
**作業者**: Claude

## 概要

Windows共有フォルダ同期機能（T9）を新規実装。UNCパス対応の共有フォルダ同期と、git push/pullベースのGitLab連携を追加。CLI・APIの両方から操作可能。

## 実施内容

### Phase 9-1: 基盤モデル・ストレージ
- `services/sync/models.py` — SyncState, SyncStatus, SyncDirection (Pydantic)
- `services/sync/storage.py` — SyncStorage (YAML永続化)
- `services/sync/backends/__init__.py` — AbstractSyncBackend (__init_subclass__自動登録)
- `services/sync/exclude.py` — IgnoreConfig再利用ラッパー
- `config/__init__.py` — SyncConfig, SharedFolderMapping, load_sync_config()追加
- テスト25件追加

### Phase 9-2: SharedFolderBackend + SyncService
- `services/sync/backends/shared_folder.py` — shutil.copy2 + UNCパス + 差分同期(mtime+size)
- `services/sync/service.py` — SyncService (push/clone/status/dry_run)
- テスト27件追加

### Phase 9-3: CLI (push/clone/sync)
- `services/cli/__init__.py` — jj push/clone/syncサブコマンド追加
- dispatch()・normalize_compat()更新

### Phase 9-4: APIエンドポイント
- `services/api/routes.py` — POST sync/push, POST sync/clone, GET sync/status, GET sync/{id}

### Phase 9-5: GitLabバックエンド
- `services/sync/backends/gitlab.py` — subprocess git push/clone, .gitignore自動生成, GITLAB_TOKEN認証
- テスト14件追加

### Phase 9-6: ドキュメント
- `docs/specs/sync-shared-folder.md` — 仕様書
- `docs/status/status-076.md` — 本ファイル

### テスト結果

- 同期関連テスト: 66件全合格
- ruff check / ruff format 合格

## 新規ファイル

```
services/sync/__init__.py
services/sync/models.py
services/sync/storage.py
services/sync/service.py
services/sync/exclude.py
services/sync/backends/__init__.py
services/sync/backends/shared_folder.py
services/sync/backends/gitlab.py
tests/test_sync_models.py
tests/test_sync_storage.py
tests/test_sync_config.py
tests/test_sync_service.py
tests/test_shared_folder_backend.py
tests/test_gitlab_backend.py
docs/specs/sync-shared-folder.md
```

## 変更ファイル

```
config/__init__.py             — SyncConfig/SharedFolderMapping/load_sync_config追加
services/cli/__init__.py       — push/clone/syncコマンド追加
services/api/routes.py         — syncエンドポイント追加
```

## TODO

### ワークトラック（進行中）
- [ ] **T7**: Ollama AI連携 — Phase 7-1〜7-6完了
- [ ] **T8**: 汎用データ管理 — Phase 8-1〜8-2完了
- [ ] **T9**: 共有フォルダ同期 — Phase 9-1〜9-6完了、Windows実環境テスト待ち

### 今後の改善候補
- [ ] Windows実環境でのUNCパス動作確認
- [ ] robocopyバックエンド追加（大量ファイル時のパフォーマンス最適化）
- [ ] GitLab API mode（git以外のアップロード方式）
- [ ] 同期履歴のダッシュボード表示

## 懸念事項・次のAIへの引き継ぎ

- UNCパス（`\\server\share`）はWindows専用。Linux/macOSではSMBマウントパス（`/mnt/share/`等）を使用。テストはtmp_pathで模擬しており、実UNCパスのテストはWindows環境が必要。
- GitLabバックエンドはsubprocessでgitコマンドを呼び出す方式。gitがインストールされていない環境ではエラーになる。
- 差分同期はmtime+sizeの比較で行っている。ハッシュ比較はパフォーマンスの理由で未採用。
- `config.yaml` のsyncセクションが未定義でもデフォルト除外パターンが適用される。
