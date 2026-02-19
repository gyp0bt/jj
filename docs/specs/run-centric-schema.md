[← README.md](../../README.md)

# Run中心スキーマ再設計仕様書

**日付**: 2026-02-19
**関連マイルストーン**: M7（Run中心スキーマ再設計）
**前提**: M6 Phase 4完了（MLパーサー9種実装済み）

---

## 1. 動機と課題

### 1.1 現状の問題

現在のjjデータモデルは以下の問題を抱えている:

1. **ノードタイプの乱立**: `file`, `go`, `mesh`, `material`, `step`, `dataset`, `model_checkpoint`, `training_script`, `experiment_run`, `optimization_study` 等、30種類以上のtypeが暗黙的に増殖
2. **Runの潜在性**: CAEジョブ、スクリプト実行、ML学習はいずれも「入力→処理→出力」のRunだが、統一的なモデルがない
3. **比較の困難さ**: Abaqus vs LS-DYNA、要素種類ごとの結果比較、ハイパーパラメータ違いのモデル性能比較が構造的に表現できない
4. **RunServiceとパーサーの断絶**: `jj run`で記録するRunResult（実行時）と、パーサーが発見する「潜在的Run」（静的解析時）が別概念

### 1.2 本質的な認識

> **jjの最重要管理対象はRunである。**

- CAEのジョブ実行 → Run
- Pythonスクリプトの処理 → Run
- ML前処理、学習、推論 → Run
- 実験（物理試験） → Run
- jjによるparse自体 → Run
- 最適化ループの各trial → Run

全ての価値ある作業はRunであり、File/Directory/Dataはそのコンテキスト（入力・出力・実行媒体）に過ぎない。

### 1.3 設計目標

1. **Node分類の明確化**: 全NodeをFile/Directory/Data/Repository/Runの5カテゴリに整理
2. **Runを一級市民に**: 入力・出力・実行媒体の三項関係をRunの基本構造とする
3. **Run比較の構造化**: 同種Runの比較を型安全に表現
4. **潜在RunとリアルタイムRunの統一**: パーサーが発見するRunと実行記録のRunを同一モデルで表現
5. **後方互換性**: 既存パーサー・エクスポーター・テストを段階的に移行可能にする

---

## 2. ノード分類体系

### 2.1 NodeCategory

全てのNodeは以下の5カテゴリのいずれかに属する:

| カテゴリ | 説明 | 例 |
|---------|------|-----|
| `file` | ディスク上の物理ファイル | `.inp`, `.csv`, `.py`, `.pt` |
| `directory` | ディスク上の物理ディレクトリ | `cae/`, `experiments/exp_001/` |
| `data` | ファイルやディレクトリではない論理データ | material定義, elset, メトリクス |
| `repository` | File/Directory/Data/Relationの集合体 | プロジェクト全体 |
| `run` | 入力→処理→出力の実行単位 | CAEジョブ, ML学習, 実験 |

### 2.2 Nodeモデル拡張

```python
class NodeCategory(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    DATA = "data"
    REPOSITORY = "repository"
    RUN = "run"

class Node(BaseModel):
    id: int
    type: str                          # 詳細タイプ（後方互換）
    name: str
    format: str
    properties: dict[str, Any] = Field(default_factory=dict)
    category: NodeCategory = NodeCategory.FILE  # 新規フィールド
```

**後方互換性**: `category`フィールドにデフォルト値`"file"`を設定。既存のgraph.yamlに`category`がない場合は`file`として読み込む。

### 2.3 type → category マッピング

既存の`type`値から`category`を推定するルール:

| type パターン | category |
|--------------|----------|
| `go`, `mesh`, `material`, `step`, `file`, `unknown` | `file` |
| `directory` | `directory` |
| `dataset`, `model_checkpoint`, `training_script`, `experiment_config`, `feature_set`, `prediction_output` | `file`（ファイルの特化型） |
| `material_definition`, `elset`, `metric_log` | `data` |
| `run`, `experiment_run`, `optimization_trial` | `run` |
| `optimization_study` | `data`（Runの集合メタデータ） |
| `repository` | `repository` |

---

## 3. Run データモデル

### 3.1 Runの定義

Runは**入力Node(s) → 実行媒体Node(s) → 出力Node(s)**の三項関係を持つ特殊なNodeである。

