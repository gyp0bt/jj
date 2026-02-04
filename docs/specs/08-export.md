[READMEへ戻る](../../README.md)

# 出力層 仕様書

## 1. 概要

本ドメインは、jj内部のグラフデータを外部ツール向けの形式に変換・出力する機能を提供します。Obsidian、Neo4j、カスタムJSON等、多様な出力形式をサポートします。

### 目的

- グラフデータを外部ツール向けに変換
- 多様な出力形式への対応
- 出力フォーマットのプラグイン化

### 責務範囲

- `services/export/` : 出力形式の変換とエクスポート機能

---

## 2. 対応出力形式

### 2.1 Obsidian（Markdown）

#### 概要

- Obsidian Vaultに配置可能なMarkdownノートを生成
- `[[wikilink]]` 形式でノード間をリンク
- Frontmatterにメタ情報を埋め込み

#### 出力例

詳細は [noteコマンド層仕様書](./05-note-command.md) を参照。

### 2.2 Neo4j（Cypher）

#### 概要

- Neo4jにインポート可能なCypherクエリを生成
- ノードとリレーションを効率的に作成
- プロパティの型を適切に変換

#### 出力例

```cypher
// Nodes
CREATE (n1:File {id: 1, name: "go_sample_v1_idx1.inp", format: "inp", idx: "1", ver: "1"})
CREATE (n2:Run {id: 1001, name: "run-2026-02-04-120000", duration: 125.3, user: "username"})

// Relations
CREATE (n2)-[:GENERATED]->(n1)
```

#### 出力コマンド（将来）

```bash
jj export neo4j --output graph.cypher
```

### 2.3 JSON

#### 概要

- 標準的なJSON形式でグラフを出力
- カスタムツールでの読込に適する
- `GraphModel` の直列化

#### 出力例

```json
{
  "nodes": [
    {
      "id": 1,
      "type": "file",
      "name": "go_sample_v1_idx1.inp",
      "format": "inp",
      "properties": {
        "idx": "1",
        "ver": "1"
      }
    },
    {
      "id": 1001,
      "type": "run",
      "name": "run-2026-02-04-120000",
      "format": null,
      "properties": {
        "duration": 125.3,
        "user": "username"
      }
    }
  ],
  "relations": [
    {
      "id": 1,
      "label": "generated",
      "node1_id": 1001,
      "node2_id": 1
    }
  ]
}
```

#### 出力コマンド（将来）

```bash
jj export json --output graph.json
```

### 2.4 GraphML

#### 概要

- 標準的なグラフ交換形式
- Gephi、Cytoscape等での可視化に適する

#### 出力例

```xml
<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="1">
      <data key="type">file</data>
      <data key="name">go_sample_v1_idx1.inp</data>
    </node>
    <node id="1001">
      <data key="type">run</data>
      <data key="name">run-2026-02-04-120000</data>
    </node>
    <edge source="1001" target="1">
      <data key="label">generated</data>
    </edge>
  </graph>
</graphml>
```

#### 出力コマンド（将来）

```bash
jj export graphml --output graph.graphml
```

---

## 3. Exporterインターフェース

### 3.1 基底クラス

```python
from abc import ABC, abstractmethod
from pathlib import Path
from types import GraphModel

class Exporter(ABC):
    """グラフデータのエクスポーター基底クラス"""

    @abstractmethod
    def get_name(self) -> str:
        """エクスポーター名を返す"""
        pass

    @abstractmethod
    def export(self, graph: GraphModel, output_path: Path) -> None:
        """グラフを指定形式でエクスポート"""
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """出力ファイルの拡張子を返す"""
        pass
```

### 3.2 実装例: Neo4jExporter

