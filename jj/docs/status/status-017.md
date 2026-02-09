[READMEへ戻る](../../README.md)

# 実装状況 (status-017)

## 概要

Obsidianファイル名記法を全面的に更新し、全てのObsidian向けファイルに"O-"プレフィックスを追加しました。また、バージョングループ化を全ファイルタイプに拡張し、フォルダ用mdファイルへの実ファイルリンク追加機能を実装しました。

## 変更点

### 1. Obsidianファイル名記法の統一

#### 1.1 "O-"プレフィックスの全面適用

**従来の記法**:
```
baseファイル: notes/bases/go.base
mdファイル: notes/props/inp/go/O-go_1_v1.inp.md
```

**新しい記法**:
```
baseファイル: notes/bases/O-go.base
mdファイル: notes/props/inp/go/O-go_1_v1.inp.md
```

**影響範囲**:
- 全てのbaseファイル: go.base → O-go.base、mesh.base → O-mesh.base、など
- index.md: base.md → O-base.md、go_index.md → O-go_index.md、group_index.md → O-group_index.md
- 個別バージョンbase: go_1.base → O-go_1.base、など
- グループbase: go.base → O-go.base、mesh.base → O-mesh.base、など

#### 1.2 実ファイルへのリンクからの"O-"除去

**重要**: Obsidianファイル自体は"O-"プレフィックスを持つが、実ファイルへのリンクは"O-"を省く。

```markdown
---
includes:
  - [[O-go.base]]        # Obsidianファイルへのリンク
  - [[O-go_1.v1.inp]]    # 親mdファイルへのリンク
---
- [[O-go.base]]
- [[O-go_1.v1.inp]]

- [[go/go_1_v2.inp]]     # 実ファイルへのリンク（"O-"なし）
```

#### 1.3 修正箇所

**cli/__init__.py**:
- 行851-897: baseファイル名に"O-"プレフィックスを追加
- 行900: base_listの初期値を"O-go.base"に変更
- 行921-931: 個別バージョンbaseファイルに"O-"プレフィックスを追加
- 行950-960: グループbaseファイルに"O-"プレフィックスを追加
- 行963-971: base_list内の全baseファイル名に"O-"プレフィックスを追加
- 行1006-1016: index.mdファイル名に"O-"プレフィックスを追加
- 行189-196: write_frontmatter_props関数内のbase_name補正を"O-go.base"に変更
- 行212: 親mdファイルへのリンクに"O-"プレフィックスを追加
- 行238-243: match文のbase_name条件を"O-tools.base"などに更新
- 行1343-1363: inp_groupsとbase_keysのキーを"O-"プレフィックス付きに変更
- 行1386: includesの実ファイル名をmdファイル名に変換（"O-"プレフィックス追加）
- 行1445-1451: mdファイル名に"O-"プレフィックスを追加
- 行1437-1449: reports/toolsのキー収集と制約反映を"O-"プレフィックス付きに更新
- 行1456-1459: go.baseのサブベース更新を"O-go.base"と"O-*.base"に変更

**services/service/entry.py**:
- cli/__init__.pyと同じ変更を全て適用

### 2. 全ファイルタイプへのバージョングループ化の拡張

#### 2.1 変更内容

**従来の動作**:
- go_シリーズのみバージョングループ化を実施
- mesh, material, stepは個別baseファイルを作成しない

**新しい動作**:
- 全カテゴリ（go, mesh, material, step）にバージョングループ化を適用
- 各カテゴリごとに、2つ以上のバージョンがあるファイルに対して個別baseファイルを作成
- 各カテゴリごとにindex.mdを作成（例：O-mesh_index.md）

#### 2.2 バージョングループ化のロジック

```python
# 各カテゴリごとにバージョングループ化を実行
for category in ["go", "mesh", "material", "step"]:
    category_list = list(glob.glob(str(root / "props" / "inp" / category / "*.md")))

    # バージョンを正規化（v1, v2などを除去してグループ化）
    category_list_normalized = []
    for item in category_list:
        idx, ver = get_index_and_version(item)
        if ver:
            normalized = item.replace(f".v{ver}", "")
        else:
            normalized = item
        category_list_normalized.append(normalized)

    # バージョン数をカウント
    version_count = Counter(category_list_normalized)

    # 2つ以上のバージョンがあるグループのみbaseファイルを作成
    for i in category_list_unique:
        if version_count[i] >= 2:
            _write_yaml_if_missing(
                root / "bases" / category / f"O-{i}.base",
                _base_template(...)
            )
```

#### 2.3 生成されるファイル構造

```
notes/
  bases/
    go/
      O-go_index.md          # goカテゴリのindex
      O-go_1.base            # go_1のバージョングループbase
      O-go_2.base            # go_2のバージョングループbase
    mesh/
      O-mesh_index.md        # meshカテゴリのindex
      O-mesh_1.base          # mesh_1のバージョングループbase
    material/
      O-material_index.md    # materialカテゴリのindex
      O-material_abc.base    # material_abcのバージョングループbase
    step/
      O-step_index.md        # stepカテゴリのindex
      O-step_xyz.base        # step_xyzのバージョングループbase
```

#### 2.4 修正箇所

