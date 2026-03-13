[← README.md](../../README.md)

# status-075: プロパティキー正規化・ダッシュボード改善

**日付**: 2026-03-13
**ブランチ**: claude/execute-status-todos-W5eUH
**作業者**: Claude

## 概要

status-074のTODOからプロパティキー正規化（K-1〜K-3）とダッシュボード改善（D-1〜D-5）を実施。

## 実施内容

### プロパティキー正規化 (K-1〜K-3)

#### K-1: get_file_base_name() 関数追加
- `services/query/sort.py` に `get_file_base_name()` 関数を追加
- ファイル名から末尾の `_v{N}` / `_idx{N}` を除去してベース名を返す
- `services/query/__init__.py` にエクスポート追加
- テスト7件追加（バージョン、インデックス、非バージョン、空文字等）

#### K-2: MeshInheritParser プレフィックス正規化
- `services/parse/connectors/abaqus/mesh_inherit_parser.py` 変更
- キー競合時の接頭辞を `child.name` → `get_file_base_name(child.name)` に変更
- `mesh_v2:v, mesh_v3:v` → `mesh:v`（後勝ちマージ）

#### K-3: 既存テスト更新
- `test_prefix_escaping_on_key_conflict` のアサーションを更新
- `test_versioned_includes_merge_to_base_name` テスト追加

### ダッシュボード改善 (D-1〜D-5)

#### D-1: AgGridフィルタ強化
- `TablePage.render_saved_view()` で `try_render_aggrid()` を使用するよう変更
- saved_viewでもAgGridフィルタ（数値/テキスト）が利用可能に

#### D-2: テーブル/ギャラリーロジック関数抽出
- `render_table_section()`: テーブル描画のコアロジックをモジュールレベル関数に抽出
- `render_gallery_section()`: ギャラリー描画のコアロジックをモジュールレベル関数に抽出
- TablePage/GalleryPageの `render_page()` から呼び出すよう変更

#### D-3: OverviewPage実装
- `services/dashboard/components/overview.py` 新規作成
- テーブル（上）+ ギャラリー（下）の統合レイアウト
- `app.py` にインポート追加（自動登録）

#### D-4: デフォルト保存ボタン + config書き戻し
- `services/dashboard/config_writer.py` 新規作成
  - `save_dashboard_defaults()`: dashboardセクションのみを更新
  - `collect_current_dashboard_state()`: session_stateから設定収集
  - バックアップ自動作成（`.yaml.bak`）
- `app.py` サイドバーにデフォルト保存ボタン追加

#### D-5: default-page config対応
- `DashboardConfig` に `default_page` フィールド追加
- `from_dict()` で `default-page` キーをパース
- `app.py` でデフォルトページインデックスを反映

### テスト結果

- 全1888テスト合格、102スキップ
- ruff check / ruff format 合格

## TODO

### 仕様書→実装（status-074引き継ぎ、未着手分）

**Windows連携（windows-integration.md）** — Windows環境依存のため保留
- [ ] W-1〜W-5: Excel/PPT出力（Win32 COM依存）

**プロパティキー正規化（property-key-normalization.md）**
- [ ] K-4: （オプション）config property-key-aliases 対応

### ワークトラック（進行中）

- [ ] **T7**: Ollama AI連携 — Phase 7-1〜7-6完了
- [ ] **T8**: 汎用データ管理 — Phase 8-1〜8-2完了

## 懸念事項・次のAIへの引き継ぎ

- OverviewPageはテーブル+ギャラリーの単純結合。仕様書ではプロットセクション（中段）のオプション追加も提案されているが、UIが複雑になるため初期版では省略。
- `config_writer.py` はPyYAMLを使用（ruamel.yaml未導入）。コメント保持が必要な場合はruamel.yamlの導入を検討。
- `render_gallery_section()` の `key_prefix` パラメータにより、同一ページ内で複数ギャラリーセクションを描画する際のsession_stateキー衝突を防止。