```
       ┌──────────┐
       │   Run     │
       │ (Node)    │
       └──┬──┬──┬──┘
          │  │  │
    ┌─────┘  │  └─────┐
    ▼        ▼        ▼
 Input    Media    Output
 Node(s)  Node(s)  Node(s)
```

### 3.2 Run固有のRelationラベル

| ラベル | 方向 | 説明 |
|--------|------|------|
| `run_input` | Run → Input Node | Runの入力 |
| `run_output` | Run → Output Node | Runの出力 |
| `run_media` | Run → Media Node | Runの実行媒体（ソルバー、スクリプト、装置） |

これらの3ラベルはRunの**構造的リレーション**であり、既存の`includes`, `extracted_from`等の**意味的リレーション**とは別レイヤーで管理する。

### 3.3 Run Node の properties

```python
# Run共通properties
{
    "run_type": str,          # "cae_job", "ml_training", "ml_preprocessing",
                              # "experiment", "optimization_trial", "parse", "script"
    "run_status": str,        # "completed", "failed", "running", "latent"（潜在Run）
    "started_at": str,        # ISO8601（実行時のみ）
    "finished_at": str,       # ISO8601（実行時のみ）
    "duration_seconds": float,# 実行時間（実行時のみ）
    "host": str,              # 実行ホスト
    "user": str,              # 実行ユーザー
    "exit_code": int,         # 終了コード（実行時のみ）
    "discovery": str,         # "runtime"（jj run実行時）or "static"（パーサー発見）
}
```

### 3.4 Run種別と典型的なInput/Output/Media

| run_type | Input | Media | Output |
|----------|-------|-------|--------|
| `cae_job` | .inp, .k, .cas | abaqus, lsdyna, fluent (solver binary/config) | .odb, .d3plot, .dat.h5 |
| `ml_training` | dataset (.csv, .npy) | train.py, config.yaml | model.pt, metrics.json |
| `ml_preprocessing` | raw data (.csv) | preprocess.py | processed data (.npy) |
| `ml_inference` | model.pt, input data | predict.py | predictions.csv |
| `optimization_trial` | search space, model | optimizer.py, optuna config | trial params, objective value |
| `experiment` | 試験条件, 試験片 | 試験装置, 手順書 | 測定データ, 写真 |
| `parse` | project files | jj parser config | graph.yaml |
| `script` | input files | script (.py, .sh) | output files |

### 3.5 潜在Run（Latent Run）

パーサーが発見する「まだ実行されていないが、構造から推定できるRun」:

- **CAE潜在Run**: `.inp` ファイルと対応する `.odb` ファイルのペアから推定
- **ML潜在Run**: `train.py` + `dataset.csv` + `model.pt` のトリプルから推定
- **最適化潜在Run**: `optuna_study.db` + `trial_history.csv` から推定

`run_status: "latent"` で区別する。実際に`jj run`で実行するとstatusが`"completed"`等に昇格する。

---

## 4. Run比較モデル

### 4.1 比較の軸

Run比較は以下の軸で行われる:

| 比較軸 | 説明 | 例 |
|--------|------|-----|
| **同一Media・異なるInput** | パラメータスタディ | 要素種類ごとのAbaqus計算比較 |
| **異なるMedia・同一Input** | ソルバー比較 | Abaqus vs LS-DYNA |
| **同一Input/Media・異なるVersion** | バージョン比較 | v1 vs v2のモデル |
| **異なるrun_type** | ドメイン横断比較 | CAE vs 実験、CAE vs ML予測 |
| **同一run_type・異なるハイパーパラメータ** | チューニング比較 | 学習率0.01 vs 0.001 |

### 4.2 ComparisonGroup

Runの比較を構造的に表現する:

```python
# ComparisonGroupはNodeではなく、ビューレイヤーの概念
# graph.yamlには保存せず、クエリ時に動的に構築する

class ComparisonAxis(str, Enum):
    INPUT = "input"          # 入力が異なる
    MEDIA = "media"          # 実行媒体が異なる
    VERSION = "version"      # バージョンが異なる
    CROSS_DOMAIN = "cross_domain"  # run_typeが異なる

@dataclass
class ComparisonGroup:
    """比較対象のRunグループ"""
    runs: list[Node]                 # 比較対象のRunノード群
    axis: ComparisonAxis             # 比較の軸
    common_aspects: dict[str, Any]   # 共通点（固定された軸の値）
    varying_aspects: list[str]       # 変動点（比較したい属性名）
```

