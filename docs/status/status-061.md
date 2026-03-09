[← README.md](../../README.md)

# status-061: status-060 TODO実行（CLI・ダッシュボード改善11件）

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-6R9QI

## 実施内容

### CLI改善

1. **`jj r` でvenv Pythonパスを自動使用**
   - `python`/`python3` コマンドを `sys.executable` に置換
   - venv環境でjjを実行している場合、`jj r -- python script.py` でもvenvのPythonが使われる

### ダッシュボード改善

2. **ギャラリー列数・行数をUI入力で変更可能に**
   - ギャラリーページ上部に列数（1-10）・行数（1-20）のnumber_inputを追加
   - セッション状態経由で下流のoutput/propertyギャラリーにも反映

3. **各ビューページにビュー保存ボタン追加**
   - 全PageComponentのrender後に「このビューを保存」expanderを表示
   - ビュー名入力→保存で動的ビューとして永続化

4. **配列プロットでプロパティベースの色分けオプション追加**
   - 「色分け設定」expanderでプロパティキーを選択可能
   - 選択した属性値ごとにplotly色パレットを割り当て、legendgroupで凡例統合

5. **AgGridに文字列/数値フィルター有効化**
   - 数値列に`agNumberColumnFilter`、文字列列に`agTextColumnFilter`を設定
   - AgGrid本来のフィルタ機能（contains, equals, greater than等）が使用可能に

6. **テーブルのindex/version列をint型に変換**
   - `pd.to_numeric(errors="coerce").astype("Int64")` で変換
   - AgGridで数値ソート・数値フィルタが正しく動作する

7. **Run比較ビューのimport登録漏れ修正**
   - `app.py` で `run_comparison` コンポーネントのimportが欠落していたためページ一覧に表示されなかった

8. **Re-parse後自動リロード・Configリロードボタン追加**
   - Re-parse後にフィルタ初期化をリセットしてrerun
   - サイドバーに「Config再読み込み」ボタンを追加（config.yaml変更後の反映用）

### jj diff 改善

9. **parameterブロック差分検出の修正**
   - `ABQData` に `parameters` フィールドを追加（`field(default_factory=dict)`）
   - `read_inp()` で `context.parameters` を `ABQData.parameters` に保存
   - `_diff_parameters()` 関数を追加し、parameterブロックの差分を正しく検出

10. **diff表示のフォーマット改善**
    - `_format_location()` で人間可読な差分位置表示（例: "Step 1 > boundary"）
    - `_format_diff_value()` で `json.dumps(indent=2)` による整形表示
    - `format_diff_summary_table()` と `format_diff_blocks_markdown()` の両方に適用

### CLI追加改善

11. **`jj r` コマンドの `--` 引数を不要化**
    - `parse_known_args()` を使用し、残り引数をコマンドに自動追加
    - `jj r python script.py arg1` のように `--` なしで実行可能

### Python API

12. **`import jj` でプロジェクトグラフにアクセスするAPI提供**
    - `jj/__init__.py` に `load()`, `get_node()`, `get_nodes()`, `get_properties()`, `get_property()` を実装
    - `_find_project_root()` で `.j2` ディレクトリを上位探索し自動検出
    - `pyproject.toml` のパッケージ一覧に `jj` を追加

### ドキュメント

13. **Prefect連携ガイド追加**
    - `docs/prefect-integration-guide.md` を新規作成
    - 5パターン: CLIタスク、Python APIタスク、jj r統合、パラメータスイープ、結果収集
    - `docs/README.md` にリンク追加

## テスト

- ruff check / ruff format: パス
- pytest: 1660 passed, 102 skipped（全テスト通過）

## TODO

### ワークトラック（継続）

- [ ] T3: M6 Phase 5 MLダッシュボード
- [ ] T5: リモートジョブ実行基盤
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理
