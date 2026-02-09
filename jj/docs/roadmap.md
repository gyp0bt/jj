[READMEへ戻る](../README.md)

# ロードマップ

本ドキュメントは、jjプロジェクトの実装計画を機能ドメイン別に整理し、優先順位と実装フェーズを明確化したものです。

詳細な仕様は [機能ドメイン別仕様書](./specs/README.md) を参照してください。

---

## 完了

### コアデータモデル層

- [x] `Node`, `Relation`, `GraphModel` の型定義（Pydantic）
- [x] `GraphStorage` の基本実装（YAML保存・読込）
- [x] 基本的なCRUD操作

### パーサー層

- [x] `FileParse` 基底クラスの実装
- [x] 命名規則の解析（index, version, props, tags）
- [x] 拡張子判定（複数ドット対応）
- [x] ファイルタイプ判別（接頭辞による）
- [x] `ObsidianFileParse` の実装
- [x] パス変換機能

### runコマンド層

- [x] `jj r -- <command>` の基本実装
- [x] 実行ログの保存（`.jj/storage/run/`）
- [x] メタ情報の記録（duration, user, host, script_path）
- [x] 単体テスト

### その他

- [x] SSH設定（`.pyssh.yaml`）の読込機能
- [x] CLI構造の整理（`services/service/entry.py`）

---

## Phase 1: 基盤整備（完了）

### 優先度: 最高

#### 1. コアデータモデル層の拡張

- [ ] グラフのマージ機能（複数グラフの統合）
- [ ] ノード/関係の更新・削除機能
- [ ] トランザクション管理（保存の原子性）
- [ ] バリデーション強化（循環参照チェック、孤立ノード検出）

