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

## TODO

- [ ] `build_composite_group_key` の `target_keys` もconfigに外部化
  - 現在 `{"step", "frame", "vmax", "vmin", "gallery"}` がハードコード
- [ ] ダッシュボードやエクスポート等で `resolve_externalized=True` への移行（status-072引き継ぎ）
- [ ] GraphService.load() のラッパーに resolve_externalized パラメータを伝搬（status-072引き継ぎ）
- [ ] ギャラリー画像解像度向上の検討（st.image のwidthパラメータ / HTMLエクスポート時の解像度制御）
- [ ] pptx連携：ギャラリーの列数×行数指定画像をPowerPointに貼り付け機能
  - python-pptx または Windows COM連携（win32com）で実現可能
- [ ] 配列プロット・材料データのExcel書き出し（Windows COM連携 / xlwings）

## 懸念事項・次のAIへの引き継ぎ

- Streamlit APIの `use_container_width` は完全に削除済み。今後新規コードでは `width="stretch"` を使用すること。
- `build_composite_group_key` の `exclude_keys` パラメータは現在無効（target_keysホワイトリスト方式に変更済み）。
  テストもホワイトリスト方式に合わせて修正済み。
- ユーザーからの追加リクエスト:
  - ギャラリー画像の解像度向上
  - pptx連携（ギャラリー画像→PowerPoint貼り付け）
  - 配列プロット・材料データのExcel書き出し（Windows COM連携）
