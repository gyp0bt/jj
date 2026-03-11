[← README.md](../../README.md)

# status-074: composite_target_keys外部化・resolve_externalized伝搬

**日付**: 2026-03-11
**ブランチ**: claude/execute-status-todos-7YJMZ
**作業者**: Claude

## 概要

status-073のTODO3件を実施。`build_composite_group_key`のtarget_keysをconfigに外部化し、
`GraphService.load()`にresolve_externalizedパラメータを伝搬、ダッシュボード・CLI・APIの
全呼び出し元でフルロード（resolve_externalized=True）を有効化。

## 実施内容

### 1. composite_target_keys のconfig外部化

`build_composite_group_key()`で使用していたハードコード`{"step", "frame", "vmax", "vmin", "gallery"}`を
`GalleryDefaults.composite_target_keys`としてconfigに外部化。

**変更ファイル:**
- `config/__init__.py`: `GalleryDefaults`に`composite_target_keys: tuple[str, ...]`フィールド追加
  - デフォルト値: `("step", "frame", "vmax", "vmin", "gallery")`
  - YAML設定: `gallery-defaults.composite-target-keys` で上書き可能
- `services/dashboard/query.py`: `build_composite_group_key()`に`target_keys`引数追加
  - Noneの場合は`GalleryDefaults`のデフォルトから取得
  - TODOコメント・デッドコード削除

### 2. GraphService.load() resolve_externalized伝搬

`GraphService.load()`ラッパーメソッドに`resolve_externalized`キーワード引数を追加し、
内部の`GraphStorage.load()`に伝搬。

**変更ファイル:**
- `services/graph/__init__.py`: `load()`に`resolve_externalized: bool = False`パラメータ追加

### 3. 呼び出し元でresolve_externalized=True適用

外部化プロパティのフルロードが必要な全箇所で`resolve_externalized=True`を指定。

**変更ファイル:**
- `services/dashboard/app.py`: `_load_graph()`でフルロード有効化
- `services/service/api_service.py`: `_ensure_graph()`でフルロード有効化
- `services/service/graph_command.py`: `show()`と`load_or_parse()`でフルロード有効化

### テスト結果

- 全1875テスト合格、102スキップ（optional依存による想定内）
- ruff check / ruff format 合格

## TODO

### 仕様書→実装（status-073引き継ぎ）

**Windows連携（windows-integration.md）**
- [ ] W-1: Excel新規ファイル出力（テーブル + メイリオ書式）
- [ ] W-2: Excel配列データ出力（複数シート）
- [ ] W-3: PPTギャラリーグリッド貼り付け（Win32 COM、プレゼンテーション一覧選択）
- [ ] W-4: PPTプロット貼り付け
- [ ] W-5: ダッシュボードUI統合

**ダッシュボード改善（dashboard-improvements.md）**
- [ ] D-1: AgGridフィルタ強化（saved_viewでもAgGrid使用）
- [ ] D-2: テーブル/ギャラリーロジック関数抽出
- [ ] D-3: OverviewPage実装（テーブル上＋ギャラリー下）
- [ ] D-4: デフォルト保存ボタン + config書き戻し
- [ ] D-5: default-page config対応

**プロパティキー正規化（property-key-normalization.md）**
- [ ] K-1: `get_file_base_name()` 関数 + テスト
- [ ] K-2: MeshInheritParserプレフィックス正規化
- [ ] K-3: 既存テスト更新
- [ ] K-4: （オプション）config property-key-aliases

### ワークトラック（進行中）

- [ ] **T7**: Ollama AI連携 — Phase 7-1〜7-6完了
- [ ] **T8**: 汎用データ管理 — Phase 8-1〜8-2完了

## 懸念事項・次のAIへの引き継ぎ

- `build_composite_group_key`の`exclude_keys`引数は後方互換のため残置しているが未使用。将来的に削除可能。
- `resolve_externalized=True`の適用により、大規模プロジェクトでダッシュボード初回ロードが若干遅くなる可能性がある。パフォーマンス問題が出た場合は遅延ロード（必要なノードのみフルロード）を検討。
- 仕様書3件（Windows連携・ダッシュボード改善・プロパティキー正規化）は未着手。実装環境（Windows COM等）の制約に注意。
