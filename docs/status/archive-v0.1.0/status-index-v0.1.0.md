[← README.md](../../README.md)

# Status Index — v0.1.0 (2026-01-24 〜 2026-02-14)

> このファイルはv0.1.0の全statusファイルのインデックス。個別ファイルは `archive-v0.1.0/` に格納。

---

## jj（Python CLI）: status-001〜090

### Phase 0: 基盤構築（status-001〜018, 01-24）

プロジェクト初期化、Pydanticデータモデル(Node/Relation)、設定管理(vocab/extensions/prefixes)、runコマンド(実行ログ/差分検出/props抽出)。

| # | 概要 |
|---|------|
| 001 | プロジェクト初期化、README/roadmap/status/.jj構造整備 |
| 002〜010 | run機能設計、Node/Relation YAMLスキーマ、config管理、submit→run移行 |
| 011〜018 | runコマンド拡張（実行ログ/差分検出/props自動抽出/daily note連携） |

### Phase 1: graphコマンド（status-019〜036, 02-04〜02-08）

`jj parse`によるフォルダスキャン→グラフ生成、Obsidianエクスポート、Abaqusコネクタ(INP解析/材料/メッシュ/差分/結果)。

| # | 概要 |
|---|------|
| 019〜024 | graphコマンド基盤、フォルダスキャン→Node/Relation生成 |
| 025 | Phase 2 Abaqusコネクター強化（グラフ機能作り込み） |
| 026 | パスパース・型判定バグ修正（Windows/Linux対応） |
| 027 | Obsidianエクスポート改善 + Abaqusコネクタ(.msg解析) |
| 028〜031 | Abaqus解析強化（.sta/.msg/.dat、材料/メッシュ/include） |
| 032 | CLI省略記法、info/diff/include伝搬/daily解析、Obsidian強化 |
| 033 | Daily紐付け、verbose_name、材料プロパティ、Obsidianタグ |
| 034 | メッシュキーワード要約（Node/Element/Nset/Elset） |
| 035 | ダッシュボードアーキテクチャ設計・ロードマップ策定 |
| 036 | jjrv統合設計（jj × jjrv × Neo4j） |

### Phase R: 構造改革（status-037〜043, 02-08〜02-10）

graph/__init__.py分解（2026行→510行）、AbstractFileParser.__init_subclass__パターン確立、16パーサーへ分散。**最重要転換点**。

| # | 概要 |
|---|------|
| 037 | Neo4jエクスポート実装 |
| 038 | parse exportバグ修正 + jjrv統合ロードマップ整備 |
| 039 | parseタグ振り・verbose_name改善・Node方針変更 |
| 040 | pymesh移動・jj info強化・credential管理 |
| 041 | **services構造改革ロードマップ根本改変** |
| 042 | **Phase R1-R3完了: 抽象パーサーパイプライン確立** |
| 043 | **Phase R4-R6完了: services構造リファクタリング完了** |

### Phase 2: 機能拡充（status-044〜067, 02-10〜02-12）

パーサー拡張、CLI強化、エクスポート統一(AbstractExporter)、レガシー削除。

| # | 概要 |
|---|------|
| 044 | NO_NODE_EXTENSIONS、materialパーサーvocab、ディレクトリ階層relation、JSONプロパティパーサー |
| 045 | CLIビジネスロジックのservices.service分離 |
| 046 | warning/error重複排除、cpu_time修正、Obsidian directory修正 |
| 047 | 共通選択コマンド・jj info拡張・CSV改善・vocab一括置換 |
| 048 | vocab統合修正・エクスポート改善・parse --full/--lite |
| 049〜055 | Abaqus解析強化（差分、include、Elset、キャッシュ） |
| 056〜059 | Obsidian全ノード出力・Include解決・材料relation・パースエラー修正 |
| 060 | パーサーキャッシュ基盤実装、DashboardDataProvider開始 |
| 061 | タイムスタンプ差分パース |
| 062 | Elset品質統計・ABQDataキャッシュ永続化 |
| 063 | Export基盤整備(AbstractExporter)・キャッシュクリーンアップ |
| 064 | エクスポートロジック統一・3層Canvas |
| 065 | CLIレジストリディスパッチ・Obsidianプラグイン構成 |
| 066 | Obsidian Vault自動セットアップ |
| 067 | レガシーコード削除・Vault設定config.yaml駆動化 |

### Phase 2.5: ダッシュボード（status-068〜084, 02-12〜02-13）

Streamlitダッシュボード、REST API(FastAPI)、配列プロット、物性一覧、HTMLエクスポート。

