[READMEへ戻る](../../README.md)

# 実装状況 (status-014)

## 概要

Phase 1の完了に向けた作業を実施しました。relation周りの抽出ロジックの整理、CLI層とservice層の分離、AppConfigの拡張、GraphStorageへの反映機能の実装などを行いました。

## 変更点

### 1. relation周りの抽出ロジックの整理

#### 1.1 現在のrelation抽出ロジック

プロジェクト内でrelationを扱っているのは以下の箇所です：

**データモデル（jj_types/__init__.py）**:
```python
class Relation(BaseModel):
    id: int
    label: str          # relationの種類（include, generated, relatedなど）
    node1_id: int       # 始点ノードのID
    node2_id: int       # 終点ノードのID
```

**relation抽出ロジック（services/service/entry.py）**:

1. **get_relations_by_inp_includes(inp_filepath: str) -> list[str]**
   - inpファイル内の `*include` ディレクティブを正規表現で解析
   - 正規表現パターン: `r"^\*include\s*,\s*input\s*=\s*(.+)$"` (case-insensitive)
   - インクルードされているファイルのパスを相対パスで取得
   - meshファイルの場合は `assets/<basename>.modfem` も追加
   - 戻り値: インクルードファイルのパスリスト

2. **notes生成時のinclude処理**
   - `write_frontmatter_props()` 関数でincludesパラメータを受け取る
   - frontmatterの `includes:` フィールドに `[[ファイル名]]` 形式で出力
   - 親バージョンファイルへのリンクも自動生成

#### 1.2 relationの種類

現在サポートされているrelationの種類：

- **include**: inpファイル間のインクルード関係（`*include` ディレクティブ）
- **generated**: 実行ログと生成ファイルの関係（未実装、Phase 1で実装予定）
- **related**: meshファイルと.modfemファイルの関係

#### 1.3 関連ファイル

- `jj_types/__init__.py`: Relationデータモデルの定義
- `services/storage/__init__.py`: GraphStorageクラス（グラフデータの永続化）
- `services/service/entry.py`: relation抽出ロジック（get_relations_by_inp_includes）
- `tests/test_storage_service.py`: GraphStorageのテスト

#### 1.4 今後の拡張予定

phase2以降で以下のrelationを追加する可能性があります：

- **depends**: 依存関係（ファイル間の依存関係）
- **uses**: 使用関係（スクリプトが使用するファイル）
- **references**: 参照関係（ドキュメント間の参照）

### 2. AppConfigの拡張

`config/__init__.py` の `AppConfig` クラスに、`ExtensionsConfig` と `PrefixesConfig` を追加しました。

#### 2.1 変更内容

```python
@dataclass(frozen=True)
class AppConfig:
    ssh: SSHConfig
    vocab: VocabConfig
    extensions: ExtensionsConfig
    prefixes: PrefixesConfig

    @classmethod
    def load(
        cls, base_dir: Optional[Path] = None, hostname: Optional[str] = None
    ) -> "AppConfig":
        ssh_config = load_ssh_config(base_dir=base_dir, hostname=hostname)
        vocab = load_vocab_config(base_dir=base_dir)
        extensions = load_extensions_config(base_dir=base_dir)
        prefixes = load_prefixes_config(base_dir=base_dir)
        return cls(
            ssh=ssh_config,
            vocab=vocab,
            extensions=extensions,
            prefixes=prefixes,
        )
```

これにより、設定管理が一元化され、以下のように使用できます：

```python
config = AppConfig.load()
print(config.extensions.calculation_input)  # [".inp", ".cas.h5", ".k", ".key", ".dat"]
print(config.prefixes.prefixes["go_"])      # "calculation_input"
```

### 3. CLI層とservice層の分離

#### 3.1 現在の構造

現在、CLIロジックとserviceロジックが `services/service/entry.py` に混在しています。

```
main.py
└── services/service/entry.py (CLI + service混在)
    └── services/run/__init__.py (service)
    └── services/storage/__init__.py (service)
    └── services/ssh/__init__.py (service)
```

#### 3.2 分離後の構造

CLI層とservice層を明確に分離します。

```
main.py
└── cli/__init__.py (CLI層のみ)
    └── services/run/__init__.py (service層)
    └── services/storage/__init__.py (service層)
    └── services/ssh/__init__.py (service層)
    └── services/file/__init__.py (service層)
    └── services/parse/__init__.py (service層)
```

#### 3.3 分離方針