### 4.3 比較可能性の判定

2つのRunが比較可能であるための条件:

1. **少なくとも1つの共通軸**: 同じInput OR 同じMedia OR 同じOutput形式
2. **少なくとも1つの相違軸**: 何かが異なっていること
3. **出力の比較可能性**: 同種の出力形式（数値結果同士、画像同士等）

---

## 5. アーキテクチャ変更

### 5.1 レイヤー構成

```
┌──────────────────────────────────────────────┐
│ L4: ダッシュボード / エクスポート / API        │
│     ComparisonView, RunTimeline, DataFlowDiag │
├──────────────────────────────────────────────┤
│ L3: Run比較・分析レイヤー（新規）               │
│     ComparisonGroup, RunQuery, RunDiff        │
├──────────────────────────────────────────────┤
│ L2: Run発見レイヤー（拡張）                     │
│     AbstractRunDiscoverer（パーサー群の上位概念）│
│     RunService（実行時記録）                    │
├──────────────────────────────────────────────┤
│ L1: ファイル・データ解析レイヤー（既存）          │
│     AbstractFileParser（ファイル名解析、構造解析）│
├──────────────────────────────────────────────┤
│ L0: コアデータモデル（拡張）                     │
│     Node(category), Relation, GraphModel       │
└──────────────────────────────────────────────┘
```

### 5.2 L0: コアデータモデル拡張

**変更ファイル**: `jj/jj_types/__init__.py`

```python
from enum import Enum

class NodeCategory(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    DATA = "data"
    REPOSITORY = "repository"
    RUN = "run"

# Run固有のRelationラベル定数
RUN_INPUT = "run_input"
RUN_OUTPUT = "run_output"
RUN_MEDIA = "run_media"

class Node(BaseModel):
    id: int
    type: str
    name: str
    format: str
    properties: dict[str, Any] = Field(default_factory=dict)
    category: NodeCategory = NodeCategory.FILE

class Relation(BaseModel):
    id: int
    label: str
    node1_id: int
    node2_id: int
    # 変更なし

class GraphModel(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    # 変更なし
```

### 5.3 L1: 既存パーサー層（変更最小）

既存のAbstractFileParserは変更しない。各パーサーが生成するNodeに`category`フィールドを付与することを推奨するが、付与しなくてもデフォルト`"file"`が適用される。

### 5.4 L2: Run発見レイヤー（新規）

```python
class AbstractRunDiscoverer(ABC):
    """Runの発見・構築を担う抽象基底クラス

    AbstractFileParserを継承し、パーサーパイプライン内で
    Run Nodeの生成とrun_input/run_output/run_mediaリレーションの
    構築を行う。
    """
    priority: int = 200  # ファイル解析パーサーの後に実行

    @abstractmethod
    def discover_runs(self, graph: ProjectGraph) -> list[RunCandidate]:
        """グラフからRunの候補を発見する"""
        ...

    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """AbstractFileParser互換のapplyメソッド"""
        candidates = self.discover_runs(graph)
        for candidate in candidates:
            self._materialize_run(graph, candidate)
        return graph

    def _materialize_run(self, graph: ProjectGraph, candidate: RunCandidate) -> Node:
        """RunCandidateをNodeとRelation群に変換してグラフに追加"""
        ...

@dataclass
class RunCandidate:
    """Run発見の中間表現"""
    name: str
    run_type: str               # "cae_job", "ml_training", etc.
    input_node_ids: list[int]   # 入力ノードID群
    output_node_ids: list[int]  # 出力ノードID群
    media_node_ids: list[int]   # 実行媒体ノードID群
    properties: dict[str, Any]  # Run固有プロパティ
    discovery: str = "static"   # "static" or "runtime"
```

### 5.5 L3: Run比較レイヤー（新規）

