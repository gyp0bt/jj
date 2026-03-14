[← README.md](../../../README.md) | [← status-index](status-index.md)

# status-009 — ダッシュボード改善: ライトテーマ・ビュー永続化・results除外ロジック

- **日付**: 2026-02-17
- **マイルストーン**: M2（マルチソルバー基盤）
- **ブランチ**: `claude/dashboard-views-light-theme-3Dimf`

---

## 実施内容

### 1. results/直下ファイルのノード化ロジック変更

**変更ファイル**: `jj/services/parse/parsers/enrichment_filter.py`

これまでresults/直下のファイルはすべてノード化せず除外していたが、
追加パラメータの有無で判定するよう変更:

- **除外**: go_inpと同じプロパティ（result_keyのみ）のファイル
  - 例: `results/go_idx1.v1_RF3.csv` → result_keyのみ（RF3）→ 除外
- **保持**: 追加パラメータがあるファイル
  - 例: `results/go_idx1.v1_RF3_step0.csv` → step0が追加パラメータ → 保持
- **保持**: results/のサブディレクトリ内のファイルは従来通り保持
  - 例: `results/step0/go_idx1.v1_RF3.csv`

**実装**: `_count_suffix_tokens()` 関数でgo_basename後のトークン数を判定。
トークン1個（result_keyのみ）なら除外、2個以上（追加パラメータあり）なら保持。

**テスト**: `TestEnrichmentOnlyFilter` に3テスト追加（合計6テスト通過）

### 2. ダッシュボードのデフォルトテーマをライトに変更

**変更ファイル**: `jj/services/cli/launchers.py`

Streamlit起動コマンドに `--theme.base light` を追加。
システムテーマではなくライトテーマが常にデフォルトとなる。

### 3. ダッシュボードのビュー保存・閲覧機能（永続化対応）

**変更ファイル**: `jj/services/dashboard/app.py`

これまで動的ビューはStreamlitのsession_stateにのみ保存され、
ブラウザを閉じると消えていた。以下の変更で永続化を実現:

| 機能 | 実装 |
|------|------|
| **保存先** | `.j2/storage/saved-views.yaml` |
| **読み込み** | セッション開始時にファイルから自動読み込み |
| **保存タイミング** | ビューの追加・編集・削除時に自動保存 |
| **ページ表示** | 「保存済みビュー」ページを常にサイドバーに表示 |

**追加関数**:
- `_load_persistent_views()`: YAMLファイルからビュー読み込み
- `_save_persistent_views()`: YAMLファイルにビュー保存
- `_saved_views_path()`: 保存パス解決

---

## テスト結果

- **全テスト**: 875 passed, 41 skipped（pymesh/scipy依存のみskip）
- **lint/format**: ruff check + ruff format 通過
- **EnrichmentOnlyFilter**: 6テスト通過（新規3テスト含む）
- **パイプラインresultsテスト**: 4テスト通過
- **実データテスト**: 4テスト通過

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `jj/services/parse/parsers/enrichment_filter.py` | results直下の除外ロジックをプロパティ判定方式に変更 |
| `jj/services/cli/launchers.py` | Streamlit起動時にライトテーマをデフォルト指定 |
| `jj/services/dashboard/app.py` | ビュー永続化（saved-views.yaml）、保存済みビューページ常時表示 |
| `jj/tests/test_parser_units.py` | EnrichmentOnlyFilterの新テスト3件追加 |
| `docs/status/status-009.md` | 本statusファイル |
| `docs/status/status-index.md` | インデックス更新 |

---

## 確認事項・TODO

- [ ] ビュー永続化のテスト追加（app.pyはStreamlit依存のため単体テストは要検討）
- [ ] ライトテーマの実機確認（Streamlit起動環境で視認性確認）
- [ ] results除外ロジックの実プロジェクトでの動作確認
