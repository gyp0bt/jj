[READMEへ戻る](../../README.md)

# jj-db統合設計書（jj × mat-db × Neo4j）

## 1. 背景と目的

### 1.1 現状

- **jj**: CAE業務データをグラフ化するPython CLIツール。ローカルのYAMLファイル（`.jj/storage/graph.yaml`）にグラフデータを保存。
- **mat-db**: 材料・解析データの組織横断DBを管理するNext.jsアプリケーション。別リポジトリで運用。

### 1.2 統合の目的

1. jjが生成したグラフデータをNeo4jに投入し、mat-dbから参照可能にする
2. mat-dbの材料データをjjから参照可能にする（Neo4j経由）
3. データ型やconfig概念を両者で共通化し、不整合を防ぐ
4. 将来的にはsubmodule分離を前提としつつ、開発効率を確保する

---

## 2. アーキテクチャ概要

```
┌────────────────────┐         ┌─────────┐         ┌────────────────────┐
│   jj (Python CLI)  │ ──W/R──▶│  Neo4j  │◀──W/R── │  mat-db (Next.js)  │
│                    │         │  (共有)  │         │                    │
│ ・graph.yaml生成   │         │         │         │ ・材料DB管理       │
│ ・parse/export     │         │         │         │ ・テーブル/カード   │
│ ・Streamlit        │         │         │         │ ・グラフ可視化     │
│ ・FastAPI          │         └─────────┘         │ ・ユーザー管理     │
└────────┬───────────┘                              └────────┬───────────┘
         │                                                   │
         └───────── 直接的なコード依存は禁止 ─────────────────┘
                    （Neo4jスキーマ契約のみ共有）
```

### 設計原則

| 原則 | 説明 |
|------|------|
| **Neo4j Only** | jjとmat-dbは互いのコード・APIを直接呼び出さない。Neo4jを唯一の通信手段とする |
| **スキーマ契約** | Neo4jのノードラベル・リレーションシップタイプ・プロパティキーを共通仕様として定義 |
| **共有型定義** | データ型（Node/Relation等）とconfig構造を`shared/`パッケージで共通化 |
| **独立デプロイ** | jjとmat-dbはそれぞれ単独で動作可能。Neo4jがなくても既存機能は使える |
| **分離準備** | 将来のsubmodule化を前提に、依存方向を制限する |

---

## 3. リポジトリ構成方針

### 3.1 判断結果: 一時的なモノレポ方式

**理由**: この環境からmat-dbのプライベートリポジトリへのアクセスが不可（`repository not authorized`）。
submoduleの追加・クローン・プッシュができないため、開発フェーズでは同一リポジトリ内に配置する。

### 3.2 ディレクトリ構成

```
jj/                              # リポジトリルート
├── README.md
├── main.py                      # jj CLIエントリポイント
├── requirements.txt
├── cli/                         # jj CLI
├── config/                      # jj 設定ローダー
├── services/                    # jj サービス群
├── jj_types/                    # jj 型定義
├── pymesh/                      # メッシュ操作ライブラリ
├── tests/                       # jj テスト
├── docs/                        # jj ドキュメント
│
├── shared/                      # ★ 共通パッケージ（新規）
│   ├── __init__.py
│   ├── neo4j_schema.py          # Neo4jスキーマ定義（ラベル/関係/プロパティ）
│   ├── types.py                 # 共有データ型（jj_typesから昇格する型）
│   └── config.py                # 共有config定義
│
├── mat_db/                      # ★ mat-dbモジュール（新規、将来submodule化）
│   ├── README.md
│   ├── __init__.py
│   ├── package.json             # Next.js依存（mat-dbフロントエンド）
│   ├── neo4j_client.py          # Neo4jアクセス層（Python）
│   └── ...                      # mat-db既存コード
│
└── neo4j/                       # ★ Neo4j関連設定（新規）
    ├── docker-compose.yml       # Neo4j起動設定
    ├── init/                    # 初期化スクリプト（制約/インデックス定義）
    │   └── 01-schema.cypher
    └── README.md
```

### 3.3 分離ルール

| ルール | 詳細 |
|--------|------|
| `services/` → `shared/` | 参照OK（共有型・スキーマを使用） |
| `mat_db/` → `shared/` | 参照OK（共有型・スキーマを使用） |
| `services/` → `mat_db/` | **禁止**（Neo4j経由でのみ通信） |
| `mat_db/` → `services/` | **禁止**（Neo4j経由でのみ通信） |
| `shared/` → `services/` | **禁止**（逆依存禁止） |
| `shared/` → `mat_db/` | **禁止**（逆依存禁止） |

### 3.4 submodule移行計画

将来、mat-dbリポジトリへのアクセスが可能になった時点で以下を実施:

