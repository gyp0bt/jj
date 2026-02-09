[READMEへ戻る](../../README.md)

# jj-db統合設計書（jj × jj-db × Neo4j）

## 1. 背景と目的

### 1.1 現状

- **jj**: CAE業務データをグラフ化するPython CLIツール。ローカルのYAMLファイル（`.jj/storage/graph.yaml`）にグラフデータを保存。
- **jj-db**（旧jj-db）: 材料・解析データの組織横断DBを管理するNext.jsアプリケーション。別リポジトリ（`gyp0bt/jj-db`）で運用。
  - **技術スタック**: Next.js 15 / React 19 / TypeScript / Tailwind CSS v4
  - **現行DB**: SQLite（sql.js）
  - **パッケージ管理**: pnpm
  - **コンポーネント**: Storybook
  - **リンター**: Biome

### 1.2 統合の目的

1. jjが生成したグラフデータをNeo4jに投入し、jj-dbから参照可能にする
2. jj-dbの材料データをjjから参照可能にする（Neo4j経由）
3. データ型やconfig概念を両者で共通化し、不整合を防ぐ
4. 将来的にはsubmodule分離を前提としつつ、開発効率を確保する

---

## 2. アーキテクチャ概要

```
┌────────────────────┐         ┌─────────┐         ┌─────────────────────────┐
│   jj (Python CLI)  │ ──W/R──▶│  Neo4j  │◀──W/R── │  jj-db (Next.js 15)     │
│                    │         │  (共有)  │         │                         │
│ ・graph.yaml生成   │         │         │         │ ・材料DB管理(SQLite現行) │
│ ・parse/export     │         │         │         │ ・テーブル/カード        │
│ ・Streamlit        │         │         │         │ ・グラフ可視化           │
│                    │         └─────────┘         │ ・ユーザー管理           │
└────────┬───────────┘                              └────────┬────────────────┘
         │                                                   │
         └───────── 直接的なコード依存・API通信は禁止 ────────┘
                    （Neo4jスキーマ契約のみ共有）
```

### jj-dbの現行技術スタック

| 項目 | 値 |
|------|------|
| フレームワーク | Next.js 15 / React 19 / TypeScript |
| 現行DB | SQLite (sql.js) |
| スタイル | Tailwind CSS v4 |
| パッケージ管理 | pnpm |
| コンポーネント | Storybook |
| リンター | Biome |

**注意**: jj-dbは現在SQLiteを使用しており、Neo4j統合にあたっては以下の選択肢がある:

| 方式 | 説明 | メリット | デメリット |
|------|------|---------|-----------|
| **SQLite + Neo4j併用** | 既存SQLiteは維持、グラフ関係のみNeo4jに投入 | 既存機能への影響なし | 2つのDB管理が必要 |
| **Neo4jへ移行** | SQLiteを廃止しNeo4jに一本化 | 管理が統一 | 移行コスト大、jj-dbの大幅改修が必要 |
| **SQLite→Neo4j同期** | SQLiteをマスタとし、Neo4jへ定期同期 | 既存コード最小変更 | 同期ロジックの実装が必要 |

**推奨**: SQLite + Neo4j併用（Phase N3）。jj-db側はSQLiteで既存機能を維持しつつ、jjとの通信にのみNeo4jを使用する。

### 設計原則

| 原則 | 説明 |
|------|------|
| **Neo4j Only** | jjとjj-dbは互いのコード・APIを直接呼び出さない。Neo4jを唯一のデータ通信手段とする。jj serverのAPIをjj-db側から叩くことはしない |
| **スキーマ契約** | Neo4jのノードラベル・リレーションシップタイプ・プロパティキーを共通仕様として定義 |
| **共有型定義** | データ型（Node/Relation等）とconfig構造を`shared/`パッケージで共通化 |
| **独立デプロイ** | jjとjj-dbはそれぞれ単独で動作可能。Neo4jがなくても既存機能は使える |
| **分離準備** | 将来のsubmodule化を前提に、依存方向を制限する |

---

## 3. リポジトリ構成方針

### 3.1 判断結果: 一時的なモノレポ方式

**理由**: jj-dbはパブリック化されたが、この開発環境のGitプロキシがjjリポジトリのみを認可しており、jj-dbへのgit clone/pushが不可（`repository not authorized`）。
submoduleの追加・クローン・プッシュができないため、開発フェーズでは同一リポジトリ内に配置する。
WebFetch経由でのリポジトリ閲覧は可能なため、jj-dbのコード構造は把握済み。

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
| `jj-db` → `shared/` | 参照OK（共有型・スキーマを使用、jj-dbリポジトリ側で実装） |
| `services/` → `jj-db` | **禁止**（Neo4j経由でのみ通信） |
| `jj-db` → `services/` | **禁止**（Neo4j経由でのみ通信） |
| `shared/` → `services/` | **禁止**（逆依存禁止） |
| `shared/` → `jj-db` | **禁止**（逆依存禁止） |

> **注**: jj-dbの実装はjj-dbリポジトリ（gyp0bt/jj-db）で行う。jjリポジトリ内に`jj_db/`ディレクトリは作成しない。

