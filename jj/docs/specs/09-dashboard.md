[READMEへ戻る](../../README.md)

# ダッシュボード層 仕様書

## 1. 概要

jjが抽出したプロパティとrelationを一覧・可視化するダッシュボード機能の設計仕様。
jj側は**即時的な一覧性**（ローカルStreamlit）を、jj-db側は**詳細で高機能なレンダリング**（Next.js）を担う。

### 設計判断の根拠

| 選択肢 | 利点 | 欠点 | 判定 |
|--------|------|------|------|
| **Streamlit** | インタラクティブ、Pythonネイティブ、ag-grid/plotly統合、実績あり | 外部サーバー不要だがプロセス常駐 | **jj側で採用** |
| Jinja2 → HTML | 静的生成、依存少ない | フィルター/プロット不可、更新のたびに再生成 | 不採用 |
| Obsidian | ナレッジグラフに強い | テーブル/プロットに弱い、プログラマブルでない | 既存のエクスポート先として継続 |
| jj-db (Next.js) | 高機能ビュー一式、ユーザー管理済み | jjとは別プロジェクト | **将来的な統合先** |

### 役割分担

```
┌─────────────────────────────┐    ┌──────────────────────────────┐
│  jj dashboard (Streamlit)   │    │  jj-db (Next.js)            │
│                             │    │                              │
│  ・プロジェクトローカル      │    │  ・組織横断のDB              │
│  ・即時起動・即時フィルター  │    │  ・グラフDB検索/可視化       │
│  ・実行中ステータス監視     │    │  ・テーブル/カード/詳細ビュー │
│  ・簡易プロット             │    │  ・高度なプロット/比較       │
│  ・graph.yaml直接読み込み   │    │  ・アップロード/解析連携     │
│                             │    │  ・ユーザー情報管理          │
│  jj dashboard               │    │                              │
│  jj serve (API)    ────────────▶ │  jj API経由でデータ取得      │
└─────────────────────────────┘    └──────────────────────────────┘
```

---

## 2. jj dashboard（Streamlit）

### 2.1 起動コマンド

```bash
jj dashboard                    # Streamlitアプリをローカル起動
jj dashboard --port 8501        # ポート指定
jj dashboard --no-browser       # ブラウザを開かない
```

### 2.2 ページ構成

#### Page 1: テーブルビュー（メイン画面）

go_ファイル一覧をag-gridテーブルで表示。プロパティをカラムとして展開。

```
┌──────────────────────────────────────────────────────────────┐
│ [フィルター: type ▼] [index ▼] [status ▼] [検索: ________]  │
├──────┬───────┬─────┬────────┬───────┬────────────┬──────────┤
│ name │ index │ ver │ status │ props │ materials  │ actions  │
├──────┼───────┼─────┼────────┼───────┼────────────┼──────────┤
│go_01 │ idx1  │ v3  │ ✅完了  │ RF3=5 │ Steel,Al   │ 📄 🔍   │
│go_02 │ idx1  │ v2  │ ❌失敗  │ RF3=3 │ Steel      │ 📄 🔍   │
│go_03 │ idx2  │ v1  │ ⏳実行中│ RF3=- │ -          │ 📄 🔍   │
└──────┴───────┴─────┴────────┴───────┴────────────┴──────────┘
```

**データソース**: `GraphModel.nodes` (type=go系) + `GraphModel.relations`

**カラム構成**:
- 固定カラム: name, index, version, type, format, active
- 動的カラム: properties辞書のキーを展開（prop1, prop2, ...）
- ステータスカラム: analysis_status（.sta/.msg解析結果）
- 関連カラム: materials（abaqus_material relation経由）、elset

**フィルター機能**:
- ag-gridのビルトインフィルター（テキスト、数値、選択）
- サイドバーからのグローバルフィルター（type, index, status）
- active/非activeの切り替え

#### Page 2: カードビュー

テーブルで選択した行の詳細をカード形式で表示。

