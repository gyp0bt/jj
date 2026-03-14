[← README.md](../../README.md)

# Migration Guide — jj バージョン移行ガイド

> 旧ワークフロー（手動管理・スクリプト散在）から jj への移行手順と、
> バージョン間の変更点をまとめたガイド。

---

## 目次

1. [手動ワークフローからの移行](#1-手動ワークフローからの移行)
2. [初期セットアップ](#2-初期セットアップ)
3. [旧CLI（submit系）から新CLI（graph系）への移行](#3-旧clisubmit系から新cligraph系への移行)
4. [設定ファイルの移行](#4-設定ファイルの移行)
5. [v0.1.0 → v0.2.0 の変更点](#5-v010--v020-の変更点)
6. [プラグインシステムへの移行](#6-プラグインシステムへの移行)
7. [データ永続化の変更](#7-データ永続化の変更)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. 手動ワークフローからの移行

### Before: 従来の手動管理

```
project/
├── go_setup_v1.inp          # 手動でファイル管理
├── go_setup_v2.inp          # バージョン管理は命名規則頼み
├── mesh_solid.inp
├── material.inp
├── *.odb, *.sta, *.msg      # 結果ファイルが散在
└── (メモ帳やExcelで条件管理)
```

問題点:
- 条件・バージョンの対応関係が不明確
- 結果ファイルの入力ファイルとの紐付けが人力
- 横断的な比較・検索が困難
- ファイル数が増えると管理が破綻

### After: jj によるグラフ管理

```
project/
├── .j2/                     # jj管理ディレクトリ（自動生成）
│   ├── config/
│   │   └── config.yaml      # プロジェクト設定
│   └── storage/
│       └── graph.yaml       # グラフデータ（自動更新）
├── go_setup_v1.inp
├── go_setup_v2.inp
├── mesh_solid.inp
├── material.inp
└── *.odb, *.sta, *.msg
```

利点:
- ファイル構造・依存関係を自動解析
- バージョン系列の自動検出
- *INCLUDE 参照の自動解決
- ダッシュボード・CSV・Neo4j等への即時エクスポート

---

## 2. 初期セットアップ

### Step 1: インストール

```bash
# コア（最小構成）
pip install -e .

# Abaqus + ダッシュボード（推奨）
pip install -e ".[abaqus,dashboard]"

# 全機能
pip install -e ".[all]"

# 開発用（テスト含む）
pip install -e ".[dev]"
```

### Step 2: プロジェクト初期化

```bash
cd /path/to/your/abaqus/project
jj init
```

`.j2/config/config.yaml` が生成される。必要に応じてカスタマイズ。

### Step 3: 初回パース

```bash
# 軽量モード（推奨: 初回確認用）
jj parse

# フルモード（メッシュ統計含む）
jj parse --full
```

### Step 4: 確認

```bash
jj show --summary
```

---

## 3. 旧CLI（submit系）から新CLI（graph系）への移行

v0.1.0以降、CLIの主軸は **graph系コマンド** に移行した。
旧submit系コマンドは凍結状態（Phase 3まで変更禁止）。

### コマンド対応表

| 旧コマンド | 新コマンド | 備考 |
|-----------|-----------|------|
| `jj` (引数なし) | — | 旧: submit扱い。新: ヘルプ表示 |
| `jj -fn file.inp` | `jj info file.inp` | ファイル情報表示 |
| `jj -ls` | `jj show` | ファイル一覧 |
| `jj check syntax` | （凍結中） | Phase 3で再実装予定 |
| `jj f get` | （凍結中） | Phase 3で再実装予定 |
| `jj f put` | （凍結中） | Phase 3で再実装予定 |
| `jj submit` | （凍結中） | Phase 3で再実装予定 |
| — | `jj parse` | **新規**: グラフ構築 |
| — | `jj export` | **新規**: 多フォーマットエクスポート |
| — | `jj dashboard` | **新規**: ダッシュボード起動 |
| — | `jj r <command>` | **新規**: コマンド実行＋ログ記録 |
| — | `jj diff file1 file2` | **新規**: Abaqusキーワード差分 |
| — | `jj serve` | **新規**: REST API起動 |

### 現在アクティブなコマンド一覧

```bash
# プロジェクト管理
jj init                          # 設定初期化
jj parse [--full]                # グラフ構築
jj show [--summary]              # グラフ表示

# ファイル操作
jj info <filename>               # ファイル詳細
jj diff <file1> <file2>         # ファイル差分

# エクスポート
jj export --target csv           # CSV出力
jj export --target obsidian      # Obsidian Vault
jj export --target neo4j         # Neo4jデータベース
jj export --target json          # JSON出力
jj export --target cypher        # Cypherクエリ出力

# ダッシュボード・API
jj dashboard                     # Streamlitダッシュボード
jj serve                         # REST API

# コマンド実行
jj r -- <command>                # 実行＋ログ記録

# 認証
jj credential set --service neo4j
jj credential show --service neo4j

# 設定
jj config migrate                # レガシー設定の移行
```

---

## 4. 設定ファイルの移行

### 旧: `.pyssh.yaml`（SSH設定）

```yaml
# 旧形式（submit系コマンド用 — 引き続き使用可能）
LINUX_LOCAL_BASEDIRPATH: /path/to/local
REMOTE_ABQ_PATH: /path/to/abaqus
```

### 新: `.j2/config/config.yaml`

```yaml
# 新形式（graph系コマンド用）
project-name: My Analysis Project
directory-max-depth: 5
include-search-depth: 5

# 表示名マッピング
vocab:
  idx: 条件
  v: v
  wallclock_time: 計算時間

# ファイルタイプ判定
path-type-map:
  "**go_* | **go":
    "*.inp": ABQ inp
  "**mesh_*":
    "*.inp": ABQ mesh

# ダッシュボード設定
dashboard:
  exclude-table-columns: [type, format]
  default-filters:
    active: true
```

### 移行コマンド

既存のレガシー設定がある場合:

```bash
jj config migrate
```

これにより旧設定値が `.j2/config/config.yaml` に統合される。

---

## 5. v0.1.0 → v0.2.0 の変更点

### 新機能

| 機能 | 説明 |
|------|------|
| **マルチソルバー対応** | Abaqus以外のソルバー（LS-DYNA, Fluent, OpenFOAM等）をプラグインとして追加可能 |
| **Run-centricスキーマ** | 実行（Run）を中心としたグラフスキーマ。DAG可視化対応 |
| **2層設定** | デフォルト設定 + ユーザー設定のディープマージ |
| **Neo4j統合** | Cypherクエリ生成、認証情報管理を含む完全なパイプライン |
| **ダッシュボード拡張** | SavedView、HTML一括出力、Run DAG表示 |
| **ML/最適化** | PyTorch/scikit-learn/Optunaによるモデル学習・最適化タスクのグラフ統合 |
| **REST API** | FastAPIベースのREST API（`jj serve`） |

### 破壊的変更

| 変更 | 対応方法 |
|------|---------|
| 設定ファイルパスの変更 | `jj config migrate` で自動移行 |
| NodeCategoryの追加 | `RUN` カテゴリが追加。既存ノードには影響なし |
| グラフスキーマの拡張 | 後方互換。既存graph.yamlはそのまま読み込み可能 |
| パーサー優先度の再調整 | 自動適用。ユーザー操作不要 |

### 非推奨化

| 項目 | 代替 | 削除予定 |
|------|------|---------|
| `jj g parse` | `jj parse` | v0.3.0 |
| `jj g show` | `jj show` | v0.3.0 |
| `jj g export` | `jj export` | v0.3.0 |
| `jj g info` | `jj info` | v0.3.0 |

`jj g` プレフィックスは互換性のため残っているが、トップレベルコマンドの使用を推奨。

---

## 6. プラグインシステムへの移行

### v0.1.0: Abaqusハードコード

v0.1.0ではAbaqusパーサーがコア層に含まれていた。

### v0.2.0: entry_points プラグイン

Abaqusはプラグインとして分離された:

```toml
# pyproject.toml
[project.entry-points."jj.plugins"]
abaqus = "services.plugins.abaqus:register"
```

**ユーザーへの影響:**
- `pip install -e ".[abaqus]"` で明示的にインストール
- コア機能（parse, show, export）はAbaqusなしでも動作
- Abaqus以外のソルバーも同じパターンで追加可能

### 利用可能なプラグイン

| プラグイン | optional-dependencies | 状態 |
|-----------|----------------------|------|
| abaqus | `jj[abaqus]` | 安定 |
| obsidian | `jj[obsidian]` | 安定 |
| fluent | `jj[fluent]` | 実験的 |
| lsdyna | — | スケルトン |
| openfoam | — | スケルトン |
| calculix | — | スケルトン |
| hfss | — | スケルトン |
| flow3d | — | スケルトン |
| ml | `jj[ml-all]` | 安定 |

---

## 7. データ永続化の変更

### グラフストレージ

```
.j2/storage/
├── graph.yaml           # メイングラフデータ
├── abq_cache/           # Abaqusパーサーキャッシュ（pickle）
└── plugin_cache/        # プラグインキャッシュ（namespace隔離）
    └── abaqus/
```

### キャッシュ管理

キャッシュは自動管理:
- `cache-max-age-days: 30` — 古いキャッシュの自動削除
- `cache-max-count: 100` — 上限超過時に古い順に削除
- `jj parse` 実行時にキャッシュ更新

キャッシュを手動クリアする場合:

```bash
rm -rf .j2/storage/abq_cache/
jj parse --full
```

---

## 8. トラブルシューティング

### Q: `jj parse` でAbaqusファイルが認識されない

**原因:** Abaqusプラグインが未インストール

```bash
pip install -e ".[abaqus]"
```

### Q: `ModuleNotFoundError: No module named 'modules.pymesh'`

**原因:** pymeshはプロジェクト内パッケージ（optionalではない）

```bash
pip install -e ".[pymesh]"    # pymesh依存をインストール
pip install -e ".[abaqus]"    # またはabaqus経由（pymesh含む）
```

### Q: `jj dashboard` でエラー

**原因:** dashboard依存が未インストール

```bash
pip install -e ".[dashboard]"
```

### Q: 設定ファイルが見つからない

```bash
jj init    # .j2/config/config.yaml を生成
```

### Q: `jj export --target neo4j` で認証エラー

```bash
jj credential set --service neo4j    # 認証情報を設定
jj credential show --service neo4j   # 設定確認
```

### Q: 旧graph.yamlが読めない

v0.2.0のスキーマは後方互換。読み込みエラーが出る場合は再パース:

```bash
jj parse --full
```

### Q: `.gitignore` で `.j2/` を除外すべきか

推奨構成:

```gitignore
# jj管理ディレクトリ
.j2/storage/          # グラフデータ（再生成可能）
.j2/config/.credentials  # 認証情報（秘匿）

# 以下はコミットしてもよい
# .j2/config/config.yaml  # プロジェクト設定（チーム共有可能）
```
