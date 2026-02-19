[← status-index](status-index.md)

# status-029 — Run中心スキーマ再設計 Phase 1: コアモデル拡張・仕様書策定

- **日付**: 2026-02-19
- **マイルストーン**: M7（Run中心スキーマ再設計）
- **ブランチ**: `claude/run-centric-schema-redesign-KanLN`

---

## 概要

データモデルをRun中心に再設計する第一段階として、仕様書策定とコアモデル拡張を実施。

### 設計思想

> **jjの最重要管理対象はRunである。**

CAEジョブ、スクリプト実行、ML学習、物理実験、jjのparse自体 — 全ての価値ある作業はRun。File/Directory/Dataはそのコンテキスト（入力・出力・実行媒体）に過ぎない。Runの比較（パラメータスタディ、ソルバー比較、ハイパーパラメータチューニング）がjjの中核機能となる。

### 変更内容

1. **仕様書策定**: `docs/specs/run-centric-schema.md` — Run中心スキーマの全体設計
2. **NodeCategory enum追加**: `FILE`, `DIRECTORY`, `DATA`, `REPOSITORY`, `RUN` の5分類
3. **Node.categoryフィールド追加**: デフォルト`file`で後方互換性確保
4. **Run構造的リレーション定数**: `run_input`, `run_output`, `run_media`
5. **ProjectGraph Run検索メソッド**: `get_run_nodes()`, `get_run_inputs()`, `get_run_outputs()`, `get_run_media()`, `add_run_node()`, `get_nodes_by_category()`
6. **AbstractRunDiscoverer基盤**: パーサーパイプライン内でRun Nodeを生成する抽象基底クラス
7. **RunCandidate**: Run発見の中間表現
8. **RunQueryService**: Runの検索・比較・分析サービス（`get_runs()`, `get_run_io()`, `find_comparable_runs()`, `diff_runs()`）
9. **GraphStorage修正**: `model_dump(mode="json")`でEnum値のYAMLシリアライズ対応

---

## 変更ファイル

### 新規

| ファイル | 内容 |
|---------|------|
| `docs/specs/run-centric-schema.md` | Run中心スキーマ再設計仕様書 |
| `jj/services/parse/run_discoverer.py` | AbstractRunDiscoverer, RunCandidate |
| `jj/services/run/query.py` | RunQueryService, RunIO, ComparisonGroup, RunDiff |
| `jj/tests/test_run_centric_schema.py` | 新規テスト35件 |

### 修正

| ファイル | 変更内容 |
|---------|----------|
| `jj/jj_types/__init__.py` | NodeCategory enum, Node.categoryフィールド, Run定数 |
| `jj/services/graph/project_graph.py` | Run検索メソッド6種追加 |
| `jj/services/graph/storage/__init__.py` | `model_dump(mode="json")`でEnum対応 |

---

## テスト結果

- **test_run_centric_schema.py**: 35件全通過（新規）
- **既存テスト**: 986件通過（環境依存の8件はpandas/pymesh未インストールで除外、既知）
- ruff check / ruff format: エラーなし

### テスト内訳

| テストクラス | テスト数 | 内容 |
|-------------|---------|------|
| TestNodeCategory | 7 | enum値、デフォルト、シリアライズ、デシリアライズ、後方互換 |
| TestRunRelationConstants | 2 | 定数値、frozenset |
| TestGraphModelSerialization | 2 | ラウンドトリップ、後方互換 |
| TestProjectGraphRunMethods | 8 | Run検索、IO取得、add_run_node |
| TestRunCandidate | 2 | 基本生成、デフォルト値 |
| TestAbstractRunDiscoverer | 4 | apply、複数候補、空、priority |
| TestRunQueryService | 8 | 検索、IO、比較、差分、空グラフ |
| TestStorageBackwardCompat | 2 | YAML読み書きの後方互換 |

---

## アーキテクチャ

### レイヤー構成

```
L4: ダッシュボード / エクスポート / API
L3: Run比較・分析（RunQueryService）    ← 新規
L2: Run発見（AbstractRunDiscoverer）    ← 新規
L1: ファイル・データ解析（AbstractFileParser）← 既存
L0: コアデータモデル（NodeCategory拡張）  ← 拡張
```

### Run構造

```
       ┌──────────┐
       │   Run     │ category=RUN
       │ (Node)    │ type=run_type
       └──┬──┬──┬──┘
          │  │  │
    ┌─────┘  │  └─────┐
    ▼        ▼        ▼
 run_input run_media run_output
```

---

## 残TODO

- [ ] Phase 2: CaeRunDiscoverer実装（inp→odbペアからCAE潜在Runを発見）
- [ ] Phase 3: MlTrainingRunDiscoverer実装（script→dataset→modelからML潜在Runを発見）
- [ ] Phase 4: RunServiceのRun Node統合（実行時RunもRun Nodeとして記録）
- [ ] Phase 5: RunQueryServiceのダッシュボード統合
- [ ] Phase 6: Neo4j Run Nodeエクスポート対応
- [ ] roadmap.mdにM7マイルストーン追加

---

## 設計上の判断

### categoryを別フィールドにした理由

`type`フィールドの値変更は36パーサー、エクスポーター、ダッシュボード、1000+テストに影響する破壊的変更。`category`を別フィールドにすれば既存コードへの影響ゼロ。

### RunリレーションをRun→Target方向にした理由

「このRunの入力は?」「このRunの出力は?」が `node1_id=run.id` の単純フィルタで済む。

### ComparisonGroupを永続化しない理由

比較は分析の視点であり、データそのものではない。保存すると同期問題が発生し、動的構築の方が柔軟。

---

## 確認事項・懸念

- [ ] 既存パーサーのcategory設定移行をどの程度の優先度で行うか（段階的でOK?）
- [ ] run_typeの値の標準化タイミング（今はフリーテキスト、将来enum化?）
- [ ] Run Node追加によるgraph.yamlサイズ増加（大規模プロジェクトでの検証が必要）
