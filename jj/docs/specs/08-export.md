[READMEへ戻る](../../README.md)

# 出力層 仕様書

## 1. 概要

本ドメインは、jj内部のグラフデータを外部ツール向けの形式に変換・出力する機能を提供します。Obsidian、Neo4j、CSV/JSON、ダッシュボード向けJSON等、多様な出力形式をサポートします。

### 目的

- グラフデータを外部ツール向けに変換
- 多様な出力形式への対応
- `__init_subclass__`自動登録によるプラグインアーキテクチャ

### 責務範囲

- `services/export/` : AbstractExporter基底クラスとレジストリ
- `services/export/connectors/` : 各形式のエクスポーター実装

---

## 2. AbstractExporterアーキテクチャ

### 2.1 基底クラス

```python
class AbstractExporter(ABC):
    format: str = "unknown"     # エクスポート形式識別子
    priority: int = 100         # 実行順序（小さいほど先）

    def __init_subclass__(cls, **kwargs):
        # 抽象メソッドが残っていないサブクラスを自動登録

    @abstractmethod
    def export(self, graph: GraphModel, **kwargs) -> dict[str, Any]:
        """グラフをエクスポートし、結果メタデータを返す"""

    def format_cli_result(self, result: dict, project_root: Path) -> str:
        """CLI出力用文字列をフォーマット（オーバーライド可能）"""
```

### 2.2 レジストリ

```python
get_exporter_for_format(fmt: str) -> type[AbstractExporter] | None
get_exporter_registry() -> list[type[AbstractExporter]]
clear_exporter_registry()  # テスト用
```

### 2.3 登録済みエクスポーター

| priority | クラス | format | 場所 |
|----------|--------|--------|------|
| 10 | CsvExporter | csv | connectors/csv_json.py |
| 11 | JsonExporter | json | connectors/csv_json.py |
| 20 | ObsidianExporter | obsidian | connectors/obsidian/ |
| 30 | Neo4jExporter | neo4j | connectors/neo4j.py |
| 31 | CypherExporter | cypher | connectors/neo4j.py |
| 40 | DashboardJsonExporter | dashboard-json | connectors/dashboard_json.py |

---

## 3. 統一エクスポートパイプライン

### 3.1 CLI層

```
_run_export()
  ↓ target文字列取得
  ↓ _build_export_kwargs(target, args) → kwargs構築
  ↓ service.export_unified(graph, target, **kwargs) → (result, exporter)
  ↓ exporter.format_cli_result(result, project_root) → CLI出力
```

### 3.2 Service層

```
GraphCommandService.export_unified(graph, target, **kwargs)
  ↓ get_exporter_for_format(target) → exporter_cls
  ↓ CSV/JSON: _prepare_data_export_kwargs() でノード事前選択
  ↓ dashboard-json: config設定自動注入
  ↓ exporter.export(graph, **kwargs) → result
  → (result, exporter)
```

### 3.3 後方互換

既存の個別メソッド（`export_obsidian()`, `export_data()`, `export_neo4j()` 等）は
内部的に `export_by_format()` を呼び出しており、引き続き使用可能。

---

## 4. 対応出力形式

### 4.1 CSV

- UTF-8 BOM付きCSVファイル
- プロパティ平坦化（"."区切り）
- 単位表示形式: header（`key[unit]`）またはrow（別行）
- カラム選択（globパターン対応）

### 4.2 JSON

- インデント付きJSON
- ensure_ascii=Falseで日本語対応
- プロパティ平坦化オプション

### 4.3 Obsidian

