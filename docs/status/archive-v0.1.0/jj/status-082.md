[READMEへ戻る](../../README.md)

# status-082: 純粋関数モジュール単体テスト追加 + 設計検討

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-081のTODOに基づき、以下を実施:

1. **query.py, html_export.py, abaqus_query.pyの単体テスト追加**（65テスト新規）
2. **app.pyの後方互換ラッパー関数の削除計画**を文書化
3. **services/query（jjレベル）昇格の設計検討**を文書化

---

## 1. 単体テスト追加

`tests/test_dashboard.py`に以下3クラスのテストを追加:

### TestQueryModule（37テスト）

| 対象関数 | テスト内容 |
|---------|-----------|
| `is_truthy` | bool/文字列/None/intの各パターン |
| `sort_columns_by_vocab` | vocab順ソート、空、vocab無し |
| `select_table_columns` | None/パターン/glob/不一致/vocab付き |
| `apply_filters` | フィルタなし/type/status/active/複合/"すべて" |
| `apply_saved_view_filters` | 空/active_true/active_false/type/カスタムキー |
| `saved_view_filters_to_provider_filters` | 形式変換 |
| `normalize_group_key` | daily形式/通常/短形式 |
| `collect_group_keys` | output/property/内部キー除外/空 |
| `find_graph_path` | yaml/json/None |
| `get_graph_mtime` | 存在/不存在 |

### TestAbaqusQueryModule（24テスト）

| 対象関数 | テスト内容 |
|---------|-----------|
| `get_material_table` | 全materialノード取得、内部キー除外、テーブルデータサマリ |
| `get_material_table_data` | 正常取得、非テーブル型、欠損キー、間違ノード型、欠損ノード |
| `get_material_table_keys` | Steel(2キー)、Aluminum(1キー)、間違ノード、欠損ノード |
| `guess_table_column_names` | config有/列数超過/config無/不明キー/列数不足 |
| `get_curve_plot_axes` | デフォルト/config指定/クランプ/単一列 |
| `parse_material_curve_columns` | dict形式/list形式/空/不正入力 |
| `get_material_usage` | uses_material関係有/関係なし |

### TestHtmlExportHelpers（8テスト、plotly依存はskip対応）

| 対象関数 | テスト内容 |
|---------|-----------|
| `_create_plot_figure` | 散布図/棒グラフ/折れ線 |
| `_add_ng_regions_to_fig` | 矩形/カーブ/空 |
| `_add_group_lines_to_fig` | 2グループ結線/単一点グループ(結線なし) |

### テスト結果

- **新規テスト: 65通過、8スキップ**（plotly未インストール環境）
- 既存テスト: 25通過、17スキップ（変更なし）
- 既存失敗: 29件（chardet未インストール + 未実装機能テスト = 本変更と無関係）

---

## 2. app.py 後方互換ラッパー関数の削除計画

### 現状

app.pyに以下の委譲ラッパー関数が残存:

| ラッパー関数 | 委譲先 | 参照元 |
|------------|--------|--------|
| `_sort_columns_by_vocab()` | `query.sort_columns_by_vocab` | app.py内部のみ |
| `_select_table_columns()` | `query.select_table_columns` | app.py内部 + テスト |
| `_is_truthy()` | `query.is_truthy` | app.py内部 + テスト |
| `_apply_shared_filters()` | `query.apply_filters`（session_state経由） | app.py内部のみ |
| `_add_ng_regions()` | `html_export._add_ng_regions_to_fig` | app.py内部のみ |
| `_add_group_lines()` | `html_export._add_group_lines_to_fig` | app.py内部のみ |
| `_normalize_group_key()` | `query.normalize_group_key` | app.py内部のみ |
| `_collect_group_keys()` | `query.collect_group_keys` | app.py内部のみ |

### 削除方針

**Phase A: テストの移行（完了）**
- query.py / abaqus_query.py / html_export.py の関数を直接テストするテストケースを追加 → **status-082で完了**
- 既存テスト中の`app._is_truthy`, `app._select_table_columns`等のインポートを`query.*`に置き換え可能な状態

**Phase B: テストインポート更新**
- `TestSelectTableColumns`: `app._select_table_columns` → `query.select_table_columns`
- `TestIsTruthy`: `app._is_truthy` → `query.is_truthy`
- `TestGraphChangeDetection`: `app._find_graph_path` → `query.find_graph_path`（※既にapp.pyからラッパー削除済みのため、テストが失敗中）
- streamlitスキップ条件を除去可能（query.pyはStreamlit非依存）