1. `mat_db/` を別リポジトリに切り出す
2. `.gitmodules` に `mat_db` を追加
3. `shared/` は独立パッケージ（pip installable）化するか、両リポジトリにコピーを持つ
   - 推奨: `shared/` も独立リポジトリ化 → 両者がsubmoduleとして参照

```
# 将来の.gitmodules
[submodule "mat_db"]
    path = mat_db
    url = <mat-db-repo-url>
[submodule "shared"]
    path = shared
    url = <shared-repo-url>
```

---

## 4. Neo4jスキーマ設計

### 4.1 ノードラベル

jjとmat-dbが共有するNeo4jノードラベル定義。

```cypher
// --- jj由来のノード ---
(:JJFile {
    jj_id: INTEGER,          // jj内部ID
    name: STRING,            // ファイル名
    type: STRING,            // "go", "mesh", "material", "folder", ...
    format: STRING,          // "inp", "csv", "png", ...
    project: STRING,         // jjプロジェクトパス
    active: BOOLEAN,
    // 動的プロパティ（index, version, RF3, temperature, ...）
})

(:JJMaterial {
    jj_id: INTEGER,
    name: STRING,            // 材料名
    project: STRING,
    // Abaqusキーワードから抽出したプロパティ
})

(:JJRun {
    jj_id: INTEGER,
    command: STRING,
    duration: FLOAT,
    user: STRING,
    host: STRING,
    started_at: DATETIME,
    project: STRING,
})

// --- mat-db由来のノード ---
(:MatMaterial {
    mat_id: INTEGER,         // mat-db内部ID
    name: STRING,
    category: STRING,        // "metal", "polymer", "ceramic", ...
    // 物性値プロパティ
})

(:MatTest {
    mat_id: INTEGER,
    test_type: STRING,       // "tensile", "fatigue", ...
    // 試験条件・結果
})
```

### 4.2 リレーションシップタイプ

```cypher
// jj内部のリレーション（既存のRelation.labelと対応）
(:JJFile)-[:INCLUDES]->(:JJFile)           // includes
(:JJFile)-[:HAS_OUTPUT]->(:JJFile)         // has_output
(:JJFile)-[:DERIVED_FROM]->(:JJFile)       // derived_from
(:JJFile)-[:RESULT_OF]->(:JJFile)          // result_of
(:JJFile)-[:CONTAINS]->(:JJFile)           // contains (folder)
(:JJFile)-[:TAGGED]->(:JJTag)              // tagged
(:JJFile)-[:USES_MATERIAL]->(:JJMaterial)  // material relation
(:JJFile)-[:EXECUTED_BY]->(:JJRun)         // run relation
(:JJFile)-[:GENERATED]->(:JJFile)          // generated (by run)

// jj-mat-db間のクロスリレーション
(:JJMaterial)-[:MATCHES]->(:MatMaterial)   // 材料名の紐付け
(:JJFile)-[:REFERENCES]->(:MatTest)        // 試験データへの参照
```

### 4.3 制約とインデックス

```cypher
// 一意性制約
CREATE CONSTRAINT jjfile_unique IF NOT EXISTS
FOR (n:JJFile) REQUIRE (n.project, n.jj_id) IS UNIQUE;

CREATE CONSTRAINT jjmaterial_unique IF NOT EXISTS
FOR (n:JJMaterial) REQUIRE (n.project, n.jj_id) IS UNIQUE;

CREATE CONSTRAINT matmaterial_unique IF NOT EXISTS
FOR (n:MatMaterial) REQUIRE n.mat_id IS UNIQUE;

// インデックス
CREATE INDEX jjfile_name IF NOT EXISTS FOR (n:JJFile) ON (n.name);
CREATE INDEX jjfile_type IF NOT EXISTS FOR (n:JJFile) ON (n.type);
CREATE INDEX jjfile_project IF NOT EXISTS FOR (n:JJFile) ON (n.project);
```

---

## 5. 共有パッケージ設計（`shared/`）

### 5.1 `shared/neo4j_schema.py`