→ **[5. Obsidianエクスポート詳細](#5-obsidianエクスポート詳細)** を参照

### 4.4 Neo4j

- Neo4jデータベースへの直接upsert
- UNWIND+MERGEによるバッチ処理
- プロジェクト単位でのデータ管理

### 4.5 Cypher

- Neo4j不要のCypherクエリファイル出力
- Neo4j BrowserまたはCypher-shellで実行可能

### 4.6 dashboard-json

- DashboardDataProvider経由のJSON出力
- Streamlit/Webダッシュボード向け

---

## 5. Obsidianエクスポート詳細

### 5.1 出力構造

```
.obsidian/                           # Vault設定（初回のみ自動生成）
│   ├── app.json                     # アプリ設定
│   ├── community-plugins.json       # 推奨プラグインID一覧
│   └── core-plugins-migration.json  # コアプラグイン設定
notes/
├── props/                       # ノードのマークダウンファイル
│   ├── go/                      # タイプ別ディレクトリ
│   │   ├── O-go_test_v1.inp.md  # 個別ノードファイル
│   │   └── O-go_test_v2.inp.md
│   ├── abaqus_elset/
│   ├── abaqus_material/
│   └── ...
├── bases/                       # .base フィルター条件ファイル
│   ├── go/
│   │   ├── go_idx1.base         # 同一index .base
│   │   └── go.base              # 同一type .base
│   └── ...
├── jj-summary.md               # プロジェクトサマリーノート
├── elset_material_map.canvas    # Elset-材料 Canvas
└── elset_material_go_map.canvas # Elset-材料-go 3層 Canvas
```

### 5.2 命名規則

- 実ファイル: プレフィックスなし（例: `go_test_v1.inp`）
- Obsidianファイル: `O-`プレフィックス付き（例: `O-go_test_v1.inp.md`）
- ディレクトリ: プレフィックスなし（例: `notes/props/go/`）
- daily_note由来ノードは`O-`プレフィックスなし

### 5.3 プラグイン前提の機能

以下の機能はObsidianプラグインが前提:

| 機能 | 必要プラグイン | 説明 |
|------|--------------|------|
| テーブルクエリ | Dataview | `notes/props/`内のノードを動的テーブル表示 |
| .baseファイル | DB Folder | YAML形式フィルター条件でテーブル表示 |
| Canvas | Obsidian Canvas (コア) | Elset-材料関係の視覚化 |
| サマリーノート | Dataview | `jj-summary.md`のプロジェクト概要 |

---

## 6. Obsidian推奨プラグイン構成

### 6.1 必須プラグイン

#### Dataview

jjが出力するマークダウンはDataviewクエリを多用しています。

- **用途**: サマリーノート、ノード間関係のテーブル表示、Elset/材料の一覧
- **インストール**: Obsidian設定 → コミュニティプラグイン → "Dataview"を検索
- **設定**: デフォルト設定で動作。`Enable JavaScript Queries`は不要。

#### DB Folder（またはMetadata Menu）

`.base`ファイル（YAMLフィルター条件）を使ったテーブル表示に必要です。

- **用途**: `notes/bases/`配下の`.base`ファイルでフィルター付きテーブル表示
- **インストール**: Obsidian設定 → コミュニティプラグイン → "DB Folder"を検索
- **設定**: デフォルト設定で動作

### 6.2 推奨プラグイン

#### Templater

ノートテンプレートを活用してカスタムノートを追加する場合に便利です。

- **用途**: 日報ノートのテンプレート化、カスタムノートの定型作成
- **設定**: Template folder → `templates/`に設定

#### Tag Wrangler

jjが出力する多数のタグ（`#go`, `#material/Steel`等）の管理に有用です。

- **用途**: タグの一括リネーム、階層タグの管理

#### Graph Analysis

Obsidianのグラフビューを拡張し、jjのノード間関係を視覚的に探索できます。

### 6.3 Vault自動セットアップ

`jj export --target obsidian` を実行すると、`.obsidian/` ディレクトリが存在しない場合に
Vault設定を自動生成します（初回のみ）。

#### 自動生成されるファイル

| ファイル | 内容 |
|---------|------|
| `.obsidian/app.json` | WikiLinks有効化、frontmatter表示等 |
| `.obsidian/community-plugins.json` | 推奨プラグインID一覧（dataview, dbfolder） |
| `.obsidian/core-plugins-migration.json` | Canvas等のコアプラグイン有効化 |

#### セットアップ手順

1. `jj export --target obsidian` を実行（Vault設定自動生成）
2. Obsidianでプロジェクトルートをフォルダとして開く
3. コミュニティプラグインを有効化（設定 → コミュニティプラグイン → 「制限モードをオフ」）
4. **Dataview**をインストール・有効化
5. **DB Folder**をインストール・有効化
6. `notes/props/jj-summary.md` を開いてプロジェクト概要を確認

> **注意**: `.obsidian/` が既に存在する場合（既存Vault）は設定を変更しません。

### 6.4 Dataviewクエリ例

jjが生成するマークダウン内に埋め込まれるクエリの例:

```dataview
TABLE node_type AS "タイプ", node_format AS "フォーマット", tags AS "タグ"
FROM "notes/props"
WHERE node_type != null
SORT node_type ASC, file.name ASC
```

```dataview
TABLE material AS "材料", element_count AS "要素数"
FROM "notes/props/abaqus_elset"
SORT element_count DESC
```

---

## 7. 出力コマンド

### 7.1 基本形式

```bash
jj export --target <format> [options]
```

### 7.2 対応形式と例

```bash
# Obsidian（デフォルト）
jj export --target obsidian
jj export --target obsidian --parse  # parse後にexport

# CSV/JSON
jj export --target csv --flatten
jj export --target json -type go -id 1..3

# Neo4j
jj export --target neo4j --clear

# Cypher（Neo4j不要）
jj export --target cypher --output graph.cypher

# ダッシュボード
jj export --target dashboard-json
```

### 7.3 共通オプション

| オプション | 説明 |
|-----------|------|
| `--target` | エクスポート形式（obsidian/csv/json/neo4j/cypher/dashboard-json） |
| `--parse` | エクスポート前にparseを実行 |
| `--full` | fullモードでparse |
| `--output` | 出力先ファイルパス |

### 7.4 CSV/JSON固有オプション

| オプション | 説明 |
|-----------|------|
| `-type` | ノードタイプフィルタ |
| `-id` | インデックスフィルタ（範囲展開対応） |
| `-v` | バージョンフィルタ |
| `-all` | 全ノード |
| `-active` | activeのみ |
| `-prop` | プロパティフィルタ |
| `--flatten` | プロパティ平坦化 |
| `--unit-format` | 単位表示形式（header/row） |
| `--columns` | カラム選択 |

---

## 8. テスト方針

### テストケース

- AbstractExporter自動登録テスト
- 各エクスポーターのレジストリ経由実行
- format_cli_result()の出力フォーマット
- export_unified()の統一パイプライン
- Obsidianサマリーノート生成

---

## 9. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [DB統合設計書](./10-db-integration.md)