**Phase C: app.py内ラッパー削除**
- app.py内部で直接`query.*`/`html_export.*`を呼び出すように変更
- `_apply_shared_filters`のみsession_state依存があるため、query.apply_filtersへの引数展開で置換

**推奨**: Phase B → Phase C の順で、次回のステータスで実施

### 注意点
- `_find_graph_path`/`_get_graph_mtime`のラッパーはapp.pyから既に削除されているが、既存テスト（`TestGraphChangeDetection`）がapp.pyからインポートしようとしている → **Phase Bで修正必須**

---

## 3. services/query（jjレベル）昇格の設計検討

### 背景

現在、クエリ/フィルタロジックは`services/dashboard/query.py`に配置されている。しかしREST API (`services/api/routes.py`)でも同様のフィルタリングが必要で、実際にAPI側で独自にフィルタ処理を実装している。

### 現状の重複

```
services/dashboard/query.py     → apply_filters(), apply_saved_view_filters()
services/api/routes.py          → 独自のフィルタ実装（type, name, label, props.* 条件式）
services/dashboard/data_provider.py → get_go_table(filters=...) 内部フィルタ
```

### 提案: services/query/ パッケージ

```
services/
├── query/                        # NEW: jjレベルの汎用クエリ層
│   ├── __init__.py               # 公開API
│   ├── filters.py                # 汎用フィルタ（type, status, active, props条件式）
│   └── sort.py                   # ソート（vocab順、カラム選択）
├── dashboard/
│   ├── query.py                  # → services/query からインポート、dashboard固有のみ残す
│   │                             #    (find_graph_path, normalize_group_key等)
│   └── ...
├── api/
│   ├── routes.py                 # → services/query.filters を利用
│   └── ...
```

### 昇格候補の関数

| 関数 | 現配置 | 理由 |
|------|--------|------|
| `apply_filters()` | dashboard/query.py | APIでも同等の処理が必要 |
| `is_truthy()` | dashboard/query.py | GraphModel全般で使用 |
| `sort_columns_by_vocab()` | dashboard/query.py | CSVエクスポートでも使用可能 |
| `select_table_columns()` | dashboard/query.py | CSVエクスポートでも使用可能 |

### 残留候補（dashboard固有）

| 関数 | 理由 |
|------|------|
| `find_graph_path()` | ファイルシステム操作、dashboard/API共通だが graph/storage に近い |
| `normalize_group_key()` | ギャラリー表示専用 |
| `collect_group_keys()` | ギャラリー表示専用 |
| `apply_saved_view_filters()` | 保存済みビュー固有 |

### 実装ステップ

1. `services/query/__init__.py` を作成し、汎用フィルタ/ソート関数を配置
2. `services/dashboard/query.py` を `services/query` からインポートに変更（後方互換維持）
3. `services/api/routes.py` の独自フィルタを `services/query` に統合
4. テストを `tests/test_query.py` に追加

### 前提条件

- プラグイン化Phase 1の設計（jj-sdk定義）と整合させる必要がある
- REST APIのprops条件式（`props.RF3.gt=5`）はAPI固有の可能性もあるため、分離の粒度を慎重に検討

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `tests/test_dashboard.py` | テスト追加: TestQueryModule, TestAbaqusQueryModule, TestHtmlExportHelpers |
| `docs/status/status-082.md` | 本ステータスファイル（新規） |

---

## TODO / 次回引き継ぎ事項

### 本status由来
- [ ] Phase B: テストインポート更新（app.* → query.* への移行）
- [ ] Phase C: app.pyラッパー関数削除
- [ ] services/query パッケージの実装（設計検討セクション参照）
- [ ] TestGraphChangeDetection の修正（app._find_graph_path → query.find_graph_path）

### 過去status引き継ぎ
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV・ヘッダーなしCSV対応
- [ ] ダッシュボード: Excelダウンロード機能・UIからの動的ビュー保存
- [ ] REST API拡張（POST parse, クエリフィルター）
- [ ] プラグイン化Phase 1-3（jj-sdk定義、CacheProvider抽象化、entry_points動的発見）

---

## 設計上の懸念

- [ ] app.pyの既存テスト（TestGraphChangeDetection）が`app._find_graph_path`をインポートしているが、ラッパーは既に削除済み → テスト移行が必要
- [ ] services/queryの粒度: REST APIのprops条件式フィルタを汎用層に含めるかAPI固有にするか
- [ ] プラグイン化Phase 1（jj-sdk）との設計整合性
