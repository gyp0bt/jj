[READMEへ戻る](../../README.md)

# 実装状況 (status-016)

## 概要

Obsidian向けのファイル名記法を変更し、グループ機能を追加しました。また、go_シリーズのbase生成ロジックを改善し、サブバージョンが1つのみの場合はgo.baseに直接リンクするようにしました。

## 変更点

### 1. Obsidianファイル名記法の変更

#### 1.1 変更内容

**従来の記法**:
```
実ファイル: go/go_1_v1.inp
markdownファイル: notes/props/inp/go/O-go_1_v1_inp.md
```

**新しい記法**:
```
実ファイル: go/go_1_v1.inp
markdownファイル: notes/props/inp/go/O-go_1_v1.inp.md
frontmatter内のリンク: - [[go/go_1_v1.inp]]
```

#### 1.2 修正箇所

**services/parse/file_parse.py** (237-239行目):
```python
# 修正前
basename = f"{basename}_{ext.lstrip('.')}"

# 修正後
basename = f"{basename}.{ext.lstrip('.')}"  # .inp → .inp.md に変更
```

**cli/__init__.py** (1333行目):
```python
# 既に修正済み
_basename + "." + ext[1:]  # .inp → .inp.md に変更
```

**services/service/entry.py** (1335行目):
```python
# 既に修正済み
_basename + "." + ext[1:]  # .inp → .inp.md に変更
```

### 2. go_シリーズのbase生成ロジック改善

#### 2.1 変更内容

**従来の動作**:
- go_1_v1.inpが1つだけでも、bases/go/go_1.baseを作成していた

**新しい動作**:
- go_1_v1.inpとgo_1_v2.inpのように2つ以上のバージョンがある場合のみbases/go/go_1.baseを作成
- バージョンが1つのみの場合は、専用baseファイルを作成せず、go.baseに直接リンク

#### 2.2 修正箇所

**cli/__init__.py** (887-914行目):

```python
# バージョン数をカウントする処理を追加
go_list = list([get_basename(i) for i in go_list])  # setを使わない（カウント用）
go_list_normalized = [i.replace(f".v{get_index_and_version(i)[1]}.", "_") for i in go_list]

# バージョン数をカウント
from collections import Counter
version_count = Counter(go_list_normalized)

# 重複を除去してソート
go_list_unique = list(set(go_list_normalized))
go_list_unique = list(sorted(go_list_unique, key=lambda x: get_index_and_version(x)[0]))

go_base_list = []
for i in go_list_unique:
    # バージョンが2つ以上ある場合のみbaseファイルを作成
    if version_count[i] >= 2:
        go_base_list.append(f"{i}.base")
        _write_yaml_if_missing(...)
        base_list.append(f"{i}.base")
```

**cli/__init__.py** (189-196行目):

```python
# base_name の補正（既存ロジック踏襲）
if base_name == "go.base" and ver:
    candidate_base_name = basename.replace(f".v{ver}", "") + ".base"
    # 専用baseファイルが存在する場合のみ使用、なければgo.baseのまま
    base_dir = md_path.parent.parent / "bases"
    candidate_base_path = base_dir / "go" / candidate_base_name
    if candidate_base_path.exists():
        base_name = candidate_base_name
    # else: base_name = "go.base" のまま（サブバージョンが1つのみの場合）
```

同様の修正を **services/service/entry.py** にも適用しました。

### 3. グループ機能の追加

#### 3.1 概要

同一インデックスまたはver以外のファイル名が同じファイルをグループとして扱い、bases/group/配下にグループbaseファイルを作成します。

**グループの定義**:
- ファイル名の先頭部分（headの部分）が同じファイルをグループ化
- 例: go_1_v1.inp, go_1_v2.inp, go_2_v1.inp → グループ名は "go"
- 例: mesh_1.inp, mesh_2.inp → グループ名は "mesh"

#### 3.2 実装内容

**新規関数の追加** (cli/__init__.py, services/service/entry.py):

```python
def get_group_name(filepath: str) -> str:
    """ファイル名からグループ名を抽出（idx/verを除いた部分）"""
    if os.path.isdir(filepath):
        return ""

    basename, ext = get_basename_with_ext(filepath)
    # headを取得（例: go_1_v2 → go）
    head = basename.split("_")[0]
    return head
```

**ディレクトリ構造の追加** (cli/__init__.py:837行目, services/service/entry.py:839行目):

```python
(root / "bases" / "group").mkdir(parents=True, exist_ok=True)
```

**グループbaseファイルの生成** (cli/__init__.py:933-960行目, services/service/entry.py:935-962行目):

```python
# グループbaseファイルの生成
all_inp_files = []
for subdir in ["go", "mesh", "material", "step"]:
    all_inp_files.extend(glob.glob(str(root / "props" / "inp" / subdir / "*.md")))

# グループ名ごとにファイルをまとめる
from collections import defaultdict
group_files = defaultdict(list)
for filepath in all_inp_files:
    group_name = get_group_name(filepath)
    if group_name:
        group_files[group_name].append(filepath)

# 2つ以上のファイルがあるグループのみbaseファイルを作成
group_base_list = []
for group_name in sorted(group_files.keys()):
    if len(group_files[group_name]) >= 2:
        group_base_list.append(f"{group_name}.base")
        _write_yaml_if_missing(
            root / "bases" / "group" / f"{group_name}.base",
            _base_template(
                root / "props" / "inp",
                additional_filters=[f'file.basename.startsWith("{group_name}_")'],
                idx=False,
                ver=False,
                show_only_active=False,
            ),
        )
```

**group_index.mdの生成** (cli/__init__.py:985-989行目, services/service/entry.py:987-991行目):

```python
with open(str(root / "bases" / "group" / "group_index.md"), "w") as f:
    f.write("# グループ一覧\n\n")
    for i in group_base_list:
        f.write(f"- [[{i}]]\n")
```

#### 3.3 生成されるファイル構造

```
notes/
  bases/
    group/
      group_index.md      # グループ一覧
      go.base             # goグループのbaseファイル
      mesh.base           # meshグループのbaseファイル
      material.base       # materialグループのbaseファイル
      step.base           # stepグループのbaseファイル
```

各グループbaseファイルには、そのグループに属する全ファイルがフィルターされて表示されます。

## テスト結果

- 構文チェック: すべて正常に完了
  - cli/__init__.py
  - services/service/entry.py
  - services/parse/file_parse.py

## TODO

- [ ] 実際のプロジェクトでグループ機能が正しく動作するか確認
- [ ] Obsidian上でグループbaseファイルが正しく表示されるか確認
- [ ] ファイル名記法の変更による既存ファイルへの影響を確認

## 次のステップ

1. 実際のプロジェクトでinit_notes_treeを実行し、グループbaseファイルが正しく生成されるか確認
2. Obsidian上でグループbaseファイルを開き、フィルターが正しく機能するか確認
3. 必要に応じて、_base_template関数のadditional_filtersの記法を調整

## 関連ファイル

- cli/__init__.py
- services/service/entry.py
- services/parse/file_parse.py
- docs/status/status-015.md

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-015.md](./status-015.md)
**次回**: status-017.md (未作成)
