[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-058: CI YAML構文エラー修正

- **日付**: 2026-03-08
- **マイルストーン**: v0.3.0 インフラ整備
- **ブランチ**: `claude/execute-status-todos-R96yx`

---

## 概要

GitHub Actions CIが全run失敗（ジョブ0件）の原因を調査・修正:

1. **根本原因**: `ci.yml` 48行目のYAML構文エラー。`python -c` のインラインコードに含まれるf-string（`f'..{names}'`）の波括弧がYAMLパーサーに誤解釈されていた
2. **修正**: `run:` をブロックスカラー（`|`）に変更し、Pythonコードを複数行に展開

## 変更内容

| ファイル | 変更 |
|---------|------|
| `.github/workflows/ci.yml` | L48: `run:` インラインPython → `run: \|` ブロックスカラーに修正 |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 217 files already formatted
- **pytest**: 1657 passed, 101 skipped
- **YAML検証**: `yaml.safe_load()` でパース成功

## TODO

- [ ] T3: M6 Phase 5 MLダッシュボード（MLOverviewPage, 三層データフロー可視化）
- [ ] T5: リモートジョブ実行基盤（jj submit/watch/collect）
- [ ] T7: Ollama AI連携（AIProviderプロトコル, 要約, RAG, tips）
- [ ] T8: 汎用データ管理（Run中心プラットフォームへの昇華）
- [ ] streamlit-agraphの本番環境でのテスト
- [ ] Abaqus Explicit形式の.staファイル対応（サンプル入手後）
- [ ] status-052 TODO: Run DAG可視化（T6-3のグラフビューを拡張）
- [ ] CIが正常にジョブ実行されることをpush後に確認

## 確認事項・懸念

- CI失敗の原因はYAML構文エラーであり、status-057時点ではmain→master修正のみで構文問題に気づけなかった
- f-stringの`{}`がYAMLのフロースカラーと競合する典型的な問題。今後CI YAMLでは`run: |`ブロックスカラーを使うべき

## 開発運用メモ

- **効果的**: ユーザーのスクリーンショット共有により、GitHub上のAnnotation「Invalid workflow file: .github/workflows/ci.yml#L48」から即座に原因特定できた
- **非効果的**: `gh api` でCI runのログ取得を試みたが、ジョブ0件のrunはログZIPが存在せず404になる。Annotationはgh apiでは取得しにくい
