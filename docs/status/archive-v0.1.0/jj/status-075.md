[READMEへ戻る](../../README.md)

# status-075: 物性カーブ列名config駆動化・トークン重複コメント追加

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

status-074のTODOに基づき、物性カーブの列名推定（`_guess_table_column_names()`）とプロットのX/Y軸分岐をハードコードからconfig.yaml駆動に変更。CSV配列パーサーのトークンマッチングに関する設計上の懸念にコメントを追加。

---

## 実装内容

### 1. DashboardConfigにmaterial-curve-columns設定を追加

config.yamlの`dashboard.material-curve-columns`セクションで物性プロパティごとの列名とプロット軸を指定可能にした。

**設定構造**:
```yaml
dashboard:
  material-curve-columns:
    plastic:
      columns: [stress, strain]
      x: 1    # X軸に使う列インデックス（strain）
      y: 0    # Y軸に使う列インデックス（stress）
    elastic:
      columns: [E, nu]
    density:
      columns: [density]
```

**簡略形式**（列名のみ）:
```yaml
  material-curve-columns:
    density: [density]
```

| 項目 | 内容 |
|------|------|
| ファイル | `config/__init__.py` |
| 変更 | `DashboardConfig`に`material_curve_columns`フィールド追加 |
| パース | dict形式（columns + x/y）とlist簡略形式の両方を受け付ける |
| デフォルト | 空dict（configにマッチしない場合はcol_0, col_1で補完） |

### 2. _guess_table_column_names() のconfig駆動化

ハードコードされていた列名マップを削除し、`material_curve_columns` configから列名を取得するように変更。configにマッチしないキーは`col_0`, `col_1`, ...で補完する。

| 項目 | 内容 |
|------|------|
| ファイル | `services/dashboard/app.py` |
| 変更前 | `column_map`辞書にハードコードされた9種類のマッピング |
| 変更後 | `material_curve_columns` configからの動的取得 |
| フォールバック | configなし/マッチなし → col_0, col_1, ... |

### 3. _get_curve_plot_axes() の新設

物性カーブプロットのX/Y軸インデックスをconfigから取得する関数を新設。configにx/yが未指定の場合はデフォルト（x=0, y=1）。

| 項目 | 内容 |
|------|------|
| ファイル | `services/dashboard/app.py` |
| 関数 | `_get_curve_plot_axes(property_key, num_cols, material_curve_columns)` |
| 変更前 | `if selected_key in ("plastic", "damage-initiation")` のハードコード分岐 |
| 変更後 | config.x / config.y からインデックスを取得 |

### 4. _render_material_page() のconfig対応

`dashboard_config`引数を追加し、物性カーブの列名推定とプロット軸の両方でconfigを使用するように変更。

### 5. default-config.yamlの拡充

dashboardセクションに`material-curve-columns`を追加。以下のデフォルト設定を含む:
- plastic: [stress, strain] x=1 y=0
- elastic: [E, nu]
- density: [density]
- specific-heat: [specific_heat]
- conductivity: [conductivity]
- expansion: [alpha]
- damage-initiation: [value, strain] x=1 y=0
- damage-evolution: [displacement]
- creep: [A, n, m]

### 6. _compute_extra_token() コメント追加

ファイル命名規約（同一トークンはファイル名中に2回出現しない）を明記するNoteコメントを追加。`list.remove()`による先頭一致削除が正しく動作する前提を文書化。

---

## テスト結果

- 新規テスト: **15件**追加
  - `TestGuessTableColumnNames`: 6件（config駆動列名取得、Noneフォールバック、列数過不足）
  - `TestGetCurvePlotAxes`: 5件（デフォルト軸、config指定、未指定、クランプ、未知キー）
  - `TestDashboardConfigMaterialCurveColumns`: 4件（デフォルト空、辞書形式、簡略形式、GraphConfig統合）
- 既存テスト: リグレッションなし
- 全テスト: 157パス、1警告（deprecation）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `DashboardConfig`に`material_curve_columns`フィールド追加、パース処理追加 |
| `shared/assets/default-config.yaml` | `material-curve-columns`セクション追加 |
| `services/dashboard/app.py` | `_guess_table_column_names()` config駆動化、`_get_curve_plot_axes()` 新設、`_render_material_page()` config対応 |
| `services/parse/parsers/csv_array_parser.py` | `_compute_extra_token()` にNoteコメント追加 |
| `tests/test_dashboard.py` | 15件テスト追加（config駆動列名、プロット軸、DashboardConfig） |
| `docs/roadmap.md` | 最新ステータスリンク更新 |
| `docs/status/status-075.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でCSV配列取り込みの動作確認（実プロジェクトのparse実行）
- [ ] 配列プロットページ: 保存済みビュー対応（saved-viewsでarray_plot型追加）
- [ ] 配列プロットページ: フィルタ連携（activeフィルタ等との統合）
- [ ] 物性一覧ページ: 物性比較機能（複数materialの同一プロパティ重ね書き）
- [ ] 物性一覧ページ: materialノードとgo_ノードの使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV（go_idx1_w5_t20/history_RF3.csv）の対応
- [ ] CSV配列: ヘッダーなしCSVへの対応（数値のみの場合のcol_N自動命名）
- [ ] status-072のTODO引き継ぎ（UIからの動的ビュー保存、Excelダウンロード等）
- [ ] ダッシュボード: Excelダウンロード機能（openpyxl利用）
- [ ] ダッシュボード: NG領域塗りつぶし（Baskinカーブ等のconfig定義対応）
- [ ] ダッシュボード: グループ結線（同一条件のデータ点を灰色点線で結線）
- [ ] REST API: POST /api/v1/parse（再パース実行）
- [ ] REST API: クエリフィルター拡張（props.RF3.gt=5等）

---

## 設計上の懸念

- `material-curve-columns` の設定はAbaqusキーワード名に依存している。他のCAEソフトの物性定義に対応する場合、キー名の命名規約を検討する必要がある。
- プロット軸のx/yインデックスはnum_colsでクランプされるが、ユーザーが意図しないインデックスを指定した場合のバリデーション警告は未実装。
