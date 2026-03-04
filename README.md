# jj

CAE業務データをグラフ構造化し、検索・可視化・横断比較を可能にするPython CLIツール。

## 概要

ローカルCAEプロジェクトのフォルダ/ファイルを解析し、グラフデータとして構造化。
Streamlitダッシュボード、Obsidian Vault、Neo4j、CSV/JSONなど多彩なフォーマットにエクスポート可能。

### アーキテクチャ概要

```
ローカルCAEプロジェクト
    │
    ▼
[jj parse] ── フォルダ/ファイル解析 → グラフ構築 (.j2/storage/)
    │
    ├── [jj dashboard] ── Streamlitダッシュボード（ローカル即時確認）
    ├── [jj serve] ──── REST API (FastAPI)
    ├── [jj export --target obsidian] ── Obsidian Vault
    ├── [jj export --target neo4j] ── Neo4j Database
    └── [jj export --target csv] ── CSVエクスポート
```

### Getting Started

```bash
pip install -e ".[dev]"        # 開発用インストール（コア + テスト依存）
jj init                         # 設定ファイル初期化（.j2/config/ 生成）
jj parse                        # プロジェクトをスキャンしグラフ構築 → .j2/storage/graph.yaml
jj show --summary               # グラフのサマリー表示
jj export --target csv          # ノード属性をCSVエクスポート
```

Abaqus解析やダッシュボードを使う場合:
```bash
pip install -e ".[abaqus,dashboard]"   # Abaqus + ダッシュボード依存を追加
jj dashboard                            # Streamlitダッシュボード起動
```

テスト実行:
```bash
pytest                          # テスト実行
```

### ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [docs/roadmap.md](docs/roadmap.md) | **v0.2.0 ロードマップ**（マイルストーン・仕様書リンク） |
| [docs/status/status-index.md](docs/status/status-index.md) | v0.2.0 statusインデックス |
| [docs/README.md](docs/README.md) | ドキュメント一覧 |
| [docs/specs/](docs/specs/) | 機能ドメイン別仕様書 |
| [CLAUDE.md](CLAUDE.md) | コーディング規約・技術リファレンス |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 開発参加ガイド |

### 技術スタック

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.10+ |
| グラフ | NetworkX |
| データモデル | Pydantic |
| ダッシュボード | Streamlit |
| API | FastAPI |
| テスト | pytest |
| lint/format | ruff |

### v0.1.0 サマリー（2026-02-14）

- テスト1,002件、パーサー16+クラス、エクスポーター6種、Abaqusプラグイン完全分離、Streamlitダッシュボード稼働
- レビュー: [v0.1.0 レビュー](docs/review/review-v0.1.0.md)
