[← README.md](../../README.md)

# status-073: ダッシュボードStreamlit非推奨API修正・ギャラリー改善

**日付**: 2026-03-11
**ブランチ**: claude/setup-project-docs-KtzaJ
**作業者**: Claude

## 概要

Streamlit `use_container_width` 非推奨警告の解消、ギャラリービューのハードコード外部化、
idxキーによる整数ソート機能追加、デバッグprint文の削除、`group_images_by_composite_key`のバグ修正。

## 実施内容

### 1. use_container_width → width 置換

Streamlitが `use_container_width` を非推奨化（2025-12-31以降削除予定）。
全ダッシュボードファイル（11ファイル + example plugin 1ファイル）で
`use_container_width=True` → `width="stretch"` に一括置換。

**対象ファイル（39箇所）:**
- `services/dashboard/connectors/abaqus.py` (16箇所)
- `services/dashboard/connectors/job_monitor.py` (1箇所)
- `services/dashboard/connectors/ml.py` (2箇所)
- `services/dashboard/components/run_comparison.py` (3箇所)
- `services/dashboard/components/card.py` (2箇所)
- `services/dashboard/components/status.py` (5箇所)
- `services/dashboard/components/table.py` (2箇所)
- `services/dashboard/components/gallery.py` (1箇所)
- `services/dashboard/components/plot.py` (2箇所)
- `services/dashboard/components/batch_overview.py` (2箇所)
- `services/dashboard/components/array_plot.py` (3箇所)
- `examples/jj-plugin-example/src/jj_plugin_example/dashboard.py` (1箇所)

### 2. ギャラリーgroup_keys外部化

gallery.pyの出力画像ギャラリーで、グループ表示に使用するキーが
`["result_key", "step", "frame", "vmax", "vmin"]` とハードコードされていた。
これを `GalleryDefaults.group_keys` としてconfigに外部化。

**変更ファイル:**
- `config/__init__.py`: `GalleryDefaults` に `group_keys: tuple[str, ...]` フィールド追加
  - デフォルト値: `("result_key", "step", "frame", "vmax", "vmin")`
  - YAML設定: `gallery-defaults.group-keys` で上書き可能
- `services/dashboard/components/gallery.py`: configから読み取りに変更

### 3. idxキー整数ソート

ギャラリービューで `idx` キーを持つ画像を整数に変換して昇順ソートする機能を追加。

- `_sort_by_idx()` ヘルパー関数を追加
- output画像・property画像・グループ表示の全パスで適用
- `group_images_by_composite_key()` でも同様にidxソート適用

### 4. バグ修正

- `query.py` の `group_images_by_composite_key()`: `return dict(groups)` → `return dict(groups_sorted)` に修正
  - ソート結果が返されていなかったバグ
- `query.py` / `gallery.py` のデバッグ `print()` 文を3箇所削除

### テスト結果

- 全1875テスト合格、102スキップ（optional依存による想定内）
- ruff check / ruff format 合格

### 5. 仕様書策定（3件）

新機能の仕様書を策定:
- [windows-integration.md](../specs/windows-integration.md) — PPT貼り付け（Win32 COM）・Excel書き出し（openpyxl）
- [dashboard-improvements.md](../specs/dashboard-improvements.md) — AgGridフィルタ強化・テーブル+ギャラリー統合・デフォルト保存
- [property-key-normalization.md](../specs/property-key-normalization.md) — include継承時のバージョン付きキー正規化

## TODO

### 実装（コード変更）

- [ ] `build_composite_group_key` の `target_keys` もconfigに外部化
  - 現在 `{"step", "frame", "vmax", "vmin", "gallery"}` がハードコード
- [ ] ダッシュボードやエクスポート等で `resolve_externalized=True` への移行（status-072引き継ぎ）
- [ ] GraphService.load() のラッパーに resolve_externalized パラメータを伝搬（status-072引き継ぎ）

### 仕様書→実装（フェーズ順）

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

## 懸念事項・次のAIへの引き継ぎ

- Streamlit APIの `use_container_width` は完全に削除済み。今後新規コードでは `width="stretch"` を使用すること。
- `build_composite_group_key` の `exclude_keys` パラメータは現在無効（target_keysホワイトリスト方式に変更済み）。
  テストもホワイトリスト方式に合わせて修正済み。
- Win32 COMの`ActivePresentation`はフォーカスの問題がある。プレゼンテーション一覧ドロップダウンで選択させる設計を採用。
- プロパティキー正規化は `_v{N}` / `_idx{N}` パターンのみ自動対応。その他のパターンはconfigで手動定義。
- saved_views機能はユーザーフィードバックにより方針変更 → configデフォルト保存にシフト。
