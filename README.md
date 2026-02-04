# jj

CAE業務データをグラフデータ化し、ObsidianやNeo4jなどの外部ソフトに渡すためのCLIコマンドモジュールです。jj内部でグラフデータを構築し、外部ソフトはあくまで出力先として扱う方針です。

## 目的と方針
- プロジェクトフォルダを解析してグラフデータを生成します。
- jjが保持するデータはテキスト形式（主にYAML）とし、`.jj/storage`に保存します。
- プロジェクトごとの語彙マッピングなどの設定は`.jj/config`に配置します（例: `vocab.yaml`）。
- ObsidianやNeo4jは外部ソフトとして扱い、jj内部で完結したグラフを出力する設計です。
- グラフデータの一時構築には `networkx` を採用します。

## コマンド構成
- `jj n` (note)
  - プロジェクトフォルダを解析し、グラフデータ化します。
  - 現状はObsidian向けのnotesフォルダ出力が中心です。
- `jj f` (file)
  - ファイルテンプレート生成、関係を保持したフォルダ移動、リネーム、サーバー送受信などを担当します。
- `jj r` (run)
  - CAEソフトでの計算実行やプリ/ポスト処理の実行履歴、指定オプションのログ取得を担います。
  - 既存のsubmit機能（Abaqusのサーバー投入）を`run`機能としてリファクタリングする方針です。

## データモデル
- **Node**: `id: int`, `type: str`, `name: str`, `format: str`, `properties: dict[str, Any]`
- **Relation**: `id: int`, `label: str`, `node1_id: int`, `node2_id: int`

例: タグ付け
- `Node(type=タグ, name=sample)`
- `Relation(label=tagged, node1_id=1, node2_id=2)`

## 入力データの扱い
- 対象はバイナリ、テキスト、フォルダなど多様です。
- ソフト固有フォーマットの拡張を見据え、**アダプター**の概念を導入し、機能を独立させます。
- 計算inpは拡張子やフォルダで表現されることがあり、ソフト依存の解析が必要です。
- 現状は以下を計算inpとして集計しています。
  - 指定拡張子を持ち、`go_`で始まるファイル名
  - 例: Abaqusなら`.inp`、Fluentなら`.cas.h5`、Dynaなら`.k`/`.key`/`.dat`

## ディレクトリ
- `.jj/storage/` : 解析で生成したグラフデータ（YAML想定）
- `.jj/config/` : プロジェクト固有の設定（例: `vocab.yaml`）
- `docs/status/` : 実装状況の記録（最大indexが最新）
- `docs/roadmap.md` : 今後の計画
- `docs/detail.md` : 実装詳細と仕様リンク
- `services/` : CLI向けサービス群（詳細は各README）
  - `services/parse/file_parse.py` : FileParse/ObsidianFileParseの共通基盤
- `types/` : Pydanticモデル
- `tests/` : pytestテスト
- `assets/` : テストデータ/サンプル

## 運用メモ
- CodexとClaude Codeの2交代制を前提に、引き継ぎ可能な形で実装状況を記録します。
- 実装状況は`docs/status/status-{index}.md`に詳細を記載し、常に最新のindexを参照します。

## 仕様リンク
- [実装詳細](docs/detail.md)
- [ロードマップ](docs/roadmap.md)
- [services/README](services/README.md)
- [types/README](types/README.md)
- [tests/README](tests/README.md)
- [assets/README](assets/README.md)
