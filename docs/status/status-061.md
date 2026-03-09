[← README.md](../../README.md)

# status-061: status-060 TODO実行（CLI・ダッシュボード改善8件）

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

## テスト

- ruff check / ruff format: パス
- 既存テスト: 変更はUI層中心のため既存テストへの影響なし

## TODO

### 今回のセッションで受けた追加要望（未着手）

- [ ] jj diff: parameterブロックに差があるのにno differenceになるバグ修正
- [ ] jj diff: スタイル表示でなくparameter.blocks[0]のような生キー表示になる問題修正
- [ ] CLI: `jj r` の `--` 引数を不要にする
- [ ] Python API: `import jj` でノード情報にアクセスするAPI提供（`jj.get_property(path)`, `jj.get_node(path)` 等）

### ワークトラック（継続）

- [ ] T3: M6 Phase 5 MLダッシュボード
- [ ] T5: リモートジョブ実行基盤
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理

### 設計懸念・開発運用メモ

- ユーザーから矢継ぎ早に要望が来る場合、コミット前にTODOリストにまとめて確認を取るフローが有効
- jj diff の問題は Abaqus コネクター固有のシリアライズ・比較ロジックに起因する可能性が高い（要詳細調査）
- Python API (`import jj`) は pyproject.toml の entry_points や `__init__.py` でのパブリックAPI設計が必要