```python
"""Neo4jスキーマ定義 - jjとmat-dbの共有契約"""

# ノードラベル
class NodeLabel:
    JJ_FILE = "JJFile"
    JJ_MATERIAL = "JJMaterial"
    JJ_RUN = "JJRun"
    JJ_TAG = "JJTag"
    MAT_MATERIAL = "MatMaterial"
    MAT_TEST = "MatTest"

# リレーションシップタイプ
class RelType:
    INCLUDES = "INCLUDES"
    HAS_OUTPUT = "HAS_OUTPUT"
    DERIVED_FROM = "DERIVED_FROM"
    RESULT_OF = "RESULT_OF"
    CONTAINS = "CONTAINS"
    TAGGED = "TAGGED"
    USES_MATERIAL = "USES_MATERIAL"
    EXECUTED_BY = "EXECUTED_BY"
    GENERATED = "GENERATED"
    # クロスリレーション
    MATCHES = "MATCHES"
    REFERENCES = "REFERENCES"

# jj Relation.label → Neo4j RelType マッピング
LABEL_TO_RELTYPE = {
    "includes": RelType.INCLUDES,
    "has_output": RelType.HAS_OUTPUT,
    "derived_from": RelType.DERIVED_FROM,
    "result_of": RelType.RESULT_OF,
    "contains": RelType.CONTAINS,
    "tagged": RelType.TAGGED,
    "uses_material": RelType.USES_MATERIAL,
    "executed_by": RelType.EXECUTED_BY,
    "generated": RelType.GENERATED,
}
```

### 5.2 `shared/types.py`

jj_typesの`Node`/`Relation`/`GraphModel`をそのまま再エクスポートするか、
Neo4j向けの拡張型を追加定義する。

```python
"""共有データ型"""
from pydantic import BaseModel, Field
from typing import Any

# 既存jj_typesからの再エクスポート
from jj_types import Node, Relation, GraphModel

# Neo4j投入用の拡張型
class Neo4jNodeData(BaseModel):
    """Neo4jに投入するノードデータ"""
    label: str                                # NodeLabel値
    properties: dict[str, Any]
    jj_id: int | None = None
    mat_id: int | None = None
    project: str | None = None

class Neo4jRelationData(BaseModel):
    """Neo4jに投入するリレーションデータ"""
    rel_type: str                             # RelType値
    source_jj_id: int
    target_jj_id: int
    project: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
```

### 5.3 `shared/config.py`

```python
"""共有設定定義"""
from pydantic import BaseModel

class Neo4jConfig(BaseModel):
    """Neo4j接続設定"""
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

class SharedConfig(BaseModel):
    """jjとmat-dbの共有設定"""
    neo4j: Neo4jConfig = Neo4jConfig()
    project_name: str = ""                    # jjプロジェクト識別子
```

---

## 6. jj側の実装計画

### 6.1 Neo4jExporter（`services/connectors/neo4j_connector.py`）

既存の08-export.md仕様を拡張し、Neo4jへの直接書き込みを実装。

```python
class Neo4jConnector:
    """jj GraphModel → Neo4j 書き込み"""

    def __init__(self, config: Neo4jConfig, project: str):
        self.driver = GraphDatabase.driver(config.uri, auth=(config.user, config.password))
        self.project = project

    def export_graph(self, graph: GraphModel) -> None:
        """GraphModelをNeo4jにupsert"""

    def sync_incremental(self, old_graph: GraphModel, new_graph: GraphModel) -> None:
        """差分のみ更新"""

    def read_materials(self) -> list[dict]:
        """mat-dbが投入した材料データを読み取り"""
```

### 6.2 CLIコマンド追加

```bash
jj export --target neo4j           # Neo4jにグラフをエクスポート
jj export --target neo4j --sync    # 差分同期
jj import --source neo4j           # Neo4jから材料データを取得
```

### 6.3 依存パッケージ追加

```
neo4j>=5.0                         # Neo4j Pythonドライバ
```

---

## 7. mat-db側の実装計画

### 7.1 Neo4jクライアント（mat_db/neo4j_client.py）

```python
class MatDbNeo4jClient:
    """mat-db → Neo4j 読み書き"""

    def write_materials(self, materials: list[dict]) -> None:
        """材料データをNeo4jに投入"""

    def read_jj_files(self, project: str | None = None) -> list[dict]:
        """jjが投入したファイルデータを読み取り"""

    def link_material_to_jj(self, mat_id: int, jj_id: int, project: str) -> None:
        """材料データとjjファイルをMATCHESリレーションで紐付け"""
```

### 7.2 Next.js側の対応

mat-dbのフロントエンドからNeo4jを参照するために:
- バックエンドAPI（Python or Node.js）を経由してNeo4jクエリを実行
- jjプロジェクト一覧の取得、ファイルノードの表示

---

## 8. コンテキスト肥大化への対策

### 8.1 問題認識

モノレポ化すると、AIアシスタント（Codex/Claude Code）のコンテキストウィンドウにjjとmat-db両方のコードが入り、肥大化する恐れがある。

### 8.2 対策

| 対策 | 詳細 |
|------|------|
| **ディレクトリ分離** | `mat_db/` を独立ディレクトリに配置。jj作業時は `mat_db/` を意識しなくてよい |
| **独立したREADME** | `mat_db/README.md` にmat-db固有の情報を集約。jjのREADMEとは分離 |
| **共有層を最小化** | `shared/` は型定義とスキーマ定義のみ。ビジネスロジックを入れない |
| **テスト分離** | `tests/` と `mat_db/tests/` を分離。CIも独立実行 |
| **.gitignore活用** | 一方の作業時に他方のキャッシュ等が影響しないようにする |
| **早期submodule化** | mat-dbリポジトリへのアクセスが可能になり次第、即座にsubmodule化する |
| **statusファイルで作業範囲明示** | statusに「今回の作業はjj側のみ」等を明記し、AIが不要なコードを読まないようにする |

