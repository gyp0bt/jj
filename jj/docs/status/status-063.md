[READMEへ戻る](../../../README.md)

# status-063: Export基盤整備・キャッシュクリーンアップ・Obsidian Elset-材料可視化

**日付**: 2026-02-11
**担当**: Claude Code

---

## 概要

6つの機能を実装: (1) AbstractExporter基底クラスの定義、(2) CSV/JSONエクスポートのexport/connectors/への移動、(3) Elset品質統計のCSVエクスポート対応、(4) ABQData永続化キャッシュの自動クリーンアップ、(5) ObsidianでElset-材料関係のDataviewクエリ追加、(6) Obsidian Canvas形式でElset-材料マップ生成。

---

## 実装内容

### 1. AbstractExporter基底クラスの定義

**概要**: AbstractFileParserに倣った`__init_subclass__`自動登録パターンで、エクスポーターを統一的に管理する基底クラスを定義。

| ファイル | 変更内容 |
|---|---|
| `services/export/__init__.py` | `AbstractExporter` ABC、`_exporter_registry`、`get_exporter_registry()`、`clear_exporter_registry()`、`get_exporter_for_format()` を実装 |

**パターン**:
```python
class AbstractExporter(ABC):
    format: str = "unknown"
    priority: int = 100

    def __init_subclass__(cls, **kwargs):
        # 自動登録

    @abstractmethod
    def export(self, graph: GraphModel, **kwargs) -> dict[str, Any]:
        ...
```

### 2. CSV/JSONエクスポートのexport/connectors/への移動

**概要**: InfoService内に直接書かれていたCSV/JSONエクスポートロジックを`export/connectors/csv_json.py`に抽出し、AbstractExporterサブクラスとして実装。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/csv_json.py` | **新規作成**: `CsvExporter`、`JsonExporter`、`_export_data()`、`flatten_properties()`、`match_unit()` |
| `services/export/connectors/__init__.py` | `CsvExporter`、`JsonExporter` のre-export追加 |
| `services/service/info.py` | `export_data()` を `csv_json._export_data()` への委譲に変更。不要なimport・関数を削除 |

**後方互換**: InfoService.export_data()のインターフェースは変更なし。内部的にcsv_json.pyのコアロジックに委譲する方式。

### 3. Elset品質統計のCSVエクスポート対応

**概要**: abaqus_elsetノードの品質統計（quality辞書）がCSVエクスポート時に`flatten_properties()`により自動的に"."区切りカラムに展開される。

**出力例**:
```
name,type,element_count,quality.volume.min,quality.volume.max,quality.volume.mean
ELSET1,abaqus_elset,100,0.1,1.0,0.5
```

`--type abaqus_elset`指定でelsetノードのみのCSV出力が可能。

### 4. ABQData永続化キャッシュの自動クリーンアップ

**概要**: parse_and_save()完了後に自動でキャッシュクリーンアップを実行。古いキャッシュの削除と数量制限の2段階ポリシー。

| ファイル | 変更内容 |
|---|---|
| `services/graph/storage/__init__.py` | `cleanup_abq_cache()` メソッド追加（max_age_days、max_count制御） |
| `services/graph/__init__.py` | `parse_and_save()` 後に `cleanup_abq_cache()` を自動呼び出し |
| `config/__init__.py` | `GraphConfig` に `cache_max_age_days`（デフォルト30）、`cache_max_count`（デフォルト100）追加 |

**クリーンアップポリシー**:
1. `max_age_days`日以上前のキャッシュファイルを削除（デフォルト30日）
2. 残ったキャッシュが`max_count`を超える場合、古い順に削除（デフォルト100件）

**設定例**:
```yaml
# .jj/config/config.yaml
cache-max-age-days: 60    # 60日間保持
cache-max-count: 200      # 最大200ファイル
```

### 5. ObsidianでElset-材料関係のDataviewクエリ追加

**概要**: Obsidianエクスポートの各ノードタイプにDataviewクエリを追加し、Elset-材料の関係をObsidian上で動的にテーブル表示できるようにする。

| ノードタイプ | 追加クエリ |
|---|---|
| `abaqus_elset` | 同一材料のelset一覧（TABLE: material, element_count） |
| `abaqus_material` | 使用しているelset一覧（TABLE: element_count, source_file） |
| `go`/`Abaqusインプット` | 所属elset一覧（TABLE: element_count, material、elsets propertyがある場合のみ） |

**出力例（abaqus_elsetノード）**:
```markdown
### 関連材料（Dataview）

