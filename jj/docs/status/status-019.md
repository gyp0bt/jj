[READMEへ戻る](../../README.md)

# 実装状況 (status-019)

## 概要

`jj g` (graph) コマンドの実装と、cli.pyからのビジネスロジック分離を開始しました。また、`relative_to`のWindows対応問題を修正し、Obsidianコネクタを独立したモジュールとして切り出しました。

## 実装内容

### 1. GraphService の実装

**ファイル**: `services/graph/__init__.py`

プロジェクトフォルダのスキャンとグラフデータ管理を担当するサービスを実装しました。

**主要機能**:
- `scan_files()`: プロジェクト配下のファイルをスキャン
- `file_to_node()`: ファイルをNodeに変換
- `parse_project()`: プロジェクト全体をパースしてGraphModelを生成
- `load()` / `save()`: グラフデータの読み込み/保存
- `summary()`: グラフのサマリー生成

**Windows対応**: `_safe_relative_path()`メソッドでPOSIX形式のパスを生成

### 2. jj g コマンドの実装

**ファイル**: `cli/graph.py`

CLIレイヤーを担当し、ビジネスロジックはすべて`services/graph/`から呼び出す設計です。

**サブコマンド**:
```bash
jj g parse          # プロジェクトをスキャンしてグラフデータを生成
jj g show           # グラフデータを表示
jj g show --summary # サマリーのみ表示
jj g export         # Obsidian等にエクスポート
```

### 3. Obsidianコネクタの分離

**ファイル**: `services/connectors/obsidian.py`

グラフデータをObsidian向けにエクスポートする機能を独立したコネクタとして実装しました。

**重要な命名規則**:
| 対象 | プレフィックス | 例 |
|------|---------------|-----|
| 実ファイル | なし | `go_test_v1.inp` |
| Obsidianファイル | `O-` | `O-go_test_v1.inp.md` |
| ディレクトリ | なし | `notes/props/inp/go/` |

**提供関数**:
```python
to_obsidian_filename("go_test_v1.inp")  # → "O-go_test_v1.inp.md"
from_obsidian_filename("O-go_test_v1.inp.md")  # → "go_test_v1.inp"
to_obsidian_link("go_test_v1.inp")  # → "[[O-go_test_v1.inp]]"
get_directory_for_type("O-go")  # → "go"（O-を除去）
```

### 4. relative_toのWindows対応修正

**修正箇所**:
- `cli/__init__.py`: `safe_relative_path()`関数を追加（1095行目）
- `services/service/entry.py`: 同様の関数を追加（1106行目）
- `services/run/__init__.py`: try-exceptでValueErrorをハンドリング

**修正内容**:
```python
def safe_relative_path(file_path: Path, base_path: Path | None = None) -> str:
    """Windowsでも安全に相対パスを生成（POSIX形式で返す）"""
    base = base_path or Path.cwd()
    try:
        resolved_file = file_path.resolve()
        resolved_base = base.resolve()
        rel = resolved_file.relative_to(resolved_base)
        return rel.as_posix()  # 常にPOSIX形式
    except ValueError:
        return file_path.as_posix()
```

### 5. テストの追加

**ファイル**: `tests/test_obsidian_connector.py`

O-プレフィックス処理のテスト12件を追加し、すべてパスしました。

## ファイル構成の変更

```
jj/
├── cli/
│   ├── __init__.py  (変更: jj gコマンド統合、safe_relative_path追加)
│   └── graph.py     (新規: jj gコマンドのCLIレイヤー)
├── services/
│   ├── graph/
│   │   └── __init__.py  (新規: GraphService)
│   ├── connectors/
│   │   ├── __init__.py  (新規)
│   │   └── obsidian.py  (新規: ObsidianConnector)
│   ├── service/
│   │   └── entry.py     (変更: safe_relative_path追加)
│   └── run/
│       └── __init__.py  (変更: relative_toのエラーハンドリング)
└── tests/
    └── test_obsidian_connector.py  (新規)
```

## テスト結果

```
$ python -m pytest tests/test_obsidian_connector.py -v
12 passed in 0.35s
```

```
$ python main.py g parse
プロジェクトをスキャン中: /home/user/jj
=== スキャン完了 ===
ノード数: 82
保存先: /home/user/jj/.jj/storage/graph.yaml
```

## TODO

- [ ] cli/__init__.pyから残りのビジネスロジックを分離（n, f, submit等）
- [ ] jj g コマンドでファイルタイプを正しく認識するよう拡張
- [ ] リレーション生成機能の実装（includesなど）
- [ ] Obsidianコネクタをjj nコマンドから呼び出すよう統合
- [ ] 既存のjj nコマンドとjj gコマンドの機能統合を検討

## 設計上の懸念事項

1. **cli/__init__.pyの肥大化**: 現在1800行を超えており、段階的にservicesへの分離が必要
2. **SSH設定の必須化**: jj gコマンドはSSH機能を使わないが、cli/__init__.pyのインポート時に設定ファイルが必要になる問題あり。遅延インポートの検討が必要

## 次のステップ

1. Obsidianコネクタをjj gコマンドの`export`サブコマンドで使用できることを確認
2. jj nコマンドのビジネスロジックをservices/noteに分離
3. 段階的にcli/__init__.pyをスリム化

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-018.md](./status-018.md)
**次回**: status-020.md (未作成)
