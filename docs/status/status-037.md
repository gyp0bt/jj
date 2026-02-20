[← README.md](../../README.md) | [← status-index](status-index.md)

# status-037 — status-036 TODO実行: plotlyテーマ横断適用・ProcessPool検証・メッシュフィルタ

**日付**: 2026-02-20
**マイルストーン**: M2
**ブランチ**: claude/execute-status-todos-11ExX

---

## 概要

status-036のTODO3件を実行。get_plotly_template()を全plotly使用コンポーネントに横断適用、
ProcessPoolExecutorのパース結果一致性検証テスト追加、diff_abq_metadata_blocksの
raw_blocksからメッシュトポロジー関連キーワードを除外するフィルタを実装。

---

## 実施内容

### 1. get_plotly_template() の全plotlyコンポーネントへの横断適用

**変更ファイル**:
- `services/dashboard/components/array_plot.py`
- `services/dashboard/connectors/abaqus.py`
- `services/dashboard/html_export.py`

- `array_plot.py`: 3箇所のfig.update_layout()にtemplate=get_plotly_template()を追加
  - 個別ノード重ね書き（L244付近）
  - 全条件比較overlay（L322付近）
  - 単一ノードビュー（L440付近）
- `abaqus.py`: 4箇所のfig.update_layout()にtemplate=get_plotly_template()を追加
  - 物性カーブプロット（L148付近）
  - 物性比較プロット（L272付近）
  - 保存ビュー物性比較（L835付近）
  - 単一物性詳細（L904付近）
- `html_export.py`: 5箇所にtemplate=get_plotly_template()を追加
  - 配列プロットoverlay/grid（L314, L346付近）
  - _create_plot_figure() のpx.scatter/px.bar/px.line全3分岐
- ハードコード `color="black"` の除去:
  - array_plot.pyの軸/凡例フォント色指定を削除（テンプレートに委譲）
  - html_export.pyの_create_plot_figure()のフォント色指定を削除

**設計判断**: `color="black"` のハードコードはダークモードテンプレート適用時に文字が
見えなくなる問題を引き起こすため、フォントサイズのみ維持しつつ色指定を削除。
plotly_white/plotly_darkテンプレートが適切なデフォルト色を提供する。

### 2. ProcessPoolExecutor パース結果一致性検証テスト

**変更ファイル**: `tests/test_parser_pipeline.py`

- `TestProcessPoolBenchmark` テストクラスを追加（4テスト）:
  - `test_thread_and_process_parse_same_result`: 3ファイルのINPパース結果一致性
  - `test_parse_inp_worker_function_is_picklable`: ワーカー関数のpickle可能性
  - `test_parse_inp_worker_produces_valid_result`: ワーカー関数の結果妥当性
  - `test_process_pool_fallback_to_thread`: 自動選択ロジックの閾値検証

**設計判断**: 大規模実ファイルでのベンチマーク計測はpytest-benchmark等で別途実施可能な
設計にし、CIでは結果一致性とpickle可能性の検証に集中。テストフィクスチャはProcess閾値以上の
3ファイルで作成。

### 3. diff_abq_metadata_blocks のメッシュトポロジーキーワード除外フィルタ

**変更ファイル**: `services/parse/connectors/abaqus/__init__.py`

- `_MESH_TOPOLOGY_KEYWORDS` 定数を追加（frozenset）:
  - コアメッシュ定義: node, element, nset, elset
  - ジオメトリ変換: transform
  - メッシュ拘束: mpc, equation, tie, rigidbody
  - パート/アセンブリ構造: part, endpart, instance, endinstance, assembly, endassembly
- `_filter_non_mesh_raw_blocks()` 関数を追加:
  - RawBlock型でキーワードが_MESH_TOPOLOGY_KEYWORDSに含まれるブロックを除外
  - ReadComponent型のブロックはフィルタせず通過
- `diff_abq_metadata_blocks()` の raw_blocks 比較箇所に適用:
  - `_build_logical_blocks()` の前に `_filter_non_mesh_raw_blocks()` を挟む

**設計判断**: セクション定義（SHELL SECTION等）はメッシュ参照を持つが材料割り当て・
板厚定義も含むため、メッシュ同一でも変更される可能性がありフィルタ対象外とした。
フィルタ対象はメッシュトポロジー/ジオメトリに密結合したキーワードに限定。

---

## テスト結果

- 新規テスト: 10件追加（全通過）
  - `TestMeshTopologyFilter`: 6件（キーワード定義・フィルタ動作・メタデータ差分除外）
  - `TestProcessPoolBenchmark`: 4件（結果一致性・pickle・ワーカー検証・閾値）
- 既存テスト: 82件通過（test_parser_pipeline.py）、329件通過（test_dashboard.py）
- ruff check/format: クリーン

---

## TODO

- [ ] Streamlitダークモード時のplotlyグラフ視認性の実機確認
- [ ] 大規模INPファイル（100+）での ProcessPool vs ThreadPool ベンチマーク実測
- [ ] _MESH_TOPOLOGY_KEYWORDS の拡充（実プロジェクトで未知のメッシュキーワードを発見次第追加）

---

## 確認事項・懸念

- HTML exportはStreamlit非依存のため`get_plotly_template()`は常に`plotly_white`を返す。HTML export時のダークテーマが必要な場合はテンプレートを引数で渡す拡張が必要。
- `color="black"`除去により、ライトモードでのフォント色はテンプレートデフォルト（ほぼ黒）になるため視覚的変化はほぼないが、厳密には微妙に異なる可能性がある。