### 3.4 shared/ パッケージの共有方式

`shared/`パッケージはNeo4jスキーマ契約を定義する。将来的にはpip/npm両対応の独立パッケージ化を検討する。

- 現状: jjリポジトリ内の`shared/`に配置
- 将来: 独立パッケージ化し、jj-dbからもnpmまたはpip経由で参照

---

## 4. Neo4jスキーマ設計

### 4.1 ノードラベル

jjとjj-dbが共有するNeo4jノードラベル定義。

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

// --- jj-db由来のノード ---
(:JJDBMaterial {
    jjdb_id: INTEGER,         // jj-db内部ID
    name: STRING,
    category: STRING,        // "metal", "polymer", "ceramic", ...
    // 物性値プロパティ
})

(:JJDBTest {
    jjdb_id: INTEGER,
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

// jj-jj-db間のクロスリレーション
(:JJMaterial)-[:MATCHES]->(:JJDBMaterial)   // 材料名の紐付け
(:JJFile)-[:REFERENCES]->(:JJDBTest)        // 試験データへの参照
```

### 4.3 制約とインデックス

```cypher
// 一意性制約
CREATE CONSTRAINT jjfile_unique IF NOT EXISTS
FOR (n:JJFile) REQUIRE (n.project, n.jj_id) IS UNIQUE;

CREATE CONSTRAINT jjmaterial_unique IF NOT EXISTS
FOR (n:JJMaterial) REQUIRE (n.project, n.jj_id) IS UNIQUE;

CREATE CONSTRAINT matmaterial_unique IF NOT EXISTS
FOR (n:JJDBMaterial) REQUIRE n.jjdb_id IS UNIQUE;

// インデックス
CREATE INDEX jjfile_name IF NOT EXISTS FOR (n:JJFile) ON (n.name);
CREATE INDEX jjfile_type IF NOT EXISTS FOR (n:JJFile) ON (n.type);
CREATE INDEX jjfile_project IF NOT EXISTS FOR (n:JJFile) ON (n.project);
```

---

## 5. 共有パッケージ設計（`shared/`）

### 5.1 `shared/neo4j_schema.py`

```python
"""Neo4jスキーマ定義 - jjとjj-dbの共有契約"""

# ノードラベル
class NodeLabel:
    JJ_FILE = "JJFile"
    JJ_MATERIAL = "JJMaterial"
    JJ_RUN = "JJRun"
    JJ_TAG = "JJTag"
    MAT_MATERIAL = "JJDBMaterial"
    MAT_TEST = "JJDBTest"

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
    jjdb_id: int | None = None
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
    """jjとjj-dbの共有設定"""
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
        """jj-dbが投入した材料データを読み取り"""
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

## 7. jj-db側の実装計画

### 7.1 Neo4jクライアント（TypeScript / Next.js API Route）

jj-dbはNext.js 15 / TypeScriptで構築されているため、Neo4jクライアントもTypeScriptで実装する。

```typescript
// src/lib/neo4j-client.ts
import neo4j, { Driver } from 'neo4j-driver';

export class JJDbNeo4jClient {
  private driver: Driver;

  constructor(uri: string, user: string, password: string) {
    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password));
  }

  /** 材料データをNeo4jに投入 */
  async writeMaterials(materials: JJDBMaterial[]): Promise<void> { ... }

  /** jjが投入したファイルデータを読み取り */
  async readJJFiles(project?: string): Promise<JJFile[]> { ... }

  /** 材料データとjjファイルをMATCHESリレーションで紐付け */
  async linkMaterialToJJ(jjdbId: number, jjId: number, project: string): Promise<void> { ... }
}
```

```typescript
// src/app/api/neo4j/route.ts (Next.js API Route)
import { JJDbNeo4jClient } from '@/lib/neo4j-client';

export async function GET(request: Request) {
  const client = new JJDbNeo4jClient(
    process.env.NEO4J_URI!, process.env.NEO4J_USER!, process.env.NEO4J_PASSWORD!
  );
  // ...
}
```

### 7.2 jj-dbの現行アーキテクチャとの統合

jj-dbは現在SQLite（sql.js）をDBとして使用しているため:

- **SQLiteは維持**: 既存の材料・プロジェクト管理機能はSQLiteのまま運用
- **Neo4jは追加**: jjとのグラフ連携にのみNeo4jを使用
- **同期方向**: SQLiteの材料データ → Neo4jに投入、Neo4jのjjデータ → jj-dbフロントで表示
- **パッケージ追加**: `neo4j-driver`（npm）をjj-dbに追加

---

## 8. コンテキスト肥大化への対策

### 8.1 問題認識

モノレポ化すると、AIアシスタント（Codex/Claude Code）のコンテキストウィンドウにjjとjj-db両方のコードが入り、肥大化する恐れがある。

### 8.2 対策

| 対策 | 詳細 |
|------|------|
| **ディレクトリ分離** | `jj_db/` を独立ディレクトリに配置。jj作業時は `jj_db/` を意識しなくてよい |
| **独立したREADME** | `jj_db/README.md` にjj-db固有の情報を集約。jjのREADMEとは分離 |
| **共有層を最小化** | `shared/` は型定義とスキーマ定義のみ。ビジネスロジックを入れない |
| **テスト分離** | `tests/` と `jj_db/tests/` を分離。CIも独立実行 |
| **.gitignore活用** | 一方の作業時に他方のキャッシュ等が影響しないようにする |
| **早期submodule化** | jj-dbリポジトリへのアクセスが可能になり次第、即座にsubmodule化する |
| **statusファイルで作業範囲明示** | statusに「今回の作業はjj側のみ」等を明記し、AIが不要なコードを読まないようにする |

### 8.3 段階的移行

```
Phase 1（現在）: jj_db/ を jj リポジトリ内に配置
    ↓ アクセス復旧後
Phase 2: jj_db/ を別リポジトリに切り出し、submodule化
    ↓ 安定後
Phase 3: shared/ も独立パッケージ化（pip install jj-shared）
```

---

## 9. 通信フロー

### 9.1 jj → Neo4j → jj-db（解析データの共有）

```
1. ユーザーが `jj parse` でグラフ生成
2. ユーザーが `jj export --target neo4j` でNeo4jに投入
3. jj-dbがNeo4jを参照し、jjプロジェクトデータを表示
```

### 9.2 jj-db → Neo4j → jj（材料データの参照）

```
1. jj-dbで材料データを登録 → Neo4jに投入
2. ユーザーが `jj import --source neo4j` で材料データを取得
3. jjのGraphModelに材料ノードを追加
4. 材料名の一致で自動リンク（MATCHES関係）
```

### 9.3 双方向同期

```
1. jj parse → jj export neo4j （定期的）
2. jj-db → Neo4j write materials （材料登録時）
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

### Phase N1: 基盤構築 ✅ (status-037)

- [x] `shared/` パッケージ作成（neo4j_schema.py, types.py, config.py）
- [x] `neo4j/docker-compose.yml` 作成
- [x] `neo4j/init/01-schema.cypher` 作成（制約/インデックス）
- [x] requirements.txtに`neo4j`ドライバ追加

### Phase N2: jj Neo4jエクスポーター ✅ (status-037)

- [x] `services/connectors/neo4j.py` 実装（Neo4jConnector）
- [x] `jj export --target neo4j` CLI追加
- [x] `jj export --target cypher` CLI追加
- [x] GraphModel → Neo4j Cypherマッピング実装
- [x] upsert（既存データの更新）対応（UNWIND + MERGE）
- [x] テスト（71件: 69パス + 2スキップ）

### Phase N3: jj-db Neo4jクライアント（jj-db側で実装）

- [ ] jj-dbリポジトリ内でNeo4jクライアント実装（TypeScript）
- [ ] 材料データのNeo4j投入
- [ ] jjデータの読み取りインターフェース

> **注**: jj-db側の実装はjj-dbリポジトリで行う。jjリポジトリ内にjj_db/ディレクトリは作成しない。

### Phase N4: クロスリレーション

- [ ] 材料名マッチングロジック（MATCHES関係の自動生成）
- [ ] `jj import --source neo4j` 実装
- [ ] jj-db側のjjプロジェクトビュー

### Phase N5: shared/パッケージの独立化

- [ ] shared/ の独立パッケージ化検討（pip/npm両対応）
- [ ] CI/CD分離

---

## 12. 既存ロードマップとの関係

| 既存Phase | DB統合との関係 |
|-----------|---------------|
| Phase 2.5 (ダッシュボード) | jj側ローカルダッシュボード。jj-dbとのAPI連携は行わない |
| Phase 2.N (DB統合) | 本設計書の具体化。Neo4j経由のデータ共有がjj-db統合の唯一の手段 |
| Phase 4-12 (出力層基盤) | Neo4jExporterは出力層の一部として実装済み（Phase 2.N N2） |

> **注**: 旧D3（jj serve REST API）・D4（jj-db API統合）は廃止。jj-dbとの通信はNeo4jのみで行う。

---

## 13. 設計上の懸念・確認事項

- [ ] jj-dbの既存データモデル（Node/Edge型）との詳細マッピング: jj-dbのコードベースへのアクセスが復旧してから具体化
- [ ] Neo4jのバージョン: Community Edition 5.x を想定。APOC プラグインの要否
- [ ] jj-dbのバックエンドAPI: Python（FastAPI）か Node.js か → jj-dbの既存構成に依存
- [ ] 材料名マッチングの精度: 完全一致 or ファジーマッチ（将来的にはLLMベースのマッチング？）
- [ ] Neo4jの認証管理: ローカル開発時はデフォルトパスワード、本番はSecret管理
- [ ] jj-dbリポジトリへのアクセス復旧時期の確認

---

## 14. 参考資料

- [ダッシュボード仕様書](./09-dashboard.md)
- [出力層仕様書](./08-export.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [ロードマップ](../roadmap.md)
- [プロジェクトREADME](../../README.md)