**参照**: [01-core-data-model.md](./specs/01-core-data-model.md#4-実装計画)

#### 2. 設定管理層の統合（完了）

- [x] `vocab.yaml` の読込機能（既存実装）
- [x] `extensions.yaml` の読込機能
- [x] `prefixes.yaml` の読込機能
- [x] 各設定モデルの定義（`ExtensionsConfig`, `PrefixesConfig`）
- [x] `.jj/config/` の初期化処理
- [x] `AppConfig` への統合

**参照**: [03-config.md](./specs/03-config.md#6-実装計画)

#### 3. runコマンド層のproperties抽出拡張（完了）

- [x] コメント記法（`# props start` - `# props end`）の実装（既存実装で対応済み）
- [x] `sys.argv` 解析の実装（Python）（既存実装で対応済み）
- [x] Bash変数（`$1`, `$2`）の解析（Bash）（既存実装で対応済み）
- [x] 対応フォーマット（Python, Bash）の完全実装（既存実装で対応済み）

**参照**: [04-run-command.md](./specs/04-run-command.md#5-properties抽出)

#### 4. runコマンド層のファイル差分検出（完了）

- [x] 実行前後のスナップショット機能（既存実装で対応済み）
- [x] 差分検出ロジックの実装（既存実装で対応済み）
- [x] 除外ルールの設定（既存実装で対応済み）
- [x] `Relation(label=generated)` の自動生成（GraphStorageへの反映機能を実装）

**参照**: [04-run-command.md](./specs/04-run-command.md#6-ファイル差分検出)

---

## Phase 2: グラフ機能の作り込み（最優先 - 直近）

### 優先度: 最高

#### 5. Abaqusコネクター: グラフ機能の強化

- [x] 同一ファイルタイプの関連付け
  - [x] 同じファイルタイプ(go)、同じindex、同じversionでpropsが異なるファイルの検出
  - [x] csv/png/json/yamlの自動関連付け（`has_output`関係）
  - [x] 例: go_idx1_v1.inp に対して go_idx1_v1_RF3.csv は RF3キーの値を保持
- [x] フォルダベースの関連付け
  - [x] go_idx1_v1 ディレクトリ内部のファイルはすべて`contains`関係で紐付け
  - [x] ディレクトリ名のpropsも子ファイルに伝搬
- [x] material.inpの高度な解析
  - [x] 物性定義データをブロックごとに分解
  - [x] Node(abaqus_material)として扱う
  - [x] conductivity/elasticなどのキーワードをpropsに保持
  - [x] propsに配列データを保持
- [x] 解析結果ファイルの解析
  - [x] .sta/.msgからインプットの成否を判定
  - [x] エラー内容とwarning内容の抽出
  - [x] analysis_status プロパティへの反映
  - [x] .msgファイルのERROR/WARNING抽出（parse_msg_file）
  - [x] GraphServiceへの.msgエンリッチメント統合
  - [x] 結果ファイル(sta/msg)属性のAbaqusインプットNodeへの集約
  - [x] active属性の自動判定（oldフォルダ判定）
  - [x] *PARAMETER/**propsブロックのプロパティ読み取り
  - [x] Obsidianエクスポート: frontmatterのproperty化、バージョンリンク構造改善

**参照**: [services/parse/abaqus_connector.py](../../services/parse/abaqus_connector.py)

#### 6. パーサー層の拡張機能

- [ ] ファイルグループ機能の実装
- [ ] 旧形式（`.v1`）の完全対応
- [ ] バイナリファイルの判定と対応方針の明確化
- [ ] パフォーマンス最適化（大量ファイル対応）

**参照**: [02-parser.md](./specs/02-parser.md#6-実装計画)

---

## Phase 2.5: ダッシュボード・API基盤（直近〜中期）

### 優先度: 高

#### D1. データ供給基盤（DashboardDataProvider）

- [ ] `DashboardDataProvider` クラスの実装
  - [ ] `get_go_table()` → DataFrame変換（プロパティ展開済み）
  - [ ] `get_node_card()` → 詳細辞書（関連ノード含む）
  - [ ] `get_plot_data()` → 数値プロパティ抽出
  - [ ] `get_property_keys()` → 利用可能キー一覧
  - [ ] `get_status_summary()` → 実行ステータスサマリー
- [ ] `jj export --target dashboard-json` の実装
- [ ] テスト

#### D2. Streamlitダッシュボード

- [ ] `jj dashboard` CLIコマンド追加
- [ ] テーブルビュー（ag-grid + フィルター）
  - go_ファイル一覧、プロパティカラム展開、ステータス表示
- [ ] カードビュー（ノード詳細 + 関連画像表示）
- [ ] プロットビュー（plotly散布図/線図、X/Y軸選択）
- [ ] ステータスモニター（実行中/完了/失敗の一覧）

#### D3. REST API（jj serve）

- [ ] `jj serve` CLIコマンド追加（FastAPI + uvicorn）
- [ ] `/api/v1/nodes`, `/api/v1/relations` エンドポイント
- [ ] `/api/v1/summary`, `/api/v1/status` エンドポイント
- [ ] クエリフィルター（type, index, status, props条件）

#### D4. jj-db統合

- [ ] `jj export --target jj-db` の実装（jj-dbアップロード形式）
- [ ] jj-db側にjjプロジェクトインポート機能追加
- [ ] API連携（jj serve → jj-db fetch）
- [ ] jj-db既存ビュー（テーブル/カード/グラフ）でjjデータ表示

**参照**: [09-dashboard.md](./specs/09-dashboard.md)

---

## Phase 2.N: DB統合基盤（jj × jj-db × Neo4j）

### 優先度: 中（Phase 2.5と並行）

#### N1. 基盤構築 ✅ (status-037)

- [x] `shared/` パッケージ作成（neo4j_schema.py, types.py, config.py）
- [x] `neo4j/docker-compose.yml` 作成
- [x] `neo4j/init/01-schema.cypher` 作成（制約/インデックス）
- [x] requirements.txtに`neo4j`ドライバ追加

#### N2. jj Neo4jエクスポーター ✅ (status-037)

- [x] `services/connectors/neo4j.py` 実装（Neo4jConnector）
- [x] `jj export --target neo4j` CLI追加
- [x] `jj export --target cypher` CLI追加（Cypherファイル出力）
- [x] GraphModel → Neo4j Cypherマッピング実装
- [x] upsert対応（UNWIND + MERGE）
- [x] テスト（71件: 69パス + 2スキップ）

#### N3. jj-db Neo4jクライアント

- [ ] `jj_db/` ディレクトリ構築
- [ ] `jj_db/neo4j_client.py` 実装
- [ ] 材料データのNeo4j投入
- [ ] jjデータの読み取りインターフェース

#### N4. クロスリレーション

- [ ] 材料名マッチングロジック（MATCHES関係の自動生成）
- [ ] `jj import --source neo4j` 実装
- [ ] jj-db側のjjプロジェクトビュー

#### N5. submodule移行（アクセス復旧後）

- [ ] jj_db/ を別リポジトリに切り出し
- [ ] .gitmodules設定
- [ ] shared/ の独立パッケージ化検討
- [ ] CI/CD分離

**参照**: [10-db-integration.md](./specs/10-db-integration.md)

---

## Phase 3: コマンド機能の充実（中期 - 1〜3ヶ月）

### 優先度: 高

#### 7. runコマンド層のジョブ型実装

- [ ] `--mode=job` オプションの実装
- [ ] Abaqusアダプターの基本実装
- [ ] 生成ファイル予測機能
- [ ] ジョブ型の単体テスト
- [ ] 実行ログのGraphStorageへの反映

**参照**: [04-run-command.md](./specs/04-run-command.md#3-実行モードの分類)

#### 8. fileコマンド層の基本実装

- [ ] テンプレートディレクトリの構造定義
- [ ] Jinja2によるテンプレートレンダリング
- [ ] 基本テンプレート（Abaqus, Fluent, Dyna）の作成
- [ ] `jj f template` コマンドの実装
- [ ] 基本リネーム機能の実装
- [ ] 基本移動機能の実装

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

#### 9. runコマンド層のリモート実行統合

- [ ] `--remote` オプションの実装
- [ ] SSH経由の実行
- [ ] 既存submit機能の移行
- [ ] リモートログの同期

**参照**: [04-run-command.md](./specs/04-run-command.md#7-既存submit機能のリファクタリング)

#### 10. Abaqusコネクターの追加機能

- [x] pymesh(非公開)のインクルード（基盤構築完了 - status-030）
  - [x] メッシュ品質の統計情報をmeshファイルから抽出
  - [x] 要素品質（アスペクト比、ヤコビアン等）の計算
  - [x] 材料→Elset割り当て関係のグラフ化
  - [x] メッシュキーワード要約（Node/Element/Nset/Elset→統計情報に自動置換 - status-034）
  - [ ] 個々のElsetごとの品質統計
  - [ ] ODB連携（Abaqus 2024 Python 3.10対応）
- [x] ドキュメント連携（強化 - status-033）
  - [ ] index.csv/yamlとファイルの紐付け
  - [x] Obsidian dailyノートとファイルの紐付け
  - [x] 備考、結果サマリーの自動抽出（dailyからプロパティ付きファイル参照）
  - [x] Obsidianリンク＋プロパティ記法（[[O-file]]:key:value）対応
  - [x] ファイルリンク値の自動抽出（[[image.png|表示名]]）
  - [ ] dailyノートをブロックごとに切り出してNodeに逆輸入
- [ ] config.yamlの拡張
  - [ ] 配列のスライス指定機能
  - [ ] type=isoを指定された場合のelasticプロパティの列定義
    - 0列目: ヤング率
    - 1列目: ポアソン比
    - 2列目: 温度
  - [ ] type=aniso/orthoの場合の列と値の組み合わせ定義
  - [ ] パターン一致指示によるprops定義（例: RF3は長手方向荷重）
- [ ] 事前にラベリングした対処法の部分一致による紐付け

**参照**: [services/parse/abaqus_connector.py](../../services/parse/abaqus_connector.py)

---

## Phase 4: 拡張性の強化（中期〜長期 - 3〜6ヶ月）

### 優先度: 中

#### 11. アダプター層の基盤構築

- [ ] `CAEAdapter` ベースクラスの定義
- [ ] `AdapterRegistry` の実装
- [ ] アダプター自動検出機構
- [ ] Abaqusアダプターの完全実装
- [ ] Fluentアダプターの実装
- [ ] LS-DYNAアダプターの実装

**参照**: [07-adapter.md](./specs/07-adapter.md#7-実装計画)

#### 12. 出力層の基盤構築

- [ ] `Exporter` 基底クラスの定義
- [ ] `ExporterRegistry` の実装
- [ ] Neo4jExporter の実装
- [ ] JsonExporter の実装
- [ ] GraphMLExporter の実装
- [ ] `jj export` コマンドの実装

**参照**: [08-export.md](./specs/08-export.md#6-実装計画)

#### 13. fileコマンド層の高度な機能

- [ ] カスケードリネーム機能の実装
- [ ] 関係保持オプションの実装
- [ ] SSH送信機能の実装
- [ ] SSH受信機能の実装
- [ ] 送受信履歴のグラフ化

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

---

## Phase 5: 最適化と高度な機能（長期 - 6ヶ月以上）

### 優先度: 低

#### 14. コアデータモデル層の最適化

- [ ] 大規模グラフ対応（遅延読込、インデックス最適化）
- [ ] キャッシュ機構の導入
- [ ] JSON形式のパフォーマンス最適化

**参照**: [01-core-data-model.md](./specs/01-core-data-model.md#4-実装計画)

#### 15. 設定管理層の高度な機能

- [ ] 設定ファイルのバリデーション
- [ ] 設定エディタ機能（`jj config edit`）
- [ ] 設定テンプレート機能（`jj config init --template abaqus`）
- [ ] 環境変数からの設定上書き
- [ ] 設定のバージョン管理（migration）

**参照**: [03-config.md](./specs/03-config.md#6-実装計画)

#### 16. アダプター層のプラグイン化

- [ ] プラグイン方式のアダプター追加
- [ ] アダプターのバージョン管理
- [ ] アダプター間の連携（例: AbaqusからFluentへのデータ転送）

**参照**: [07-adapter.md](./specs/07-adapter.md#7-実装計画)

#### 17. 出力層の高度な機能

- [ ] カスタムテンプレートサポート
- [ ] インクリメンタルエクスポート
- [ ] エクスポートプリセット機能
- [ ] フィルタリング機能の拡張

**参照**: [08-export.md](./specs/08-export.md#6-実装計画)

#### 18. fileコマンド層の複雑な操作

- [ ] 複数ファイル一括操作
- [ ] ファイル比較機能（diff）
- [ ] ファイル履歴の可視化
- [ ] テンプレートのカスタマイズ機能

**参照**: [06-file-command.md](./specs/06-file-command.md#8-実装計画)

---

## マイルストーン

### M1: 基盤完成（Phase 1完了） ✅

**達成日**: 2026-02-04

**達成条件**:
- ✅ コアデータモデル層の基本機能完了（GraphModel, Node, Relation）
- ✅ 設定管理層の統合完了（ExtensionsConfig, PrefixesConfig, AppConfig）
- ✅ runコマンドのproperties抽出とファイル差分検出が完全動作
- ✅ GraphStorageへのRelation(label=generated)自動生成機能を実装
- ✅ CLI層とservice層の分離
- ✅ 全テスト成功

### M2: グラフ機能完成（Phase 2完了）

**目標日**: 2〜4週間以内

**達成条件**:
- Abaqusコネクターのグラフ機能が完全動作
- 同一ファイルタイプの関連付け完了
- material.inpの高度な解析完了
- 解析結果ファイルの解析完了
- パーサー層の拡張機能完了

### M2.5: ダッシュボード基盤完成（Phase 2.5 D1-D2完了）

**目標日**: M2完了後 2〜4週間以内

**達成条件**:
- DashboardDataProviderが完全動作
- `jj dashboard` でStreamlitアプリが起動
- テーブル/カード/プロット/ステータスの4ビューが利用可能
- dashboard-jsonエクスポートが動作

### M3: コマンド機能完成（Phase 3完了）

**目標日**: 3ヶ月以内

**達成条件**:
- runコマンドのジョブ型実装完了
- fileコマンドの基本機能実装完了
- リモート実行の統合完了

### M4: 拡張性確保（Phase 4完了）

**目標日**: 6ヶ月以内

**達成条件**:
- アダプター層の基盤完成
- 出力層の基盤完成
- 3つ以上のCAEソフトに対応
- jj serve REST APIが稼働
- jj-db統合が基本動作（D3-D4完了）

### M5: 最適化完了（Phase 5完了）

**目標日**: 1年以内

**達成条件**:
- 大規模プロジェクト（10,000ファイル以上）での安定動作
- 高度な設定管理機能の実装
- プラグイン方式のアダプター追加が可能

---

## 参考資料

- [機能ドメイン別仕様書](./specs/README.md)
- [実装詳細](./detail.md)
- [ダッシュボード仕様書](./specs/09-dashboard.md)
- [DB統合設計書](./specs/10-db-integration.md)
- [最新ステータス](./status/status-037.md)
- [プロジェクトREADME](../README.md)
