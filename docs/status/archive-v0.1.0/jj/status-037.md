[READMEへ戻る](../../README.md)

# status-037: Neo4jエクスポート実装（Phase N1 + N2）

**日付**: 2026-02-08

## 概要

jjrv統合設計（status-036）に基づき、Neo4jエクスポートの基盤構築（Phase N1）とエクスポーター実装（Phase N2）を完了した。

## 実装内容

### Phase N1: 基盤構築

| 成果物 | 内容 |
|--------|------|
| `shared/__init__.py` | 共有パッケージ初期化（NodeLabel, RelType, Neo4jConfig等のエクスポート） |
| `shared/neo4j_schema.py` | Neo4jスキーマ定義（ノードラベル、リレーションシップタイプ、マッピング関数） |
| `shared/types.py` | Neo4j投入用データ型（Neo4jNodeData, Neo4jRelationData） |
| `shared/config.py` | Neo4j接続設定（Neo4jConfig）、.jj/config/config.yamlからの読み込み対応 |
| `neo4j/docker-compose.yml` | Neo4j Community Edition 5.x のDocker設定 |
| `neo4j/init/01-schema.cypher` | 制約・インデックスの初期化スクリプト |
| `requirements.txt` | `neo4j>=5.0.0` 追加 |

### Phase N2: Neo4jエクスポーター

| 成果物 | 内容 |
|--------|------|
| `services/connectors/neo4j.py` | Neo4jConnectorクラス（メイン実装） |
| `services/connectors/__init__.py` | Neo4jConnectorのエクスポート追加 |
| `cli/graph.py` | `--target neo4j/cypher` 追加、Neo4j固有CLIオプション追加 |
| `tests/test_neo4j_connector.py` | テスト71件（69パス + 2スキップ） |

### Neo4jConnectorの機能

| 機能 | 説明 |
|------|------|
| `export_graph()` | GraphModel → Neo4jへのupsert（バッチ処理）|
| `export_cypher()` | GraphModel → Cypherファイル出力（Neo4j不要の代替手段）|
| `verify_connection()` | Neo4j接続確認 |
| `get_project_stats()` | プロジェクトのノード/リレーション統計取得 |

### CLIコマンド

```bash
jj export --target neo4j              # Neo4jに直接書き込み
jj export --target neo4j --clear      # 既存データ削除後に投入
jj export --target neo4j --parse      # parse → Neo4j投入
jj export --target cypher             # Cypherファイル出力（.jj/storage/export.cypher）
jj export --target cypher -o out.cypher  # 出力先指定

# Neo4j接続オプション
jj export --target neo4j --neo4j-uri bolt://host:7687 --neo4j-user admin --neo4j-password secret
```

### スキーマ契約

#### ノードラベルマッピング（jj Node.type → Neo4j Label）

| jj Node.type | Neo4j Label |
|-------------|-------------|
| calculation_input, mesh, material, step, result, asset, folder, output, other | JJFile |
| abaqus_material | JJMaterial |
| run | JJRun |
| tag | JJTag |

#### リレーションマッピング（jj Relation.label → Neo4j RelType）

| jj label | Neo4j RelType |
|----------|---------------|
| next_version | NEXT_VERSION |
| same_index_group | SAME_INDEX_GROUP |
| includes | INCLUDES |
| has_output | HAS_OUTPUT |
| derived_from | DERIVED_FROM |
| result_of | RESULT_OF |
| contains | CONTAINS |
| tagged | TAGGED |
| uses_material | USES_MATERIAL |
| executed_by | EXECUTED_BY |
| generated | GENERATED |
| defined_in | DEFINED_IN |
| assigned_to | ASSIGNED_TO |
| mentioned_in | MENTIONED_IN |

### プロパティ変換ルール

| jj型 | Neo4j型 | 備考 |
|------|---------|------|
| str | String | そのまま |
| int/float | Integer/Float | そのまま |
| bool | Boolean | そのまま |
| list[同一型] | List | 同一型リストのみ |
| list[混在型] | String (JSON) | JSON文字列化 |
| dict | String (JSON) | JSON文字列化 |
| None | 除外 | プロパティに含めない |

## テスト結果

| テストスイート | 結果 |
|---------------|------|
| test_neo4j_connector.py | **69パス + 2スキップ** |
| 既存テスト全体 | **294パス + 18スキップ** |
| リグレッション | なし |

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `shared/__init__.py` | 新規 |
| `shared/neo4j_schema.py` | 新規 |
| `shared/types.py` | 新規 |
| `shared/config.py` | 新規 |
| `neo4j/docker-compose.yml` | 新規 |
| `neo4j/init/01-schema.cypher` | 新規 |
| `services/connectors/neo4j.py` | 新規 |
| `services/connectors/__init__.py` | 変更: Neo4jConnectorエクスポート追加 |
| `cli/graph.py` | 変更: neo4j/cypherターゲット追加、Neo4j固有オプション追加 |
| `requirements.txt` | 変更: neo4j>=5.0.0追加 |
| `tests/test_neo4j_connector.py` | 新規 |
| `docs/status/status-037.md` | 新規: 本ステータス |
| `docs/roadmap.md` | 変更: N1/N2チェック更新 |
| `README.md` | 変更: ステータスリンク追加 |

## TODO / 次のステップ

- [ ] Phase N3: jjrv Neo4jクライアント（TypeScript側、jjrvリポジトリアクセス復旧後）
- [ ] Phase N4: クロスリレーション（材料マッチング、`jj import --source neo4j`）
- [ ] Phase N5: submodule移行
- [ ] Neo4j接続設定の`.jj/config/config.yaml`への組み込みドキュメント化
- [ ] `jj export --target neo4j --sync`（差分同期）の実装
- [ ] Streamlitダッシュボードとの連携（Phase 2.5 D1-D2）

## 確認事項・設計上の懸念

- Neo4jサーバーが立ち上がっていない場合、`--target neo4j`は接続エラーとなる。`--target cypher`で代替可能
- Cypherファイルは Neo4j Browser や cypher-shell で直接実行可能
- バッチupsertはUNWINDを使用しており、大量ノード（100件テスト済）でも効率的に動作する
- Neo4jドライバは遅延初期化されるため、`--target cypher`使用時はneo4jパッケージは不要
