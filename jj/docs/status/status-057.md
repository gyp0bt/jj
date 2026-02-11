[READMEへ戻る](../../README.md)

# status-057: CLI→Service分離完了・FastAPIサーバー化準備 (2026-02-11)

## 概要

`services/cli/__init__.py`のビジネスロジックをサービス層に完全分離。モジュールレベルの副作用（SSH設定読み込み・SubmitServiceインスタンス生成）を遅延初期化に変更し、FastAPIサーバー化への基盤を整備。

## 変更内容

### 1. RunCommandService 新規作成

**ファイル**: `services/service/run_command.py`

- `RunCommandService` クラス: `jj r`（runコマンド）のビジネスロジック
- `RunService` のラッパーとして、コマンド引数の前処理（`--`除去、モード解決、cwdパス解決）を担当
- CLI/FastAPI等のエントリポイントから共通利用可能

### 2. SubmitService に list_jobs() 追加

**ファイル**: `services/service/submit.py`

- `JobListItem` データクラス追加（`target`, `job_name`フィールド）
- `list_jobs(targets)` メソッド追加: ジョブ一覧を構造化データとして返す
- 旧: CLI層が `get_abq_job_name()` を直接呼んで文字列結合
- 新: サービス層が構造化データを返し、CLI層は出力整形のみ

### 3. CLI __init__.py リファクタリング

**ファイル**: `services/cli/__init__.py`

**モジュールレベル副作用の除去:**
- 旧: インポート時に `load_ssh_config()` + `SubmitService()`がモジュールレベルで実行
- 新: `_get_submit_service()` ファクトリ関数による遅延初期化
- graph系/runコマンドはSSH設定不要で動作可能に

**インポート変更:**
- 削除: `from config import load_ssh_config`（モジュールレベル）
- 削除: `from services.run import RunService`（直接使用）
- 追加: `from services.service.run_command import RunCommandService`
- 追加: `from services.service.submit import JobListItem`

**各コマンドハンドラの変更:**
| ハンドラ | 変更内容 |
|---------|---------|
| `run_list()` | `_submit_service.get_abq_job_name()` → `service.list_jobs()` |
| `run_run()` | `RunService()` 直接生成 → `RunCommandService().execute()` |
| `run_check_syntax()` | `_submit_service` → `_get_submit_service()` |
| `run_files_get()` | `_submit_service` → `_get_submit_service()` |
| `run_files_put()` | `_submit_service` → `_get_submit_service()` |
| `run_submit()` | `_submit_service` → `_get_submit_service()` |
| `resolve_targets()` | `_submit_service` → `_get_submit_service()` |
| `dispatch()` | SSH不要コマンドを先に分岐、targets解決を遅延 |

### 4. services/service/__init__.py 更新

- `RunCommandService` をエクスポートに追加

### 5. requirements.txt 更新

- `paramiko>=3.0.0` 追加（SSH操作用、既にインポートされていたが記載漏れ）
- `plotly>=5.0.0` をコメント付きオプションとして追加
- インストールコマンドのヘッダーコメント追加

## アーキテクチャ（更新後）

```
main.py
  ↓
services/cli/          # CLI層: argparse解析 + 出力整形のみ
  ├── __init__.py      # submit/list/check/files/run ディスパッチ
  │                    # ※SSH設定は遅延初期化（submit系のみ）
  └── graph.py         # init/parse/show/export/info/diff/credential ディスパッチ
       ↓
services/service/      # サービス層: ビジネスロジック
  ├── __init__.py      # SubmitService, InfoService, GraphCommandService, RunCommandService
  ├── submit.py        # SubmitService（ジョブ投入・ターゲット解決・ジョブ一覧）
  ├── info.py          # InfoService（グラフ情報検索・エクスポート）
  ├── graph_command.py # GraphCommandService（グラフコマンドオーケストレーション）
  └── run_command.py   # RunCommandService（コマンド実行）← 新規
       ↓
services/graph/        # ドメイン層: グラフデータ管理
services/parse/        # パーサー層: ファイル解析・エンリッチメント
services/export/       # エクスポート層: 外部出力
services/run/          # 実行層: コマンド実行・ログ記録
services/lib/          # ユーティリティ層
```

### FastAPIサーバー化への準備状況

| 要件 | 対応状況 |
|------|---------|
| サービス層のargparse非依存 | ✅ 全サービスがプリミティブ型引数を受け取る |
| サービス層のprint非依存 | ✅ 全サービスがデータクラスを返す |
| モジュールインポート時の副作用なし | ✅ SSH設定読み込みを遅延初期化に変更 |
| サービスの独立インスタンス化 | ✅ 各サービスがコンストラクタ引数で設定可能 |
| 構造化された戻り値 | ✅ ParseResult, ShowResult, RunResult等のデータクラス |

## テスト結果

```
600 passed, 21 skipped（既存テスト全てパス、リグレッションなし）
```

## 変更ファイル一覧

| ファイル | 変更種別 | 変更内容 |
|---------|---------|---------|
| `services/service/run_command.py` | 新規作成 | RunCommandService |
| `services/service/submit.py` | 変更 | JobListItem追加、list_jobs()メソッド追加 |
| `services/cli/__init__.py` | 変更 | モジュールレベル副作用除去、遅延初期化、RunCommandService委譲 |
| `services/service/__init__.py` | 変更 | RunCommandServiceエクスポート追加 |
| `requirements.txt` | 変更 | paramiko追加、コメント整備 |

## TODO / 次のステップ

- [ ] FastAPI `jj serve` コマンドの実装（Phase 2.5 D3）
- [ ] DashboardDataProvider の実装（Phase 2.5 D1）
- [ ] パーサーキャッシュの実装（DRY: read_inp結果の共有キャッシュ）
- [ ] expand_rangesのCLI層での直接使用をservice層に移す検討
- [ ] Obsidianでversion_diff/index_groupノードの表示方針検討
