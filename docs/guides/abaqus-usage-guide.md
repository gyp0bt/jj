[← README.md](../../README.md)

# Abaqus Usage Guide — Abaqusリポジトリ向け使用マニュアル

> Abaqus解析プロジェクトを jj で管理するための実践的なガイド。
> 具体的なディレクトリ構成例とコマンド実行例を交えて解説する。

---

## 目次

1. [前提条件](#1-前提条件)
2. [Abaqusプロジェクトの典型構成](#2-abaqusプロジェクトの典型構成)
3. [セットアップ](#3-セットアップ)
4. [プロジェクトのパース](#4-プロジェクトのパース)
5. [グラフの確認と検索](#5-グラフの確認と検索)
6. [ファイル差分の比較](#6-ファイル差分の比較)
7. [コマンド実行とログ記録（jj r）](#7-コマンド実行とログ記録jj-r)
8. [エクスポート](#8-エクスポート)
9. [ダッシュボード](#9-ダッシュボード)
10. [設定のカスタマイズ](#10-設定のカスタマイズ)
11. [実践シナリオ](#11-実践シナリオ)

---

## 1. 前提条件

### インストール

```bash
# Abaqus関連の全機能を使う場合
pip install -e ".[abaqus,dashboard,dev]"
```

これにより以下がインストールされる:
- **コア**: pydantic, pyyaml, networkx, numpy, chardet, ftfy
- **abaqus**: scipy（メッシュ品質解析）, pymesh依存（pandas, plotly等）
- **dashboard**: streamlit, streamlit-aggrid, plotly
- **dev**: pytest, pytest-cov

### 確認

```bash
python -c "from services.plugins.abaqus import register; print('OK')"
```

---

## 2. Abaqusプロジェクトの典型構成

### 推奨ディレクトリ構成

```
my-abaqus-project/
├── go_base_v1/                # 解析ケース1
│   ├── go_base_v1.inp         # メインインプットファイル
│   ├── go_base_v1.odb         # 結果ファイル
│   ├── go_base_v1.sta         # ステータスファイル
│   ├── go_base_v1.msg         # メッセージファイル
│   └── go_base_v1.dat         # データファイル
├── go_base_v2/                # 解析ケース2（v1の改良版）
│   ├── go_base_v2.inp
│   ├── go_base_v2.odb
│   └── ...
├── go_fine_mesh_v1/           # メッシュ細分化ケース
│   └── go_fine_mesh_v1.inp
├── mesh_solid_v1/             # 共有メッシュ
│   └── mesh_solid_v1.inp
├── material_steel.inp         # 材料定義（共有）
├── step_static.inp            # ステップ定義（共有）
└── old/                       # アーカイブ（自動でactive: false）
    └── go_base_v0/
        └── go_base_v0.inp
```

### ファイル命名規則

jj はファイル名からプロパティを自動抽出する:

| ファイル名 | 抽出プロパティ |
|-----------|---------------|
| `go_base_v1.inp` | idx=base, v=1 |
| `go_fine_mesh_v2.inp` | idx=fine_mesh, v=2 |
| `mesh_solid_v1.inp` | type=ABQ mesh, v=1 |
| `material_steel.inp` | type=ABQ material |

**プレフィックス別の自動分類:**

| プレフィックス | 自動分類 |
|--------------|---------|
| `go_*` | ABQ inp（メイン入力ファイル） |
| `mesh_*` | ABQ mesh（メッシュファイル） |
| `material_*` | 材料定義ファイル |
| `step_*` | ステップ定義ファイル |

---

## 3. セットアップ

### 3.1 プロジェクト初期化

```bash
cd /path/to/my-abaqus-project
jj init
```

生成されるファイル:

```
.j2/
├── config/
│   └── config.yaml    # プロジェクト設定
└── storage/           # （parseで生成される）
```

### 3.2 設定の確認

`jj init` で生成される `config.yaml` のデフォルト値が適切か確認する:

```yaml
# .j2/config/config.yaml
project-name: my-abaqus-project
directory-max-depth: 5
include-search-depth: 5
```

Abaqusプロジェクトでよく設定する項目:

```yaml
# ファイル名から抽出されるプロパティの表示名
vocab:
  idx: 条件
  v: バージョン
  wallclock_time: 計算時間
  total_time: 解析時間
  analysis_status: 状態

# ファイルタイプの自動判定ルール
path-type-map:
  "**go_* | **go":
    "*.inp": ABQ inp
    "*.dat": ABQ dat
    "*.odb": ABQ odb
    "*": 計算結果
  "**mesh_*":
    "*.inp": ABQ mesh

# ファイル間の関連付けルール
file-relations:
  input-extensions: [".inp"]
  result-extensions: [".odb", ".sta", ".msg", ".dat"]
```

---

## 4. プロジェクトのパース

### 4.1 基本パース（軽量モード）

```bash
jj parse
```

実行内容:
1. プロジェクトディレクトリを再帰スキャン
2. ファイル名からプロパティ抽出（idx, v等）
3. `*INCLUDE` 参照の解決
4. `*PARAMETER` の抽出
5. 結果ファイル（.sta, .msg）のパース
6. バージョン系列の自動検出
7. 材料定義（material.inp）の解析
8. グラフを `.j2/storage/graph.yaml` に保存

### 4.2 フルパース（メッシュ統計含む）

```bash
jj parse --full
```

軽量モードに加えて:
- メッシュ品質統計（要素数、アスペクト比、ジャコビアン等）
- メッシュ継承関係の解析
- 材料割当の解析
- エレメントセット情報の抽出

### 4.3 パースオプション

```bash
# ディレクトリ深度を制限（大規模プロジェクト用）
jj parse --max-depth 3

# デバッグモード（エラー時にスタックトレース表示）
jj parse --debug

# 出力先を変更
jj parse -o analysis-graph.yaml

# JSON形式で出力
jj parse --format json -o graph.json
```

### 4.4 パースの再実行

ファイルを追加・変更した後は再パースが必要:

```bash
# ファイル追加後
cp new_analysis/go_new_v1.inp .
jj parse
```

---

## 5. グラフの確認と検索

### 5.1 サマリー表示

```bash
jj show --summary
```

出力例:

```
=== プロジェクトグラフサマリー ===
ノード数: 45
リレーション数: 62
ノードタイプ別:
  file: 28
  directory: 8
  abaqus_material: 5
  abaqus_elset: 4
カテゴリ別:
  FILE: 28
  DIRECTORY: 8
  DATA: 9
```

### 5.2 ノード一覧

```bash
# 全ノード表示
jj show

# タイプでフィルタ
jj show --type "ABQ inp"

# アクティブのみ
jj show --active

# インデックスでフィルタ
jj show -id 1 2 3

# バージョンでフィルタ
jj show -v 2

# プロパティでフィルタ
jj show -prop wallclock_time
```

### 5.3 ファイル詳細

```bash
# 特定ファイルの情報
jj info go_base_v1.inp
```

出力例:

```
=== go_base_v1.inp ===
type: ABQ inp
format: inp
category: FILE
active: true
properties:
  idx: base
  v: 1
  wallclock_time: 3600
  analysis_status: COMPLETED
  total_time: 1.0
relations:
  → has_output: go_base_v1.odb
  → has_output: go_base_v1.sta
  → next_version: go_base_v2.inp
  → includes: mesh_solid_v1.inp
  → includes: material_steel.inp
```

```bash
# 複数ファイルの特定プロパティ
jj info go_*.inp -prop idx v wallclock_time analysis_status
```

```bash
# アクティブファイルのみ
jj info -all --active -prop idx v wallclock_time
```

---

## 6. ファイル差分の比較

### 6.1 基本差分

```bash
jj diff go_base_v1.inp go_base_v2.inp
```

出力例:

```
=== Abaqus Block Diff ===
go_base_v1.inp → go_base_v2.inp

[変更] *BOUNDARY
  - v1: OP=NEW
  + v2: OP=MOD

[追加] *CONTACT PAIR
  + v2: interaction=SURF-SURF, adjust=0.01

[削除] *SPRING
  - v1: ELSET=SPRING1, NONLINEAR
```

### 6.2 詳細差分

```bash
jj diff go_base_v1.inp go_base_v2.inp --detail
```

キーワードブロック単位で詳細な差分を表示。

---

## 7. コマンド実行とログ記録（jj r）

`jj r` コマンドは任意のコマンドを実行し、結果をグラフに記録する。

### 7.1 基本的な使い方

```bash
# スクリプト実行（前処理・後処理など）
jj r -- python preprocess.py

# シェルスクリプト実行
jj r -- bash run_analysis.sh

# 実行モード指定
jj r --mode script -- python mesh_check.py
```

### 7.2 実行結果の記録

実行後、以下が自動的に記録される:
- 実行コマンド
- exit code
- 実行時間
- 実行ユーザー・ホスト
- 標準出力・エラー出力のログ
- トレースファイル

### 7.3 実行後の自動パース

デフォルトでは実行後にグラフが自動パースされる:

```bash
# 自動パースあり（デフォルト）
jj r -- python generate_mesh.py

# 自動パースをスキップ
jj r --no-parse -- python quick_check.py
```

### 7.4 プロパティの確認（dry-run）

```bash
jj r --show-properties -- abaqus job=analysis cpus=4
```

コマンドのプロパティのみ表示し、実行はしない。

### 7.5 Run DAG可視化

ダッシュボードの Run DAG ページで実行履歴の依存関係グラフを可視化可能。

---

## 8. エクスポート

### 8.1 CSVエクスポート

```bash
# 基本エクスポート
jj export --target csv -o results.csv

# カラム指定
jj export --target csv -o results.csv \
  --columns idx v wallclock_time analysis_status

# アクティブのみ
jj export --target csv -o results.csv --active

# ワイルドカードカラム
jj export --target csv -o results.csv --columns "stress*" "RF*"

# 単位表示形式
jj export --target csv -o results.csv --unit-format row
```

### 8.2 JSONエクスポート

```bash
# 階層構造
jj export --target json -o graph.json

# フラット構造
jj export --target json -o flat.json --flatten

# タイプフィルタ
jj export --target json --type "ABQ inp"
```

### 8.3 Obsidianエクスポート

```bash
jj export --target obsidian
```

生成物:
- `notes/` — 各ノードのMarkdownファイル（frontmatter付き）
- `.base` — Dataviewクエリテンプレート

Obsidian Vault に追加すれば、Dataviewプラグインで横断検索が可能。

### 8.4 Neo4jエクスポート

```bash
# 認証設定（初回のみ）
jj credential set --service neo4j

# エクスポート
jj export --target neo4j

# 既存データを削除してからエクスポート
jj export --target neo4j --clear

# 接続情報を直接指定
jj export --target neo4j \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --neo4j-password password
```

### 8.5 Cypherエクスポート（DB接続不要）

```bash
jj export --target cypher -o queries.cypher
```

生成されたCypherファイルをNeo4j BrowserやCLIで実行可能。

---

## 9. ダッシュボード

### 9.1 起動

```bash
jj dashboard
# → http://localhost:8501 で起動
```

### 9.2 利用可能なビュー

#### テーブルビュー
- AgGridベースのインタラクティブテーブル
- カラムソート・フィルタ
- プロパティの横断比較

#### カードビュー
- 個別ノードの詳細表示
- プロパティ一覧と関連ノード

#### プロットビュー
- 散布図・棒グラフ・折れ線グラフ
- X/Y軸にプロパティを自由に割り当て
- カラー分けによるグルーピング

使用例: `wallclock_time` vs `条件` のプロットで計算時間の傾向を確認

#### ステータスビュー
- 解析成功/失敗/未実行の統計
- エラーメッセージの一覧

#### ギャラリービュー
- PNG/GIF画像のグリッド表示
- プロパティでグルーピング

#### アレイプロットビュー（Abaqus専用）
- 反力（RF）、応力等のアレイデータを比較
- オーバーレイ/グリッド/単独モード
- NG領域のハイライト

#### 物性一覧ページ（Abaqus専用）
- 材料プロパティテーブル
- 塑性/弾性/密度カーブのプロット
- 材料間の比較

### 9.3 SavedViewの設定

`config.yaml` でプリセットビューを定義:

```yaml
dashboard:
  saved-views:
    - name: アクティブ解析一覧
      type: table
      filters:
        active: true
    - name: 計算時間比較
      type: plot
      config:
        x: idx
        y: wallclock_time
    - name: 結果画像一覧
      type: gallery
      filters:
        type: "計算結果"
```

---

## 10. 設定のカスタマイズ

### 10.1 Vocab（表示名マッピング）

ファイル名トークンを業務用語に変換:

```yaml
vocab:
  idx: 条件
  v: バージョン
  active: 有効
  wallclock_time: 計算時間[sec]
  total_time: 解析時間[sec]
  analysis_status: 解析状態
  num_elements: 要素数
  num_nodes: 節点数
```

### 10.2 パスタイプマップ

ファイルパスのパターンに基づく自動分類:

```yaml
path-type-map:
  # go_プレフィックスのディレクトリ内ファイル
  "**go_* | **go":
    "*.inp": ABQ inp
    "*.dat": ABQ dat
    "*.odb": ABQ odb
    "*.sta": ABQ sta
    "*.msg": ABQ msg
    "*": 計算結果

  # meshプレフィックスのファイル
  "**mesh_*":
    "*.inp": ABQ mesh

  # 共有ファイル
  "**material_*":
    "*.inp": ABQ material
  "**step_*":
    "*.inp": ABQ step
```

### 10.3 ダッシュボード設定

```yaml
dashboard:
  # テーブルから除外するカラム
  exclude-table-columns:
    - type
    - format
    - verbose_name

  # 起動時のデフォルトフィルタ
  default-filters:
    active: true

  # プロット初期設定
  plot:
    x: idx
    y: wallclock_time

  # Abaqus材料カーブの設定
  connectors:
    abaqus:
      material-curve-columns:
        plastic:
          columns: [stress, strain]
          x: 1
          y: 0
        elastic:
          columns: [E, nu]
          x: 0
          y: 1
```

### 10.4 キャッシュ設定

```yaml
cache-max-age-days: 30    # 30日以上前のキャッシュを自動削除
cache-max-count: 100      # キャッシュ上限数
```

---

## 11. 実践シナリオ

### シナリオ1: 新規プロジェクトの立ち上げ

```bash
# 1. プロジェクトディレクトリを作成
mkdir my-analysis && cd my-analysis

# 2. 解析ファイルを配置
# (go_base_v1.inp, mesh_solid_v1.inp, material_steel.inp 等)

# 3. jj初期化
jj init

# 4. config.yamlを編集（必要に応じて）
# vim .j2/config/config.yaml

# 5. パース
jj parse

# 6. 確認
jj show --summary
jj info go_base_v1.inp
```

### シナリオ2: 解析条件の横断比較

```bash
# 1. 全条件をパース
jj parse

# 2. CSVで一覧出力
jj export --target csv -o comparison.csv \
  --columns idx v wallclock_time analysis_status \
  --active

# 3. ダッシュボードで可視化
jj dashboard
# → プロットビューで wallclock_time vs idx を確認
```

### シナリオ3: バージョン間の差分確認

```bash
# 1. v1→v2の変更点を確認
jj diff go_base_v1.inp go_base_v2.inp

# 2. 詳細差分
jj diff go_base_v1.inp go_base_v2.inp --detail

# 3. グラフで系列確認
jj info go_base_v1.inp
# relations: → next_version: go_base_v2.inp
```

### シナリオ4: メッシュ品質の確認

```bash
# 1. フルパース（メッシュ統計含む）
jj parse --full

# 2. メッシュファイルの品質確認
jj info mesh_solid_v1.inp

# 3. ダッシュボードで可視化
jj dashboard
# → テーブルビューでメッシュ品質カラムを確認
```

### シナリオ5: 材料定義の管理

```bash
# 1. パース（材料ファイルを解析）
jj parse

# 2. 材料ノードの確認
jj show --type abaqus_material

# 3. ダッシュボードの物性一覧ページ
jj dashboard
# → 物性一覧ページで材料カーブを確認
```

### シナリオ6: スクリプト実行のログ管理

```bash
# 1. 前処理スクリプト実行
jj r -- python preprocess.py --input mesh_raw.inp --output mesh_solid_v1.inp

# 2. 解析の実行とログ記録
jj r -- bash run_abaqus.sh go_base_v1

# 3. 後処理
jj r -- python postprocess.py --odb go_base_v1.odb

# 4. 実行履歴の確認
jj show --type run
jj dashboard
# → Run DAGページで依存関係を確認
```

### シナリオ7: Neo4jでの横断検索

```bash
# 1. 認証設定
jj credential set --service neo4j

# 2. エクスポート
jj export --target neo4j --clear

# 3. Neo4j Browserでクエリ
# MATCH (n:Node {type: 'ABQ inp'})-[:has_output]->(r)
# RETURN n.name, r.name, n.properties.wallclock_time
```

### シナリオ8: REST APIとの連携

```bash
# 1. APIサーバー起動
jj serve --port 8000

# 2. 別ターミナルからクエリ
# ノード一覧
curl http://localhost:8000/api/v1/nodes?type=ABQ+inp

# サマリー
curl http://localhost:8000/api/v1/summary

# 特定ノードの関連
curl http://localhost:8000/api/v1/nodes/1/related

# 再パース（API経由）
curl -X POST http://localhost:8000/api/v1/parse
```

### シナリオ9: Obsidianナレッジベース構築

```bash
# 1. Obsidianエクスポート
jj export --target obsidian

# 2. 生成されたnotes/をObsidian Vaultに配置

# 3. Dataviewプラグインで横断検索
# TABLE idx, v, wallclock_time
# FROM "notes"
# WHERE type = "ABQ inp" AND active = true
# SORT wallclock_time DESC
```

---

## 付録: よく使うコマンド一覧

```bash
# === 基本 ===
jj init                              # プロジェクト初期化
jj parse                             # 軽量パース
jj parse --full                      # フルパース（メッシュ統計含む）
jj show --summary                    # サマリー表示
jj show --active                     # アクティブノード一覧

# === 検索 ===
jj info go_base_v1.inp               # ファイル詳細
jj info go_*.inp -prop idx v         # 複数ファイルのプロパティ
jj show --type "ABQ inp" --active    # タイプ + アクティブフィルタ

# === 差分 ===
jj diff file1.inp file2.inp          # キーワード差分
jj diff file1.inp file2.inp --detail # 詳細差分

# === 実行 ===
jj r -- python script.py             # スクリプト実行＋ログ
jj r --no-parse -- quick_test.sh     # 自動パースなし
jj r --show-properties -- cmd args   # dry-run

# === エクスポート ===
jj export --target csv -o out.csv    # CSV
jj export --target json -o out.json  # JSON
jj export --target obsidian          # Obsidian
jj export --target neo4j             # Neo4j
jj export --target cypher -o q.cyp   # Cypher

# === ダッシュボード ===
jj dashboard                         # Streamlit起動
jj serve                             # REST API起動

# === 設定 ===
jj config migrate                    # レガシー設定移行
jj credential set --service neo4j    # 認証設定
```
