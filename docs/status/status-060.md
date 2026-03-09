# status-060: Migration Guide・Abaqus使用マニュアル作成

- 日付: 2026-03-09
- ブランチ: claude/execute-status-todos-LGHaP

## 実施内容

### ドキュメント追加

1. **Migration Guide** (`docs/migration-guide.md`)
   - 手動ワークフローからjjへの移行手順
   - 旧CLI（submit系）→ 新CLI（graph系）コマンド対応表
   - 設定ファイルの移行方法（`.pyssh.yaml` → `.j2/config/config.yaml`）
   - v0.1.0 → v0.2.0 の破壊的変更・非推奨化一覧
   - プラグインシステム移行ガイド
   - トラブルシューティング

2. **Abaqus使用マニュアル** (`docs/abaqus-usage-guide.md`)
   - Abaqusリポジトリ前提の実践的な使用例マニュアル
   - 推奨ディレクトリ構成とファイル命名規則
   - parse → show → info → diff → export → dashboard の全フロー解説
   - `jj r` によるコマンド実行とログ記録
   - 設定カスタマイズ（vocab, path-type-map, dashboard）
   - 11の実践シナリオ（新規立ち上げ, 横断比較, 差分確認, メッシュ品質, 材料管理, Run管理, Neo4j, REST API, Obsidian）
   - よく使うコマンド一覧

3. **docs/README.md** にリンク追加

## テスト

- ドキュメントのみの変更、テスト影響なし

## TODO

### ワークトラック

- [ ] T3: M6 Phase 5 MLダッシュボード
- [ ] T5: リモートジョブ実行基盤
- [ ] T7: Ollama AI連携
- [ ] T8: 汎用データ管理

### ダッシュボード改善

- [ ] ギャラリービューで横・縦の列数をユーザー入力で選択可能にする
- [ ] 各ビュー画面にビュー保存ボタンを追加し、SavedView機能をその場で使えるようにする
- [ ] 配列プロットで各線の色をプロパティ属性値ベースで色分けするオプションを追加（現在は線ごとに自動色分け）

### CLI改善

- [ ] `jj parse` を他コマンドと繋ぎ合わせるタスクチェイン機能をプロジェクトごとに管理できる仕組みとして標準搭載する
- [ ] `jj r` でPython実行時にシステムPythonではなくCLIのアクティブなPythonパス（venv等）を使用するようにする
