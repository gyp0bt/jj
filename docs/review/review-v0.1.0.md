[← README.md](../../README.md)

# jj v0.1.0 レビュー — 開発フェーズ総括と次期ロードマップ

**日付**: 2026-02-14
**対象期間**: 2026-01-24 〜 2026-02-14（約3週間）
**対象モジュール**: jj（Python CLI, status-001〜089）、jjrv（Next.js Web, status-001〜060）

---

## 目次

1. [開発フェーズの変遷](#1-開発フェーズの変遷)
2. [定量的サマリー](#2-定量的サマリー)
3. [開発運用の考察](#3-開発運用の考察)
4. [機能の俯瞰評価](#4-機能の俯瞰評価)
5. [次フェーズの優先機能](#5-次フェーズの優先機能)
6. [v0.2.0ロードマップ案](#6-v020ロードマップ案)

---

## 1. 開発フェーズの変遷

### jj（Python CLI）— 89 status / 92 PR / 105 commits

| フェーズ | 期間 | status | 概要 |
|---------|------|--------|------|
| **Phase 0: 基盤構築** | 01-24 〜 02-04 | 001〜018 | プロジェクト初期化、Pydanticデータモデル(Node/Relation)、設定管理(vocab/extensions/prefixes)、runコマンド(実行ログ/差分検出/props抽出) |
| **Phase 1: graphコマンド** | 02-04 〜 02-08 | 019〜036 | `jj parse`によるフォルダスキャン→グラフ生成、Obsidianエクスポート、Abaqusコネクタ(INP解析/材料/メッシュ/差分/結果)、Daily note連携、Neo4jエクスポート基盤 |
| **Phase R: 構造改革** | 02-09 〜 02-10 | 037〜043 | graph/__init__.pyの分解（2026行→510行）、AbstractFileParser.__init_subclass__パターン確立、ProjectGraph型定義、16パーサーサブクラスへの分散、export層独立化。**MR達成（443テスト）** |
| **Phase 2: 機能拡充** | 02-10 〜 02-11 | 044〜067 | パーサー拡張(JSON/CSV/Elset/差分/キャッシュ/タイムスタンプ差分)、CLI強化(info/diff/選択記法)、エクスポート統一(AbstractExporter)、CLI→Service分離、レガシー削除 |
| **Phase 2.5: ダッシュボード** | 02-11 〜 02-13 | 068〜084 | Streamlitダッシュボード(テーブル/カード/プロット/ステータス/ギャラリー/配列プロット/物性一覧)、REST API(FastAPI 9+エンドポイント)、HTMLエクスポート、query汎用化 |
| **Phase P: プラグイン化** | 02-13 〜 02-14 | 085〜089 | SDK/CacheProviderプロトコル、entry_points動的発見、Abaqus/Obsidianプラグイン分離、パッケージセットアップ修正、Abaqusコネクター作り込み。**1002テスト到達** |

### jjrv（Next.js Web）— 60 status / ロードマップ1〜6

| フェーズ | 期間 | status | 概要 |
|---------|------|--------|------|
| **RM1: ユーザー運用** | 01-24 〜 01-25 | 001〜020 | SQLite (sql.js)、エンティティCRUD、検索/フィルタ、タグ管理、ログイン/アカウント管理 |
| **RM2/2.5: 検索・閲覧** | 01-25 〜 02-01 | 021〜041 | カード/テーブル/グラフ(D3-Force)/ダイアグラム、詳細ビュー、Bodyプレビュー、Import/Export設計 |
| **RM3: 操作性** | 02-01 〜 02-04 | 042〜048 | インライン編集、検索条件保存、ファイル名/拡張子表示、ドキュメント集約 |
| **RM4/5: 本番運用** | 02-04 〜 02-06 | 049〜057 | 階層折りたたみ、プレビュー、レポジトリ階層制約、バリデーション |
| **RM6: jj統合設計** | 02-06 〜 02-08 | 058〜060 | GitHub形式レポジトリ構造、サイドバーツリー、jj統合ロードマップ/ダッシュボード設計（未実装） |

### 開発フェーズの転換点

1. **Phase R（構造改革）**: graph/__init__.pyに全ロジックが集中し背反が続出した問題を、AbstractFileParserパターンで根本解決。これ以降のパーサー追加がプラグイン的に可能になり開発速度が向上した。**最も重要な設計判断**。
2. **Phase 2.5（ダッシュボード）**: CLIのみだった出力がStreamlit/APIで視覚的に利用可能になり、CAE業務での実用性が飛躍的に向上。
3. **Phase P（プラグイン化）**: CacheProvider/entry_pointsによるAbaqus/Obsidianの完全分離。他CAEソフト対応への拡張基盤を確立。
4. **jjrv RM6（統合設計）**: mat-db→jjrvリネームとNeo4j経由統合の設計完了。ただし**実装は未着手**。

---

## 2. 定量的サマリー

### jj

| 指標 | 値 |
|------|-----|
| テスト数 | 1,002件（59スキップ） |
| statusファイル | 89件 |
| PR/マージ | 92件 |
| 仕様書 | 11件（specs/01〜11） |
| パーサークラス | 16+（AbstractFileParserサブクラス） |
| エクスポーター | 6種（Obsidian/Neo4j/Cypher/CSV/JSON/DashboardJSON） |
| CLIコマンド | parse/show/info/diff/export/dashboard/serve/run/init/credential |
| 依存グループ | 8（コア/abaqus/dashboard/api/neo4j/ssh/dev/all） |

### jjrv

| 指標 | 値 |
|------|-----|
| statusファイル | 60件 |
| ロードマップ | 6段階（RM1完了〜RM6設計済み） |
| UIコンポーネント | 20+（EntityCard/EntityGraph/SearchBar/BatchEditor等） |
| ページ | 5（search/register/view/dev/login） |
| データソース | SQLite (sql.js)、Neo4j接続は設計のみ |

---

## 3. 開発運用の考察

### 3-1. 効果的だった点

#### (a) statusファイルによる引き継ぎプロトコル

Codex/Claude Code 2交代制において、status-{index}.mdの連番管理は極めて有効だった。

- **変更内容の追跡性**: 各statusにコミットメッセージ・変更ファイル・テスト結果が記録されており、前任者の作業を数分で把握可能
- **TODO連鎖**: 未完了TODOが次のstatusに引き継がれ、タスク漏れを防止
- **コミットとの整合**: statusの番号がコミットメッセージに明記され（例: `(status-089)`）、git log → status → 詳細の導線が確立

#### (b) 抽象パーサーパターン（__init_subclass__）

Phase Rで導入したAbstractFileParser自動登録パターンは、以降のすべての機能追加の速度を支えた。

- パーサー追加がファイル1つで完結（既存コードへの変更不要）
- priority属性による実行順序制御で、パーサー間の依存関係を明示的に管理
- 同パターンをAbstractExporter、DashboardPageConnectorにも適用し、一貫したプラグインアーキテクチャを確立

#### (c) テスト駆動のリファクタリング

構造改革時に既存テスト（396件→443件）を壊さず完遂。以降もテスト数を一貫して増加させ、1,002件まで積み上げた。

- テストアセット（shared/tests/test_asset1/）を共有し、E2Eテストの基盤が安定
- 各パーサーの単体テストにより、リグレッションの即時検出が可能

#### (d) ドキュメント先行設計

仕様書（specs/01〜11）とロードマップが実装より先に作成され、設計判断が文書化されている。これにより交代するAIアシスタント間で方針のブレが最小化された。

### 3-2. 改善すべき点

#### (a) statusファイルの粒度不均一と検索コスト

**問題**: 89件（jj）＋60件（jjrv）＝149件のstatusが蓄積。全件読み込みはトークン消費が甚大であり、新規エージェントの立ち上がりコストが高い。

**根拠**:
- review-00（jjrv）が指摘した通り「statusファイル全読みの回避」が課題
- jjrvではstatus-indexを導入したが、jj側には存在しない
- statusの粒度が1バグ修正から大規模リファクタリングまでバラバラ

**改善案**:
- jj側にもstatus-index.mdを導入し、フェーズ単位の要約を維持
- v0.1.0リリースでstatusをアーカイブし、v0.2.0はstatus-001から再開
- statusの粒度基準を明文化（1 status = 1 PR程度）

#### (b) jjとjjrvのstatus/docs体系の不統一

**問題**: jjのstatusは `jj/docs/status/` に、jjrvは `jjrv/docs/status/` にあるが、プロジェクト横断のstatusが存在しない。READMEのバックリンク記法も異なる。

**改善案**:
- プロジェクトルートに `docs/` を設け、横断的な文書（レビュー、ロードマップ）を配置
- 各モジュールのstatusは現行のまま維持し、ルートdocsにサマリーのみ集約

#### (c) ブランチ命名の無秩序

**問題**: 多くのブランチが `claude/setup-project-docs-*` という汎用名で、内容との対応が不明瞭。PRタイトルは適切だがブランチ名では何が変更されたか読み取れない。

**改善案**:
- ブランチ命名規約を `claude/{feature-keyword}-{hash}` に統一
- feature-keywordをstatusで使用している機能名と一致させる

#### (d) jjrv側の開発停滞

**問題**: jjrvはRM6（jj統合）の設計が完了したが、実装は完全に未着手。2026-02-08のstatus-060以降、jjrv側のコミットがない。jj側のStreamlitダッシュボードと機能的に重複する部分（テーブル/グラフ/検索）が出始めている。

**整理（決定事項）**:
- **jj dashboard（Streamlit）はjjrvのレポジトリビューの先駆け軽量検証**という位置づけ。単一プロジェクト内の即時確認に特化し、プロトタイプとしての役割を果たした
- **jjrvがダッシュボードの本番実装**。Streamlitで検証した可視化パターン（配列プロット/物性一覧/ジョブサマリー等）をjjrvに洗練移植し、さらにレポジトリ・ノード・リレーションの横断視認性を付加する
- Streamlitは開発期のクイック確認ツールとして残すが、機能追加のメインストリームはjjrvに移行する

#### (e) テストの環境依存性

**問題**: 59件のスキップはpandas/pymesh/streamlit未インストール環境に起因。CIが存在せず、テストはローカル手動実行のみ。

**改善案**:
- GitHub Actionsで最小CI（pytest `.[dev]`）を構築
- optional依存のテストはCI matrixで分離実行

---

## 4. 機能の俯瞰評価

### 4-1. CAE業務従事者の思考をシームレスにできるか？

#### 現状の強み

CAE業務の典型ワークフロー「条件設定→計算実行→結果確認→条件変更→再計算」に対し、jjは以下の対応を実現している：

| CAE業務の思考 | jjの対応機能 | 評価 |
|--------------|-------------|------|
| 「このモデルでどの材料を使っているか」 | abaqus_material Node + uses_material relation | ○ 実用レベル |
| 「前バージョンから何が変わったか」 | version_diff Node + diff_from/diff_to relation | ○ キーワードブロック単位で差分表示 |
| 「計算は正常に終わったか」 | .sta/.msg/.dat解析 → analysis_status/warning/error | ○ ダッシュボードでジョブサマリー可視化 |
| 「メッシュ品質は問題ないか」 | pymesh統合 → メッシュ/Elset品質サマリー | ○ ダッシュボードで一覧表示 |
| 「結果の時刻歴を比較したい」 | CsvArrayParser → 配列プロットページ | ○ グリッド比較+重ね書き |
| 「このパラメータで何ケース走らせたか」 | props自動抽出 + index_group Node | ○ テーブルでフィルタ・ソート |
| 「レポートに貼る図を出したい」 | 保存済みビュー + HTMLエクスポート | ○ スタンドアロンHTML出力 |
| 「過去の類似案件を探したい」 | - | △ jjrv統合未実装。Streamlitは単一プロジェクト内のみ |
| 「チームメンバーに計算状況を共有したい」 | jj serve (REST API) | △ APIは動作するが、UIは単一ユーザー前提 |
| 「テンプレートから新しい計算を作りたい」 | - | × fileコマンド凍結中 |

#### 評価

**単一プロジェクト内のAbaqus業務については、解析→可視化→比較のフローがほぼシームレスに実現されている。** 特にStreamlitダッシュボードの配列プロット・物性一覧・ジョブサマリーはCAEエンジニアの日常的な確認作業を直接支援する。

**不足しているのはプロジェクト横断の検索・再利用と、計算投入（fileコマンド/runジョブ型）の自動化**。CAE業務では「過去の類似ケースを探して流用する」思考が頻繁に発生するが、現状ではプロジェクト単位でのグラフ構築にとどまっている。

### 4-2. レポジトリを見たときに5分以内に概要を把握できるか？

#### 評価基準と判定

| 観点 | 判定 | コメント |
|------|------|---------|
| プロジェクトの目的 | ○ | ルートREADMEに「CLIベースのグラフデータ構築ツール」と明記 |
| アーキテクチャ全体像 | ○ | jj/README.mdにディレクトリ構成・データモデル・コマンド一覧が充実 |
| インストール方法 | ○ | 依存グループ別のpipコマンドが明記 |
| テストの実行方法 | ○ | READMEにpytest手順あり |
| 現在の開発状況 | △ | READMEの「最新ステータス」セクションはあるが、status-089を読む必要がある |
| 仕様一覧と優先度 | △ | roadmap.mdは詳細だが722行と長大。フェーズ完了/未完了の見通しに時間がかかる |
| jjとjjrvの関係 | × | ルートREADMEの記述が最小限。統合のアーキテクチャ図がない |
| 次に何をすべきか | × | roadmapの未完了項目が多く、優先度の判断が困難 |

#### 改善案

- ルートREADMEに**アーキテクチャ図**（ASCII/Mermaid）を追加
- **「Getting Started in 5 min」セクション**を追加（目的→インストール→最初のparse→ダッシュボード起動）
- roadmapに**v0.1.0完了マーカー**を明記し、以降の機能は「v0.2.0 計画」として分離

### 4-3. 類似案件にどの程度の労力で流用できるか？

#### 流用可能な要素

| 要素 | 流用コスト | 条件 |
|------|-----------|------|
| コアデータモデル(Node/Relation/GraphModel) | 低 | そのまま流用可能 |
| AbstractFileParser/AbstractExporter | 低 | パターンとして即座に利用可能 |
| ProjectGraph＋ディレクトリスキャン | 低 | 任意のフォルダ構造に適用可能 |
| vocab/config機構 | 低 | yaml設定でドメイン固有語彙を定義するだけ |
| Streamlitダッシュボード基盤 | 中 | DashboardDataProvider/DashboardPageConnectorの汎用部分は流用可能。Abaqus固有部分はコネクタ分離済み |
| Abaqusパーサー群 | 高 | Abaqus固有。ただしプラグイン化済みなので「入れ替え」で対応可能 |
| jjrv (Next.js) | 高 | mat-db由来のSQLite/エンティティCRUDはCAE非依存だが、UIカスタマイズが必要 |

#### 評価

**プラグインアーキテクチャの確立により、新しいCAEソフト対応は「コネクタ追加」で実現できる設計になっている。** `parse/connectors/{solver}/` にパーサークラスを追加し、`dashboard/connectors/{solver}.py` にダッシュボードページを追加するだけで拡張可能。pyproject.tomlのentry_pointsとoptional-dependenciesも整備済み。

ただし、**実際に2つ目のコネクタ（Fluent/LS-DYNA等）を実装した実績がなく、汎用性は設計上の想定にとどまる**。初回の流用時に「Abaqus前提で書かれた暗黙の仮定」が発覚するリスクがある。

---

## 5. 次フェーズの優先機能

### 優先度基準

- **P0（必須）**: v0.2.0の価値提案に不可欠。これがなければリリースの意味が薄い
- **P1（推奨）**: ユーザー体験を大幅に改善。余力があれば実装
- **P2（将来）**: v0.3.0以降に先送り可能

### 機能一覧

| # | 機能 | 対象 | 優先度 | 理由 |
|---|------|------|--------|------|
| F1 | **プロジェクト横断検索基盤** | jj+jjrv | P0 | 「過去の類似案件を探す」はCAE業務の最頻思考。現状は単一プロジェクトに閉じている |
| F2 | **jj → Neo4j → jjrv パイプラインの実装** | 全体 | P0 | jjrv統合ロードマップ（RM6）の実装。F1の前提条件 |
| F3 | **Fluentコネクタ実装（pyansys経由）** | jj | P0 | プラグインアーキテクチャの実証。pyansysライセンス認証が制約（深入り禁止、トライ＆フォールバック方針） |
| F4 | **CI/CD構築** | 全体 | P0 | 1,002テストをローカル手動実行のみは持続不可能 |
| F5 | **ドキュメント構造の整理** | 全体 | P0 | status アーカイブ、ルートREADME強化、5分把握の実現 |
| F6 | **runコマンドのジョブ型実装** | jj | P1 | Abaqusジョブ投入→監視→結果取得のワークフロー自動化 |
| F7 | **fileコマンドの基本実装** | jj | P1 | テンプレート生成、リネーム、ファイル操作。計算準備の自動化 |
| F8 | **STAパース拡張（カットバック/インクリメント）** | jj | P1 | 収束情報はCAE業務で頻繁に確認する |
| F9 | **jjrvダッシュボード洗練（Streamlit検証パターンの移植）** | jjrv | P1 | Streamlitで検証済みの配列プロット/物性一覧/ジョブサマリーをjjrvに移植・洗練 |
| F10 | **config.yaml拡張（配列スライス/材料タイプ定義）** | jj | P2 | iso/aniso/orthoの材料特性カラム定義。専門性が高い |
| F11 | **ODB連携** | jj | P2 | Abaqus結果ファイルの直接読み込み。Python 3.10対応が前提 |
| F12 | **3Dレンダラー** | jjrv | P2 | review-00の評価通り、デモ価値は高いが実務への寄与は限定的 |

---

## 6. v0.2.0ロードマップ案

### テーマ: 「単一プロジェクト → 複数プロジェクト横断」

v0.1.0が「1つのCAEプロジェクトのグラフ化と可視化」を実現したのに対し、v0.2.0は「複数プロジェクトの横断検索・比較・再利用」を目指す。

### マイルストーン

```
M1: 基盤整備（F4, F5）
 │  CI/CD構築、ドキュメント再編、statusアーカイブ
 │
M2: Fluentコネクタ（F3）
 │  プラグインアーキテクチャの実証（pyansys経由、ライセンス認証は深入り禁止）
 │  Fluent parse connector + dashboard connector
 │
M3: Neo4j統合パイプライン（F2）
 │  jj export --target neo4j → Neo4j → jjrv参照 の実稼働
 │  データソース抽象化層（SQLite/Neo4j両対応）
 │
M4: jjrv横断ダッシュボード（F1, F9）
 │  jjrvレポジトリダッシュボード実装（Streamlit検証パターンの洗練移植）
 │  レポジトリ・ノード・リレーションの横断視認性
 │
M5: ワークフロー自動化（F6, F7）
    runジョブ型実装、fileコマンド基本実装
```

### 各マイルストーンの詳細

#### M1: 基盤整備

| タスク | 内容 | 成果物 |
|--------|------|--------|
| CI/CD構築 | GitHub Actions でpytest/biome lint/build を自動実行 | `.github/workflows/ci.yml` |
| ドキュメント再編 | ルートREADMEにアーキテクチャ図追加、Getting Started セクション | `README.md` 更新 |
| status アーカイブ | v0.1.0のstatus-001〜089を`docs/status/archive-v0.1.0/`に移動。v0.2.0はstatus-001から再開 | ディレクトリ移動 |
| jj status-index導入 | jj側にstatus-index.mdを新設 | `jj/docs/status/status-index.md` |
| ブランチ命名規約 | CONTRIBUTING.mdにブランチ命名規約を記載 | `CONTRIBUTING.md` |

#### M2: Fluentコネクタ

**対象**: Fluent (.cas.h5/.dat) — pyansys経由

**pyansysライセンス制約**:
- pyansys（PyFluent/PyMAPDL等）はAnsysライセンスサーバーへの認証が必要
- ライセンス認証ロジックは複雑で環境依存性が高いため、**深入りしない方針**
- 方針: トライ→認証失敗時はgraceful fallback（テキストベースの.datパース等に切り替え）
- テスト環境ではpyansys非依存のテキストパーサーのみをCIで実行

| タスク | 内容 | 成果物 |
|--------|------|--------|
| Fluent設計文書 | .cas.h5/.datの構造調査、pyansysのReader API調査、フォールバック設計 | `jj/docs/specs/12-fluent-connector.md` |
| parse connector実装 | `services/plugins/fluent/` にパーサー群を実装（pyansys版 + テキストフォールバック版） | パーサークラス群 |
| dashboard connector実装 | `services/dashboard/connectors/fluent.py` にダッシュボードページを追加 | ダッシュボードコネクタ |
| pyproject.toml拡張 | `[project.optional-dependencies]` に `fluent = ["ansys-fluent-core"]` を追加 | pyproject.toml |
| コア層の暗黙的Abaqus前提の除去 | 2つ目のコネクタ実装で発覚する問題の修正 | コア層修正 |

#### M3: Neo4j統合パイプライン

| タスク | 内容 | 成果物 |
|--------|------|--------|
| Neo4jスキーマ確定 | jj Nodeとjjrv StringEntityのマッピング確定 | スキーマ文書 |
| ID体系統一 | int → string変換ルール（"jj-{id}"プレフィックス等） | 設計文書 + 実装 |
| jjrv Neo4jクライアント | `neo4j-driver` パッケージ導入、IEntityRepository実装 | `src/lib/datasource/neo4j-*.ts` |
| データソース切替 | 環境変数/UIでSQLite↔Neo4j切替 | 設定UI + factory |

#### M4: jjrv横断ダッシュボード

**位置づけ**: jj dashboard（Streamlit）で軽量検証した可視化パターンをjjrvに洗練移植し、レポジトリ・ノード・リレーションの横断視認性を実現する。

| タスク | 内容 | 成果物 |
|--------|------|--------|
| jjrvレポジトリ一覧 | `/repos` ページ（カード形式一覧） | Reactコンポーネント |
| レポジトリ詳細 | ファイルブラウザ、README表示 | ページコンポーネント |
| Streamlit検証パターンの移植 | 配列プロット/物性一覧/ジョブサマリーをjjrvに洗練移植 | ダッシュボードページ群 |
| ノード・リレーション横断ビュー | 複数レポジトリ間でノード/リレーションを横断検索・比較 | 検索UI + Cypherクエリ |
| グラフトラバーサル検索 | N親等以内のノード近傍検索 | Cypherクエリ |

#### M5: ワークフロー自動化

| タスク | 内容 | 成果物 |
|--------|------|--------|
| runコマンド ジョブ型 | `jj r --mode=job` でAbaqusジョブ投入 | RunCommandService拡張 |
| fileコマンド基本 | テンプレート生成、リネーム | FileCommandService |
| リモート実行統合 | `jj r --remote` でSSH経由実行 | lib/file活用 |

### 推奨実装順序と依存関係

```
M1（基盤整備）──→ M2（2つ目のコネクタ）
       │
       └──→ M3（Neo4j統合）──→ M4（横断検索）
                                     │
M5（ワークフロー自動化） ←──────────┘
```

M1は他の全てに先行する。M2とM3は並行可能（jjとjjrvの片方ずつ実施の原則に適合）。M4はM3の完了が前提。M5はM4と並行可能。

---

## 付録: 決定事項と残課題

### 決定事項（2026-02-14）

1. **2つ目のコネクタ → Fluent**: pyansys経由。ライセンス認証は深入りせず、トライ＆フォールバック方針
2. **jjrv = ダッシュボードの本番実装**: jj dashboard（Streamlit）は先駆け軽量検証。jjrvがダッシュボードを洗練し、レポジトリ・ノード・リレーションの横断視認性を付加する
3. **Streamlitは開発期クイック確認ツールとして残存**: 機能追加のメインストリームはjjrvに移行

### 残課題

1. **statusアーカイブのタイミング**: v0.1.0タグ付与後に即アーカイブするか、移行期間を設けるか
2. **CI環境**: GitHub Actions / GitLab CI のどちらを使用するか。neo4j/docker-compose.ymlのCI統合方法
3. **pyansysの利用可能範囲**: ライセンスなし環境でどこまでのデータ読み出しが可能か（.cas.h5のテキスト部分のみ？）
4. **Neo4j ID体系**: jj(int) → jjrv(string) の変換ルール確定

---

## 関連ドキュメント

- [jj README](../../jj/README.md)
- [jjrv README](../../jjrv/README.md)
- [jj ロードマップ](../../jj/docs/roadmap.md)
- [jjrv ロードマップ6](../../jjrv/docs/spec-roadmap6.md)
- [jjrv レビュー00](../../jjrv/docs/review/review-00.md)
- [jj status-089](../../jj/docs/status/status-089.md)
- [jjrv status-060](../../jjrv/docs/status/status-060.md)