```dataview
TABLE material AS "材料", element_count AS "要素数"
FROM "notes/props/abaqus_elset"
WHERE material = "Steel_S235"
SORT element_count DESC
```
```

### 6. Obsidian Canvas形式でElset-材料マップ生成

**概要**: Obsidian Canvasの.canvas形式（JSON）でElset-材料の関係グラフを自動生成。

| ファイル | 変更内容 |
|---|---|
| `services/export/connectors/obsidian/__init__.py` | `_write_elset_material_canvas()` と `_get_canvas_md_path()` を追加。`export_graph()` にcanvas生成フックを追加 |

**Canvas構造**:
- 上段: 材料ノード（緑系カラー）
- 下段: Elsetノード（材料ごとにグループ化、赤系カラー）
- 未割り当てElset: 灰色系カラー
- エッジ: `uses_material` ラベル付きの接続線

**出力先**: `notes/props/elset_material_map.canvas`

---

## テスト結果

- **670テストパス、21スキップ**（前回: 652テストパス、21スキップ）
- 新規追加テスト: **18件**
  - `TestAbstractExporter`: 6件（レジストリ登録、format検索、CSV/JSONエクスポート動作）
  - `TestElsetCsvExport`: 2件（品質統計平坦化、type_filterによるelset絞り込み）
  - `TestABQCacheCleanup`: 4件（古いキャッシュ削除、max_count制限、空ディレクトリ、parse_and_save連携）
  - `TestObsidianElsetDataview`: 3件（elset/material/goノードのDataviewクエリ）
  - `TestObsidianElsetCanvas`: 3件（canvas生成、elsetなし、未割り当てelset）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/export/__init__.py` | AbstractExporter基底クラス・レジストリ新規実装 |
| `services/export/connectors/__init__.py` | CsvExporter/JsonExporter re-export追加 |
| `services/export/connectors/csv_json.py` | **新規作成**: CSV/JSONエクスポーター |
| `services/export/connectors/obsidian/__init__.py` | Dataviewクエリ・Canvas生成追加 |
| `services/service/info.py` | export_dataをcsv_json.pyに委譲 |
| `services/graph/storage/__init__.py` | cleanup_abq_cache() 追加 |
| `services/graph/__init__.py` | parse_and_save後にキャッシュクリーンアップ呼び出し |
| `config/__init__.py` | cache_max_age_days, cache_max_count 設定追加 |
| `tests/test_parser_units.py` | 18件のテスト追加 |
| `docs/status/status-063.md` | 本ステータスファイル |

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

## エクスポーター実行順（新規）

| priority | エクスポーター | format |
|----------|--------------|--------|
| 10 | CsvExporter | csv |
| 11 | JsonExporter | json |
| - | ObsidianConnector | obsidian（直接呼び出し） |
| - | Neo4jConnector | neo4j/cypher（直接呼び出し） |

---

## TODO（次回への引き継ぎ）

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] ObsidianConnector / Neo4jConnectorをAbstractExporterサブクラスに移行
- [ ] `jj export --target <format>` のAbstractExporterレジストリ経由での実行
- [ ] Obsidian Canvas: goノードも含めたelset-material-goの3層関係グラフ

---

## 設計上の懸念

- CSV/JSONエクスポートはAbstractExporterサブクラスとして実装したが、ObsidianとNeo4jは現時点では直接呼び出しのまま。段階的にAbstractExporter化する方針。
- Obsidian Canvasの座標計算は単純な格子配置。ノード数が多い場合はレイアウトの調整が必要になる可能性がある。
- Dataviewクエリは固定文字列でObsidian Dataviewプラグインの存在を前提としている。プラグイン未導入環境ではコードブロックとして表示される（害はない）。
