[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-019 — status-018 TODO実行: 新構造パーサー・connector_config UI・CI統合・プラグイン検証・Neo4j設計

**日付**: 2026-02-18
**マイルストーン**: M2（マルチソルバー基盤）/ M3（Neo4j統合パイプライン）
**ブランチ**: claude/execute-status-todos-UcI3G

---

## 実施内容

### 1. ResultsMetadataParser GOノードベース新ディレクトリ構造対応

**背景**: 仕様書（`docs/specs/results-directory-restructure.md`）に基づき、`results/{go_basename}/` 形式の新しいGOノードベースディレクトリ構造をサポートする必要があった。

**変更**:
- `_is_go_node_directory()` ヘルパー関数追加（`go_`プレフィックスでディレクトリ判定）
- `_parse_new_result_filename()` ヘルパー関数追加（新構造: result_keyファースト形式のパース）
- `apply()` メソッド拡張: 旧構造（`step{N}_frame{M}/`）と新構造（`{go_basename}/`）を自動判別
- テスト14件追加（新構造8件 + ヘルパー6件）、既存テスト12件は全て退行なし

### 2. connector_config編集UIをビュー追加/編集フォームに統合

**背景**: コネクターページの保存済みビュー（`connector_config`）はコードでのみ設定可能で、UIからの入力に非対応だった。

**変更**:
- `DashboardPageConnector` に `get_connector_config_schema()` クラスメソッド追加
- Abaqus3コネクターにスキーマ定義:
  - 物性一覧: `material_name`, `property_key`, `compare_materials`
  - メッシュ品質: `go_name`, `show_elset`（checkbox型）
  - ジョブサマリー: `status_filter`, `go_name`
- ビュー追加フォーム: コネクタータイプ選択時にスキーマベースの入力UI表示
- ビュー編集フォーム: 既存connector_config値の表示・編集UI
- 編集フォームのタイプ選択にコネクタータイプも追加
- `compare_materials` カンマ区切り→リスト自動変換
- `get_connector_config_schema()` レジストリ関数追加
- テスト6件追加

### 3. Streamlit E2EテストのCI統合

**背景**: AppTest（Streamlit 1.28+）依存のE2Eテストが全てskipされており、CI環境での実行が未確認だった。

**変更**:
- streamlitインストール環境でAppTest利用可能であることを確認
- `.github/workflows/ci.yml` に `python-dashboard-e2e` ジョブ追加
- 全27件のE2Eテストが正常にパス（skip解除状態）
- `skipif` は Streamlit 未インストール環境の後方互換として維持

### 4. 外部プラグインパッケージの分離検証

**背景**: プラグインシステムが独立パッケージとして分離可能か検証が必要だった。

**検証結果**:
- `examples/jj-plugin-example/` を `pip install -e .` で導入
- entry_points経由でプラグイン発見成功（9プラグイン検出）
- exampleプラグインのテスト3件全てパス
- **結論**: プラグインシステムは既に独立パッケージ化に対応済み
- **注意**: `load_all_plugins()` 内での循環インポート警告あり（機能に影響なし）

### 5. M3 Neo4j統合パイプライン設計仕様書

**変更**:
- `docs/specs/neo4j-pipeline-design.md` を新規作成
- jj側の完了済みコンポーネント整理（9コンポーネント）
- jjrv側の未着手コンポーネント定義（6コンポーネント）
- 4フェーズの実装計画策定
- ID体系統一・接続情報管理・パフォーマンスの設計判断を文書化

---

## テスト結果

- **既存テスト**: 1174 passed → 1216 passed（42件増 + streamlit E2Eテスト解除）
- **新規テスト**: 20件追加
  - ResultsMetadataParser新構造: 14件（8 + 6ヘルパー）
  - connector_configスキーマ: 6件
- **pymesh関連**: 6件失敗（環境依存、今回の変更とは無関係）
- ruff lint: All checks passed
- ruff format: 168 files already formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/parse/parsers/results_metadata_parser.py` | 修正 | 新構造検出・パース関数追加、apply()拡張 |
| `tests/test_parser_units.py` | 修正 | 新構造テスト14件追加 |
| `services/dashboard/connectors/__init__.py` | 修正 | get_connector_config_schema()メソッド・関数追加 |
| `services/dashboard/connectors/abaqus.py` | 修正 | 3コネクターのスキーマ定義追加 |
| `services/dashboard/app.py` | 修正 | 追加/編集フォームのconnector_config UI統合 |
| `tests/test_dashboard_e2e.py` | 修正 | connector_configスキーマテスト6件追加 |
| `.github/workflows/ci.yml` | 修正 | dashboard E2Eテストジョブ追加 |
| `docs/specs/neo4j-pipeline-design.md` | 新規 | M3 Neo4j統合パイプライン設計仕様書 |

---

## 次回TODO

- [ ] ResultsMetadataParser: output_parser.pyの新パス対応（仕様書Phase 3に対応）
- [ ] ResultsMetadataParser: マイグレーションスクリプト（旧→新構造変換ツール、オプション）
- [ ] connector_config: 新規コネクター追加時のスキーマ自動ドキュメント生成検討
- [ ] プラグインローダー: `load_all_plugins()` 循環インポート警告の解消
- [ ] M3 Phase 2: jjrv IEntityRepository抽象化着手
- [ ] M3: Neo4jドライバ選定（neo4j-driver vs neo4j-driver-core）

---

## 設計メモ

### connector_config スキーマパターン

各コネクターは `get_connector_config_schema()` クラスメソッドでフィールド定義を返す:

```python
@classmethod
def get_connector_config_schema(cls) -> list[dict[str, Any]]:
    return [
        {"key": "go_name", "label": "GOノード名", "type": "text", "help": "..."},
        {"key": "show_elset", "label": "elset表示", "type": "checkbox", "help": "..."},
    ]
```

フォームUIはスキーマに基づいて動的に生成:
- `text` → `st.text_input()`
- `checkbox` → `st.checkbox()`
- リスト値（`compare_materials`）はカンマ区切り入力→リスト変換

### 外部プラグイン分離の可能性

検証の結果、以下が確認された:
- SDKバウンダリ（`services.sdk`）は既に抽象化済み
- entry_points経由の自動発見は正常動作
- CacheProviderプロトコルでnamespace分離
- exampleプラグインがテスト3件全てパス

独立パッケージ化の手順:
1. `services/plugins/{solver}/` → 独立リポジトリ
2. 実際のパーサー/コネクター実装も移動
3. `pyproject.toml` にentry_points設定
4. `pip install jj-plugin-{solver}` で導入

### 開発運用メモ

- Streamlit AppTestは環境が整っていれば問題なく動作する。CIジョブを分離してstreamlit依存を明示した。
- コンテキスト管理: 5つのTODOを1セッションで処理。ステップバイステップのコミットで管理した。
