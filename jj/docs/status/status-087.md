[READMEへ戻る](../../README.md)

# status-087: パッケージセットアップ修正（エントリポイント・コア依存関係・packages.find）

**日付**: 2026-02-14
**担当**: Claude Code

---

## 概要

新環境で `pip install -e .` 後に `jj` コマンドが動作しない問題、および `jj init` 時に numpy/ftfy/chardet が見つからない問題を修正。

## 問題の原因

### 1. エントリポイント解決不能
- `pyproject.toml` の `[project.scripts]` が `jj = "main:main"` と定義されていた
- `main.py` はスタンドアロンモジュールだが、`[tool.setuptools.packages.find]` の `include` リストに含まれておらず、インストール後に `import main` が失敗
- `main.py` 自体が `sys.path` ハックに依存しており、パッケージインストール時に正しく機能しない設計だった

### 2. 必須依存の未同梱
- `services/parse/connectors/abaqus/__init__.py` でnumpy/ftfy/chardet がモジュールレベルimportされている
- Abaqusプラグインは `services/graph/__init__.py` → `services/sdk/plugin_registry.py` → `services/plugins/abaqus/__init__.py` の経路で **全コマンド実行時に自動ロード** される
- これらの依存は `[project.optional-dependencies].abaqus` にのみ定義されており、`pip install jj` では未インストール

### 3. shared パッケージ未同梱
- `shared/` パッケージ（Neo4jスキーマ契約等）が `[tool.setuptools.packages.find].include` に含まれておらず、`services/export/connectors/neo4j.py` からの `from shared.neo4j_schema import ...` が失敗

## 変更内容

### pyproject.toml（3箇所）

1. **エントリポイント修正**: `jj = "main:main"` → `jj = "services.cli:main"`
   - `services.cli` パッケージは `packages.find` に含まれるため確実に解決可能
   - `main.py` の `sys.path` ハックが不要になる

2. **コア依存関係追加**: chardet/ftfy/numpy を `[project.dependencies]` に移動
   - プラグイン自動ロードでモジュールレベルimportされるため、optional では不適切
   - `[project.optional-dependencies].abaqus` からは除去し、pandas/scipy のみ残存（メッシュ品質解析用）

3. **packages.find 拡張**: `shared*` を `include` リストに追加

## 変更ファイル
- `pyproject.toml`

## テスト結果
- 756テスト通過、21スキップ
- 既存失敗3件（pandas未インストールに起因、今回の変更とは無関係）
- `jj --help` 正常動作確認済み

## TODO
- `main.py` は `python main.py` での直接実行用として残存。将来的に削除を検討
- pandas/scipy が必要な pymesh 系テスト3件はオプショナルのまま（`pip install jj[abaqus]` で解消）
