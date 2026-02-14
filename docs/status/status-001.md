[← README.md](../../README.md)

# status-001: v0.2.0 開始 — 基盤整備・CI構築・docs共有化・statusアーカイブ

**日付**: 2026-02-14
**バージョン**: v0.2.0
**前バージョン最終status**: [status-index-v0.1.0](status-index-v0.1.0.md)

---

## 概要

v0.1.0を区切り、v0.2.0の開発基盤を整備した。

## 完了した作業

### 1. v0.1.0レビュー・v0.2.0ロードマップ案

[review-v0.1.0.md](../review/review-v0.1.0.md) を作成。開発フェーズ変遷の整理、開発運用の考察、機能評価、優先機能(F1〜F12)、v0.2.0ロードマップ案(M1〜M5)を策定。

### 2. CI/CD構築

`.github/workflows/ci.yml` を新設:

| ジョブ | 内容 |
|--------|------|
| python-lint | ruff check + format check |
| python-test | pytest (コア依存) |
| ts-lint | biome check |
| ts-typecheck | tsc --noEmit |
| ts-build | next build |

`jj/pyproject.toml` に `[tool.ruff]` セクション追加（E/W/F/I/UP/B/SIM/RUF）。

### 3. docs共有化

このフェーズから `docs/` をjj/jjrv共有とする:
- `docs/review/` — レビュー文書
- `docs/status/` — 共有statusファイル（v0.2.0〜）
- `docs/status/archive-v0.1.0/` — v0.1.0のstatus全件（jj: 90件、jjrv: 61件）
- `docs/status/status-index-v0.1.0.md` — v0.1.0全statusのインデックス

### 4. statusアーカイブ

v0.1.0のstatusファイル（jj: 001〜090、jjrv: 001〜060）をインデックス作成後にアーカイブ。フェーズ単位のサマリーと転換点を記録。

### 5. 方針決定

- **Fluentコネクタ**: pyansys経由、ライセンス認証は深入り禁止
- **jjrv**: Streamlitダッシュボードの先駆け検証→jjrvが本番ダッシュボード
- **docs共有**: このフェーズからdocsをjj/jjrv共有

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `docs/review/review-v0.1.0.md` | 新規 | v0.1.0レビュー・v0.2.0ロードマップ案 |
| `docs/status/status-index-v0.1.0.md` | 新規 | v0.1.0全statusインデックス |
| `docs/status/archive-v0.1.0/` | 新規 | v0.1.0 statusファイルアーカイブ（151件） |
| `docs/status/status-001.md` | 新規 | 本ファイル（v0.2.0最初のstatus） |
| `.github/workflows/ci.yml` | 新規 | CI構成（Python + TypeScript） |
| `jj/pyproject.toml` | 修正 | ruff設定追加 |
| `README.md` | 修正 | アーキテクチャ図・v0.1.0サマリー・共有docs構成 |
| `jj/README.md` | 修正 | status-090追記 |
| `jj/docs/roadmap.md` | 修正 | v0.1.0完了マーカー |

## TODO（v0.2.0 M1残タスク）

- [ ] Getting Startedセクションをルートまたはjj READMEに追加
- [ ] CONTRIBUTING.md（ブランチ命名規約）
- [ ] jj側の旧statusファイル群を削除（アーカイブ済み）
- [ ] jjrv側の旧statusファイル群を削除（アーカイブ済み）

## TODO（v0.2.0 M2〜M5）

- [ ] M2: Fluentコネクタ設計文書 → parse/dashboardコネクタ実装
- [ ] M3: Neo4j統合パイプライン（スキーマ確定→jjrv Neo4jクライアント）
- [ ] M4: jjrv横断ダッシュボード（Streamlit検証パターン移植→横断視認性）
- [ ] M5: runジョブ型・fileコマンド基本
