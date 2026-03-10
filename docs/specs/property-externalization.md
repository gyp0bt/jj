[← README.md](../../README.md)

# プロパティ外部化（Property Externalization）仕様

## 概要

graph.yaml に格納されるノードプロパティのうち、配列やdict等の重いデータを
別ファイル（JSON）に分離し、必要時のみオンデマンドでロードする仕組み。

## 課題

- graph.yaml にノード数×重いプロパティが直接書き込まれ、ロード時間が増大
- 全ノードの全プロパティを毎回デシリアライズする必要がある
- ダッシュボード等では一部ノードのプロパティしか参照しない

## 設計

### ストレージ構造

```
.j2/storage/
├── graph.yaml              # 軽量: スカラー値のみ
├── properties/             # 外部化されたプロパティ
│   ├── node_1.json         # Node id=1 の重いプロパティ
│   ├── node_3.json         # Node id=3 の重いプロパティ
│   └── ...
├── parse_timestamps.json
└── plugin_cache/
```

### 外部化の判定ロジック

プロパティ値が以下のいずれかに該当する場合、外部化対象:
1. `list` 型で要素数 > 0
2. `dict` 型で要素数 > 0

スカラー値（str, int, float, bool, None）は graph.yaml に残す。

### graph.yaml のフォーマット

```yaml
nodes:
  - id: 1
    type: go_model
    name: model_001
    format: inp
    properties:
      path: models/model_001.inp
      index: '1'
      version: '1.0'
      active: 'true'
      mesh_node_count: 15234        # スカラー → そのまま
      _ext_keys:                    # 外部化マーカー
        - mesh_element_types
        - mesh_elset_summary
        - mesh_topology_groups
```

### 外部プロパティファイル（node_{id}.json）

```json
{
  "mesh_element_types": ["C3D8", "C3D10"],
  "mesh_elset_summary": {"ELSET_1": 2000, "ELSET_2": 3000},
  "mesh_topology_groups": [
    {"id": 1, "node_count": 5000, "connected": true}
  ]
}
```

## API

### GraphStorage

| メソッド | 説明 |
|---------|------|
| `save(project_root, graph)` | 重いプロパティを自動外部化して保存 |
| `load(project_root, resolve_externalized=False)` | 軽量ロード（デフォルト）/ フルロード |
| `load_node_properties(project_root, node_id)` | 特定ノードの外部プロパティをオンデマンドロード |
| `save_node_properties(project_root, node_id, properties)` | 特定ノードの外部プロパティを保存 |

### CacheProvider プロトコル

```python
def load_node_properties(self, project_root: Path, node_id: int) -> dict[str, Any]: ...
def save_node_properties(self, project_root: Path, node_id: int, properties: dict[str, Any]) -> Path: ...
```

### ロードモード

1. **軽量ロード**（デフォルト）: graph.yaml のスカラー値 + `_ext_keys` マーカーのみ
2. **フルロード**: graph.yaml + 全外部プロパティを結合して返す
3. **オンデマンド**: `load_node_properties(node_id)` で個別ノードを取得

## 後方互換性

- `save()` は自動的に外部化（既存コード変更不要）
- `load(resolve_externalized=True)` で従来と同一のGraphModelを取得可能
- `_ext_keys` プロパティはNode.propertiesの一部として透過的に保持
- 外部プロパティファイルが存在しない場合は空dictを返す（新規プロジェクト対応）
