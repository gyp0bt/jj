[READMEへ戻る](../../README.md)

# status-038: parse exportバグ修正 + jj-db統合ロードマップ整備

**日付**: 2026-02-09

## 概要

parse exportの4点修正と、jj-db統合に向けたドキュメント・ロードマップの整備を実施した。

## 実装内容

### 1. pymesh相対パスインポート化

pymesh内の絶対パスインポート（`from pymesh import ...`）を相対パスインポート（`from .. import ...`）に変更。パッケージの独立性と移植性を向上。

| ファイル | 変更内容 |
|---------|---------|
| `pymesh/utils/one_layer.py` | `from pymesh import Mesher` → `from .. import Mesher` |
| `pymesh/utils/one_layer.py` | `from pymesh.etypes import ...` → `from ..etypes import ...` |
| `pymesh/io.py` | `from pymesh import mesher` → `from . import mesher` |
| `pymesh/io.py` | `from pymesh.io import parse_inp_structure` → 同一ファイル内のため削除 |

### 2. タグ分離ロジック改善

Obsidianエクスポート時、`_`を含むタグを単語ごとに分離するように変更。

- `_split_tag()`ヘルパー関数を追加
- `node_to_frontmatter()`: frontmatterのタグリストで`_`分割適用
- `_format_md()`: markdown本文の`#tag`出力でも`_`分割適用
- `material/xxx`等の`/`区切りタグは分割対象外

**例**: `#calculation_input` → `#calculation #input`

### 3. includes記載の相対パス化

Obsidianエクスポートのincludes（.baseファイルリンク）をファイル名からノート相対パスに変更。

**変更前**: `includes: [[O-Abaqusインプット_idx1.base]]`
**変更後**: `includes: [[notes/bases/Abaqusインプット/Abaqusインプット_idx1.base]]`

| メソッド | 変更内容 |
|---------|---------|
| `_build_parent_links()` | .baseリンクを`{bases_dir}/{dir_name}/{filename}`形式に変更 |
| `node_to_frontmatter()` | パスを含むincludesは`[[path]]`形式で生成（O-プレフィックス不要） |

### 4. directoryノードにroot.directoryタグ追加

すべてのディレクトリノード（命名規則合致・汎用の両方）のタグに`root.directory`を追加。

| ディレクトリ種別 | 変更 |
|----------------|------|
| 命名規則合致（go_idx1_v1/等） | `tags`に`root.directory`を追加 |
| 汎用ディレクトリ（reports/等） | `tags: ["root.directory"]`を追加（従来はpropertyなし） |

### 5. jj-db統合ロードマップ整備

jj-db統合に向けた方針をロードマップ（Phase 2.N）に追記。

**統合原則**:
- データ構造はjjの`Node`, `Relation`, `Abaqusインプット`等を優先
- レポジトリ概念はjj-dbを保持
- `shared/neo4j_schema.py`をスキーマの正とする
- `services/`と`jj_db/`は直接通信禁止、Neo4j契約のみ共有

**確認が必要な事項（次回以降に段階的解決）**:
- ID体系の統一（jj int vs jj-db string）
- ノードタイプマッピングの正規化
- リレーションラベルの不整合解消（spec-roadmap6 vs 10-db-integration）
- 全文検索戦略
- ユーザー/認証モデル
- 並行書き込み時の競合解決

## テスト結果

| テストスイート | 結果 |
|---------------|------|
| 全テスト | **363パス + 20スキップ** |
| リグレッション | なし |

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `pymesh/utils/one_layer.py` | 変更: 相対パスインポート |
| `pymesh/io.py` | 変更: 相対パスインポート |
| `services/connectors/obsidian.py` | 変更: タグ分割、includes相対パス化 |
| `services/graph/__init__.py` | 変更: directoryノードにroot.directoryタグ追加 |
| `docs/roadmap.md` | 変更: Phase 2.N統合方針追記 |
| `docs/status/status-038.md` | 新規: 本ステータス |
| `README.md` | 変更: 最新ステータスリンク更新 |

## TODO / 次のステップ

- [ ] jj-db統合: ID体系の統一方針決定
- [ ] jj-db統合: ノードタイプマッピング表の作成
- [ ] jj-db統合: リレーションラベルの正規化
- [ ] Phase N3: jj-db Neo4jクライアント実装
- [ ] Phase N4: 材料名マッチングロジック
- [ ] `_split_tag()`の追加テスト作成
- [ ] includes相対パスの追加テスト作成

## 確認事項・設計上の懸念

1. **タグ分割の範囲**: 現在は`_`を含むすべてのタグを分割している。特定のタグ（例: `root.directory`）は`.`区切りで分割すべきか？現状は`/`を含むもののみ分割対象外としている
2. **jj-db統合のスコープ**: spec-roadmap6と10-db-integrationの間にノードタイプ/リレーションラベルの不整合がある。次回以降のセッションで段階的に解決予定
3. **ID体系**: jjは`int`、jj-dbは`string`。Neo4j内で`jj_id`と`jjdb_id`を別フィールドで保持する方針だが、統一方針の確定が必要
