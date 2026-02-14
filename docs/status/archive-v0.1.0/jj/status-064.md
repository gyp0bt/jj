[READMEへ戻る](../../../README.md)

# status-064: エクスポートロジック統一・AbstractExporter全形式対応・3層Canvas

**日付**: 2026-02-11
**担当**: Claude Code

---

## 概要

5つの機能を実装: (1) ObsidianConnectorのAbstractExporterサブクラス化、(2) Neo4jConnector/CypherのAbstractExporterサブクラス化、(3) DashboardJsonExporterの新規作成、(4) `jj export --target <format>` のAbstractExporterレジストリ経由での統一実行、(5) Obsidian Canvas 3層（go-material-elset）関係グラフ生成。

---

## 実装内容

### 1. ObsidianExporter（AbstractExporterサブクラス）

**概要**: ObsidianConnectorをラップするAbstractExporterサブクラスを追加。レジストリに自動登録される。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | `ObsidianExporter`クラス追加（format="obsidian", priority=20）、AbstractExporterインポート追加 |

### 2. Neo4jExporter / CypherExporter（AbstractExporterサブクラス）

**概要**: Neo4jConnectorをラップする2つのAbstractExporterサブクラスを追加。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/neo4j.py` | `Neo4jExporter`（format="neo4j", priority=30）と`CypherExporter`（format="cypher", priority=31）を追加 |

### 3. DashboardJsonExporter（新規）

**概要**: DashboardDataProviderをAbstractExporterサブクラスとしてラップ。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/dashboard_json.py` | **新規作成**: `DashboardJsonExporter`（format="dashboard-json", priority=40） |

### 4. AbstractExporterレジストリ経由の統一実行

**概要**: GraphCommandServiceに`export_by_format()`メソッドを追加し、全エクスポート形式をレジストリ経由で統一的に呼び出せるようにした。既存のexport_obsidian/export_neo4j/export_dashboard_jsonメソッドもexport_by_format経由に内部変更。

| ファイル | 変更内容 |
|---|---|
| `services/service/graph_command.py` | `export_by_format()`メソッド追加、`export_obsidian()`/`export_neo4j()`/`export_dashboard_json()`をレジストリ経由に内部変更 |
| `services/export/connectors/__init__.py` | 新エクスポーター（ObsidianExporter, Neo4jExporter, CypherExporter, DashboardJsonExporter）のre-export追加 |

**壊れていたインポートパスの修正**: `graph_command.py`の`from services.connectors.neo4j import Neo4jConnector`（存在しないパス）を、レジストリ経由の呼び出しに置き換えることで解消。

### 5. Obsidian Canvas 3層（go-material-elset）関係グラフ

**概要**: 2層（material-elset）に加えて、goノードを含む3層関係グラフを自動生成。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | `_write_elset_material_go_canvas()`メソッド追加、`export_graph()`に3層Canvas生成フック追加 |

**Canvas構造**:
- 上段(Y=0): goノード（青系、source_fileで紐付けられたインプットファイル）
- 中段(Y=150): 材料ノード（緑系）
- 下段(Y=350〜): Elsetノード（赤系、材料ごとにグループ化）
- エッジ: `uses_material`（elset→material）、`defined_in`（elset→go）

**出力先**: `notes/props/elset_material_go_map.canvas`

---

## テスト結果

- **117テストパス、2スキップ**（前回: 106テストパス（pymesh除外時）、21スキップ）
- 新規追加テスト: **11件**
  - `TestExporterRegistry`: 7件（全形式登録確認、priority順序、Obsidian/Cypher/DashboardJsonのレジストリ経由実行、export_by_format動作、未知形式エラー）
  - `TestObsidianElsetMaterialGoCanvas`: 4件（3層Canvas生成、goなし、材料未割り当て+go、elsetなし）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | ObsidianExporter追加、3層Canvas生成メソッド追加 |
| `services/export/connectors/neo4j.py` | Neo4jExporter/CypherExporter追加 |
| `services/export/connectors/dashboard_json.py` | **新規作成**: DashboardJsonExporter |
| `services/export/connectors/__init__.py` | 新エクスポーターのre-export追加 |
| `services/service/graph_command.py` | export_by_format()追加、レジストリ経由に内部変更、壊れたインポートパス修正 |
| `tests/test_parser_units.py` | 11件のテスト追加 |
| `docs/status/status-064.md` | 本ステータスファイル |

---

## エクスポーター実行順（更新）

| priority | エクスポーター | format |
|----------|--------------|--------|
| 10 | CsvExporter | csv |
| 11 | JsonExporter | json |
| 20 | ObsidianExporter | obsidian |
| 30 | Neo4jExporter | neo4j |
| 31 | CypherExporter | cypher |
| 40 | DashboardJsonExporter | dashboard-json |

全エクスポーターがAbstractExporterサブクラスとしてレジストリに登録済み。
`get_exporter_for_format("obsidian")` 等でクラスを取得し、`exporter.export(graph, **kwargs)` で統一的に呼び出し可能。

---

## パーサー実行順（更新なし）

| priority | パーサー | 備考 |
|----------|---------|------|
| 20 | VersionRelationParser | |
| 30 | ResultRelationParser | |
| 31 | AssetRelationParser | |
| 32 | OutputRelationParser | |
| 33 | JsonPropertyParser | |
| 40 | IncludesRelationParser | |
| 50 | DirectoryRelationParser | |
| 60 | AbaqusInpParser | |
| 80 | AbaqusMeshParser | requires_full=True |
| 81 | MeshInheritParser | |
| 85 | AbaqusMaterialAssignmentParser | |
| 86 | AbaqusResultRelationParser | |
| 90 | AbaqusDiffParser | |
| 95 | ObsidianDailyParser | |
| 98 | AbaqusElsetParser / RootDirectoryParser | |
| 99 | EnrichmentOnlyFilter | |
| 100 | VocabFinalizer | |

---

## TODO（次回への引き継ぎ）

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] CLI `_run_export()` のレジストリ経由統一化（現在はtargetごとのif分岐だが、レジストリ経由で自動ディスパッチする拡張が可能）

---

## 設計上の懸念

- CLI層（graph.py）の`_run_export()`はtargetごとにif分岐で出力整形を行っている。エクスポーター自体はレジストリ経由で統一されたが、CLI出力整形は形式固有のためif分岐を維持している。将来的にエクスポーターに`format_output()`メソッドを追加して完全統一化する選択肢もある。
- Neo4jExporterは内部でNeo4jConnectorを生成・closeするため、1回のexportごとに接続が発生する。バッチ連続呼び出しにはNeo4jConnector直接使用を推奨。
- 3層Canvasのレイアウトは固定座標（格子配置）。ノード数が多い場合は見づらくなる可能性がある。