**cli/__init__.py** (906-964行目):
```python
# 全カテゴリに対してバージョングループ化を適用
from collections import Counter

# 各カテゴリごとにバージョングループ化を実行
all_category_bases = []
for category in ["go", "mesh", "material", "step"]:
    # バージョン正規化とグループ化
    # カテゴリごとのbaseディレクトリを作成
    (root / "bases" / category).mkdir(parents=True, exist_ok=True)

    # 2つ以上のバージョンがあるグループのみbaseファイルを作成
    # カテゴリごとのindex.mdを作成
```

**services/service/entry.py**:
- 同様の変更を適用

### 3. v1省略とv2の自動v1判定ロジック

#### 3.1 変更内容

**ロジック**:
- バージョンがないファイル（例：go_1.inp）とバージョン付きファイル（例：go_1.v2.inp）を同じグループとして扱う
- write_frontmatter_props関数の親選択ロジックで、v2の親として「v1」または「バージョンなし」を探す

**実装箇所** (cli/__init__.py:203-213行目):
```python
parent_path_list = [
    basename.replace("v" + ver, "v" + str(int(ver) - 1)),  # v2 → v1を探す
    basename.replace("v" + ver, ""),                        # v2 → バージョンなしを探す
]
```

**バージョン正規化** (cli/__init__.py:919-928行目):
```python
# バージョンを正規化（v1, v2などを除去してグループ化）
for item in category_list:
    idx, ver = get_index_and_version(item)
    if ver:
        normalized = item.replace(f".v{ver}", "")
    else:
        normalized = item
    category_list_normalized.append(normalized)
```

これにより、"go_1.inp"、"go_1.v1.inp"、"go_1.v2.inp"は全て同じグループ"go_1"として扱われます。

### 4. フォルダ用mdファイルへの実ファイルリンク追加

#### 4.1 変更内容

**従来の動作**:
- フォルダのmdファイルには、フォルダ名へのリンクのみ

**新しい動作**:
- フォルダのmdファイルには、フォルダ内の全実ファイルへのリンクを列挙

#### 4.2 実装内容

**write_frontmatter_props関数の拡張** (cli/__init__.py:167-276行目):
```python
def write_frontmatter_props(
    md_path: Path,
    base_name: str,
    all_basename_list: list[str],
    props: dict[str, str],
    includes: list[str] | None = None,
    folder_files: list[str] | None = None,  # 新規パラメータ
) -> None:
    # ...

    # 本文：リンクだけ置く（実ファイルの相対パスをそのまま使用）
    body_lines: list[str] = []
    if folder_files:
        # フォルダの場合は、フォルダ内の全実ファイルへのリンクを追加
        for file in folder_files:
            body_lines.append(f"- [[{file}]]")
    else:
        # 通常のファイルの場合
        body_lines.append(f"- [[{true_filepath}]]")
    body_lines.append("")
```

**run_notes関数での呼び出し** (cli/__init__.py:1427-1471行目):
```python
# frontmatterが真実源なので「追記のみ」
folder_files_list = None
if os.path.isdir(i):
    basename = Path(i).name
    # フォルダ内の実ファイルリストを取得
    folder_path = Path(i)
    folder_files_list = []
    for file in folder_path.iterdir():
        if file.is_file():
            # 相対パスを生成
            rel_path = str(file.relative_to(Path.cwd()))
            folder_files_list.append(rel_path)

# ...

write_frontmatter_props(
    md_path=md_path,
    base_name=base_name,
    all_basename_list=all_basename_list,
    props=props,
    includes=includes,
    folder_files=folder_files_list,  # フォルダ内ファイルリストを渡す
)
```

#### 4.3 生成される例

**フォルダ: docs/tutorial**:
```markdown
---
idx:
ver:
includes:
  - [[O-docs.base]]
---
- [[O-docs.base]]

- [[docs/tutorial/intro.md]]
- [[docs/tutorial/advanced.md]]
- [[docs/tutorial/examples.py]]
```

### 5. その他の重要な修正

#### 5.1 includesの実ファイル名からmdファイル名への変換

**修正箇所** (cli/__init__.py:1384-1386行目):
```python
# includesは実ファイル名を返すので、mdファイル名に変換（"O-"プレフィックス追加）
raw_includes = get_relations_by_inp_includes(i)
includes += [f"O-{inc}" for inc in raw_includes]
```

get_relations_by_inp_includes関数は実ファイル名を返すため、Obsidianのmdファイル名に変換する必要があります。

## テスト結果

- 構文チェック: すべて正常に完了
  - cli/__init__.py
  - services/service/entry.py
  - services/parse/file_parse.py

## TODO

- [ ] 実際のプロジェクトでinit_notes_treeを実行し、"O-"プレフィックスが正しく適用されるか確認
- [ ] Obsidian上で、baseファイルとmdファイルのリンクが正しく機能するか確認
- [ ] 全カテゴリのバージョングループ化が正しく動作するか確認
- [ ] フォルダ用mdファイルに実ファイルリンクが正しく追加されるか確認
- [ ] 既存プロジェクトでのマイグレーション手順を検討

## 次のステップ

1. 実際のプロジェクトでinit_notes_treeを実行し、生成されたファイルを確認
2. Obsidian上で全てのリンクが正しく機能するか確認
3. 必要に応じて、既存のObsidianファイル（"O-"プレフィックスなし）を新しい記法にマイグレーション

## 関連ファイル

- cli/__init__.py
- services/service/entry.py
- services/parse/file_parse.py
- docs/status/status-016.md

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-016.md](./status-016.md)
**次回**: status-018.md (未作成)
