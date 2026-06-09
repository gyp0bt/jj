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
{type}: {日本語の変更概要}
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
feat: Fluentコネクタ parse connector実装
fix: AbaqusパーサーのINP読み込みエラー修正
docs: Getting Startedセクション追加
```

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
