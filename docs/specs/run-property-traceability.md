[← README.md](../../README.md)

# Run-Propertyトレーサビリティ仕様書

## 概要

Run（実行単位）とProperty（プロパティ）の双方向追跡機能を提供する。

- **Run→Property方向**: あるRunがどのプロパティ（ファイル/ノード/値）を生成・変更したかを一覧化
- **Property→Run方向**: あるプロパティがどのRunによって生成されたかを逆引き

## 設計方針

### 現状の課題

現在のRunモデルでは:
- `run_output` リレーションでRunの出力**ファイル**は追跡できる
- しかし出力ファイル内の**プロパティ**（メタデータ、解析結果値等）がどのRunに帰属するかは追跡できない
- ディレクトリノードのプロパティ（idx, version等）がどのRunの産物かも不明

### アプローチ: property_source属性

各ノードのpropertiesに `_property_sources` メタデータを付与し、どのプロパティキーがどのRunノードに由来するかを記録する。

```python
# ノードのpropertiesに追加されるメタデータ
node.properties = {
    "stress_max": 450.0,
    "analysis_status": "completed",
    "_property_sources": {
        "stress_max": {"run_id": 42, "run_name": "go_idx1 abaqus解析"},
        "analysis_status": {"run_id": 42, "run_name": "go_idx1 abaqus解析"},
    }
}
```

### RunQueryService拡張

`RunQueryService` に以下のメソッドを追加:

```python
class RunQueryService:
    def get_run_properties(self, run_node: Node) -> dict[str, list[PropertyTrace]]:
        """Run→Property: Runが生成/変更したプロパティを全ノードから収集"""

    def get_property_source(self, node: Node, property_key: str) -> PropertyTrace | None:
        """Property→Run: 特定プロパティの生成元Runを返す"""

    def get_run_property_summary(self, run_node: Node) -> RunPropertySummary:
        """Runのプロパティ生成サマリー（出力ノード数、プロパティ数、キー一覧）"""

    def get_property_timeline(self, node: Node, property_key: str) -> list[PropertyTrace]:
        """プロパティの変更履歴（複数Runによる上書きの時系列）"""
```

## データモデル

### PropertyTrace

```python
@dataclass
class PropertyTrace:
    """プロパティの帰属情報"""
    run_id: int              # Run NodeのID
    run_name: str            # Run名
    node_id: int             # プロパティを持つNodeのID
    node_name: str           # Node名
    property_key: str        # プロパティキー
    property_value: Any      # プロパティ値
    timestamp: str | None    # Runの実行時刻（started_at）
```

### RunPropertySummary

```python
@dataclass
class RunPropertySummary:
    """Runのプロパティ生成サマリー"""
    run_node: Node
    output_nodes: list[Node]         # run_outputで接続されたノード
    properties_by_node: dict[int, list[PropertyTrace]]  # ノードID→プロパティ一覧
    total_property_count: int        # 生成プロパティ総数
    unique_keys: set[str]            # ユニークなプロパティキー集合
```

## 実装計画

### Phase 1: _property_sources記録（パーサー側）

1. `RunService._update_graph_storage()` でRun Node追加時に、run_outputで接続されたノードの既存プロパティを記録
2. パーサーがプロパティを追加する際に `_property_sources` も併せて記録（VocabFinalizer等の後処理パーサーが追加するプロパティは除外）

### Phase 2: RunQueryService拡張

1. `get_run_properties()`: run_outputリレーション経由で出力ノードを取得し、`_property_sources` からRun帰属プロパティを収集
2. `get_property_source()`: ノードの `_property_sources` から逆引き
3. `get_run_property_summary()`: サマリー生成

### Phase 3: CLIインターフェース

```bash
# Runが生成したプロパティ一覧
jj run --show-properties <run-name>

# プロパティの生成元Run
jj query --property-source <node-name> <property-key>
```

## 簡易実装（Phase 1のみ）

大規模な`_property_sources`追跡はオーバーヘッドが大きいため、まず**既存のrun_output/run_inputリレーションを活用した逆引きクエリ**を実装する。

- Run→出力ノードのプロパティ: `run_output` リレーションから出力ノードを辿り、そのpropertiesを列挙
- Property→Run: 全Runの `run_output` を走査し、対象ノードを含むRunを特定

これにより `_property_sources` メタデータなしでも双方向追跡が可能。

## テスト計画

- `test_get_run_properties`: Runの出力ノードからプロパティ一覧を取得
- `test_get_property_source_run`: プロパティを持つノードの生成元Runを逆引き
- `test_run_property_summary`: サマリー生成の正確性
- `test_multiple_runs_same_output`: 同一出力への複数Run帰属
