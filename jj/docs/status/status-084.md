[READMEへ戻る](../../README.md)

# status-084: services/query パッケージ実装 — props条件式フィルタ汎用化

**日付**: 2026-02-13
**担当**: Claude Code

---

## 概要

status-083のTODO「services/query パッケージの実装」を実施:

1. **services/query/ パッケージ新設** — dashboard/APIで共通利用される汎用フィルタ/ソートロジックを集約
2. **props条件式フィルタの汎用化** — API固有だった `props.KEY.OPERATOR=VALUE` フィルタを汎用層に昇格し、dict行データ・Nodeオブジェクト両対応に
3. **QueryServiceクラス新設** — API層が `services.service` 経由でフィルタ操作を行えるようにサービス層を追加
4. **API依存関係の整理** — `services/api/routes.py` のフィルタロジックを `services.service.QueryService` 経由に変更

---

## 1. services/query/ パッケージ構成

```
services/query/
├── __init__.py     # 公開API（全関数を再エクスポート）
├── filters.py      # 汎用フィルタ（type/status/active/props条件式）
└── sort.py         # ソート（vocab順、テーブルカラム選択）
```

### filters.py の関数

| 関数 | 由来 | 説明 |
|------|------|------|
| `is_truthy()` | dashboard/query.py | bool/文字列のtruthy判定 |
| `apply_filters()` | dashboard/query.py | type/status/activeフィルタ |
| `apply_saved_view_filters()` | dashboard/query.py | 保存済みビューフィルタ |
| `saved_view_filters_to_provider_filters()` | dashboard/query.py | フィルタ形式変換 |
| `parse_prop_filters()` | api/routes.py | クエリパラメータからprops条件式を抽出 |
| `apply_prop_filters()` | api/routes.py | **汎用化**: prop_getter引数で任意オブジェクトに対応 |
| `node_prop_getter()` | 新規 | Node.properties用のprop_getterヘルパー |
| `PROP_FILTER_PATTERN` | api/routes.py | props条件式の正規表現パターン |
| `OPERATORS` | api/routes.py | 比較オペレータ辞書(eq/ne/gt/ge/lt/le) |

### sort.py の関数

| 関数 | 由来 | 説明 |
|------|------|------|
| `sort_columns_by_vocab()` | dashboard/query.py | vocab順カラムソート |
| `select_table_columns()` | dashboard/query.py | configパターン基づくカラム選択 |

---

## 2. props条件式フィルタの汎用化

### 変更前（API固有）

```python
# services/api/routes.py に private 関数として実装
def _apply_prop_filters(nodes: list[Node], filters) -> list[Node]:
    prop_value = node.properties.get(prop_key)  # Node固定
```

### 変更後（汎用）

```python
# services/query/filters.py
def apply_prop_filters(
    items: list[Any],
    filters: list[tuple[str, str, float]],
    prop_getter: Callable | None = None,  # 任意オブジェクト対応
) -> list[Any]:
    # prop_getter省略時: item.get(key) → dict行データ
    # prop_getter=node_prop_getter → Node.properties.get(key)
```

### 利用例

```python
# dict行データ（ダッシュボード等）
result = apply_prop_filters(rows, [("RF3", "gt", 5.0)])

# Nodeオブジェクト（API等）
result = apply_prop_filters(nodes, filters, prop_getter=node_prop_getter)

# カスタムデータ構造
result = apply_prop_filters(items, filters, prop_getter=lambda item, key: item.data.get(key))
```

---

## 3. QueryService（サービス層）

`services/service/query_service.py` に `QueryService` クラスを新設:

| メソッド | 説明 |
|----------|------|
| `filter_nodes()` | type/active/name/props条件式を一括適用 |
| `parse_prop_filters()` | クエリパラメータからprops条件式を抽出 |
| `apply_prop_filters_to_nodes()` | ノードリストにprops条件式を適用 |

### API層の依存変更

```python
# Before: api/routes.py が直接 jj_types, graph, data_provider をインポート
from jj_types import GraphModel, Node
from services.dashboard.data_provider import DashboardDataProvider
from services.graph import GraphService

# After: services.service.QueryService 経由でフィルタ操作
from services.service import QueryService
# GraphService, DashboardDataProvider は関数内遅延インポートに変更
```

---

## 4. 後方互換性

`services/dashboard/query.py` は `services/query` からの再エクスポートにより完全な後方互換性を維持:

```python
from services.query.filters import (  # noqa: F401
    apply_filters, apply_saved_view_filters, is_truthy,
    saved_view_filters_to_provider_filters,
)
from services.query.sort import (  # noqa: F401
    select_table_columns, sort_columns_by_vocab,
)
```

