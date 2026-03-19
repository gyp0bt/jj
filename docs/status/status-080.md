[← README.md](../../README.md)

# status-080 — T10 P-1/P-2 PluginManifest・JJApp実装

| 項目 | 内容 |
|------|------|
| **日付** | 2026-03-14 |
| **ブランチ** | `claude/execute-status-todos-YZtpS` |
| **トラック** | T10: プラグインコア設計 |
| **フェーズ** | P-1 PluginManifest + PluginManager, P-2 JJApp統一コア |

---

## 実施内容

### P-1: PluginManifest + PluginManager

設計仕様書（docs/specs/plugin-core-design.md）に基づき、宣言的プラグイン登録基盤を実装した。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/sdk/plugin_manifest.py` | `PluginManifest` (frozen dataclass) + `PluginInfo` |
| `services/sdk/plugin_manager.py` | `PluginManager` クラス — 発見・登録・ライフサイクル管理 |
| `tests/test_plugin_manifest.py` | 22テスト |

#### 主要設計判断

1. **PluginManifest (frozen dataclass)**: プラグインが提供する機能を型安全に宣言。`on_load`/`on_unload`ライフサイクルフック対応
2. **PluginManager**: 既存の `load_all_plugins()` をクラスとして再構成。`register()` の戻り値で新旧方式を自動判定
3. **後方互換100%**: 旧方式（`register()` → `None`）のプラグインは `_legacy_plugins` リストで管理。既存コードの変更不要

### P-2: JJApp統一コア

CLI / Dashboard / API の共通APIオブジェクトを実装した。

#### 新規ファイル

| ファイル | 内容 |
|---------|------|
| `services/app.py` | `JJApp` クラス — 統一コア、`ParseResult`, `ExportResult` |
| `tests/test_app.py` | 19テスト |

#### JJAppの提供API

| メソッド | 説明 |
|---------|------|
| `parse()` | パース実行 → `ParseResult` |
| `load_graph()` | 保存済みグラフのロード |
| `export()` | エクスポート → `ExportResult` |
| `query_nodes()` | ノード検索（type/name/properties フィルタ） |
| `query_relations()` | リレーション検索（label/node_id フィルタ） |
| `get_summary()` | グラフサマリー統計 |
| `get_node_by_id()` | ID指定ノード取得 |
| `get_plugins()` | ロード済みプラグイン一覧 |
| `get_available_export_formats()` | 利用可能なエクスポート形式 |

#### SDK公開API更新

`services/sdk/__init__.py` に `PluginManifest`, `PluginInfo`, `PluginManager` をエクスポート追加。

---

## テスト結果

| テストファイル | テスト数 | 結果 |
|-------------|---------|------|
| `tests/test_plugin_manifest.py` | 22 | 全パス |
| `tests/test_app.py` | 19 | 全パス |
| `tests/test_plugin_integration.py` | 9 | 全パス（既存テスト破壊なし） |

---

## 未完了TODO

### T10 実装フェーズ（次セッション以降）

- [ ] P-3: 既存プラグイン (abaqus, obsidian, ml, office) のマニフェスト対応
- [ ] P-4: `services/sdk/event_bus.py` 実装 + テスト
- [ ] P-5: `services/sdk/capabilities.py` (CapabilityRegistry) 実装 + テスト

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
| Q-1 | JJApp を既存CLI (cli.py) に統合するタイミング | P-3完了後に段階的に移行推奨 |
| Q-2 | JJApp を Dashboard に統合する方法 | DashboardDataProvider の薄いラッパーとして段階的に移行 |

### 開発運用メモ

- **効果的だった点**: 仕様書ベースの実装で設計と実装の乖離が少なかった
- **注意点**: JJApp の `export()` メソッドは現行の `AbstractExporter.__init__` 引数（`project_root`, `config`）に依存。P-3でプラグインをマニフェスト対応する際にエクスポーターのDI方式も検討が必要