```
┌──────────────────────────────────────────────────┐
│ go_idx1_v3.inp                                   │
│ ──────────────────────────────────────────────── │
│ Properties:                                      │
│   index: idx1  version: v3  status: completed    │
│   RF3: 5.0     温度: 300K                        │
│ ──────────────────────────────────────────────── │
│ Relations:                                       │
│   includes → material_steel.inp                  │
│   has_output → go_idx1_v3_RF3.csv                │
│   derived_from → go_idx1_v2.inp                  │
│ ──────────────────────────────────────────────── │
│ Images:                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ RF3.png │ │ mesh.png│ │ disp.png│           │
│  └─────────┘ └─────────┘ └─────────┘           │
│ ──────────────────────────────────────────────── │
│ Mesh Summary:                                    │
│   nodes: 12,345  elements: 48,000                │
│   size: 0.5-2.3 (mean: 1.2)                     │
│   skew: 0.0-5.7° (mean: 1.3°)                   │
│ ──────────────────────────────────────────────── │
│ Warnings: 3    Errors: 0                         │
│   WARNING: Element distortion in elset PART-A    │
└──────────────────────────────────────────────────┘
```

**データソース**:
- Node properties（直接プロパティ）
- Relations（node1_id/node2_id経由で関連ノード取得）
- has_output関係のCSV/PNG/JSONを探索
- abaqus_material関係経由で材料ノード取得
- メッシュ要約（abq_to_dict結果のsummary）

#### Page 3: プロットビュー

プロパティを縦横軸に選択して散布図・線図を描画。

```
┌──────────────────────────────────────────────────┐
│ X軸: [index     ▼]   Y軸: [RF3       ▼]        │
│ 色分け: [version ▼]   プロット: [散布図 ▼]       │
│                                                  │
│    RF3                                           │
│    ^                                             │
│ 10 │         ● v3                                │
│  8 │     ● v2    ● v3                            │
│  6 │  ● v1  ● v2                                 │
│  4 │  ● v1                                       │
│  2 │                                             │
│    └──────────────────────────> index             │
│       idx1   idx2   idx3   idx4                  │
└──────────────────────────────────────────────────┘
```

**機能**:
- plotly.express による散布図・線図・棒グラフ
- X/Y軸はプロパティ辞書のキーから動的選択
- 色分け: version, type, tags等で指定
- ホバー: ファイル名、全プロパティ表示
- 選択した点をクリック → カードビューに遷移

#### Page 4: ステータスモニター

実行中・完了・失敗のジョブ一覧。

```
┌──────────────────────────────────────────────────┐
│ 実行中 (2)                                       │
│ ┌────────────────────────────────────────────┐   │
│ │ go_idx3_v1.inp  開始: 14:30  経過: 2h15m  │   │
│ │ go_idx4_v1.inp  開始: 15:00  経過: 1h45m  │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ 最近完了 (5)                                     │
│ ┌────────┬──────────┬────────┬─────────────────┐ │
│ │ name   │ status   │ 所要   │ errors/warnings │ │
│ │ go_01  │ ✅ 完了  │ 3h20m │ W:3 E:0        │ │
│ │ go_02  │ ❌ 失敗  │ 0h05m │ W:0 E:2        │ │
│ └────────┴──────────┴────────┴─────────────────┘ │
└──────────────────────────────────────────────────┘
```

**データソース**:
- Node properties: analysis_status, execution_time
- .sta/.msgの解析結果
- run コマンドのログ（`.jj/storage/run/`）

#### Page 5: グラフビュー（オプション）

ノード間の関係をネットワーク図で可視化。

**実装候補**: pyvis（networkx連携）またはstreamlit-agraph
**優先度**: 低（Obsidianやjj-dbが担う領域）

### 2.3 データ取得レイヤー

```python
# services/dashboard/data_provider.py

class DashboardDataProvider:
    """ダッシュボード向けデータ供給"""

    def __init__(self, graph: GraphModel):
        self.graph = graph

    def get_go_table(self, filters: dict | None = None) -> pd.DataFrame:
        """go_ファイルのテーブルデータ（プロパティ展開済み）"""

    def get_node_card(self, node_id: int) -> dict:
        """ノード詳細カード（関連ノード含む）"""

    def get_plot_data(self, x_key: str, y_key: str,
                      color_key: str | None = None) -> pd.DataFrame:
        """プロット用データ（数値プロパティのみ）"""

    def get_status_summary(self) -> dict:
        """実行ステータスサマリー"""

    def get_property_keys(self) -> list[str]:
        """利用可能なプロパティキー一覧"""

    def get_related_files(self, node_id: int,
                          label: str | None = None) -> list[Node]:
        """関連ファイル一覧"""
```

### 2.4 ディレクトリ構成

