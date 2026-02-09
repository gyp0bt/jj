[READMEへ戻る](../../README.md)

# 実装状況 (status-023)

## 概要

CLIリファクタリング: cli/__init__.pyからビジネスロジックを分離し、`jj n`コマンドを`jj g notes`に統合。

## 実装内容

### 1. ファイルユーティリティの分離 (services/parse/file_utils.py)

cli/__init__.pyから以下の関数を`services/parse/file_utils.py`に移動:

```python
# 移動した関数
- normalize_extension_to_inp()  # 拡張子を正規化
- get_basename_with_ext()       # basename と拡張子を分離
- get_basename()                # basename のみ取得
- get_group_name()              # グループ名を抽出
- get_index_and_version()       # index と version を抽出
- safe_relative_path()          # 安全な相対パス生成
```

### 2. Notes関連ロジックの分離 (services/notes/__init__.py)

cli/__init__.pyから以下の関数・クラスを`services/notes/__init__.py`に移動:

```python
# 移動した関数/クラス
- NotesConfig              # Notes生成設定
- NotesService             # Notes生成サービスクラス
- safe_rglob_files()       # 再帰的ファイル収集
- safe_rglob_dirs()        # 再帰的ディレクトリ収集
- frontmatter_keys()       # frontmatterキー抽出
- base_template()          # baseテンプレート生成
- write_yaml_if_missing()  # YAML書き込み
- update_go_base()         # go.base更新
- write_frontmatter_props() # frontmatter書き込み
- update_frontmatter_props() # frontmatter更新
- clear_notes_props()      # notesディレクトリクリア
- parse_word_with_vocab()  # vocabulary解析
- get_properties_by_filepath()     # ファイルパスからプロパティ取得
- get_properties_by_inp_parameter() # inp内パラメータからプロパティ取得
- get_relations_by_inp_includes()  # includeディレクティブ解析
```

### 3. `jj n` → `jj g notes` コマンド統合

**旧コマンド（廃止予定）**:
```bash
jj n -all  # Obsidian notes生成
```

**新コマンド**:
```bash
jj g notes          # parse + export のショートカット
jj g notes --overwrite  # 既存ファイルを上書き
```

**後方互換性**:
- `jj n` を実行すると自動的に `jj g notes` にリダイレクト
- 廃止予定のメッセージを表示

```
[DEPRECATED] 'jj n' は廃止予定です。'jj g notes' を使用してください。
[INFO] 'jj g notes' への自動リダイレクト中...
```

### 4. cli/graph.py の拡張

`notes` サブコマンドを追加:

```python
def _run_notes(project_root: Path, args: argparse.Namespace) -> int:
    """notesサブコマンドを実行（parse + export のショートカット）"""
    # Step 1: parse - グラフデータ生成
    # Step 2: export - Obsidianにエクスポート
```

## テスト結果

```
42 passed in 1.24s
```

全テストがパス。

## ファイル構成の変更

```
jj/
├── services/
│   ├── parse/
│   │   ├── __init__.py      (変更: file_utils からエクスポート追加)
│   │   └── file_utils.py    (新規: ファイルユーティリティ)
│   └── notes/
│       └── __init__.py      (新規: Notes生成サービス)
├── cli/
│   ├── __init__.py          (変更: ロジック分離、jj n → jj g notes リダイレクト)
│   └── graph.py             (変更: notes サブコマンド追加)
└── docs/
    └── status/
        └── status-023.md    (新規)
```

## コマンド対応表

| 旧コマンド | 新コマンド | 状態 |
|---|---|---|
| `jj n -all` | `jj g notes` | 廃止予定（リダイレクト有） |
| `jj n init` | `jj g init` | 廃止予定（リダイレクト有） |
| `jj g parse` | `jj g parse` | 維持 |
| `jj g export` | `jj g export` | 維持 |
| - | `jj g notes` | 新規（parse + export） |

## 廃止理由

`jj n` (notes) コマンドは以下の理由で廃止予定となりました：

1. **機能の重複**: `jj g parse` + `jj g export --target obsidian` で同等の機能が実現可能
2. **グラフ中心設計への移行**: jjはグラフデータを中心に設計されており、Obsidian出力は「エクスポート先の一つ」という位置づけ
3. **コードの簡素化**: cli/__init__.pyに埋め込まれた複雑なnotes生成ロジックを、GraphService + ObsidianConnector に統一

`jj g notes` は移行期間中のショートカットとして提供されますが、将来的には `jj g parse && jj g export` の使用を推奨します。

## TODO（今後の課題）

- [ ] cli/__init__.pyの重複関数を完全に削除（現在はservices/notesからインポートしつつ、ローカル定義も残存）
- [ ] cli/__init__.pyからAbaqusジョブ関連ロジックを`services/job/`に分離
- [ ] includes関係のパフォーマンス最適化（ファイル読み込みのキャッシュ）
- [ ] 日付の検証機能追加（不正な日付の検出）
- [ ] CAEソフト別の拡張子プリセット機能
- [ ] NotesServiceをより完全に実装し、run_notes関数を置き換え

## 設計上の懸念事項

1. **cli/__init__.pyの肥大化**: 依然として1700行以上あり、さらなる分離が必要
2. **重複関数**: services/notesにロジックを移動したが、cli/__init__.pyにも同名関数が残存（インポートで上書きされる）
3. **後方互換性**: `jj n` コマンドを完全に削除するタイミングの検討が必要

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-022.md](./status-022.md)
**次回**: status-024.md (未作成)
