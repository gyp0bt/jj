[← README.md](../../README.md)

# status-081 — T10 P-3/P-4/P-5 マニフェスト対応・EventBus・CapabilityRegistry

| 項目 | 内容 |
|------|------|
| **日付** | 2026-03-14 |
| **ブランチ** | `claude/execute-status-todos-9VMW5` |
| **トラック** | T10: プラグインコア設計 |
| **フェーズ** | P-3 既存プラグインマニフェスト対応, P-4 EventBus, P-5 CapabilityRegistry |

---

## 実施内容

### P-3: 既存プラグインのマニフェスト対応

abaqus, obsidian, ml, office の4プラグインの `register()` 関数を `PluginManifest` を返すように変更。

#### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/plugins/abaqus/__init__.py` | `register()` が `PluginManifest` を返すように変更。8パーサー・1ダッシュボードページを宣言 |
| `services/plugins/obsidian/__init__.py` | `register()` が `PluginManifest` を返すように変更。1パーサー・1エクスポーターを宣言 |
| `services/plugins/ml/__init__.py` | `register()` が `PluginManifest` を返すように変更。9パーサーを宣言 |
| `services/plugins/office/__init__.py` | `register()` が `PluginManifest` を返すように変更。動的に検出したパーサー・エクスポーターを宣言 |

#### 設計判断

1. **二重登録防止**: `_registered` フラグがTrueの場合は `None` を返す（PluginManager が二重登録しない）
2. **動的capability宣言**: Office プラグインのように optional 依存でコンポーネントが変わる場合、実際にロードできたもののみマニフェストに含める
3. **後方互換100%維持**: `__init_subclass__` による実際の登録メカニズムは変更なし

### P-4: EventBus 実装

仕様書（docs/specs/plugin-core-design.md §6）に基づき、Pub/Subイベントバスを実装。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/sdk/events.py` | `Event` (基底), `GraphParsed`, `GraphExported`, `PluginLoaded` (frozen dataclass) |
| `services/sdk/event_bus.py` | `EventBus` クラス — subscribe/publish/unsubscribe/clear |

#### 主要設計

- **同期実行**: シングルスレッド前提。ハンドラは順次実行
- **例外耐性**: ハンドラ内の例外は他のハンドラ実行を妨げない（ログ出力のみ）
- **型ベース分岐**: `type(event)` でハンドラを振り分け（サブクラスイベントは基底ハンドラを呼ばない）
- **unsubscribe 対応**: 仕様にはないがテスト容易性のため追加

### P-5: CapabilityRegistry 実装

仕様書（docs/specs/plugin-core-design.md §5）に基づき、拡張ポイントの統合レジストリを実装。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/sdk/capabilities.py` | `Capability` (Enum), `CapabilityEntry` (frozen dataclass), `CapabilityRegistry` |

#### Capability enum メンバー

| メンバー | 対応する拡張ポイント |
|---------|-------------------|
| `PARSER` | AbstractFileParser |
| `EXPORTER` | AbstractExporter |
| `DASHBOARD_PAGE` | DashboardPageConnector |
| `CLI_COMMAND` | CLIサブコマンド |
| `API_ROUTE` | APIルート |
| `EVENT_HANDLER` | イベントハンドラ |
| `CONFIG_SECTION` | 設定スキーマ拡張 |

#### SDK公開API更新

`services/sdk/__init__.py` に以下をエクスポート追加:
- `EventBus`, `Event`, `GraphParsed`, `GraphExported`, `PluginLoaded`
- `Capability`, `CapabilityEntry`, `CapabilityRegistry`

---

## テスト結果

| テストファイル | テスト数 | 結果 |
|-------------|---------|------|
| `tests/test_event_bus.py` | 16 | 全パス |
| `tests/test_capabilities.py` | 14 | 全パス |
| `tests/test_plugin_manifest_p3.py` | 9 | 全パス |
| 全テストスイート | 2085 | 全パス（130 skipped） |

---

## 未完了TODO

### T10 実装フェーズ（次セッション以降）

- [ ] P-6: CLIコマンド拡張ポイント（`services/sdk/cli_extension.py`）
- [ ] P-7: APIルート拡張ポイント（`services/sdk/api_extension.py`）
- [ ] P-8: `DashboardPageConnector.get_page_data()` フレームワーク非依存化
- [ ] JJApp に EventBus を統合（parse/export 完了時にイベント発行）
- [ ] JJApp に CapabilityRegistry を統合（プラグインロード時に自動登録）
- [ ] 既存CLI (cli.py) の JJApp 統合（段階的移行）

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
| Q-1 | EventBus を JJApp に統合するタイミング | P-6/P-7 実装前に統合し、parse/export 完了時にイベント発行を開始 |
| Q-2 | CapabilityRegistry を既存レジストリと統合するか | 既存レジストリ（`_parser_registry` 等）は温存し、CapabilityRegistry はメタデータ層として並行運用 |

### 開発運用メモ

- **効果的だった点**: 仕様書に設計が明確に記載されていたため、P-4/P-5 の実装が迅速だった
- **注意点**: 現時点では EventBus・CapabilityRegistry は独立モジュール。JJApp への統合（DI注入）は次フェーズで実施
