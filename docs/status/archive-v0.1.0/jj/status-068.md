[READMEへ戻る](../../README.md)

# status-068: Streamlitダッシュボード・REST API実装（Phase 2.5 D2/D3）

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

Phase 2.5のD2（Streamlitダッシュボード）とD3（REST API）を実装。`jj dashboard`でStreamlitアプリを起動し、テーブル/カード/プロット/ステータスの4ビューでグラフデータを可視化できる。`jj serve`でFastAPI REST APIサーバーを起動し、外部ツール（jjrv等）からのデータ取得を可能にする。

---

## 実装内容

### 1. Streamlitダッシュボード (`jj dashboard`)

**概要**: DashboardDataProviderの既存APIを活用し、4つのビューを持つStreamlitアプリを実装。

| ファイル | 変更内容 |
|---|---|
| `services/dashboard/app.py` | **新規作成**: Streamlitアプリ本体（4ページ構成） |

**ページ構成**:
- **テーブルビュー**: go_ファイル一覧をDataFrame表示。タイプ/ステータス/activeフィルタ対応
- **カードビュー**: 選択ノードの詳細（プロパティ/リレーション）をカード形式で表示
- **プロットビュー**: plotly.expressによる散布図/棒グラフ/線図。X/Y軸・色分けを動的選択
- **ステータスモニター**: 完了/失敗/不明の集計メトリクスと詳細一覧

**起動コマンド**:
```bash
jj dashboard                    # デフォルト起動（port 8501）
jj dashboard --port 9000        # ポート指定
jj dashboard --no-browser       # ブラウザを開かない
```

**データフロー**:
```
graph.yaml → GraphService.load() → DashboardDataProvider → Streamlitビュー
```

### 2. REST API (`jj serve`)

**概要**: FastAPIベースのREST APIサーバー。OpenAPIドキュメント自動生成付き。

| ファイル | 変更内容 |
|---|---|
| `services/api/__init__.py` | **新規作成**: モジュール公開（create_app） |
| `services/api/routes.py` | **新規作成**: 全エンドポイント定義 |

**エンドポイント一覧**:

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/graph` | グラフ全体（nodes + relations） |
| GET | `/api/v1/nodes` | ノード一覧（type/active/name/limit/offsetフィルタ） |
| GET | `/api/v1/nodes/{id}` | ノード詳細（カード情報） |
| GET | `/api/v1/nodes/{id}/related` | 関連ノード（labelフィルタ） |
| GET | `/api/v1/relations` | リレーション一覧（label/limit/offsetフィルタ） |
| GET | `/api/v1/properties/keys` | プロパティキー一覧 |
| GET | `/api/v1/summary` | サマリー統計 |
| GET | `/api/v1/status` | 実行ステータス |
| POST | `/api/v1/reload` | グラフ再読み込み |

**起動コマンド**:
```bash
jj serve                        # デフォルト起動（127.0.0.1:8080）
jj serve --port 9090            # ポート指定
jj serve --host 0.0.0.0         # 外部公開
```

**APIドキュメント**: `http://localhost:8080/docs` でSwagger UI自動生成

### 3. CLIコマンド追加

| ファイル | 変更内容 |
|---|---|
| `services/cli/graph.py` | `_add_dashboard_args()`、`_add_serve_args()`、`_run_dashboard()`、`_run_serve()` 追加。`add_top_level_graph_commands()`にdashboard/serve登録 |
| `services/cli/__init__.py` | `normalize_compat()`と`dispatch()`にdashboard/serveのルーティング追加 |

### 4. 依存パッケージ追加

| ファイル | 変更内容 |
|---|---|
| `requirements.txt` | streamlit>=1.30.0、plotly>=5.0.0、fastapi>=0.100.0、uvicorn>=0.25.0 追加 |

---

## テスト結果

- **721テストパス、21スキップ**（前回: 699テストパス、21スキップ）
- 新規追加テスト: **22件**
  - `TestRestApi`: 15件（全エンドポイントの動作検証、フィルタ、ページネーション、404、reload）
  - `TestStreamlitAppHelpers`: 2件（app/apiモジュールのインポート可能性）
  - `TestCliRegistration`: 5件（dashboard/serveコマンド登録、オプション解析）
- リグレッションなし

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/dashboard/app.py` | **新規作成**: Streamlitアプリ（4ビュー） |
| `services/api/__init__.py` | **新規作成**: APIモジュール公開 |
| `services/api/routes.py` | **新規作成**: FastAPIルート定義（9エンドポイント） |
| `services/cli/graph.py` | dashboard/serveコマンド追加 |
| `services/cli/__init__.py` | dashboard/serveのルーティング追加 |
| `requirements.txt` | streamlit/plotly/fastapi/uvicorn依存追加 |
| `tests/test_dashboard.py` | 22件のテスト追加 |
| `docs/status/status-068.md` | 本ステータスファイル |

---

## アーキテクチャ

### ダッシュボードアーキテクチャ

```
jj dashboard
  → subprocess: streamlit run services/dashboard/app.py
    → JJ_PROJECT_ROOT環境変数でプロジェクトパスを渡す
    → GraphService.load() でgraph.yamlを読み込み
    → DashboardDataProvider でビューデータに変換
    → Streamlitの4ページで表示
```

### REST APIアーキテクチャ

```
jj serve
  → uvicorn.run(create_app(project_root))
    → FastAPI app
      → /api/v1/* ルート
        → DashboardDataProvider / GraphService でデータ取得
        → JSONレスポンス返却
```

### CLIコマンドステータス（更新）

| コマンド | ステータス |
|---------|----------|
| jj init/parse/show/export/info/diff/credential | アクティブ |
| jj r (run) | アクティブ |
| jj g (graph) | アクティブ（互換性維持） |
| **jj dashboard** | **新規追加** |
| **jj serve** | **新規追加** |
| submit/list/check/files(f) | 凍結（Phase 3まで） |

---

## TODO / 次回引き継ぎ事項

- [ ] Phase 3: runコマンド層のジョブ型実装・リモート統合（凍結CLIの着手時期）
- [ ] Phase 3: fileコマンド層の基本実装（凍結CLIの着手時期）
- [ ] ダッシュボード: AgGridテーブル表示（streamlit-aggrid導入）
- [ ] ダッシュボード: 画像ギャラリー（has_output関係のPNG/GIF表示）
- [ ] ダッシュボード: graph.yaml変更検知による自動リフレッシュ
- [ ] REST API: POST /api/v1/parse（再パース実行）
- [ ] REST API: クエリフィルター拡張（props.RF3.gt=5等）
- [ ] jjrv統合: jj serve → jjrv fetch連携

---

## 設計上の懸念

- Streamlitアプリはsubprocessで起動するため、jj本体とは別プロセスで動作する。JJ_PROJECT_ROOT環境変数でプロジェクトパスを渡す方式。
- REST APIはファクトリパターン（create_app()）で構成。uvicornに直接appインスタンスを渡す。将来的に--reloadが必要な場合は文字列パス指定への変更が必要。
- streamlit/fastapi/uvicorn/plotlyはオプション依存としてrequirements.txtに追加。未インストール時はCLI起動時にエラーメッセージとインストールコマンドを表示する。
- CORS設定はローカル開発用にallow_origins=["*"]としている。本番環境ではホワイトリスト化が必要。
