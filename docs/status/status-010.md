[← README.md](../../README.md) | [← status-index](status-index.md)

# status-010 — ダッシュボード改善: verbose_name展開・グループ結線修正・プロット変数制御・グローバルカラム設定

- **日付**: 2026-02-17
- **マイルストーン**: M2（マルチソルバー基盤）
- **ブランチ**: `claude/fix-verbose-names-plot-LM8Nf`

---

## 実施内容

### 1. verbose_name_formatの動的展開をダッシュボードに実装

**変更ファイル**: `jj/services/dashboard/data_provider.py`

これまでverbose_nameはparse時に生成された値をプロパティから読み取るだけだったが、
ダッシュボード側でも`verbose_name_format`テンプレートを動的に展開するように変更。

- `_apply_verbose_name_format(node)`: ノードプロパティからテンプレートを展開
- vocab変換前（`{t}`）・変換後（`{高さ}`）どちらのキー名でも参照可能
- 存在しないキーは空文字に置換（`defaultdict(str)`使用）

**例**: `verbose-name-format: "条件{idx}(高さ{t})"` → `"条件1(高さ20)"`

### 2. 全ビューでの表示名統一

**変更ファイル**: `jj/services/dashboard/app.py`, `data_provider.py`

| ビュー | 変更前 | 変更後 |
|--------|--------|--------|
| テーブル | `name`列がraw name | `name`列を表示名で置換 |
| ギャラリー | `go_node_name`のみ | `display_name`フィールド追加 |
| プロット | hover表示のみ | デフォルト色分け=表示名、hover=表示名 |
| カード | 変更なし | 詳細プロパティは従来通りカードのみ |

### 3. プロットビューのグループ結線バグ修正

**根本原因**: `get_plot_data()`がx/y/color以外のプロパティをDataFrameに含めていなかった。
`group_line_key`のカラムがDataFrameに存在しないため、`gl_key in df.columns`が常にFalseになっていた。

**修正**: `get_plot_data()`に`extra_keys`パラメータを追加。
プロットビュー側でグループ結線キーを`extra_keys`に指定し、データに含めるようにした。

**影響範囲**:
- `app.py`の通常プロットビュー
- `app.py`の保存済みプロットビュー
- `html_export.py`のHTMLエクスポート

### 4. プロットビュー変数候補のconfig絞り込み + 軸範囲number_input

**変更ファイル**: `data_provider.py`, `app.py`

- `get_filtered_property_keys()`: `global_columns`設定でglobパターンフィルタしたキーを返す
- プロットビューのX/Y軸候補がフィルタ済みキーのみに制限される
- 軸範囲設定: `st.number_input`による直接入力（plotly標準のスライダーより使いやすい）

### 5. export columns/unitsのグローバル設定昇格

**変更ファイル**: `app.py`, `data_provider.py`

`export.csv-columns`をグローバル設定として昇格:
- ダッシュボードのテーブル表示カラム制御
- プロットビューの変数候補フィルタ
- CSVエクスポート（従来通り）

`dashboard.table-columns`が設定されていない場合、`export.csv-columns`のglobパターンをフォールバックとして使用。

---

## テスト結果

- **全テスト**: 1075 passed, 59 skipped（pymesh/pandas/scipy依存のみ）
- **新規テスト**: 11件追加（全件通過）
  - `TestVerboseNameFormat`: 4件（フォーマット展開、原キー、欠損キー、フォールバック）
  - `TestGetFilteredPropertyKeys`: 2件（全件返却、globフィルタ）
  - `TestGetPlotDataExtraKeys`: 2件（extra_keys有無）
  - `TestDisplayNameInImages`: 3件（output/property画像、フォーマット適用）
- **lint/format**: ruff check + ruff format 通過

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `jj/services/dashboard/data_provider.py` | verbose_name_format動的展開、get_filtered_property_keys、extra_keys対応、display_name追加 |
| `jj/services/dashboard/app.py` | プロットビュー: 結線修正・変数フィルタ・number_input・デフォルト色分け、テーブル: 表示名・グローバルカラム |
| `jj/services/dashboard/html_export.py` | プロット結線修正、デフォルト色分け表示名、hover_name_col対応 |
| `jj/tests/test_dashboard.py` | 新規テスト11件追加 |
| `docs/status/status-010.md` | 本statusファイル |
| `docs/status/status-index.md` | インデックス更新 |

---

## 確認事項・TODO

- [ ] 実プロジェクトでのverbose_name_format展開動作確認
- [ ] plotly軸範囲number_inputの実機確認（None入力時の挙動）
- [ ] `export.csv-columns`と`dashboard.table-columns`が両方設定されている場合の優先順位確認
- [ ] カードビューの詳細プロパティ表示は意図通り維持されているか確認

---

## 設計上の懸念

- **verbose_name_format二重適用**: parse時とdashboard時の両方で適用する設計。parse時のverbose_nameプロパティが存在していても、verbose_name_formatが設定されていればdashboard側で動的に再計算する。これはconfigを変更してre-parseしなくても即座にdashboard表示が変わるメリットがある反面、parse結果との不整合が発生する可能性がある。
- **グローバルカラム設定**: `export.csv-columns`をダッシュボードでも使う設計は、「エクスポートで見たいカラム＝ダッシュボードで見たいカラム」という前提に基づく。将来的にダッシュボード独自のカラム設定が必要になる場合は分離を検討。
