[← README.md](../../README.md)

# 仕様書: Windows共有フォルダ同期 + GitLab連携 (T9)

**策定日**: 2026-03-13

---

## 概要

Windows環境間でCAEプロジェクトファイルを共有フォルダ経由で同期する機能。
結果ファイル（.odb等）が巨大なため、configベースの除外パターンで軽量ファイルのみを同期。
同等の機能をGitLab（git push/pull）向けにも提供し、REST APIからも操作可能。

## コマンド

```
jj push [--backend shared_folder|gitlab] [--destination PATH] [--exclude PATTERN...]
        [--dry-run] [--force]

jj clone <source> [--backend shared_folder|gitlab] [--dest DIR] [--exclude PATTERN...]

jj sync status [--filter STATUS]
jj sync show <sync_id>
```

## 設定 (config.yaml)

```yaml
sync:
  exclude:
    - "*.odb"
    - "*.res"
    - "*.lck"
    - "__pycache__"
    - ".j2"
    - ".git"
  shared_folder:
    folder_mappings:
      - local: "C:/projects/"
        shared: "\\\\server\\share\\projects\\"
  gitlab:
    url: "https://gitlab.example.com"
    token_env: "GITLAB_TOKEN"
    default_group: "cae-projects"
```

## アーキテクチャ

```
services/sync/
├── __init__.py
├── models.py              # SyncState, SyncStatus, SyncDirection (Pydantic)
├── storage.py             # SyncStorage (.j2/storage/sync/)
├── service.py             # SyncService
├── exclude.py             # IgnoreConfig再利用ラッパー
└── backends/
    ├── __init__.py        # AbstractSyncBackend (__init_subclass__自動登録)
    ├── shared_folder.py   # shutil.copy2 + UNCパス + 差分同期
    └── gitlab.py          # subprocess git push/clone
```

### バックエンド登録パターン

`AbstractFileParser` と同じ `__init_subclass__` 自動登録:

```python
class SharedFolderBackend(AbstractSyncBackend):
    backend_name = "shared_folder"  # これだけで自動登録
```

### 差分同期（SharedFolderBackend）

- `os.stat().st_mtime` + `st_size` でファイル変更を検出
- 変更があったファイルのみ `shutil.copy2()` でコピー
- 初回pushは全ファイルコピー、2回目以降は差分のみ

### GitLabバックエンド

- `subprocess` で `git init/add/commit/push` を実行
- 除外パターン → `.gitignore` にマーカー区間で自動反映
- 認証: 環境変数 `GITLAB_TOKEN` → URL注入（`https://oauth2:{token}@...`）

## APIエンドポイント

```
POST /api/v1/sync/push     → SyncService.push()
POST /api/v1/sync/clone    → SyncService.clone()
GET  /api/v1/sync/status   → SyncService.status()
GET  /api/v1/sync/{id}     → SyncService.get_sync()
```

## データモデル

```
SyncState:
  sync_id, direction (push/clone), status (pending/in_progress/completed/failed),
  backend, source_path, destination_path,
  started_at, completed_at,
  files_transferred, files_skipped, bytes_transferred,
  exclude_patterns, errors, properties
```

永続化: `.j2/storage/sync/sync-{id}.yaml`

## 依存パッケージ

追加依存なし（全て標準ライブラリ: shutil, os, pathlib, subprocess）
