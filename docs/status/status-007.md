[← README.md](../../README.md)

# status-007 — ダッシュボード表示名改善（verbose-name-format・vocab表示名）

- **日付**: 2026-02-16
- **マイルストーン**: M2
- **ブランチ**: claude/setup-coding-standards-YyPx7

---

## 実施内容

### 1. pymesh依存グループ追加

- `pyproject.toml`に`pymesh`オプション依存グループを新設（pandas, ftfy, chardet）
- `abaqus`グループは`jj[pymesh]`を参照する形に変更し、重複定義を解消

**変更ファイル**:
- `jj/pyproject.toml` — `[project.optional-dependencies]`にpymeshグループ追加、abaqusグループ修正

### 2. verbose-name-format設定・テンプレート生成機能

- `GraphConfig`に`verbose_name_format: Optional[str]`フィールドを追加
- config.yamlで`verbose-name-format`キーからフォーマット文字列を読み込み
- `GraphService._build_verbose_name()`にフォーマットテンプレート分岐を追加
- `_apply_verbose_name_format()`メソッドを新設: `str.format_map()`と`defaultdict`による安全なキー解決
- フォーマット文字列内ではvocab変換後キー・変換前キーの両方を参照可能
- 未定義キーは空文字に置換（エラーにならない）
- フォーマット未設定時は従来のアンダースコア結合方式にフォールバック

**設定例**:
```yaml
verbose-name-format: "条件{idx}(高さ{t},荷重{F})"
```

**変更ファイル**:
- `jj/config/__init__.py` — `GraphConfig`に`verbose_name_format`フィールド追加・`from_dict()`で解析
- `jj/services/graph/__init__.py` — `_build_verbose_name()`修正・`_apply_verbose_name_format()`新設
- `shared/assets/default-config.yaml` — verbose-name-formatの設定例・説明を追記

### 3. dashboardのverbose_name表示対応

- `DashboardDataProvider`に`_verbose_name_key`属性を追加（vocab翻訳後の表示名キー）
- `_get_display_name(node)`ヘルパーメソッドを新設（フォールバックチェーン: vocab翻訳キー → "verbose_name" → node.name）
- `_node_to_row()`にverbose_nameキー列を追加
- `get_plot_data()`にverbose_name列を追加
- `get_array_grid_data()`に`display_name`フィールドを追加
- 全ダッシュボードビューでverbose_name/display_nameを表示に使用:
  - カードビュー: selectbox・ヘッダーに表示名を使用
  - プロットビュー: hover_nameにverbose_name列を使用
  - 配列オーバーレイ・グリッド・個別ノード: display_nameをラベルに使用
- HTMLエクスポートの`_create_plot_figure()`に`hover_name_col`パラメータを追加

**変更ファイル**:
- `jj/services/dashboard/data_provider.py` — `_verbose_name_key`属性、`_get_display_name()`、各メソッド修正
- `jj/services/dashboard/app.py` — 全ビューでverbose_name/display_name表示対応
- `jj/services/dashboard/html_export.py` — `_create_plot_figure()`に`hover_name_col`パラメータ追加

### 4. プロットビュー属性ソート確認

- `_sort_by_vocab()`がvocab指定属性を先頭、非vocab属性をアルファベット順に後方配置する動作を確認
- 既存実装で要件を満たしており、追加変更不要

---

## テスト

新規テスト11件を追加（全件pass）:

| クラス | テスト数 | 内容 |
|--------|---------|------|
| `TestVerboseNameFormat` | 5 | フォーマット基本動作、原語キー参照、未定義キー処理、レガシーフォールバック、typeキー参照 |
| `TestDashboardDisplayName` | 5 | go_tableに表示名列、vocab変換キー使用、フォールバック動作、プロットデータ、配列グリッドデータ |
| `TestPropertyKeysVocabSort` | 1 | vocab指定属性が先頭にソートされることを確認 |

**テスト結果**: 全既存テスト+新規テスト pass（pymesh環境依存の2件failは本変更と無関係）

---

## 確認事項・TODO

- [ ] verbose-name-formatの実プロジェクトでの動作確認（Abaqusデータセット等）
- [ ] dashboardの表示名が長すぎる場合のUI truncation対応は将来的な改善候補
