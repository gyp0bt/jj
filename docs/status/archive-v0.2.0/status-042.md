[← status-index.md](status-index.md) | [← README.md](../../../README.md)

# status-042: プロジェクトデータディレクトリ .jj → .j2 リネーム

- **日付**: 2026-02-24
- **マイルストーン**: M1（基盤整備）
- **ブランチ**: `claude/rename-jj-to-j2-QV2ym`

---

## 概要

jujutsu VCS（jj コマンド）との名前衝突を回避するため、プロジェクトデータディレクトリを `.jj` から `.j2` にリネームした。CLIコマンド名 `jj` およびPythonパッケージ名 `jj` は据え置き。

## 変更内容

### 変更対象

| カテゴリ | ファイル数 | 概要 |
|---------|-----------|------|
| コアPythonモジュール | 15 | CONFIG_DIRNAME, storage_dirname, exclude sets, path構築 |
| 設定ファイル | 2 | .gitignore, default-config.yaml |
| テストファイル | 10 | tmp_path / ".jj" → ".j2" |
| ドキュメント | ~45 | 仕様書、roadmap、status、README |

### 主要な変更パス

- `.jj/config/` → `.j2/config/`
- `.jj/storage/` → `.j2/storage/`
- `.jj/storage/run/` → `.j2/storage/run/`
- `.jj/storage/plugin_cache/` → `.j2/storage/plugin_cache/`
- `~/.jj/secret.key` → `~/.j2/secret.key`
- `.jj/config/.credentials` → `.j2/config/.credentials`

### 変更しないもの

- `jj` CLIコマンド名
- `jj` Pythonパッケージ名
- `jj_id`, `jj_rel_id` 等のNeo4jプロパティ名
- `jjrv` 関連

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 191 files already formatted
- **pytest**: 1497 passed, 85 skipped, 24 failed（全てoptional依存によるもの: pandas/plotly/pymesh）
- `.jj` → `.j2` 変更に起因する失敗: **0件**

## 既存ユーザーへの影響

- 既に `.jj/` ディレクトリが存在するプロジェクトは、手動で `.j2/` にリネームするか、`jj init` で再初期化が必要
- `~/.jj/secret.key` も `~/.j2/secret.key` に移動が必要

## 確認事項・TODO

- [ ] 既存ユーザー向けのマイグレーション手順をREADMEに記載するか検討
- [ ] `jj init` コマンドに `.jj` → `.j2` の自動マイグレーション機能を追加するか検討
