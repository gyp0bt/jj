[READMEへ戻る](../../README.md)

# parseコネクター仕様書

## 1. 概要

本ドメインは、CAEソフト固有のファイル解析ロジックを`AbstractFileParser`サブクラスとして実装し、パーサーパイプラインに統合するものです。Phase Rで確立した`__init_subclass__`自動登録パターンにより、新規ソフト対応はパーサーサブクラスの追加のみで完了します。

### 目的

- ソフト固有の解析ロジックを独立したパーサーサブクラスとして分離
- `AbstractFileParser.__init_subclass__`による自動登録でコアロジック変更不要
- `priority`属性による実行順序制御

### 責務範囲

```
services/parse/connectors/
├── abaqus/
│   ├── __init__.py           # ABQData, read_inp, diff_abq_blocks等
│   ├── inp_parser.py         # AbaqusInpParser, AbaqusMaterialAssignmentParser, AbaqusElsetParser
│   ├── result_parser.py      # AbaqusResultParser, AbaqusIncludePropertyParser
│   ├── mesh_parser.py        # AbaqusMeshParser
│   ├── mesh.py               # pymesh統合メッシュユーティリティ
│   └── diff_parser.py        # AbaqusDiffParser
└── obsidian/
    ├── __init__.py            # ObsidianConnector, export_graph等
    ├── daily.py               # DailyNote解析ユーティリティ
    └── daily_parser.py        # DailyNoteParser
```

---

## 2. parseコネクターパターン

### 2.1 基本構造

各コネクターは`AbstractFileParser`のサブクラスとして実装します。

```python
from services.parse.base import AbstractFileParser
from services.graph.project_graph import ProjectGraph

class MyCAEParser(AbstractFileParser):
    priority = 60  # 実行順序（小さいほど先に実行）

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # ソフト固有の解析ロジック
        for node in graph.nodes:
            # ノードのプロパティを充実化
            # リレーションを追加
            pass
        return graph
```

### 2.2 自動登録

`AbstractFileParser.__init_subclass__`により、サブクラス定義時に自動的にパーサーレジストリに登録されます。`abstractmethod`が残っているクラス（ABC中間クラス）は登録されません。

```python
# services/parse/__init__.py でモジュールをimportするだけで自動登録
import services.parse.connectors.abaqus.inp_parser  # noqa: F401
```

### 2.3 実行順序

`parse()`関数が`priority`属性の昇順で全パーサーを適用します。

---

## 3. Abaqusコネクター

### 3.1 パーサー一覧

| priority | クラス名 | 責務 |
|----------|---------|------|
| 60 | `AbaqusInpParser` | `*MATERIAL`ブロック解析、`abaqus_material` Node生成、`defined_in`リレーション |
| 70 | `AbaqusResultParser` | `.sta/.msg/.dat`ファイル解析、`analysis_status`・エラー・警告プロパティ付与 |
| 80 | `AbaqusMeshParser` | pymeshによるメッシュ統計（ノード数・要素数・品質等） |
| 85 | `AbaqusMaterialAssignmentParser` | `*SOLID SECTION`等の材料割り当て解析、`assigned_to`リレーション |
| 86 | `AbaqusIncludePropertyParser` | includeファイルのプロパティをgo_*.inpに伝搬 |
| 90 | `AbaqusDiffParser` | バージョン間のINPファイル差分解析 |
| 98 | `AbaqusElsetParser` | elset名の`abaqus_elset` Node化、`has_elset`リレーション |

### 3.2 対応拡張子

| 拡張子 | 解析内容 |
|-------|---------|
| `.inp` | 入力ファイル（`*MATERIAL`, `*PARAMETER`, `*INCLUDE`, `*SOLID SECTION`等） |
| `.sta` | 解析ステータス（成功/失敗判定、ERROR/WARNING抽出） |
| `.msg` | メッセージファイル（ERROR/WARNING抽出） |
| `.dat` | データファイル（CPU時間、Wall Clock時間抽出） |

### 3.3 生成ノードタイプ

| type | format | 説明 |
|------|--------|------|
| `abaqus_material` | `material` | `*MATERIAL`ブロックから生成された材料定義 |
| `abaqus_elset` | `elset` | ELSET名からNode化されたElement Set |

### 3.4 生成リレーション

| label | 説明 |
|-------|------|
| `defined_in` | material → 定義元の.inpファイル |
| `assigned_to` | material → 割り当て先の.inpファイル |
| `has_elset` | go_*.inp → elsetノード |

### 3.5 プロパティ伝搬

`AbaqusIncludePropertyParser`（priority=86）は、`includes`リレーションを辿り、子ファイルのプロパティを親のgo_*.inpに伝搬します。

伝搬対象:
- メッシュ統計: `mesh_node_count`, `mesh_element_count`, `mesh_element_types`, `mesh_elset_summary`, `mesh_quality`
- 解析結果: `analysis_status`, `sta_errors`, `sta_warnings`, `msg_errors`, `msg_warnings`
- キーワード: `keywords`

---

## 4. Obsidianコネクター

### 4.1 パーサー一覧

| priority | クラス名 | 責務 |
|----------|---------|------|
| 95 | `DailyNoteParser` | dailyノートファイルの解析、`mentioned_in`リレーション |

### 4.2 解析内容

- dailyノート（`.md`）からのファイル参照の検出
- プロパティ・タグ情報の抽出
- `mentioned_in`リレーションの生成

---

## 5. 新規コネクターの追加方法

新しいCAEソフトへの対応は以下の手順で行います。

### 5.1 ディレクトリ作成

```
services/parse/connectors/
└── fluent/                    # 新規ソフト名
    ├── __init__.py
    └── cas_parser.py          # パーサーサブクラス
```

### 5.2 パーサー実装

```python
# services/parse/connectors/fluent/cas_parser.py
from services.parse.base import AbstractFileParser

class FluentCasParser(AbstractFileParser):
    priority = 60

    def apply(self, graph):
        for node in graph.nodes:
            ext = f".{node.format}" if node.format else ""
            if ext.lower() != ".cas":
                continue
            # Fluent固有の解析ロジック
        return graph
```

### 5.3 自動登録

```python
# services/parse/__init__.py に1行追加するだけ
import services.parse.connectors.fluent.cas_parser  # noqa: F401
```

---

## 6. 実装状況

- [x] Abaqusコネクター（7パーサー、全てAbstractFileParserサブクラス化）
- [x] Obsidianコネクター（1パーサー、AbstractFileParserサブクラス化）
- [x] 自動登録機構（`__init_subclass__`パターン確立）
- [x] shared/tests/test_asset1 による統合テスト（29件パス）
- [ ] Fluentコネクター（Phase 4-1）
- [ ] LS-DYNAコネクター（Phase 4-1）
- [ ] ANSYSコネクター（Phase 4-1）

---

## 7. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| パーサー層（共通） | → コネクター層 | 共通パーサーの後にコネクターパーサーが実行される |
| グラフ層 | ← コネクター層 | ProjectGraphを受け取りエンリッチして返す |
| 設定管理層 | → コネクター層 | `GraphConfig`からソフト固有設定を取得 |
| export層 | ← コネクター層 | コネクターが付与したプロパティをエクスポート |

---

## 8. 参考資料

- [パーサー層仕様書](./02-parser.md)
- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
