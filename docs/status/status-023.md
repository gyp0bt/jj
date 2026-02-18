[← status-index](status-index.md)

# status-023: status-022 TODO実行 — 接続設定UI・検索アダプター・統合テスト・表示名改善

- **日付**: 2026-02-18
- **マイルストーン**: M3
- **ブランチ**: claude/execute-status-todos-AZ5Am

---

## 概要

status-022のTODO項目を実行。Neo4j接続設定UI（6-N-02）、Cypher全文検索アダプター（6-N-07）、factory切替・ドライバテスト、jj由来プロパティキーの日本語表示名改善を実装。

## 実施内容

### 1. jj側 pyproject.toml neo4j依存バージョン統一

- `neo4j>=5.0.0` → `neo4j>=5.0.0,<7.0.0` にバージョン上限を明確化
- Python neo4j driver 6.1.0 / TypeScript neo4j-driver ^6.0.1 / Docker neo4j:5-community の互換性を確認

### 2. Neo4j Docker起動・接続検証

- Docker daemonは利用可能だが、iptables/NAT制約（コンテナ環境内）により起動不可
- エンドツーエンド検証はDocker環境を持つローカルWSLでの実施が必要 → TODO継続

### 3. 接続設定UI (6-N-02)

#### neo4j-driver.ts 拡張
- `Neo4jConfig` 型エクスポート
- `runtimeConfig`: API経由でのランタイム設定オーバーライド
- `getCurrentConfig()`: 現在の接続設定取得（パスワードマスク）
- `setRuntimeConfig()`: 設定更新 + ドライバリセット
- `testConnection()`: 独立した接続テスト（既存ドライバに影響なし）

#### factory.ts 拡張
- `runtimeDataSource`: ランタイムデータソース切替
- `getCurrentDataSourceType()`: 現在のデータソース種別取得
- `switchDataSource()`: ランタイム切替 + シングルトンリセット

#### APIルート
- `GET /api/datasource` — 現在のデータソース状態（タイプ、Neo4j接続情報、接続状態）
- `POST /api/datasource/test` — Neo4j接続テスト（URI/user/password指定）
- `POST /api/datasource/switch` — データソース切替（sqlite ↔ neo4j）

#### クライアントAPI (`datasource-api.ts`)
- `getDataSourceStatus()`, `testNeo4jConnection()`, `switchDataSource()`

#### UIコンポーネント (`DataSourceSettingsModal`)
- 現在のデータソースステータス表示（SQLite/Neo4j + 接続状態）
- Neo4j Bolt接続設定フォーム（URI, ユーザー, パスワード）
- 接続テストボタン（サーバー情報表示）
- SQLite ↔ Neo4j 切替ボタン
- admin権限のみアクセス可能（AccountStatusメニューから起動）

### 4. Neo4j検索アダプター (6-N-07)

#### neo4j-search.ts
- `searchNeo4j()`: 全文検索インデックス使用 → CONTAINSフォールバック
  - Luceneクエリエスケープ + ワイルドカード前方一致
  - nodeType / format / project / プロパティ値の複合フィルタ
  - offset / limit ページネーション
- `getProjects()`: Neo4j上のプロジェクト一覧取得
- `getNodeTypes()`: ノードタイプ一覧取得
- `hasFulltextIndex()`: 全文検索インデックスの存在確認

#### 01-schema.cypher 追加
- `jjfile_fulltext`: JJFile (name, type, format) の全文検索インデックス
- `jjmaterial_fulltext`: JJMaterial (name) の全文検索インデックス

#### 検索APIルート
- `GET /api/datasource/search` — パラメータ検索（q, type, format, project, propKey, propValue, limit, offset）
- `POST /api/datasource/search` — メタデータ取得（projects一覧, nodeTypes一覧）

### 5. 統合テスト

#### test-datasource-factory.ts（9テスト全パス）
- デフォルトSQLite確認
- SQLite/Neo4jリポジトリクラスの正しいインスタンス化
- switchDataSource()によるランタイム切替
- switchDataSource(null)で環境変数に戻る
- resetRepositories()のシングルトンリセット
- シングルトン同一インスタンス確認

#### test-neo4j-driver.ts（7テスト全パス）
- getCurrentConfig()のデフォルト値
- setRuntimeConfig()による設定上書き
- setRuntimeConfig(null)でデフォルト復帰
- testConnection()の接続不可時エラー検知

### 6. 接頭辞キーのダッシュボードUI表示名改善

`PROPERTY_KEY_LABELS` マッピングに50項目追加:
- vocab共通キー: idx→条件, ver→バージョン, path→パス等
- メッシュ統計: mesh_node_count→メッシュノード数等6項目
- diff関連: diff_summary→差分要約等4項目
- ノードタイプ: calculation_input→解析入力等12項目
- リレーションラベル: next_version→次バージョン等15項目

## ファイル構成（新規・変更）

```
jj/pyproject.toml                                    # neo4j依存バージョン統一
shared/neo4j/init/01-schema.cypher                    # 全文検索インデックス追加
docs/specs/neo4j-pipeline-design.md                   # 実装状況更新
jjrv/src/lib/datasource/neo4j-driver.ts               # ランタイム設定・テスト接続
jjrv/src/lib/datasource/factory.ts                    # ランタイム切替
jjrv/src/lib/datasource/index.ts                      # 新エクスポート追加
jjrv/src/lib/datasource/neo4j-search.ts               # 全文検索アダプター [NEW]
jjrv/src/lib/datasource-api.ts                        # クライアントAPI [NEW]
jjrv/src/lib/hierarchy-builder.ts                     # 表示名ラベル50項目追加
jjrv/src/app/api/datasource/route.ts                  # 状態取得API [NEW]
jjrv/src/app/api/datasource/test/route.ts             # 接続テストAPI [NEW]
jjrv/src/app/api/datasource/switch/route.ts           # 切替API [NEW]
jjrv/src/app/api/datasource/search/route.ts           # 検索API [NEW]
jjrv/src/components/DataSourceSettingsModal/index.tsx  # 設定UIモーダル [NEW]
jjrv/src/components/AccountStatus/index.tsx            # メニューにDS設定追加
jjrv/tests/test-datasource-factory.ts                 # ファクトリテスト [NEW]
jjrv/tests/test-neo4j-driver.ts                       # ドライバテスト [NEW]
```

## テスト結果

| テスト | 結果 |
|--------|------|
| ruff check (jj) | PASSED |
| ruff format --check (jj) | PASSED |
| pytest test_neo4j_connector.py | 75 passed, 2 skipped |
| biome check (変更ファイル) | PASSED (17 files) |
| tsc --noEmit (jjrv) | PASSED (0 errors) |
| test-datasource-factory.ts | 9 passed |
| test-neo4j-driver.ts | 7 passed |

## TODO

- [ ] Neo4j Docker実環境でのエンドツーエンド検証（WSLローカル環境で実施）
- [ ] Docker環境でのSQLite↔Neo4j切替のE2Eテスト
- [ ] 検索UIでのNeo4j全文検索の統合（search/page.tsxからneo4j-search APIを呼び出し）
- [ ] M4: jjrvダッシュボード横断表示の着手

## 確認事項・懸念

- Docker daemonがコンテナ環境内でiptables制約により起動不可。E2E検証はWSLローカル環境で実施が必要
- Neo4j全文検索インデックスはNeo4j 5.x Community Editionで利用可能だが、コンテナ初回起動時にスキーマCypherが正しく実行されるか要確認
- ランタイムデータソース切替はサーバープロセスのメモリ上のみ（再起動で.envに戻る）。永続化が必要なら設定ファイル保存を検討
