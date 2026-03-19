[READMEへ戻る](../../README.md)

# 実装詳細

## 目的
- プロジェクトフォルダを解析し、グラフデータ化して `.j2/storage` に保存する。
- 外部ソフトは出力先として扱い、jj内部でグラフを完結させる。

## 採用ライブラリ
- **グラフデータ**: `networkx`
  - シンプルなグラフ構造の生成・探索に適し、Python標準の拡張で運用しやすい。
- **型定義**: `pydantic`
- **CLI**: `argparse`
- **品質**: `ruff`, `pytest`, `uv`（仮想環境は `.venv`）

## ディレクトリ構成（2026-02-09 構造改革後）

```
services/
├── graph/                  # プロジェクトツリーのスキャンと初期グラフ生成
│   ├── __init__.py         # ProjectGraph 生成（scan_directory等）
│   └── storage/            # .j2/storage への永続化（GraphStorage）
├── parse/                  # グラフへのtag/property/relation付与
│   ├── base.py             # AbstractFileParser 抽象基底クラス
│   ├── file_parse.py       # FileParse/ObsidianFileParse（レガシー）
│   ├── parsers/            # 共通パーサーサブクラス群（Phase R で作成予定）
│   └── connectors/         # ソフト固有のparse/exportロジック
│       ├── abaqus/         # Abaqus INP読み込み、メッシュ統計、差分比較
│       │   ├── __init__.py # ABQData, read_inp, diff等
│       │   └── mesh.py     # pymesh統合メッシュ品質
│       └── obsidian/       # Obsidianエクスポート、daily連携
│           ├── __init__.py # ObsidianConnector, export_graph等
│           └── daily.py    # DailyNote解析
├── export/                 # グラフの外部出力（ローカル以外）
│   └── connectors/
│       └── neo4j.py        # Neo4jConnector
├── run/                    # スクリプトラッパー（jj r）
├── service/                # サービス横断オーケストレーション
├── cli/                    # CLI（serviceからのみimport）
└── lib/                    # 薄いユーティリティ
    ├── credentials.py      # 秘匿情報管理
    └── file/               # SSH・一括rename
```

その他:
- `jj_types/`: Pydanticモデル（Node, Relation, GraphModel）
- `config/`: `.j2/config` と `.pyssh.yaml` を読み込む設定ローダー
- `tests/`: テストコード
- `assets/`: テストデータ/サンプル
- `shared/`: 共有パッケージ（Neo4jスキーマ、型定義、テストアセット）
- `docs/status/`: 実装状況と実装メモ

## グラフデータモデル
- `Node`: `id`, `type`, `name`, `format`, `properties`
- `Relation`: `id`, `label`, `node1_id`, `node2_id`
- `GraphModel`: `nodes`, `relations`

`networkx` で一時的なグラフを構築し、`jj_types/` のPydanticモデルで永続化用の型へ変換する。

## services/graph の詳細

### ProjectGraph型（Phase R で導入予定）

graph/はプロジェクトフォルダのスキャンと初期グラフデータの生成のみを担当する。

```python
@dataclass
class ProjectFile:
    path: Path
    parent_directory: ProjectDirectory

@dataclass
class ProjectDirectory:
    path: Path
    parent_directory: ProjectDirectory | None
    child_directories: list[ProjectDirectory]
    files: list[ProjectFile]

@dataclass
class ProjectGraph:
    nodes: dict[int, Node]
    relations: list[Relation]

    def iterate_directories(self) -> Iterator[ProjectDirectory]:
        """ツリー構造をProjectDirectory/ProjectFileに変換してiterate"""
```

### graph/storage
- `.j2/storage` 配下に解析済みグラフを保存。
- YAML/JSONのテキスト形式を採用。
- `GraphStorage` が保存・読込・抽出を担当。

```yaml
nodes:
  - id: 1
    type: file
    name: go_sample.v1.inp
    format: inp
    properties:
      idx: "1"
      ver: "1"
relations:
  - id: 1
    label: generated
    node1_id: 1
    node2_id: 2
```

## services/parse の詳細

### 抽象パーサーパターン

parse/はProjectGraphを受け取り、tag/property/relationを割り当てて返す。抽象パーサークラスのサブクラスを`__init_subclass__`で自動リスト化し、全サブクラスを順次適用する設計。

```python
parser_list = []

class AbstractFileParser(ABC):
    def __init_subclass__(cls):
        parser_list.append(cls)

    @abstractmethod
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        """個々のparseロジックに従いグラフを更新"""

def parse(graph: ProjectGraph) -> ProjectGraph:
    """全パーサーを順次適用"""
    for parser_cls in parser_list:
        graph = parser_cls().apply(graph)
    return graph
```

### ファイル名解析基盤（base.py）

`AbstractFileParser` を共通基盤として以下を提供する。
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

**命名規則**
- 新形式は `go_prop1_v1_idx1.inp` のようにアンダースコア区切りでpropsを記載する。
- propsは `文字列+数値` または `文字列=数値` を満たすものを採用し、それ以外はtagとして扱う。
- versionが取得できない場合は旧式の `.v1` を補完する。
- 接頭辞 `go_`/`mesh_`/`material_`/`step_` はファイルタイプとして列挙型でマッピングする。

### parse/connectors

ソフト固有のparseロジックを配置する。

- **abaqus/**: Abaqus INPファイルの読み込み（`read_inp`）、差分比較（`diff_abq_blocks`）、pymeshメッシュ統計
- **obsidian/**: Obsidian向けエクスポート（`ObsidianConnector`）、dailyノート解析（`DailyNote`）

### Obsidian向け
- `ObsidianConnector` でGraphModel→Obsidian mdファイル群へのエクスポートを行う。
- frontmatter（YAML）にNodeプロパティを書き出し、.baseファイルでフィルター条件を定義。

## services/export の詳細
- グラフの外部出力先を管理する。
- `export/connectors/neo4j.py`: Neo4jConnector（直接書き込み+Cypherファイル出力）
- CSV/JSON/dashboard-jsonエクスポーターを予定。

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
- 実行ログは `.j2/storage/run/run-<timestamp>.json` に保存する。

### ジョブ型の扱い
- 自動でのファイル追跡は行わない。
- `abaqus` や `fluent` などのフォーマットに応じて、生成されるファイル群を事前に列挙しておく。

## services/lib の詳細
- `lib/credentials.py`: Neo4j等の認証情報の暗号化保存（PBKDF2+XOR）
- `lib/file/`: SSH経由のファイル送受信・一括rename等のユーティリティ

## services/service / services/cli
- `service` がユースケースを組み立て、`cli` が argparse で呼び出す。
- `cli` は `service` からのみimportし、直接ロジックを持たない。
