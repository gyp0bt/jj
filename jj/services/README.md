[READMEへ戻る](../README.md)

# services

CLIで利用する主要サービス群のルートです。各サブモジュールは責務を明確に分け、必要に応じて依存方向を整理します。

## 構成
- `storage/`: `.jj/storage` にグラフデータを保存・取得する層。
- `parse/`: プロジェクトフォルダ解析とグラフ化、共通アダプタの基盤。
- `run/`: `jj r` で実行するシステムコマンドのラップとログ/トレース収集。
- `file/`: グラフ情報を保持しつつファイル操作・履歴管理・ssh送受信。
- `ssh/`: SSHによる送受信やリモートコマンド実行のユーティリティ。
- `dashboard/`: ダッシュボード（Streamlit）。描画層(app.py)、クエリ層(query.py)、データ供給層(data_provider.py)、HTMLエクスポート(html_export.py)に分離。コネクター(connectors/)でソフト固有ページを提供。
- `service/`: 各サービスをアセンブルし、CLIに渡す処理関数を提供。

## 依存ルール
- `main.py` -> `service` -> 各サービス。
- `parse`/`storage`/`file`/`run` は互いの責務が重複しないように設計し、必要な連携は `service` 経由で行います。

---
## 26/2/9 servicesの構成を大幅変更
- 従来のservicesは凝集性が過剰に上がって開発効率を落としていた。特にparse/graphまわりのロジックが過密であったため、構成の変更を実施。
- 従来はparseロジックが増えるたびにgraphロジックを膨らまし、手動でparseするもののparseロジック同士の関係性が不明瞭で背反が続出していた。
- 新構造：
    - graph: プロジェクトのツリー構造をスキャンして初期グラフデータの生成
        - ProjectGraph: プロジェクトのツリー構造をスキャンしたグラフデータ型
            ```
            @dataclass
            class Node:
                type: str
                filetype: Literal["directory", "file", "only-data"]
                name: str
                properties: dict[str, Any]
            
            @dataclass
            class Relation:
                type: str
                label: str
                node_id1: int
                node_id2: int
            
            @dataclass
            class ProjectFile:
                path: Path
                parent_directory: ProjectDirectory
            
            @dataclass
            class ProjectDirectory:
                path: Path
                parent_directory: ProjectDirectory
                child_directories: list[ProjectDirectory]
                files: list[File]
            
            @dataclass
            class ProjectGraph:
                nodes: dict[int, Node]
                relations: list[Relation]

                def iterate_directories(self) -> Iterator[ProjectDirectory]:
                    """プロジェクトのツリー構造をNode/RelationからProjectDirectory/ProjectFileに直してiteration"""

            ```
        - graph.storage: 加工されたグラフデータをローカルファイル(.jj/storage/)に保存
    - export: グラフデータをデフォルトのローカルファイル以外に保存
        - json, neo4j, sqlを予定
    - parse: 
        - プロジェクトのツリー構造を受け取ってtag, property, relationを割り当てて返す
        - 抽象パーサーAbstractFileParserクラスを用意し、継承したサブクラスを__init_subclass__でリスト化する。
            ```

            parser_list = []


            class AbstractFileParser(ABC):
                """Parser抽象基底クラス"""

                def __init__(
                    self,
                    true_filepath: Path,
                    extension_candidates: Iterable[str] | None = None,
                ):
                    self.true_file_path = true_filepath
                    self.extension_candidates = extension_candidates
                
                def __init_subclass__(self, cls):
                    parser_list.append(cls)
                
                @abstractmethod
                def apply(self, graph:ProjectGraph) -> ProjectGraph:
                    """個々のパースロジックに従ってグラフデータを更新する"""
                    return graph

            def parse(graph:ProjectDirectory) -> ProjectDirectory:
                """全パースロジックを実行してgraphを更新する。Abaqus、Obsidianコネクタのうちファイルの解析に関するロジックはこの枠組みに焼き直す"""
                for i in parser_list:
                    graph = i.apply(graph)
            ```
        - connectors: AbaqusやObsidianの外部ロジック
    - run: 従来通りのスクリプトラッパー
    - service: 複数サービスにまたがるロジックの凝集性を切り出すためのサービス
    - cli: cliserv用ラッパー。service以外からロジックをインポートすること、中でロジックを実装することを禁止する。
    - lib: メインのサービスではない薄いutilityロジック
        - credentials: 秘匿情報の安全な管理
        - file: sshによるファイル送受信や一括renamのutility