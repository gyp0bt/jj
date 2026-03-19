[← README.md](../../README.md)

# status-079 — T10 プラグインコア設計仕様書策定

| 項目 | 内容 |
|------|------|
| **日付** | 2026-03-14 |
| **ブランチ** | `claude/plugin-core-design-NZnTr` |
| **トラック** | T10: プラグインコア設計 |
| **フェーズ** | 設計仕様書策定 |

---

## 実施内容

### T10: プラグイン完全分離・コア共通設計

現行アーキテクチャの課題を分析し、プラグイン完全分離とCI/Dashboard/Server統一コアの設計仕様書を策定した。

#### 課題分析結果

| # | 課題 | 詳細 |
|---|------|------|
| C-1 | インターフェース間の機能格差 | CLI/Dashboard/APIで利用可能な機能が異なる |
| C-2 | サービスラッパーの重複 | GraphCommandService/ApiService/DashboardDataProviderが同一ロジックを再実装 |
| C-3 | プラグインの暗黙的登録 | `__init_subclass__` で自動登録されるが宣言的マニフェストがない |
| C-4 | ダッシュボードのStreamlit密結合 | `DashboardPageConnector.render_page()` がStreamlitに直接依存 |
| C-5 | プラグインのライフサイクル管理不在 | 初期化/終了フック、依存関係宣言がない |
| C-6 | 新インターフェース追加コスト | 新フロントエンド追加のたびにサービスラッパーが必要 |

#### 設計内容（8フェーズ）

| Phase | 内容 | 優先度 |
|-------|------|--------|
| P-1 | `PluginManifest` + `PluginManager` — 宣言的プラグイン登録 | 高 |
| P-2 | `JJApp` 統一コア — CLI/Dashboard/API共通APIオブジェクト | 高 |
| P-3 | 既存プラグインのマニフェスト対応 | 中 |
| P-4 | `EventBus` — コア⇔プラグイン疎結合通信 | 中 |
| P-5 | `CapabilityRegistry` — 拡張ポイント統合管理 | 中 |
| P-6 | CLIコマンド拡張ポイント | 低 |
| P-7 | APIルート拡張ポイント | 低 |
| P-8 | `DashboardPageConnector.get_page_data()` データ分離 | 低 |

#### 主要設計判断

1. **JJApp単一オブジェクト**: DIコンテナとして全サービスを管理。テスト時のモック注入が容易
2. **PluginManifest (frozen dataclass)**: プラグインが提供する機能を型安全に宣言
3. **EventBus (同期Pub/Sub)**: プラグイン間の疎結合通信。シングルスレッド前提
4. **漸進的移行**: 既存 `__init_subclass__` パターンを壊さず拡張。後方互換100%

#### 成果物

- [docs/specs/plugin-core-design.md](../specs/plugin-core-design.md) — 設計仕様書
- docs/specs/README.md — 仕様書一覧にT10を追加
- docs/roadmap.md — T10ワークトラック追加
- docs/status/status-index.md — T10進捗・status-079追加

---

## 未完了TODO

### T10 実装フェーズ（次セッション以降）

- [ ] P-1: `services/sdk/plugin_manifest.py` 実装 + テスト
- [ ] P-2: `services/app.py` (JJApp) 実装 + テスト
- [ ] P-3: 既存プラグイン (abaqus, obsidian, ml, office) のマニフェスト対応
- [ ] P-4: `services/sdk/event_bus.py` 実装 + テスト
- [ ] P-5: `services/sdk/capabilities.py` 実装 + テスト

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

| # | 事項 | 選択肢 | 推奨 |
|---|------|--------|------|
| Q-1 | JJApp のインスタンス化タイミング | CLI起動時 / on-demand | CLI起動時 |
| Q-2 | EventBus を async にするか | sync / async | sync |
| Q-3 | プラグインの hot-reload 対応 | する / しない | しない |
| Q-4 | 外部プラグイン（pip別パッケージ）の検証 | する / v0.4以降 | v0.4以降 |
| Q-5 | DashboardPageConnector のデータ分離タイミング | P-2で同時 / P-8で後発 | P-8で後発 |

### 開発運用メモ

- **効果的だった点**: Explore agentによる網羅的なコードベース調査で、全サービスの依存関係を正確に把握できた
- **注意点**: 設計仕様書が先行しすぎると実装時に乖離が生じる。P-1, P-2を早期に実装してフィードバックを得るべき
