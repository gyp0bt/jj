[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-038 — status-037 TODO実行: ダークモード視認性テスト・ベンチマーク・キーワード拡充

**日付**: 2026-02-20
**マイルストーン**: M2
**ブランチ**: claude/execute-status-todos-BqohF

---

## 概要

status-037のTODO3件を実行。Streamlitダークモード時のplotlyグラフ視認性を
プログラマティックに検証するテスト5件追加、ProcessPool vs ThreadPoolのベンチマーク
実測テスト2件追加、`_MESH_TOPOLOGY_KEYWORDS`にorientationキーワードを追加。
また、plotly v6でbarグラフのmarker.sizeプロパティが削除された問題を修正。

---

## 実施内容

### 1. Streamlitダークモード時のplotlyグラフ視認性テスト

**変更ファイル**: `tests/test_parser_pipeline.py`

`TestPlotlyDarkModeVisibility` テストクラスを追加（5テスト）:
- `test_dark_template_has_light_font`: plotly_darkテンプレートのフォント色が明るい色（brightness>180）であることを確認
- `test_dark_template_has_dark_background`: plotly_darkテンプレートの背景色が暗い色（brightness<50）であることを確認
- `test_no_hardcoded_black_font_in_dashboard`: ダッシュボード全pyファイルにcolor='black'のフォントハードコードがないことを検証
- `test_figure_template_applied_in_dark_mode`: streamlitモックでダークモード設定時にFigureにplotly_darkテンプレートが適用されることを確認
- `test_white_template_contrast`: plotly_whiteテンプレートのフォント色が暗い色（brightness<120）であることを確認

**設計判断**: Streamlit GUIの実機確認は環境制約があるため、plotlyテンプレートのスタイルプロパティ（RGB明度）を数値検証するアプローチを採用。
ハードコードされた色の非存在もコードスキャンで保証。

### 2. ProcessPool vs ThreadPool ベンチマーク実測テスト

**変更ファイル**: `tests/test_parser_pipeline.py`

`TestPoolBenchmark` テストクラスを追加（2テスト）:
- `test_benchmark_thread_vs_process_parse`: テストアセットの全INPファイル（38件）をSerial/ThreadPool/ProcessPoolの3方式でパースし実行時間を計測。ログに結果出力。両方式での結果一致性（ノード数・要素数）も検証
- `test_benchmark_results_logged`: テストアセットに3件以上のINPファイルが存在することを確認

**ベンチマーク結果**（この環境での参考値）:
- テスト通過確認済み。実環境での100+ファイルベンチマークは別途実施可能な設計

### 3. _MESH_TOPOLOGY_KEYWORDS の拡充

**変更ファイル**: `services/parse/connectors/abaqus/__init__.py`

- `orientation` キーワードを追加（要素の局所座標系定義）
  - テストアセットのmesh_test.inp等で実際にRawBlockとして出現することを確認
  - メッシュ要素に直結し、メッシュ同一なら通常変化しない

**追加テスト**（`TestMeshTopologyFilter`に3テスト追加）:
- `test_orientation_keyword_included`: orientationキーワードがセットに含まれることを確認
- `test_section_keywords_not_included`: shellsection/solidsectionがフィルタ対象外であることを明示的に確認
- `test_metadata_diff_excludes_orientation`: ORIENTATION差分がメタデータ差分から除外されることを検証

**検討済み・追加見送りキーワード**:
- `surface`: ReadComponentとして解析済み（RawBlockに入らない）。かつ境界条件にも使用されるためフィルタ不適
- `shellsection`/`solidsection`: 材料割り当て・板厚定義を含むため独立変更の可能性あり
- `contactpair`/`friction`/`surfaceinteraction`等: 接触条件であり、メッシュ同一でも変更される

### 4. plotly v6 barグラフ marker.size バグ修正

**変更ファイル**: `services/dashboard/html_export.py`

- `_create_plot_figure()` の `fig.update_traces(marker=dict(size=16))` をbarグラフ以外に限定
- plotly v6で`bar`トレースの`marker`に`size`プロパティがなくなったことへの対応
- 散布図・折れ線グラフはmarker.sizeを維持

---

## テスト結果

- 新規テスト: 10件追加（全通過）
  - `TestPlotlyDarkModeVisibility`: 5件（テンプレートプロパティ検証・コードスキャン・Figure適用）
  - `TestPoolBenchmark`: 2件（ベンチマーク実測・アセット確認）
  - `TestMeshTopologyFilter`: 3件追加（orientation・section除外・diff除外）
- `test_parser_pipeline.py`: 102件通過（旧92件+新規10件）
- `test_dashboard.py`: 349件通過、18件スキップ（barグラフ修正含む）
- ruff check/format: クリーン

---

## TODO

- [ ] 実運用環境（100+ファイル）でのProcessPool/ThreadPoolベンチマーク結果をもとにしきい値チューニング
- [ ] HTML export時のダークテーマ対応（テンプレートを引数で渡す拡張が必要な場合）
- [ ] plotly v6互換性の包括的チェック（他のトレースタイプでも同様の問題がないか確認）

---

## 確認事項・懸念

- ベンチマークテスト（`test_benchmark_thread_vs_process_parse`）はテストアセット38件のINPファイルを3方式でパースするため実行に数分かかる。CIでの実行時間が問題になる場合はpytest.markで分離可能
- `orientation`キーワードの追加により、ORIENTATIONの変更がメタデータ差分に表示されなくなる。ORIENTATIONの独立変更（メッシュ変更なし）は実運用では稀だが、該当ケースがあればフィルタから除外する必要がある
- plotly v6ではbarグラフのmarkerプロパティ構造が変更されている。他のchart_typeでも同様の非互換がある可能性があるため、plotlyバージョンアップ時は注意が必要
