[READMEへ戻る](../README.md)

# 実装詳細

## 目的
- プロジェクトフォルダを解析し、グラフデータ化して `.jj/storage` に保存する。
- 外部ソフトは出力先として扱い、jj内部でグラフを完結させる。

## 採用ライブラリ
- **グラフデータ**: `networkx`
  - シンプルなグラフ構造の生成・探索に適し、Python標準の拡張で運用しやすい。
- **型定義**: `pydantic`
- **CLI**: `argparse`
- **品質**: `ruff`, `pytest`, `uv`（仮想環境は `.venv`）

## ディレクトリ構成
- `services/`
  - `storage/`: `.jj/storage` 入出力。
  - `parse/`: プロジェクト解析と共通アダプタ。
  - `run/`: システムコマンド実行のラップとトレース。
  - `file/`: ファイル操作・履歴・ssh送受信。
  - `ssh/`: SSH送受信とコマンド実行。
  - `service/`: サービスアセンブル。
  - `cli/`: コマンドライン集約。
- `types/`: Pydanticモデル。
- `tests/`: テストコード。
- `assets/`: テストデータ/サンプル。
- `docs/status/`: 実装状況と実装メモ。
- `config/`: `.jj/config` と `.pyssh.yaml` を読み込む設定ローダー。

## グラフデータモデル
- `Node`: `id`, `type`, `name`, `format`, `properties`
- `Relation`: `id`, `label`, `node1_id`, `node2_id`
- `GraphModel`: `nodes`, `relations`

`networkx` で一時的なグラフを構築し、`types/` のPydanticモデルで永続化用の型へ変換する。

## services/parse の詳細
### 共通アダプタ方針
- 初期段階は共通アダプタのみ。
- 処理が複雑化した場合、ソフト固有アダプタへ分割。

### FileParse
`FileParse` を共通基盤として以下を提供する。
- `get_index()`
- `get_version()`
- `get_props()`
- `get_tags()`
- `get_basename()`（フォルダ/拡張子抜き）
- `get_directory()`
- `get_file_type()`（`go_`/`mesh_`/`material_`/`step_`）
- `get_file_group()`（同一index+接頭辞のグループ生成）

**拡張子判定**
- `.cas.h5` など複数ドット拡張子を標準モジュール任せにしない。
- 独自ルールで最後尾一致を優先し、誤判定を防ぐ。

**バイナリ対応**
- バイナリかどうかは開くまで分からないため、常に `errors="ignore"` で読み込みを行う。

**命名規則**
- 新形式は `go_prop1_v1_idx1.inp` のようにアンダースコア区切りでpropsを記載する。
- propsは `文字列+数値` または `文字列=数値` を満たすものを採用し、それ以外はtagとして扱う。
- versionが取得できない場合は旧式の `.v1` を補完する。
- 接頭辞 `go_`/`mesh_`/`material_`/`step_` はファイルタイプとして列挙型でマッピングする。

### Obsidian向け
- `ObsidianFileParse` を作成。
- `ObsidianMap(true_file_path)` で以下を提供。
  - `get_frontmatter_path()`
  - `get_base_path()`
  - `to_frontmatter_path()`

## services/storage の詳細
- `.jj/storage` 配下に解析済みグラフを保存。
- YAML/JSONのテキスト形式を採用。
- `GraphStorage` が保存・読込・抽出を担当。

## services/run の詳細
`run` は `Node(type=run)` として扱い、実行履歴をグラフ化する。

### runの分類
- **スクリプト型**: 即時に完了する処理（主に `python` / `sh`）。
- **ジョブ型**: 最大数時間など長時間の処理（CAEジョブやバッチ投入）。

### スクリプト型の扱い
- 実行前後でプロジェクトのスナップショットを比較する。
- 追加/変更されたファイルと `run` の間に `Relation(label=generated)` を付与する。
- 条件（properties）は以下から取得する。
  - `# props start` と `# props end` の間に書かれた `ncpu=1` や `ver=abq2023` などの宣言。
  - `sys.argv` や `$1` などの引数を、スクリプト内の変数名と対応付けて取得する。
  - 例: `jj r hoge.py 120 60` の実行なら、`sys.argv` に割り当てられた変数名に紐づける。

### ジョブ型の扱い
- 自動でのファイル追跡は行わない。
- `abaqus` や `fluent` などのフォーマットに応じて、生成されるファイル群を事前に列挙しておく。

## services/file の詳細
- 依存関係を保ったファイル操作。
- 操作履歴をグラフへ反映。
- `services/ssh` による送受信をここで一元化。

## services/service / services/cli
- `service` がユースケースを組み立て、`cli` が argparse で呼び出す。