### 8.3 段階的移行

```
Phase 1（現在）: mat_db/ を jj リポジトリ内に配置
    ↓ アクセス復旧後
Phase 2: mat_db/ を別リポジトリに切り出し、submodule化
    ↓ 安定後
Phase 3: shared/ も独立パッケージ化（pip install jj-shared）
```

---

## 9. 通信フロー

### 9.1 jj → Neo4j → mat-db（解析データの共有）

```
1. ユーザーが `jj parse` でグラフ生成
2. ユーザーが `jj export --target neo4j` でNeo4jに投入
3. mat-dbがNeo4jを参照し、jjプロジェクトデータを表示
```

### 9.2 mat-db → Neo4j → jj（材料データの参照）

```
1. mat-dbで材料データを登録 → Neo4jに投入
2. ユーザーが `jj import --source neo4j` で材料データを取得
3. jjのGraphModelに材料ノードを追加
4. 材料名の一致で自動リンク（MATCHES関係）
```

### 9.3 双方向同期

```
1. jj parse → jj export neo4j （定期的）
2. mat-db → Neo4j write materials （材料登録時）
3. Neo4jのMATCHESクエリで自動マッチング
```

---

## 10. Docker Compose構成

```yaml
# neo4j/docker-compose.yml
version: '3.8'
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"   # ブラウザ
      - "7687:7687"   # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - ./init:/docker-entrypoint-initdb.d
volumes:
  neo4j_data:
```

---

## 11. 実装フェーズ

### Phase N1: 基盤構築

- [ ] `shared/` パッケージ作成（neo4j_schema.py, types.py, config.py）
- [ ] `neo4j/docker-compose.yml` 作成
- [ ] `neo4j/init/01-schema.cypher` 作成（制約/インデックス）
- [ ] requirements.txtに`neo4j`ドライバ追加

### Phase N2: jj Neo4jエクスポーター

- [ ] `services/connectors/neo4j_connector.py` 実装
- [ ] `jj export --target neo4j` CLI追加
- [ ] GraphModel → Neo4j Cypherマッピング実装
- [ ] upsert（既存データの更新）対応
- [ ] テスト

### Phase N3: mat-db Neo4jクライアント

- [ ] `mat_db/` ディレクトリ構築
- [ ] `mat_db/neo4j_client.py` 実装
- [ ] 材料データのNeo4j投入
- [ ] jjデータの読み取りインターフェース

### Phase N4: クロスリレーション

- [ ] 材料名マッチングロジック（MATCHES関係の自動生成）
- [ ] `jj import --source neo4j` 実装
- [ ] mat-db側のjjプロジェクトビュー

### Phase N5: submodule移行（アクセス復旧後）

- [ ] mat_db/ を別リポジトリに切り出し
- [ ] .gitmodules設定
- [ ] shared/ の独立パッケージ化検討
- [ ] CI/CD分離

---

## 12. 既存ロードマップとの関係

| 既存Phase | DB統合との関係 |
|-----------|---------------|
| Phase 2.5 D3 (jj serve) | Neo4jエクスポーターの前段。REST APIとNeo4j書き込みは共存可能 |
| Phase 2.5 D4 (mat-db統合) | 本設計書がD4の詳細化。Neo4j経由の統合がD4の具体策 |
| Phase 4-12 (出力層基盤) | Neo4jExporterは出力層の一部として実装 |

---

## 13. 設計上の懸念・確認事項

- [ ] mat-dbの既存データモデル（Node/Edge型）との詳細マッピング: mat-dbのコードベースへのアクセスが復旧してから具体化
- [ ] Neo4jのバージョン: Community Edition 5.x を想定。APOC プラグインの要否
- [ ] mat-dbのバックエンドAPI: Python（FastAPI）か Node.js か → mat-dbの既存構成に依存
- [ ] 材料名マッチングの精度: 完全一致 or ファジーマッチ（将来的にはLLMベースのマッチング？）
- [ ] Neo4jの認証管理: ローカル開発時はデフォルトパスワード、本番はSecret管理
- [ ] mat-dbリポジトリへのアクセス復旧時期の確認

---

## 14. 参考資料

- [ダッシュボード仕様書](./09-dashboard.md)
- [出力層仕様書](./08-export.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [ロードマップ](../roadmap.md)
- [プロジェクトREADME](../../README.md)