```python
from pathlib import Path
from types import GraphModel

class Neo4jExporter(Exporter):

    def get_name(self) -> str:
        return "neo4j"

    def export(self, graph: GraphModel, output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("// Nodes\n")
            for node in graph.nodes:
                props = ", ".join([f"{k}: {self._format_value(v)}" for k, v in node.properties.items()])
                f.write(f"CREATE (n{node.id}:{node.type.capitalize()} {{id: {node.id}, name: \"{node.name}\", {props}}})\n")

            f.write("\n// Relations\n")
            for rel in graph.relations:
                f.write(f"CREATE (n{rel.node1_id})-[:{rel.label.upper()}]->(n{rel.node2_id})\n")

    def get_extension(self) -> str:
        return ".cypher"

    def _format_value(self, value):
        if isinstance(value, str):
            return f"\"{value}\""
        return value
```

---

## 4. ExporterRegistry

### 4.1 概要

エクスポーターを一元管理し、動的に選択可能にします。

### 4.2 実装

```python
class ExporterRegistry:
    """エクスポーターの管理"""

    def __init__(self):
        self._exporters: dict[str, Exporter] = {}

    def register(self, exporter: Exporter):
        """エクスポーターを登録"""
        self._exporters[exporter.get_name()] = exporter

    def get_exporter(self, name: str) -> Exporter | None:
        """名前でエクスポーターを取得"""
        return self._exporters.get(name)

    def list_exporters(self) -> list[str]:
        """登録済みエクスポーターのリストを返す"""
        return list(self._exporters.keys())
```

### 4.3 自動登録

```python
# services/export/__init__.py
from .registry import ExporterRegistry
from .neo4j import Neo4jExporter
from .json import JsonExporter
from .graphml import GraphMLExporter

registry = ExporterRegistry()
registry.register(Neo4jExporter())
registry.register(JsonExporter())
registry.register(GraphMLExporter())
```

---

## 5. 出力コマンド

### 5.1 基本形式（将来実装）

```bash
jj export <format> [options]
```

### 5.2 例

```bash
jj export neo4j --output graph.cypher
jj export json --output graph.json
jj export graphml --output graph.graphml
jj export obsidian --output ./vault/
```

### 5.3 オプション

| オプション | 説明 |
|-----------|------|
| `--output` | 出力先パス |
| `--filter` | ノードタイプでフィルタ（例: `--filter file,run`） |
| `--since` | 指定日時以降のノードのみ出力 |

---

## 6. 実装計画

### Phase 1: 基盤整備（中期）

- [ ] `Exporter` 基底クラスの定義
- [ ] `ExporterRegistry` の実装
- [ ] エクスポーター自動登録機構

### Phase 2: 基本エクスポーター実装（中期）

- [ ] Neo4jExporter の実装
- [ ] JsonExporter の実装
- [ ] GraphMLExporter の実装

### Phase 3: コマンド実装（中期）

- [ ] `jj export` コマンドの実装
- [ ] フィルタリング機能
- [ ] 出力オプションの拡張

### Phase 4: 高度な機能（長期）

- [ ] カスタムテンプレートサポート
- [ ] インクリメンタルエクスポート
- [ ] エクスポートプリセット機能

---

## 7. 設計上の注意事項

### 7.1 パフォーマンス

- 大規模グラフ（10,000ノード以上）でも高速に出力
- ストリーミング出力でメモリ使用量を抑制

### 7.2 型変換

- プロパティの型を出力形式に適切に変換
- 例: Neo4jでは数値は引用符なし、文字列は引用符あり

### 7.3 エスケープ処理

- 特殊文字のエスケープを適切に行う
- 例: Cypher内の `"` や `\`

---

## 8. テスト方針

### 単体テスト（pytest）

- `tests/services/test_export.py` : 各エクスポーターのテスト
- `tests/services/test_registry.py` : ExporterRegistryのテスト

### テストケース例

- 各形式への正確な変換
- 大規模グラフの出力
- 特殊文字のエスケープ
- エクスポーター選択の正確性

---

## 9. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| コアデータモデル層 | → 出力層 | GraphModelを受け取って変換 |
| noteコマンド層 | ← 出力層 | Obsidian出力を委譲 |

---

## 10. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [noteコマンド層仕様書](./05-note-command.md)
