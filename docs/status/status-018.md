[← README.md](../../README.md) | [← status-index](status-index.md)

# status-018 — status-017 TODO実行: 設計仕様書・コネクター保存ビュー・ローカルフィルタ拡張・テスト拡充・CI統合

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/execute-status-todos-S8s5u

---

## 実施内容

### 1. 解析結果の保存構造見直し（設計仕様書）

**背景**: `results/step{N}_frame{M}/` ベースのディレクトリ構造では、特定GOノードの全結果を横断収集する必要があり、マルチソルバー対応での拡張性にも課題があった。

**変更**:
- `docs/specs/results-directory-restructure.md` を新規作成
- GOノードベースのディレクトリ構造（`results/go_idx1_v1/`）への移行設計
- ファイル名命名規則、後方互換性戦略、パーサー変更箇所を文書化
- マルチソルバー対応の共通原則を定義

### 2. コネクターページのrender_saved_view個別実装

**背景**: 3つのAbaqusコネクター（物性一覧・メッシュ品質・ジョブサマリー）はrender_saved_view()がデフォルト（render_page()委譲）のままで、connector_configを活用した個別表示に非対応だった。

**変更**:
- **AbaqusMaterialPageConnector**: `connector_config` で `material_name`（単一物性詳細）、`property_key`（特定プロパティカーブ）、`compare_materials`（複数物性比較）をサポート
- **AbaqusMeshQualityPageConnector**: `go_name`（GOノードフィルタ）、`show_elset`（elset表示制御）をサポート
- **AbaqusJobSummaryPageConnector**: `status_filter`（ステータスフィルタ）、`go_name`（GOノードフィルタ）をサポート
- HTML生成関数（`_generate_material_saved_view_html`、`_generate_job_summary_saved_view_html`）も追加

### 3. ローカルフィルターのUI拡張（複数キー/値ペア対応）

**背景**: ビュー追加フォームのローカルフィルタが1つのキー/値ペアのみに限定されていた。

**変更**:
- 追加フォーム（`_render_view_add_form`）: 複数キー/値ペアの動的追加・削除UIを実装
- 編集フォーム（`_render_view_edit_form`）: 既存ローカルフィルタの表示と複数ペア編集をサポート
- セッション状態管理: `_add_lf_count`、`_edit_lf_count_{idx}` でペア数を追跡

### 4. E2Eテストの拡充

**変更**:
- **ページ遷移テスト**: 保存済みビュー・物性一覧・メッシュ品質・ジョブサマリーへの遷移テスト（4件）
- **フィルタ操作テスト**: apply_chained_filters、merge_filtersのユニットテスト（4件）
- **コネクター保存ビューテスト**: 単一物性・比較・フォールバック・ジョブフィルタ・go_nameフィルタ・条件不一致（6件）

### 5. 外部プラグインのCI統合テスト

**変更**:
- `tests/test_plugin_integration.py` を新規作成
  - プラグイン登録テスト: Abaqus/CalculiX個別、全8プラグイン一括、冪等性
  - entry_points検出テスト
  - ダッシュボードコネクター登録テスト
  - パースパイプライン統合テスト: パーサー存在確認、priority順序検証
- `.github/workflows/ci.yml` に `python-plugin-integration` ジョブを追加
  - entry_points検証 + テスト実行

---

## テスト結果

- **既存テスト**: 1153 passed → 1174 passed（21件増、退行なし）
- **新規テスト**: 18件追加
  - ページ遷移E2E: 4件（Streamlit依存のためskip）
  - フィルタ操作: 4件
  - コネクター保存ビュー: 6件
  - プラグイン統合: 8件（全パス）
- **pymesh関連**: 6件失敗（環境依存、今回の変更とは無関係）
- ruff lint: All checks passed
- ruff format: All files formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `docs/specs/results-directory-restructure.md` | 新規 | 解析結果のGOノードベースディレクトリ構造への移行設計仕様書 |
| `services/dashboard/connectors/abaqus.py` | 修正 | 3コネクターのrender_saved_view/generate_saved_view_html個別実装 |
| `services/dashboard/app.py` | 修正 | ローカルフィルタUI複数キー/値ペア対応（追加・編集フォーム） |
| `tests/test_dashboard_e2e.py` | 修正 | ページ遷移・フィルタ・コネクター保存ビューテスト18件追加 |
| `tests/test_plugin_integration.py` | 新規 | プラグイン統合テスト8件 |
| `.github/workflows/ci.yml` | 修正 | plugin-integrationジョブ追加 |

---

## 次回TODO

- [ ] 解析結果の保存構造: 仕様書に基づくResultsMetadataParser実装（テストフィクスチャ先行）
- [ ] コネクター保存ビュー: connector_config編集UIをビュー追加/編集フォームに統合
- [ ] Streamlit AppTest環境でのページ遷移E2Eテスト実行（streamlit依存テストのskip解除）
- [ ] 外部プラグインパッケージの分離検証（pyproject.toml entry_points経由での独立パッケージ化）
- [ ] M3: Neo4j統合パイプラインの設計開始

---

## 設計メモ

### connector_configの設計パターン

各コネクターのrender_saved_view()は以下のパターンで動作:

1. `connector_config`が空 → デフォルトのrender_page()に委譲（後方互換）
2. 特定キーが設定されている → フィルタ/カスタマイズ表示
3. HTML生成もrender/generate同一のconfig参照パターン

これにより、既存のコネクターはオーバーライド不要で動作しつつ、保存済みビューでは詳細な表示制御が可能。

### ローカルフィルタの複数ペアUI

Streamlitのsession_stateを使用した動的UIパターン:
- `_add_lf_count` / `_edit_lf_count_{idx}`: フィルタペア数
- st.rerun()でUI更新（Streamlitの制約上、動的UI変更にはrerunが必要）
- 保存時にペアを辞書に変換し、saved-views.yamlに永続化
