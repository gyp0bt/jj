[READMEへ戻る](../../README.md)

# コアデータモデル層 仕様書

## 1. 概要

本ドメインは、jjプロジェクト全体の基盤となるグラフデータモデルとその永続化機構を定義します。全ての機能がこのデータモデルに依存するため、最優先で設計・実装を完了させる必要があります。

### 目的

- CAE業務データをグラフ構造で統一的に表現
- テキストベース（YAML/JSON）での永続化により、バージョン管理との親和性を確保
- networkxによる一時的なグラフ操作と、Pydanticによる型安全な永続化の両立

### 責務範囲

- `types/` : Pydanticモデルの定義
- `services/storage/` : グラフデータの保存・読込・抽出

---

## 2. データモデル定義

### 2.1 Node（ノード）

グラフの頂点を表現します。ファイル、実行履歴、タグなど、あらゆるエンティティをNodeとして統一的に扱います。

#### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | `int` | ○ | ノードの一意識別子。グラフ内で重複不可 |
| `type` | `str` | ○ | ノードの種別（例: `file`, `run`, `tag`, `user`） |
| `name` | `str` | ○ | ノードの名称（例: ファイル名、タグ名） |
| `format` | `str` | △ | ファイルの拡張子など、type固有の付加情報 |
| `properties` | `dict[str, Any]` | ○ | メタ情報を格納（例: `{"idx": "1", "ver": "2", "ncpu": 4}`） |

#### 実装例（Pydantic）

```python
from pydantic import BaseModel, Field
from typing import Any

class Node(BaseModel):
    id: int = Field(..., description="ノードの一意識別子")
    type: str = Field(..., description="ノードの種別")
    name: str = Field(..., description="ノードの名称")
    format: str | None = Field(None, description="フォーマット（拡張子など）")
    properties: dict[str, Any] = Field(default_factory=dict, description="メタ情報")
```

### 2.2 Relation（関係）

ノード間の関係を表現します。有向グラフを前提とし、`node1_id` から `node2_id` への関係を表します。

#### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | `int` | ○ | 関係の一意識別子 |
| `label` | `str` | ○ | 関係の種別（例: `generated`, `tagged`, `depends_on`） |
| `node1_id` | `int` | ○ | 始点ノードのID |
| `node2_id` | `int` | ○ | 終点ノードのID |

#### 実装例（Pydantic）

```python
class Relation(BaseModel):
    id: int = Field(..., description="関係の一意識別子")
    label: str = Field(..., description="関係の種別")
    node1_id: int = Field(..., description="始点ノードID")
    node2_id: int = Field(..., description="終点ノードID")
```

### 2.3 GraphModel（グラフモデル）

ノードと関係をまとめたグラフ全体を表現します。

#### フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `nodes` | `list[Node]` | ○ | ノードのリスト |
| `relations` | `list[Relation]` | ○ | 関係のリスト |

#### 実装例（Pydantic）

```python
class GraphModel(BaseModel):
    nodes: list[Node] = Field(default_factory=list, description="ノードのリスト")
    relations: list[Relation] = Field(default_factory=list, description="関係のリスト")
```

---

## 3. 永続化仕様（GraphStorage）

### 3.1 保存先

- デフォルト: `.j2/storage/graph.yaml`
- JSON形式も対応: `.j2/storage/graph.json`

### 3.2 保存形式

#### YAML例

```yaml
nodes:
  - id: 1
    type: file
    name: go_sample_v1_idx1.inp
    format: inp
    properties:
      idx: "1"
      ver: "1"
  - id: 2
    type: run
    name: run-2026-02-04-120000
    format: null
    properties:
      duration: 120.5
      user: user1
      host: server01
relations:
  - id: 1
    label: generated
    node1_id: 2
    node2_id: 1
```

### 3.3 GraphStorageインターフェース

#### メソッド一覧

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `save(graph: GraphModel, path: str)` | グラフモデル、保存先パス | None | グラフをYAML/JSONで保存 |
| `load(path: str)` | 読込パス | `GraphModel` | グラフを読み込み |
| `add_node(node: Node)` | ノード | None | ノードを追加 |
| `add_relation(relation: Relation)` | 関係 | None | 関係を追加 |
| `get_node_by_id(id: int)` | ノードID | `Node \| None` | IDでノードを取得 |
| `get_nodes_by_type(type: str)` | タイプ | `list[Node]` | タイプでノードをフィルタ |
| `get_relations_by_label(label: str)` | ラベル | `list[Relation]` | ラベルで関係をフィルタ |

#### 実装方針

- `pyyaml` を使用してYAML保存・読込
- 内部的に `networkx.DiGraph` を保持し、グラフ探索を効率化
- Pydanticモデルとnetworkxの相互変換を担当

---

## 4. 実装計画

### Phase 1: 基本モデル定義（完了）

- [x] `types/graph.py` に `Node`, `Relation`, `GraphModel` を定義
- [x] Pydanticバリデーションの実装

### Phase 2: GraphStorage実装（完了）

- [x] `.j2/storage/graph.yaml` の保存・読込
- [x] 基本的なCRUD操作

### Phase 3: 拡張機能（直近）

- [ ] グラフのマージ機能（複数グラフの統合）
- [ ] ノード/関係の更新・削除機能
- [ ] トランザクション管理（保存の原子性）
- [ ] バリデーション強化（循環参照チェック、孤立ノード検出）

### Phase 4: 最適化（中期）

- [ ] 大規模グラフ対応（遅延読込、インデックス最適化）
- [ ] キャッシュ機構の導入
- [ ] JSON形式のパフォーマンス最適化

---

## 5. 設計上の注意事項

### 5.1 ID管理

- ノードIDと関係IDは別々に採番（衝突回避）
- IDの自動採番は `GraphStorage` が担当
- 既存グラフへの追加時は最大ID+1を採用

### 5.2 型安全性

- `properties` は `dict[str, Any]` だが、各ドメインで型を明確化
- 例: `Node(type="file")` なら `properties["idx"]` は文字列、`Node(type="run")` なら `properties["duration"]` は数値

### 5.3 拡張性

- 新しいノードタイプや関係ラベルは自由に追加可能
- アダプター層で独自のノードタイプを定義してもよい

---

## 6. テスト方針

### 単体テスト（pytest）

- `tests/types/test_graph.py` : Pydanticモデルのバリデーション
- `tests/services/test_storage.py` : GraphStorageのCRUD操作

### テストケース例

- ノード追加・削除・更新
- 関係追加・削除・更新
- YAML/JSON保存・読込の往復検証
- 不正なIDでの例外処理
- 大量ノード（10,000件）での性能確認

---

## 7. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| パーサー層 | → コアデータモデル層 | ファイル解析結果をNodeに変換 |
| runコマンド層 | → コアデータモデル層 | 実行履歴をNode(type=run)として保存 |
| fileコマンド層 | → コアデータモデル層 | ファイル操作履歴をRelationで記録 |
| noteコマンド層 | → コアデータモデル層 | プロジェクト全体のグラフを構築 |
| 出力層 | → コアデータモデル層 | GraphModelを外部形式に変換 |

---

## 8. 参考資料

- [networkx公式ドキュメント](https://networkx.org/)
- [Pydantic公式ドキュメント](https://docs.pydantic.dev/)
- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