| # | 概要 |
|---|------|
| 068 | **Streamlitダッシュボード・REST API実装**（テーブル/カード/プロット/ステータス） |
| 069 | AgGrid・画像ギャラリー・自動リフレッシュ |
| 070 | ABQData pickle失敗バグ修正 |
| 071 | config駆動カラム・フィルタ永続化・ギャラリーNxM・プロット軸設定 |
| 072 | activeフィルタバグ修正・保存済みビュー機能 |
| 073 | ギャラリーgroupby・float指数表示・vocab順カラム |
| 074 | **CSVパース配列取り込み・配列プロット・物性一覧** |
| 075 | 物性カーブ列名config駆動化 |
| 076 | **Abaqus依存コネクター分離(DashboardPageConnector)** |
| 077 | コネクタ固有config分離・プラグイン化分析 |
| 078 | CSV配列拡張・Excelダウンロード・REST API拡張 |
| 079 | 配列プロットビュー・物性比較・NG領域・グループ結線 |
| 080 | 配列NG領域・物性CSV・動的ビュー・HTMLエクスポート |
| 081 | ダッシュボード描画/クエリロジック分離 |
| 082 | 純粋関数モジュール単体テスト65件追加 |
| 083 | テストインポート移行 + app.pyラッパー関数削除 |
| 084 | **services/queryパッケージ — props条件式フィルタ汎用化** |

### Phase P: プラグイン化（status-085〜090, 02-13〜02-14）

SDK/CacheProviderプロトコル、entry_points動的発見、Abaqus/Obsidian完全分離。**1,002テスト到達**。

| # | 概要 |
|---|------|
| 085 | **API層リファクタリング・jj-sdk新設・CacheProviderプロトコル** |
| 086 | **SDK外部化・プラグインレジストリ・Abaqus/Obsidian分離** |
| 087 | パッケージセットアップ修正 |
| 088 | Abaqus固有ロジック分離・CacheProvider汎用化 |
| 089 | **Abaqusコネクター作り込み（v0.1.0完成準備、1,002テスト）** |
| 090 | **v0.1.0レビュー・v0.2.0ロードマップ案策定** |

---

## jjrv（Next.js Web）: status-001〜060

### RM1: ユーザー運用（status-001〜020, 01-24〜01-25）

SQLite(sql.js)、エンティティCRUD、検索/フィルタ、タグ管理、ログイン/アカウント管理。

| # | 概要 |
|---|------|
| 001〜010 | SQLiteスキーマ設計、エンティティCRUD、基本検索 |
| 011〜015 | タグ管理、ファイル添付、お気に入り |
| 016〜020 | ログイン/アカウント、統計ダッシュボード |

### RM2/2.5: 検索・閲覧（status-021〜041, 01-25〜02-01）

カード/テーブル/グラフ(D3-Force)/ダイアグラム、詳細ビュー、Import/Export設計。

| # | 概要 |
|---|------|
| 021〜030 | EntityCard/EntityTable/EntityGraph、D3-Force可視化 |
| 031〜035 | 詳細ビュー、Bodyプレビュー、ダイアグラム |
| 036〜039 | フィルタ強化、検索条件session保存 |
| 040 | review-00: プロジェクト状況・ロードマップ俯瞰レビュー |
| 041 | Project Brief/対応表（コンテキスト肥大化対策） |

### RM3: 操作性（status-042〜048, 02-01〜02-04）

インライン編集、検索条件保存、ドキュメント集約。

| # | 概要 |
|---|------|
| 042 | import/export設計仕様 |
| 043 | ロードマップ3 P0実装 |
| 044〜045 | ドキュメント集約・status更新漏れ解消 |
| 046〜048 | ロードマップ2/2.5/3追加仕様、畳み込み機能 |

### RM4/5: 本番運用（status-049〜057, 02-04〜02-06）

階層折りたたみ、プレビュー、レポジトリ階層制約、バリデーション。

| # | 概要 |
|---|------|
| 049 | ロードマップ4追加・階層折りたたみ・プレビューモーダル |
| 050〜051 | 検索・フィルター強化、インライン編集強化 |
| 052〜054 | ダイアグラム階層化・プレビュー改善・session保存 |
| 055〜056 | テーブル畳み込み・詳細ビューリサイズ・レポジトリ概念導入 |
| 057 | **レポジトリ階層制約（破壊的変更、バリデーション、マイグレーション）** |

### RM6: jj統合設計（status-058〜060, 02-06〜02-08）

GitHub形式レポジトリ構造、サイドバーツリー、jj統合ロードマップ策定（**設計のみ、実装未着手**）。

| # | 概要 |
|---|------|
| 058 | GitHub形式レポジトリ構造（user_namespace、D&D、README表示） |
| 059 | サイドバーツリーナビゲーション |
| 060 | **jj統合ロードマップ策定・レポジトリダッシュボード設計** |

---

## 転換点サマリー

| 転換点 | status | 内容 |
|--------|--------|------|
| **構造改革** | jj 041〜043 | graph/__init__.py分解、AbstractFileParserパターン確立 |
| **ダッシュボード開始** | jj 068 | Streamlit + FastAPI REST API |
| **プラグイン化** | jj 085〜086 | SDK/CacheProvider/entry_points |
| **RM6策定** | jjrv 060 | jj統合ロードマップ・ダッシュボード設計 |
| **v0.1.0区切り** | jj 090 | レビュー・v0.2.0ロードマップ案 |

---

## アーカイブ構造

```
docs/status/
├── status-index-v0.1.0.md  ← 本ファイル
├── archive-v0.1.0/
│   ├── jj/status-001.md 〜 status-090.md
│   └── jjrv/status-001.md 〜 status-060.md
└── status-001.md  ← v0.2.0の最初のstatus（新規）
```