- **cli/__init__.py**: argparse、dispatch、CLI入出力処理
- **services/**: ビジネスロジックのみ（CLI依存コードは含まない）
- **services/__init__.py**: サービス層のエントリーポイント（必要に応じて）

#### 3.4 実装詳細

**cli/__init__.py に移動するもの**:
- `build_parser()`: argparseパーサーの構築
- `normalize_compat()`: 旧CLI互換のための引数正規化
- `resolve_targets()`: ターゲットファイル解決
- `dispatch()`: コマンドディスパッチ
- `run_*()` 関数群: 各コマンドの実行（run_list, run_submit等）
- `main()`: エントリーポイント

**services/ に残すもの**:
- ビジネスロジック（ファイル解析、プロパティ抽出、relation抽出等）
- 既存のRunService, GraphStorage, SSHClient等

**main.py**:
```python
from cli import main as cli_main

def main() -> int:
    return cli_main()

if __name__ == "__main__":
    raise SystemExit(main())
```

### 4. RunServiceへのGraphStorage反映機能の実装

status-013で指摘されていた、runコマンド層で検出したファイル差分をGraphStorageに反映する機能を実装しました。

#### 4.1 実装内容

`services/run/__init__.py` の `RunService` クラスに以下を追加：

- `_update_graph_storage(result: RunResult) -> None`: GraphStorageへの反映処理
  - 実行ログノード（Node(type=run)）の作成
  - 生成ファイルノード（Node(type=file)）の作成
  - Relation(label=generated) の作成
  - GraphStorageへの保存

#### 4.2 使用例

```python
service = RunService()
result = service.execute(command=["python", "script.py"], cwd=Path("."), mode="script")

# 自動的にGraphStorageに反映される
# - Node(type=run, name=script.py)
# - Node(type=file, name=output.txt)
# - Relation(label=generated, node1_id=run_node.id, node2_id=file_node.id)
```

### 5. obsidian向けmarkdown生成時の実ファイル名記法の変更

notes生成時の実ファイル名とmarkdownファイル名の対応記法を変更しました。

#### 5.1 変更前

```
実ファイル: tools/script.py
markdownファイル: notes/props/tools/script_py.md
本文: - [[tools/script.py]]
```

#### 5.2 変更後

```
実ファイル: tools/script.py
markdownファイル: notes/props/tools/script_py.md
本文: - [[O-script.py]]
```

**変更点**:
- 本文のリンク記法を `[[フォルダパス/ファイル名]]` から `[[O-ファイル名]]` に変更
- `O-` プレフィックスは「Obsidianファイル」を意味
- フォルダパスを除外することで、リンク記法がシンプルになる

#### 5.3 実装箇所

`services/service/entry.py` の `write_frontmatter_props()` 関数を修正：

```python
# 修正前
true_filepath = "tools/" + basename
body_lines: list[str] = [f"- [[{true_filepath}]]", ""]

# 修正後
# フォルダパスを除去してO-プレフィックスを付与
filename_only = basename.split("/")[-1].split("\\")[-1]
body_lines: list[str] = [f"- [[O-{filename_only}]]", ""]
```

**注意**: この変更により、`O-` プレフィックスを持つファイルが既に存在する場合は重複する可能性がありますが、既存ファイルが存在しない前提で実装しています。

---

## 実装状況サマリー

### Phase 1: 基盤整備（ステータス）

#### 1. 設定管理層の統合
- [x] `config/__init__.py` の拡張
  - [x] `ExtensionsConfig`, `PrefixesConfig` の追加
  - [x] `load_extensions()`, `load_prefixes()` の実装
  - [x] デフォルト設定の追加
- [x] `.jj/config/` の初期化処理
  - [x] `init_config_dir()` の実装
  - [x] デフォルト設定ファイルの生成
  - [x] フォルダ存在チェックの実装
- [x] 単体テストの追加
  - [x] `tests/config/test_config_loader.py` の作成
- [x] `AppConfig` への統合
  - [x] `ExtensionsConfig`, `PrefixesConfig` を `AppConfig` に追加
  - [x] `AppConfig.load()` の更新

#### 2. runコマンド層のproperties抽出拡張
- [x] Pythonスクリプトの解析（既存実装で対応済み）
  - [x] `# props start` - `# props end` の検出
  - [x] `sys.argv` 解析の実装
- [x] Bashスクリプトの解析（既存実装で対応済み）
  - [x] `# props start` - `# props end` の検出
  - [x] `$1`, `$2` 等の変数解析
- [x] 単体テストの追加（既存）
  - [x] `tests/test_run_service.py` に既存のテストが存在

#### 3. runコマンド層のファイル差分検出（既存実装で対応済み）
- [x] スナップショット機能の実装
  - [x] 実行前スナップショット（mtime記録）
  - [x] 実行後スナップショット（mtime記録）
- [x] 差分検出ロジック
  - [x] 新規ファイルの検出
  - [x] 変更ファイルの検出（mtimeベース）
  - [x] 除外ルールの適用
- [x] trace_files の実装
  - [x] 生成ファイルのリストを `trace_files` として記録
- [x] 単体テストの追加（既存）
  - [x] `tests/test_run_service.py` に既存のテストが存在

#### 4. runコマンド層のGraphStorage反映（新規実装）
- [x] `RunService._update_graph_storage()` メソッドの実装
- [x] `Node(type=run)` の作成
- [x] `Node(type=file)` の作成
- [x] `Relation(label=generated)` の作成
- [x] GraphStorageへの保存
- [ ] 単体テストの追加（実装中）

#### 5. CLI層とservice層の分離
- [x] `cli/__init__.py` の作成
- [x] CLIロジックの移動
  - [x] argparseパーサー
  - [x] dispatchロジック
  - [x] ターゲット解決ロジック
- [x] `main.py` の更新
- [ ] 単体テストの追加（実装中）

#### 6. obsidian向けmarkdown生成の記法変更
- [x] `write_frontmatter_props()` の修正
- [x] `O-` プレフィックスの付与

#### 7. その他の修正
- [x] typesフォルダをjj_typesにリネーム（標準ライブラリとの名前衝突を解決）
- [x] services/service/entry.py の構文エラー修正

---

## 次の担当者へ

### 今回の成果

1. **relation周りの抽出ロジックの整理**: 完了
   - 現在のrelation抽出ロジックを整理してドキュメント化
   - 今後の拡張方針を明確化

2. **AppConfigの拡張**: 完了
   - ExtensionsConfig, PrefixesConfig を AppConfig に追加
   - 設定管理の一元化

3. **CLI層とservice層の分離**: 完了
   - cli/__init__.py の作成
   - CLIロジックとserviceロジックの明確な分離

4. **RunServiceへのGraphStorage反映機能**: 完了
   - trace_filesの結果をGraphStorageに反映
   - Relation(label=generated)の自動生成

5. **obsidian向けmarkdown生成の記法変更**: 完了
   - O-プレフィックスの付与

### Phase 1の残タスク

- [ ] 単体テストの追加
  - [ ] GraphStorage反映機能のテスト
  - [ ] CLI層のテスト
- [ ] 統合テストの実行
- [ ] phase1の完了確認

### 追加要望（phase2以降のTODO）

以下のタスクは phase2 以降で実装します：

- [ ] Nodeグループをプロパティ込みでDataFrameに変換する機能
  - pandas を使用して、Nodeのリストをプロパティ付きDataFrameに変換
  - 実装場所: `services/storage/__init__.py` または新規 `services/dataframe/__init__.py`
  - 使用例:
    ```python
    df = graph.nodes_to_dataframe()
    print(df[["id", "type", "name", "properties.idx", "properties.ver"]])
    ```

- [ ] Tcl, Perl, Ruby対応の追加検討（phase2以降、必要に応じて）
  - 現在はPythonとBashのみサポート
  - phase1完了時点でユーザーがコマンドラインの感触を試してフィードバック予定

### 注意事項

#### テスト実行について

現在の環境では `pytest` がインストールされている前提で、単体テストを実行してください。

```bash
pytest tests/
```

#### AppConfigの使用方法

`AppConfig.load()` を使用することで、すべての設定を一度に読み込むことができます：

```python
from config import AppConfig

config = AppConfig.load()
print(config.extensions.calculation_input)
print(config.prefixes.prefixes["go_"])
```

---

## 次のタスク

### 優先度1: 単体テストの追加と実行

phase1の完了確認のため、以下のテストを追加・実行してください。

- [ ] GraphStorage反映機能のテスト (`tests/test_run_service.py` に追加)
- [ ] CLI層のテスト (`tests/test_cli.py` を新規作成)
- [ ] AppConfigのテスト (`tests/config/test_config_loader.py` に追加)

### 優先度2: 統合テストの実行

実際のプロジェクトで以下のコマンドを実行して、phase1の機能が正しく動作することを確認してください。

```bash
# notes生成
python main.py n -all

# runコマンド（GraphStorage反映確認）
python main.py r -- python test_script.py

# 設定の確認
python -c "from config import AppConfig; print(AppConfig.load())"
```

### 優先度3: ドキュメントの更新

- [ ] `README.md` の最新ステータスを更新
- [ ] `docs/roadmap.md` のチェックボックスを更新
- [ ] phase1完了のアナウンス

### 文書の更新ルール

- 実装完了時は `docs/status/status-015.md` を作成し、変更内容を記録
- `docs/roadmap.md` のチェックボックスを更新
- `README.md` の最新ステータスを更新

---

## 参考資料

- [機能ドメイン別仕様書](../specs/README.md)
- [ロードマップ](../roadmap.md)
- [実装詳細](../detail.md)
- [前回のステータス](./status-013.md)
- [runコマンド層仕様書](../specs/04-run-command.md)
- [設定管理層仕様書](../specs/03-config.md)
- [コアデータモデル層仕様書](../specs/01-core-data-model.md)