```
services/
  dashboard/
    __init__.py           # DashboardService（起動・設定管理）
    data_provider.py      # DashboardDataProvider（データ供給）
    app.py                # Streamlitアプリ本体
    pages/
      01_table.py         # テーブルビュー
      02_card.py          # カードビュー
      03_plot.py          # プロットビュー
      04_status.py        # ステータスモニター
```

---

## 3. jj serve（REST API）

jj-dbとの統合の橋渡しとなるAPIレイヤー。

### 3.1 起動コマンド

```bash
jj serve                        # APIサーバー起動
jj serve --port 8080            # ポート指定
jj serve --host 0.0.0.0         # 外部公開
```

### 3.2 エンドポイント設計

```
GET  /api/v1/graph              # グラフ全体（nodes + relations）
GET  /api/v1/nodes              # ノード一覧（フィルター対応）
GET  /api/v1/nodes/:id          # ノード詳細
GET  /api/v1/nodes/:id/related  # 関連ノード
GET  /api/v1/relations          # リレーション一覧
GET  /api/v1/properties/keys    # プロパティキー一覧
GET  /api/v1/summary            # サマリー統計
GET  /api/v1/status             # 実行ステータス
GET  /api/v1/diff/:id1/:id2     # ノード間差分
POST /api/v1/parse              # 再パース実行
```

**クエリパラメータ例**:
```
GET /api/v1/nodes?type=go&active=true&index=idx1
GET /api/v1/nodes?props.RF3.gt=5&sort=-version
```

### 3.3 実装

- **フレームワーク**: FastAPI（型安全、OpenAPIドキュメント自動生成）
- **データソース**: GraphStorage経由でgraph.yaml/json読み込み
- **認証**: 初期は不要（ローカル専用）、jj-db統合時にAPIキーまたはOAuth

```python
# services/api/__init__.py

from fastapi import FastAPI
from .routes import graph_router, node_router

app = FastAPI(title="jj API", version="1.0.0")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(node_router, prefix="/api/v1")
```

---

## 4. jj-db統合設計

### 4.1 統合パターン

```
jj-db (Next.js)
  │
  ├── /projects          # jjプロジェクト一覧
  │   └── /projects/:id  # プロジェクト詳細
  │       ├── table      # テーブルビュー（ag-gridと同等）
  │       ├── graph      # グラフビュー（既存機能活用）
  │       ├── cards      # カードビュー（既存機能活用）
  │       ├── plots      # プロットビュー（高機能版）
  │       └── detail/:nodeId  # ノード詳細ビュー
  │
  └── API連携
      ├── jj serve → jj-db fetch  # リアルタイム取得
      └── jj export → jj-db upload # バッチアップロード
```

### 4.2 データ変換: jj GraphModel → jj-db GraphData

```typescript
// jj-db側の型定義（参考）
interface JJNode {
  id: number;
  type: string;      // "go", "mesh", "material", "folder", ...
  name: string;
  format: string;
  properties: Record<string, any>;
}

interface JJRelation {
  id: number;
  label: string;     // "tagged", "includes", "has_output", ...
  node1_id: number;
  node2_id: number;
}

interface JJGraph {
  nodes: JJNode[];
  relations: JJRelation[];
}
```

jj-dbの既存GraphData形式へのマッピングルール:
- `JJNode` → jj-dbの`Node`（typeマッピングが必要）
- `JJRelation` → jj-dbの`Edge`（labelをedge_typeに変換）
- `properties` → jj-dbのノードメタデータ

### 4.3 統合方式の選択肢

| 方式 | 説明 | 適用場面 |
|------|------|----------|
| **API連携** | `jj serve` → jj-db がfetch | リアルタイム連携、開発時 |
| **バッチアップロード** | `jj export --target jj-db` → jj-db API | 定期同期、本番運用 |
| **共有DB** | jjがjj-dbのDBに直接書き込み | 将来的な完全統合時 |

**推奨**: 初期はバッチアップロード、中期以降にAPI連携へ移行。

---

## 5. jj export拡張

ダッシュボード対応のために既存exportに追加するターゲット。

### 5.1 新規ターゲット

```bash
jj export --target dashboard-json   # ダッシュボード用JSON（プロパティ展開済み）
jj export --target jj-db           # jj-dbアップロード形式
```

### 5.2 dashboard-json形式

テーブルビューに最適化したフラットなJSON:

