[← README.md](README.md)

# CONTRIBUTING.md — 開発参加ガイド

## 開発体制

- Codex と Claude Code の2交代制

---

## ブランチ命名規約

```
claude/{feature-keyword}-{hash}
```

- `feature-keyword`: statusファイルで使用する機能名と一致させる
- `hash`: セッション識別用ハッシュ

### 例

| ブランチ名 | 機能 |
|-----------|------|
| `claude/fluent-connector-Abc12` | Fluentコネクタ実装 |
| `claude/neo4j-pipeline-Xyz34` | Neo4j統合パイプライン |
| `claude/docs-restructure-Def56` | ドキュメント再編 |
| `claude/ci-setup-Ghi78` | CI/CD構築 |

---

## コミットメッセージ

```
{type}: {日本語の変更概要} (status-{NNN})
```

### type一覧

| type | 用途 |
|------|------|
| `feat` | 新機能追加 |
| `fix` | バグ修正 |
| `refactor` | リファクタリング（機能変更なし） |
| `docs` | ドキュメントのみの変更 |
| `ci` | CI/CD設定の変更 |
| `test` | テストの追加・修正 |
| `chore` | ビルド・パッケージ設定等の雑務 |

### 例

```
feat: Fluentコネクタ parse connector実装 (status-003)
fix: AbaqusパーサーのINP読み込みエラー修正 (status-004)
docs: Getting Startedセクション追加 (status-002)
```

---

## statusファイルの書き方

### ファイル名
`docs/status/status-{NNN}.md` — NNNはゼロ埋め3桁

### テンプレート

```markdown
[← README.md](../../README.md)

# status-{NNN}: {タイトル}

**日付**: YYYY-MM-DD
**バージョン**: v0.X.0

---

## 概要
{1〜2行の概要}

## 完了した作業
### 1. {作業1}
{詳細}

### 2. {作業2}
{詳細}

## 変更ファイル
| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `path/to/file` | 新規/修正/削除 | {説明} |

## TODO
- [ ] {未完了タスク}

## 確認事項・懸念
- {ユーザーへの確認事項}
```

### 粒度基準
- 1 status = 1 PR 程度
- 複数の小さな修正をまとめた場合も1 statusとして記録可

---

## テスト

```bash
pip install -e ".[dev]"
pytest --tb=short -q
```

---

## CI/CD

GitHub Actions で以下を自動実行:

| ジョブ | 内容 |
|--------|------|
| python-lint | ruff check + format check |
| python-test | pytest（コア依存のみ） |
| python-plugin-integration | プラグインentry_points検証 + 統合テスト |
| python-dashboard-e2e | Streamlitダッシュボード E2Eテスト |