```python
class RunQueryService:
    """Runの検索・比較・分析"""

    def get_runs(self, graph: GraphModel, **filters) -> list[Node]:
        """条件に合致するRunを検索"""
        ...

    def get_run_io(self, graph: GraphModel, run_node: Node) -> RunIO:
        """Runの入力・出力・媒体を取得"""
        ...

    def find_comparable_runs(self, graph: GraphModel, run_node: Node) -> list[ComparisonGroup]:
        """比較可能なRunを探索"""
        ...

    def diff_runs(self, graph: GraphModel, run_a: Node, run_b: Node) -> RunDiff:
        """2つのRunの差分を取得"""
        ...

@dataclass
class RunIO:
    inputs: list[Node]
    outputs: list[Node]
    media: list[Node]

@dataclass
class RunDiff:
    common_inputs: list[Node]
    diff_inputs: tuple[list[Node], list[Node]]
    common_outputs: list[Node]
    diff_outputs: tuple[list[Node], list[Node]]
    common_media: list[Node]
    diff_media: tuple[list[Node], list[Node]]
    property_diffs: dict[str, tuple[Any, Any]]
```

---

## 6. 既存コードへのマッピング

### 6.1 RunService の統合

現在の`RunService`が生成する`RunResult`をRun Nodeに統合:

```python
# Before: RunServiceが直接graph.yamlを更新
run_node = Node(id=next_id, type="run", name=script_name, format="log", ...)

# After: RunServiceがRunCandidateを生成し、共通パスで追加
candidate = RunCandidate(
    name=script_name,
    run_type="script",
    input_node_ids=[...],
    output_node_ids=[trace_file_node_ids],
    media_node_ids=[script_node_id],
    properties={...},
    discovery="runtime",
)
```

### 6.2 既存パーサーのRun発見への移行

段階的に既存パーサーをRun発見パターンに移行:

| 既存パーサー | Run発見後の役割 |
|-------------|---------------|
| `OutputRelationParser` | → CAE Run発見（inp→odb ペアをRun化） |
| `ResultRelationParser` | → CAE Run IOマッピング |
| `MLDataFlowParser` | → ML Run発見（script→model→data のRun化） |
| `SurrogateWorkflowDetector` | → 層間Run連鎖の発見 |
| `OptimizationRunParser` | → 最適化Run発見 |
| `ExperimentRunParser` | → 実験Run発見 |

**移行は段階的**: 既存パーサーのリレーション生成を維持したまま、追加でRun Nodeを生成するパーサーを上位priority（200番台）で追加する。

---

## 7. graph.yaml スキーマ進化

### 7.1 Before（現行）

```yaml
nodes:
  - id: 1
    type: go
    name: go_idx1_v1.inp
    format: inp
    properties:
      path: cae/go_idx1_v1.inp
      index: "1"
      version: "1"
relations:
  - id: 1
    label: output
    node1_id: 1
    node2_id: 2
```

### 7.2 After（Run中心）

```yaml
nodes:
  - id: 1
    type: go
    name: go_idx1_v1.inp
    format: inp
    category: file
    properties:
      path: cae/go_idx1_v1.inp
      index: "1"
      version: "1"

  - id: 2
    type: calculation_output
    name: go_idx1_v1.odb
    format: odb
    category: file
    properties:
      path: cae/go_idx1_v1.odb

  - id: 10
    type: cae_job
    name: "go_idx1_v1 解析"
    format: ""
    category: run
    properties:
      run_type: cae_job
      run_status: latent
      discovery: static
      solver: abaqus

relations:
  # 既存の意味的リレーション（後方互換）
  - id: 1
    label: output
    node1_id: 1
    node2_id: 2

  # Run構造的リレーション（新規）
  - id: 100
    label: run_input
    node1_id: 10
    node2_id: 1
  - id: 101
    label: run_output
    node1_id: 10
    node2_id: 2
```

### 7.3 後方互換性

- `category`フィールドがないNodeは`file`として扱う
- 既存の意味的リレーション（`output`, `includes`, `extracted_from`等）はそのまま維持
- Run構造的リレーション（`run_input`, `run_output`, `run_media`）は追加レイヤー

---

## 8. 実装計画

### Phase 1: コアモデル拡張（本PR）

- [x] 仕様書策定（本ドキュメント）
- [ ] `NodeCategory` enum追加（`jj_types/__init__.py`）
- [ ] `Node`モデルに`category`フィールド追加（デフォルト`file`）
- [ ] Run関連定数の定義（`RUN_INPUT`, `RUN_OUTPUT`, `RUN_MEDIA`）
- [ ] `ProjectGraph`にRun検索メソッド追加
- [ ] 後方互換性テスト（既存テスト全通過）
- [ ] 新規テスト（NodeCategory, Run Node CRUD）