```json
{
  "metadata": {
    "project": "project-name",
    "generated_at": "2026-02-08T12:00:00",
    "node_count": 150,
    "relation_count": 300
  },
  "columns": ["name", "index", "version", "type", "format", "active",
              "analysis_status", "RF3", "temperature", "materials", "elset"],
  "rows": [
    {
      "id": 1,
      "name": "go_idx1_v3",
      "index": "idx1",
      "version": "v3",
      "type": "Abaqusインプット",
      "format": "inp",
      "active": true,
      "analysis_status": "completed",
      "RF3": 5.0,
      "temperature": 300,
      "materials": ["Steel", "Aluminum"],
      "elset": ["PART-A", "PART-B"],
      "related_files": [
        {"name": "go_idx1_v3_RF3.csv", "relation": "has_output"},
        {"name": "material_steel.inp", "relation": "includes"}
      ]
    }
  ],
  "graph": {
    "nodes": [...],
    "relations": [...]
  }
}
```

---

## 6. 依存パッケージ

### jj dashboard用

| パッケージ | 用途 | 必須/オプション |
|-----------|------|----------------|
| `streamlit` | ダッシュボードフレームワーク | 必須 |
| `streamlit-aggrid` | ag-gridテーブル | 必須 |
| `plotly` | インタラクティブプロット | 必須 |
| `pandas` | データフレーム操作 | 必須 |
| `pyvis` or `streamlit-agraph` | ネットワーク図 | オプション |

### jj serve用

| パッケージ | 用途 | 必須/オプション |
|-----------|------|----------------|
| `fastapi` | REST API | 必須 |
| `uvicorn` | ASGIサーバー | 必須 |
| `pydantic` | 既存で対応 | - |

### インストールグループ

```toml
# pyproject.toml or setup.cfg
[project.optional-dependencies]
dashboard = ["streamlit>=1.30", "streamlit-aggrid>=0.3", "plotly>=5.0", "pandas>=2.0"]
api = ["fastapi>=0.100", "uvicorn>=0.25"]
all = ["jj[dashboard,api]"]
```

---

## 7. 実装計画

### Phase D1: データ供給基盤

- [ ] `DashboardDataProvider` の実装
  - [ ] `get_go_table()` → DataFrame変換
  - [ ] `get_node_card()` → 詳細辞書
  - [ ] `get_plot_data()` → 数値プロパティ抽出
  - [ ] `get_property_keys()` → キー一覧
- [ ] `jj export --target dashboard-json` の実装
- [ ] テスト

### Phase D2: Streamlitダッシュボード

- [ ] `jj dashboard` CLIコマンド追加
- [ ] テーブルビュー（ag-grid + フィルター）
- [ ] カードビュー（ノード詳細 + 画像表示）
- [ ] プロットビュー（plotly散布図/線図）
- [ ] ステータスモニター

### Phase D3: REST API

- [ ] `jj serve` CLIコマンド追加
- [ ] FastAPIアプリの骨格
- [ ] /nodes, /relations エンドポイント
- [ ] /summary, /status エンドポイント
- [ ] クエリフィルター実装

### Phase D4: jj-db統合

- [ ] `jj export --target jj-db` の実装
- [ ] jj-db側にjjプロジェクトインポート機能追加
- [ ] API連携（jj serve → jj-db fetch）
- [ ] jj-db既存ビュー（テーブル/カード/グラフ）でjjデータを表示

---

## 8. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| コアデータモデル層 | → ダッシュボード層 | GraphModelを読み込んでビュー化 |
| 出力層 | ← ダッシュボード層 | dashboard-json/jj-dbエクスポートを追加 |
| Abaqusコネクター | → ダッシュボード層 | メッシュ要約・材料プロパティを表示 |
| runコマンド層 | → ダッシュボード層 | 実行ステータス・ログを表示 |

---

## 9. 設計上の注意事項

### 9.1 パフォーマンス

- graph.yamlの読み込みはキャッシュ（mtime比較）
- テーブルは遅延ロード（1000行超の場合ページネーション）
- 画像はサムネイル生成して表示

### 9.2 更新頻度

- ダッシュボードはgraph.yamlの変更を検知して自動更新
- `jj parse` 実行後に自動リフレッシュ（Streamlitのrerun）
- ステータスモニターは定期ポーリング（デフォルト30秒）

### 9.3 jj-db統合時の名前空間

- jjプロジェクトごとにjj-db上で名前空間を分離
- プロジェクト名 + パス で一意識別
- 同一ファイルの重複登録防止（upsert）

---

## 10. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [出力層仕様書](./08-export.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [プロジェクトREADME](../../README.md)
