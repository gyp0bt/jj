[← README.md](../../README.md)

# status-082 — T10 P-6/P-7/P-8 CLI拡張・API拡張・JJApp統合

| 項目 | 内容 |
|------|------|
| **日付** | 2026-03-14 |
| **ブランチ** | `claude/execute-status-todos-9OcUU` |
| **トラック** | T10: プラグインコア設計 |
| **フェーズ** | P-6 CLIコマンド拡張, P-7 APIルート拡張, P-8 get_page_data(), JJApp EventBus/CapabilityRegistry統合 |

---

## 実施内容

### P-6: CLIコマンド拡張ポイント

仕様書（docs/specs/plugin-core-design.md §7.1）に基づき、プラグインがCLIサブコマンドを宣言的に追加するための定義を実装。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/sdk/cli_extension.py` | `CLICommand` (frozen dataclass) + `collect_cli_commands()` 関数 |

#### CLICommand フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `name` | `str` | コマンド名（例: "submit"） |
| `help` | `str` | ヘルプ文字列 |
| `handler` | `Callable` | 実行関数 `(app, args) -> int` |
| `add_arguments` | `Callable \| None` | argparse引数追加関数 |
| `parent` | `str` | 親コマンド（デフォルト "root"） |
| `aliases` | `tuple[str, ...]` | コマンドエイリアス |
| `metadata` | `dict` | 追加メタデータ |

### P-7: APIルート拡張ポイント

仕様書（docs/specs/plugin-core-design.md §7.2）に基づき、プラグインがAPIルートを宣言的に追加するための定義を実装。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/sdk/api_extension.py` | `APIRoute` (frozen dataclass) + `collect_api_routes()` 関数 |

#### APIRoute フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `path` | `str` | エンドポイントパス |
| `method` | `str` | HTTPメソッド（デフォルト "GET"） |
| `handler` | `Callable \| None` | リクエストハンドラ |
| `summary` | `str` | OpenAPI summary |
| `tags` | `list[str]` | OpenAPIタグ |
| `response_model` | `type \| None` | レスポンスモデル |
| `metadata` | `dict` | 追加メタデータ |

### P-8: DashboardPageConnector.get_page_data()

仕様書（docs/specs/plugin-core-design.md §8）に基づき、フレームワーク非依存のデータ取得メソッドを追加。

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/dashboard/connectors/__init__.py` | `get_page_data()` メソッドを追加（デフォルト実装は空辞書） |

#### 設計判断

- `render_page()` (Streamlit依存) と並行して `get_page_data()` (フレームワーク非依存) を提供
- 既存サブクラスは変更不要（デフォルト実装が空辞書を返す）
- 段階的にサブクラスがオーバーライドしてデータを返すように移行

### JJApp EventBus統合

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/app.py` | `event_bus: EventBus` フィールド追加、`parse()`/`export()` 完了時にイベント発行 |

#### イベント発行タイミング

| メソッド | 発行イベント | 含まれる情報 |
|---------|-------------|-------------|
| `parse()` | `GraphParsed` | node_count, relation_count, full_mode |
| `export()` | `GraphExported` | format, output_path |

### JJApp CapabilityRegistry統合

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/app.py` | `capability_registry: CapabilityRegistry` フィールド追加、`_register_plugin_capabilities()` メソッド追加 |

#### 自動登録フロー

1. `__post_init__()` で `plugin_manager.load_all()` 実行
2. `_register_plugin_capabilities()` がマニフェストの各capability をRegistryに登録
3. 各プラグインに対して `PluginLoaded` イベントを発行

### JJApp 新メソッド

| メソッド | 説明 |
|---------|------|
| `get_cli_commands()` | プラグインのCLICommand収集 |
| `get_api_routes()` | プラグインのAPIRoute収集 |
| `get_dashboard_pages()` | ダッシュボードページ一覧 |
| `get_dashboard_page_data(page_label)` | ページデータJSON取得 |

### SDK公開API更新

`services/sdk/__init__.py` に以下をエクスポート追加:
- `CLICommand`, `collect_cli_commands`
- `APIRoute`, `collect_api_routes`

---

## テスト結果

| テストファイル | テスト数 | 結果 |
|-------------|---------|------|
| `tests/test_cli_extension.py` | 9 | 全パス |
| `tests/test_api_extension.py` | 8 | 全パス |
| `tests/test_app_integration.py` | 15 | 全パス |
| `tests/test_app.py` | 19 | 全パス（既存、変更なし） |
| 全テストスイート | 2119 | 全パス（130 skipped） |

---

## 未完了TODO

### T10 実装フェーズ（次セッション以降）

- [ ] 既存CLI (cli.py) の JJApp 段階的統合
- [ ] Abaqusプラグインに実際のCLICommand実装（submit等のマイグレーション）
- [ ] FastAPI APIアダプターの実装
- [ ] DashboardPageConnector サブクラスの get_page_data() 実装

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] W: Office連携 — Windows実環境テスト
- [ ] K-4: config property-key-aliases（オプション）
- [ ] M2: マルチソルバー検証環境確保後に本実装

---

## 確認事項・提案

### 設計上の確認事項

| # | 事項 | 推奨 |
|---|------|------|
| Q-1 | 既存CLI (cli.py) の JJApp 統合タイミング | 段階的に移行。まず新コマンドを JJApp 経由で追加し、既存コマンドは後から移行 |
| Q-2 | FastAPI APIアダプターの実装範囲 | まず graph/nodes/export の基本エンドポイントを実装し、プラグインルートは後から追加 |

### 開発運用メモ

- **効果的だった点**: P-6/P-7は仕様書に明確な設計があったため迅速に実装できた
- **注意点**: JJApp に EventBus/CapabilityRegistry を統合した結果、`__post_init__` の処理順序が重要になった。plugin_manager.load_all() → _register_plugin_capabilities() の順序を守ること
- **テスト数**: 2085 → 2119（34増加）
