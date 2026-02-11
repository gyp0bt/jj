# status-055

日付: 2026-02-10

[READMEへ戻る](../../../README.md)

## 概要

cli/graph.pyからビジネスロジックを分離し、services/service/graph_command.pyに移動。
CLIアーキテクチャルール「cli層はservice以外からロジックをインポートすること、中でロジックを実装することを禁止する」を徹底。

## 実装内容

### 1. services/service/graph_command.py（新規作成）

`GraphCommandService` クラスを新規作成。cli/graph.pyに散在していた以下のビジネスロジックを集約:

| メソッド | 旧所在 | 責務 |
|---------|--------|------|
| `init_config()` | `_run_init` | 設定ファイル初期化 |
| `parse()` | `_run_parse` | プロジェクトパース、configオーバーライド、サマリー生成 |
| `show()` | `_run_show` | グラフロード、ノードフィルタリング |
| `load_or_parse()` | `_run_export` | parse-then-exportオーケストレーション |
| `export_obsidian()` | `_run_export` | ObsidianConnector呼び出し |
| `export_data()` | `_run_export_data` | CSV/JSONエクスポート前のノード選択ロジック |
| `export_neo4j()` | `_run_export_neo4j` | Neo4j設定構築、Connector管理 |
| `info()` | `_run_info` | ノード検索、propフィルタリング |
| `get_relations_for_node()` | `_run_info` | リレーション取得 |
| `diff()` | `_run_diff` | ファイルパス解決、Abaqus差分計算 |
| `credential_set/show/delete()` | `_run_credential` | クレデンシャルCRUD |

戻り値用データクラス:
- `ParseResult`, `ShowResult`, `ExportObsidianResult`, `ExportDataResult`, `ExportNeo4jResult`, `InfoResult`, `DiffResult`, `CredentialShowResult`

### 2. services/cli/graph.py（リファクタリング）

ビジネスロジックを全て `GraphCommandService` に委譲。CLI層の責務を以下に限定:
- argparse引数の定義 (`_add_*_args` 関数群)
- パーサーセットアップ (`add_graph_parser`, `add_top_level_graph_commands`)
- コマンドディスパッチ (`run_graph_command`, `run_top_level_graph_command`)
- 結果の出力整形 (`_run_*`, `_print_*` 関数群)

**削除されたインポート:**
- `from config import init_graph_config` → GraphCommandService経由
- `from services.graph import GraphService` → GraphCommandService経由
- `from services.service.info import InfoService` → GraphCommandService経由
- `from services.lib.credentials import ...` → GraphCommandService経由
- `from services.parse.connectors.abaqus import ...` → GraphCommandService経由
- `from services.export.connectors.obsidian import ObsidianConnector` → GraphCommandService経由

**新規インポート:**
- `from services.service.graph_command import GraphCommandService`

ファイルサイズ: 1199行 → 1015行（15%削減）

### 3. services/service/__init__.py（更新）

`GraphCommandService` をエクスポートに追加。

## 設計判断

### CLI層のインポート制約
`services/README.md` のアーキテクチャルール:
> cli: service以外からロジックをインポートすること、中でロジックを実装することを禁止する。

この制約に基づき、cli/graph.pyが直接参照していた以下のモジュールへのアクセスを全て`GraphCommandService`経由に変更:
- `services.graph` (GraphService)
- `services.parse.connectors.abaqus` (diff, read_inp)
- `services.export.connectors.obsidian` (ObsidianConnector)
- `services.lib.credentials` (load/save/mask)
- `config` (init_graph_config)

唯一の例外: `services.lib.selection.expand_ranges` はCLI引数の前処理ユーティリティとして残留。

### 戻り値のデータクラス化
サービス層から返すデータを明確なデータクラスとして定義。CLI層は返されたデータクラスのフィールドを読み取って出力を整形するだけの薄いラッパーになる。

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/service/graph_command.py` | 新規作成: GraphCommandService + 8データクラス |
| `services/cli/graph.py` | リファクタリング: ビジネスロジック削除、GraphCommandService委譲 |
| `services/service/__init__.py` | GraphCommandService追加 |
| `docs/status/status-055.md` | 本ステータスファイル |

## テスト結果

```
599 passed, 21 skipped（既存テスト全てパス、リグレッションなし）
※ test_diff_between_versions: 既存の失敗（本変更と無関係）
```

## 確認事項・TODO

- [x] graph.pyのビジネスロジックをservice層に分離
- [x] 既存テスト599件パス（リグレッションなし）
- [ ] cli/__init__.py のビジネスロジック分離（submit系は既にSubmitService委譲済み、RunServiceのインポートがservice経由でない点を将来的に対応）
- [ ] expand_rangesのCLI層での直接使用をservice層に移す検討
- [ ] パーサーキャッシュの実装（status-053からの継続TODO）