dashboard固有の関数（`find_graph_path`, `get_graph_mtime`, `normalize_group_key`, `collect_group_keys`）は `services/dashboard/query.py` に保持。

---

## テスト結果

### test_query.py（新規: 55テスト）

```
46 passed, 9 skipped
```

| テストクラス | テスト数 | 内容 |
|---|---|---|
| TestIsTruthy | 6 | is_truthy のbool/文字列/None/int対応 |
| TestApplyFilters | 6 | type/status/active/複合/すべてフィルタ |
| TestApplySavedViewFilters | 4 | 保存済みビューフィルタ |
| TestSavedViewFiltersToProviderFilters | 1 | フォーマット変換 |
| TestParsePropFilters | 5 | props条件式パース（全オペレータ/不正値/空） |
| TestApplyPropFilters | 11 | **dict行データ/Nodeオブジェクト/カスタムgetter/全オペレータ** |
| TestSortColumnsByVocab | 3 | vocab順/空/vocabなしソート |
| TestSelectTableColumns | 5 | None/パターン/glob/不一致/vocab付き |
| TestQueryService | 9(skip) | filter_nodes統合テスト（numpy未インストールでskip） |
| TestBackwardCompatibility | 6 | dashboard/query.pyからの再エクスポート互換 |

### test_dashboard.py（既存テスト）

```
225 passed, 38 skipped, 27 failed
```

- **passed 225件**: 変更前比 **+3件**（TestRestApiPropFilterのインポートがfastapi不要に）
- **skipped 38件**: 変更なし
- **failed 27件**: chardet/numpy/pandas未インストール（変更前30件から3件減少）

### 合計

```
271 passed, 47 skipped, 27 failed
```

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/query/__init__.py` | **新規**: 公開API |
| `services/query/filters.py` | **新規**: 汎用フィルタ（props条件式含む） |
| `services/query/sort.py` | **新規**: vocab順ソート・カラム選択 |
| `services/service/query_service.py` | **新規**: QueryServiceクラス |
| `services/service/__init__.py` | 更新: QueryServiceエクスポート追加 |
| `services/dashboard/query.py` | 更新: services/queryからの再エクスポートに変更 |
| `services/api/routes.py` | 更新: QueryService経由に変更、privateフィルタ関数削除 |
| `tests/test_query.py` | **新規**: services/queryの単体テスト55件 |
| `tests/test_dashboard.py` | 更新: TestRestApiPropFilterのインポートをservices.queryに変更 |
| `docs/status/status-084.md` | 本ステータスファイル（新規） |

---

## アーキテクチャ変更

```
Before:
  services/dashboard/query.py  → フィルタ/ソート関数（dashboard固有）
  services/api/routes.py       → props条件式フィルタ（API固有private関数）

After:
  services/query/              → 汎用フィルタ/ソート層（jjレベル）
    ├── filters.py             ← dashboard/query.py + api/routes.py から昇格
    └── sort.py                ← dashboard/query.py から昇格
  services/service/
    └── query_service.py       → QueryService（API向けサービス層）
  services/dashboard/query.py  → services/query の再エクスポート + dashboard固有関数
  services/api/routes.py       → QueryService 経由でフィルタ操作
```

---

## TODO / 次回引き継ぎ事項

### 本status由来
- [ ] API層の完全なservices.service依存化（GraphService/DashboardDataProvider直接参照の排除）
- [ ] services/query テストのQueryService部分がnumpy未インストールでskip — 実環境で確認要

### 過去status引き継ぎ（status-083から継続）
- [ ] 実環境でCSV配列取り込みの動作確認
- [ ] 配列プロットページ: 保存済みビュー対応・フィルタ連携
- [ ] 物性一覧ページ: 物性比較機能・使用関係表示
- [ ] CSV配列: サブディレクトリ内CSV・ヘッダーなしCSV対応
- [ ] ダッシュボード: Excelダウンロード機能・UIからの動的ビュー保存
- [ ] REST API拡張（POST parse, クエリフィルター）
- [ ] プラグイン化Phase 1-3（jj-sdk定義、CacheProvider抽象化、entry_points動的発見）

---

## 設計上の懸念

- [ ] `_try_render_aggrid` / `_estimate_column_width` は widgets.py への委譲ラッパーとして残存。widgets.py自体がStreamlit依存のため、テスト移行はStreamlitモック or 統合テストが必要（status-083から継続）
- [ ] プラグイン化Phase 1（jj-sdk）との設計整合性（status-082から継続）
- [ ] API層はまだGraphService/DashboardDataProviderを直接参照している箇所がある（summary, status, parse等）。これらもservices.service経由にするかは、APIサービスクラスの設計次第
