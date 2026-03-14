[← README.md](../../../README.md)

# status-002: M1完了 — CLAUDE.md・docs二重管理・Getting Started・CONTRIBUTING.md・旧status削除

**日付**: 2026-02-14
**バージョン**: v0.2.0
**前status**: [status-001](status-001.md)

---

## 概要

v0.2.0 M1（基盤整備）の残タスクを完了。コーディング規約の明文化、docs二重管理体制の構築、Getting Startedセクション追加、CONTRIBUTING.md作成、旧statusファイル削除を実施。

## 完了した作業

### 1. CLAUDE.md 作成（コーディング規約の明文化）

v0.1.0レビューの改善点を分析し、ルートに `CLAUDE.md` を新設。以下の規約を列挙:

- **statusファイル粒度基準**: 1 status = 1 PR 程度に明文化
- **ブランチ命名規約**: `claude/{feature-keyword}-{hash}` に統一
- **コミットメッセージ形式**: `{type}: {日本語概要} (status-{NNN})`
- **パーサー/エクスポーター/プラグイン追加手順**: AbstractFileParser/__init_subclass__パターンの遵守方法
- **暗黙の仮定排除**: 特定CAEソフトに依存するコアロジック禁止
- **依存管理**: コア依存最小化、optional依存のグループ管理
- **テスト/lint規約**: jj(ruff/pytest)、jjrv(biome/tsc)

jjrv/CLAUDE.md もルートCLAUDE.mdへの参照 + jjrv固有コマンドに更新。

### 2. docs二重管理体制の構築

3層構成を確立:
- **ルート docs/** — 共有ドキュメント（status/review）+ docs/README.md（全リンク集）
- **jj/docs/** — jj固有（roadmap, specs, detail）
- **jjrv/docs/** — jjrv固有（RM1-6仕様書, dashboard設計）

docs/README.md を新設し、共有/jj固有/jjrv固有ドキュメントの一覧とリンクを整備。

### 3. Getting Startedセクション追加

ルートREADME.mdに「Getting Started」セクションを追加:
- jj: pip install → init → parse → show → export → dashboard の手順
- jjrv: pnpm install → dev の手順

### 4. CONTRIBUTING.md 作成

ブランチ命名規約、コミットメッセージ形式、statusファイルテンプレート、テスト・CI手順を一元化。

### 5. 旧statusファイル削除

v0.1.0 statusファイル（jj: 91件、jjrv: 61件）をjj/docs/status/およびjjrv/docs/status/から削除。アーカイブはdocs/status/archive-v0.1.0/に保管済み。

### 6. README/リンク整備

- ルートREADME.md: Getting Started追加、ドキュメント構成セクション刷新（CLAUDE.md/CONTRIBUTING.mdリンク追加）、規約セクションをCLAUDE.md参照に簡潔化
- jj/README.md: 巨大な旧statusログを削除し、v0.1.0開発サマリーに圧縮。docs/status参照を共有docsに変更
- jjrv/README.md: status参照を共有docsに変更、規約セクションをCLAUDE.md参照に変更

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `CLAUDE.md` | 新規 | プロジェクト規約・コーディングガイドライン |
| `CONTRIBUTING.md` | 新規 | 開発参加ガイド・ブランチ命名規約 |
| `docs/README.md` | 新規 | 共有ドキュメント一覧・リンク集 |
| `docs/status/status-002.md` | 新規 | 本ファイル |
| `README.md` | 修正 | Getting Started追加、ドキュメント構成刷新 |
| `jj/README.md` | 修正 | 旧statusログ削除、v0.1.0サマリー化、共有docs参照 |
| `jjrv/README.md` | 修正 | status参照更新、規約CLAUDE.md参照化 |
| `jjrv/CLAUDE.md` | 修正 | ルートCLAUDE.md参照 + jjrv固有コマンド |
| `jj/docs/status/*` | 削除 | v0.1.0旧statusファイル91件（アーカイブ済み） |
| `jjrv/docs/status/*` | 削除 | v0.1.0旧statusファイル61件（アーカイブ済み） |

## M1（基盤整備）完了状況

| タスク | 状態 |
|--------|------|
| CI/CD構築 | 完了（status-001） |
| ドキュメント再編 | 完了（本status） |
| statusアーカイブ | 完了（status-001 + 本status） |
| Getting Startedセクション | 完了（本status） |
| CONTRIBUTING.md | 完了（本status） |
| CLAUDE.md | 完了（本status） |
| jj/jjrv旧statusファイル削除 | 完了（本status） |

**M1: 基盤整備 — 全タスク完了**

## TODO（v0.2.0 M2〜M5）

- [ ] M2: Fluentコネクタ設計文書 → parse/dashboardコネクタ実装
- [ ] M3: Neo4j統合パイプライン（スキーマ確定→jjrv Neo4jクライアント）
- [ ] M4: jjrv横断ダッシュボード（Streamlit検証パターン移植→横断視認性）
- [ ] M5: runジョブ型・fileコマンド基本