### Phase 2: RunCandidate / AbstractRunDiscoverer 基盤

- [ ] `RunCandidate` dataclass実装
- [ ] `AbstractRunDiscoverer` 基底クラス実装
- [ ] `RunService` のRun Node統合
- [ ] 基盤テスト

### Phase 3: CAE Run発見パーサー

- [ ] `CaeRunDiscoverer`: inp→odb ペアからCAE潜在Runを発見
- [ ] 既存のOutputRelationParserとの共存
- [ ] テスト

### Phase 4: ML Run発見パーサー

- [ ] `MlTrainingRunDiscoverer`: script→dataset→model トリプルからML潜在Runを発見
- [ ] 既存のMLDataFlowParserとの共存
- [ ] テスト

### Phase 5: Run比較レイヤー

- [ ] `RunQueryService` 実装
- [ ] `ComparisonGroup` 構築ロジック
- [ ] `RunDiff` 実装
- [ ] テスト

### Phase 6: ダッシュボード・エクスポート統合

- [ ] Run一覧ビュー
- [ ] Run比較ビュー
- [ ] Run DAGビュー（データフローダイアグラム）
- [ ] Neo4j Run Nodeエクスポート

---

## 9. 設計上の判断

### 9.1 categoryをNodeフィールドに持つ理由

**選択肢A**: `type`フィールドを`category:subtype`形式に変更
**選択肢B**: 別フィールド`category`を追加 ✓ 採用

理由:
- `type`フィールドは既存の全パーサー、エクスポーター、ダッシュボード、テストで参照されている
- `type`の値変更は大規模な破壊的変更になる
- `category`を別フィールドにすれば、既存コードは一切変更不要

### 9.2 Runのリレーション方向

**選択肢A**: Input → Run → Output（Runが中心）
**選択肢B**: Run → Input, Run → Output（Runから外向き） ✓ 採用

理由:
- Run Nodeから辿る方向で統一すると、「このRunの入力は?」「このRunの出力は?」が単純なクエリになる
- `run_input`, `run_output`, `run_media` はいずれもRun(node1) → Target(node2)

### 9.3 ComparisonGroupの永続化

**選択肢A**: graph.yamlに保存
**選択肢B**: クエリ時に動的構築 ✓ 採用

理由:
- 比較グループは分析の視点であり、データそのものではない
- 保存すると同期の問題が発生する
- 動的構築の方が柔軟性が高い

### 9.4 潜在RunのNodeとしての妥当性

懸念: 「まだ実行されていないRun」をNodeにするのは過剰ではないか?

判断: **妥当である**。理由:
- ファイル構造からRunの存在を推定することがjjの核心的機能
- 潜在Runを明示的にNode化することで、「このファイルはどのRunの入力か?」という問いに直接答えられる
- `run_status: "latent"` で実行済みRunと明確に区別できる
- 実行時にstatusを更新すれば、同一ノードで追跡可能

---

## 10. 懸念事項と残課題

### 10.1 ノード数の増加

Run Nodeの追加によりgraph.yamlのサイズが増加する。N個のファイルペアからN個のRunが生成されるため、ノード数は最大2倍になる。大規模プロジェクト（1000+ファイル）での性能影響を検証する必要がある。

### 10.2 既存パーサーの移行コスト

36個の既存パーサーを段階的にRun対応に移行する必要がある。各パーサーのapply()内で`category`を設定するだけの最小変更から始め、Run発見パーサーの追加は別PRで行う。

### 10.3 ダッシュボード・Neo4j連携への影響

`category`フィールドの追加はNeo4jスキーマとダッシュボードの表示に影響する。Neo4jではNodeのラベルとして`category`を使用し、`type`はプロパティに移動する設計が考えられる。

### 10.4 run_typeの標準化

`run_type`の値をどこまで標準化するか。最初はフリーテキストとし、使用パターンが安定してからenum化する方針とする。

---

## 11. 参考資料

- [コアデータモデル仕様書](../../jj/docs/specs/01-core-data-model.md) — 既存Node/Relation定義
- [ML対応仕様書](ml-task-roadmap.md) — 三層データフローモデル
- [サロゲートモデルフレームワーク仕様書](surrogate-model-framework.md) — 層間リレーション設計
- [runコマンド仕様書](../../jj/docs/specs/04-run-command.md) — 既存RunService設計
