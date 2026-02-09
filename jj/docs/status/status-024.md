[READMEへ戻る](../../README.md)

# 実装状況 (status-024)

## 概要

CLIの大幅スリム化: `jj g notes`と`jj n`コマンドを完全廃止し、`file_utils.py`を`file_parse.py`に統合。
cli/__init__.pyを1752行から745行に削減（約57%削減）。

## 実装内容

### 1. `jj g notes` サブコマンドの廃止

graph.pyから以下を削除:
- `notes` サブコマンドのパーサー定義（117-133行）
- `_run_notes()` 関数（292-339行）
- `run_graph_command()` からnotesの処理分岐

**理由**: `jj g parse` + `jj g export --target obsidian` で同等の機能が実現可能なため、ショートカットコマンドとしての `jj g notes` は不要と判断。

### 2. `jj n` コマンドの完全廃止

cli/__init__.pyから以下を削除:
- notesサブコマンドのパーサー定義（約20行）
- `jj n` → `jj g notes` リダイレクト処理
- `--make-index-md-files` 旧フラグ
- notes関連のヘルパー関数多数（約550行）:
  - `_base_template()`
  - `_write_yaml_if_missing()`
  - `init_notes_tree()`
  - `_notes_paths()`
  - `_glob_prefixed_ext()`
  - `_ensure_bases_exist()`
  - `safe_rglob_files()`
  - `safe_rglob_dirs()`
  - `frontmatter_keys()`
  - `collect_keys_all()`
  - `parse_word_with_vocab()`
  - `get_properties_by_filepath()`
  - `get_properties_by_inp_parameter()`
  - `get_relations_by_inp_includes()`
  - `clear_notes_props()`
  - `run_notes()`
  - `_write_frontmatter_props()`
  - `update_frontmatter_props()`

### 3. `file_utils.py` → `file_parse.py` 統合

`services/parse/file_utils.py`を廃止し、内容を`services/parse/file_parse.py`に統合:

**移動した関数**:
```python
TARGET_EXTENSIONS              # 拡張子候補リスト
normalize_extension_to_inp()   # 拡張子を正規化
get_basename_with_ext()        # basename と拡張子を分離
get_basename()                 # basename のみ取得
get_group_name()               # グループ名を抽出
get_index_and_version()        # index と version を抽出
get_index_and_version_legacy() # レガシー実装（互換性用）
safe_relative_path()           # 安全な相対パス生成
```

**更新したファイル**:
- `services/parse/file_parse.py`: レガシー関数を末尾に追加
- `services/parse/__init__.py`: file_parseからのエクスポートに変更
- `services/parse/file_utils.py`: 削除

### 4. 不要インポートの削除

cli/__init__.pyから以下のインポートを削除:
```python
# 削除したインポート
import re
import shutil
from typing import Optional
import yaml
from config import VocabConfig, load_vocab_config
from services.parse import (
    get_basename_with_ext,
    get_group_name,
    normalize_extension_to_inp,
    safe_relative_path,
)
from services.notes import (...)  # 全削除
```

## 成果

| 項目 | Before | After | 削減率 |
|------|--------|-------|--------|
| cli/__init__.py | 1752行 | 745行 | 57% |
| notes関連関数 | 約550行 | 0行 | 100% |
| file_utils.py | 229行 | 0行（file_parse.pyに統合） | - |

## ファイル構成の変更

```
jj/
├── services/
│   ├── parse/
│   │   ├── __init__.py      (変更: file_parse からのみエクスポート)
│   │   ├── file_parse.py    (変更: file_utils の内容を統合)
│   │   └── file_utils.py    (削除)
│   └── notes/
│       └── __init__.py      (維持: services用のロジックを保持)
├── cli/
│   ├── __init__.py          (変更: 1752行→745行に削減)
│   └── graph.py             (変更: notesサブコマンド削除)
└── docs/
    └── status/
        └── status-024.md    (新規)
```

## コマンド対応表（最新）

| コマンド | 状態 | 説明 |
|---|---|---|
| `jj g init` | 維持 | 設定ファイル初期化 |
| `jj g parse` | 維持 | グラフデータ生成 |
| `jj g show` | 維持 | グラフデータ表示 |
| `jj g export` | 維持 | 外部ツールへエクスポート |
| `jj g notes` | **廃止** | parse + export のショートカット |
| `jj n` | **廃止** | Obsidian notes生成（旧） |
| `jj f` | 維持 | ファイル操作 |
| `jj r` | 維持 | コマンド実行＆ログ記録 |
| `jj submit` | 維持 | Abaqusジョブ投入 |

## 構文チェック結果

```
cli/__init__.py: OK
cli/graph.py: OK
services/parse/file_parse.py: OK
services/parse/__init__.py: OK
```

## TODO（今後の課題）

- [ ] cli/__init__.pyからAbaqusジョブ関連ロジック（submit/jcf）を`services/job/`に分離
- [ ] services/notes/__init__.pyの整理（未使用関数の削除検討）
- [ ] 単体テストの追加（file_parse.pyの統合後）
- [ ] ドキュメントの更新（docs/detail.md）

## 設計上の懸念事項

1. **services/notes/__init__.py**: cli/__init__.pyから削除したロジックの一部がservices/notes/にも存在する。将来的にはGraphService + ObsidianConnector で完結させ、services/notes/は廃止を検討。

2. **Abaqusジョブ関連**: cli/__init__.pyに残っているsubmit/jcf関連ロジック（約400行）を独立サービスに分離することで、さらに300行程度の削減が可能。

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-023.md](./status-023.md)
**次回**: status-025.md (未作成)
