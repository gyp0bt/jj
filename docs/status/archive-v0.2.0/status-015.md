[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-015 — メッシュ品質ダッシュボードを独立ページに分離

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ブランチ**: claude/separate-mesh-quality-dashboard-lXtf4

---

## 実施内容

### メッシュ品質ページの物性一覧からの分離

**背景**: 物性一覧ページ（AbaqusMaterialPageConnector）にメッシュ品質サマリーとElset品質サマリーが含まれていたが、材料物性とメッシュ品質は異なる関心事であり、ページが肥大化していた。

**変更**:
- `AbaqusMeshQualityPageConnector`を新規作成（`page_label="メッシュ品質"`）
- `_render_mesh_quality_page()`を新規作成（メッシュ品質サマリー + Elset品質サマリーを表示）
- `_render_material_page()`からメッシュ品質セクション（セクション5-6）を削除
- `is_available()`でgo_ノードのメッシュデータまたはelsetの品質データの存在を判定

**結果**: サイドバーに「物性一覧」「メッシュ品質」「ジョブサマリー」の3ページが独立表示される

### テスト追加（7件）

| テスト | 概要 |
|--------|------|
| `test_mesh_quality_connector_registered` | レジストリに「メッシュ品質」が登録されている |
| `test_mesh_quality_connector_key` | connector_keyが"abaqus" |
| `test_mesh_quality_available_with_mesh_data` | go_ノードにメッシュデータがある場合にis_available=True |
| `test_mesh_quality_available_with_elset_quality` | elset品質データがある場合にis_available=True |
| `test_mesh_quality_not_available_without_data` | メッシュ関連データがない場合にis_available=False |
| `test_mesh_quality_page_in_connector_pages` | get_connector_pagesで「メッシュ品質」が返される |
| `test_material_page_excludes_mesh_quality` | 物性一覧とメッシュ品質が独立ページとして共存 |

---

## テスト結果

- **全テスト**: 1128 passed, 59 skipped, 4 failed（pandas/pymesh依存の既存テスト）
- **新規テスト**: 7件追加（全パス）
- ruff lint: All checks passed
- ruff format: All files formatted

---

## 変更ファイル

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `services/dashboard/connectors/abaqus.py` | 修正 | AbaqusMeshQualityPageConnector新規追加、_render_mesh_quality_page新規追加、_render_material_pageからメッシュセクション削除 |
| `tests/test_dashboard.py` | 修正 | メッシュ品質コネクターテスト7件追加 |

---

## 次回TODO

- [ ] メッシュ品質の残課題: `get_element_node_coord_array(allow_polymorphism=False)`で要素タイプ混在時に品質計算が失敗する問題。pymesh側でelset別に分離して計算する方式への変更が必要
- [ ] DashboardPageConnector（ソルバー別コネクターページ）のPageComponentパターン統合検討
- [ ] ダッシュボードのE2Eテスト追加（Streamlit TestRunnerの導入検討）
- [ ] 外部プラグインパッケージの実例作成（pyproject.toml + entry_points設定のサンプル）
- [ ] 解析結果の保存構造見直し: `results/go_idx1_v1/` ディレクトリ方式への変更
