[READMEへ戻る](../../README.md)

# status-035: ダッシュボードアーキテクチャ設計・ロードマップ策定

**日付**: 2026-02-08

## 概要

jjが抽出したプロパティとrelationを一覧・可視化するダッシュボード機能の推奨構成を設計し、ロードマップに反映した。jj側（Streamlit）とmat-db側（Next.js）の役割分担を明確化。

## 設計判断

### 技術選定

| 比較対象 | 判定 | 理由 |
|---------|------|------|
| Streamlit | **jj側で採用** | Pythonネイティブ、ag-grid/plotly統合、インタラクティブ、実績あり |
| Jinja2 → HTML | 不採用 | 静的でフィルター/プロット不可、更新のたびに再生成が必要 |
| Obsidian | 既存継続 | ナレッジグラフに強いがテーブル/プロットに弱い。エクスポート先として維持 |
| mat-db (Next.js) | **将来的な統合先** | 高機能ビュー完備、ユーザー管理済み。詳細レンダリング担当 |

### 役割分担

- **jj dashboard (Streamlit)**: プロジェクトローカルの即時ビュー。graph.yaml直接読み込み。
- **jj serve (FastAPI)**: mat-dbとの連携用REST API。
- **mat-db (Next.js)**: 組織横断のDB検索・高度なレンダリング。将来jjと統合。

## 新規ドキュメント

| ファイル | 内容 |
|---------|------|
| `docs/specs/09-dashboard.md` | ダッシュボード層仕様書（全体設計、ページ構成、API、mat-db統合） |

## ロードマップ更新

roadmap.mdに以下を追加:

### Phase 2.5: ダッシュボード・API基盤

| サブフェーズ | 内容 |
|-------------|------|
| D1 | データ供給基盤（DashboardDataProvider、dashboard-jsonエクスポート） |
| D2 | Streamlitダッシュボード（テーブル/カード/プロット/ステータス） |
| D3 | REST API（FastAPI、jj serve） |
| D4 | mat-db統合（エクスポート、API連携） |

### マイルストーン M2.5 追加

- DashboardDataProviderが完全動作
- `jj dashboard` で4ビュー（テーブル/カード/プロット/ステータス）起動
- dashboard-jsonエクスポート動作

## Streamlitダッシュボード ページ構成

1. **テーブルビュー**: ag-gridでgo_ファイル一覧。プロパティカラム展開、analysis_statusフィルター
2. **カードビュー**: 選択ノードの詳細。関連画像、メッシュ要約、警告/エラー表示
3. **プロットビュー**: plotly散布図/線図。X/Y軸をプロパティキーから選択、色分け対応
4. **ステータスモニター**: 実行中/完了/失敗の一覧。.sta/.msg解析結果とrunログ統合

## 依存パッケージ（追加予定）

| パッケージ | 用途 |
|-----------|------|
| streamlit | ダッシュボードフレームワーク |
| streamlit-aggrid | ag-gridテーブル |
| plotly | インタラクティブプロット |
| pandas | DataFrame操作 |
| fastapi | REST API（D3フェーズ） |
| uvicorn | ASGIサーバー（D3フェーズ） |

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `docs/specs/09-dashboard.md` | 新規: ダッシュボード層仕様書 |
| `docs/roadmap.md` | 変更: Phase 2.5・M2.5追加、参照更新 |
| `docs/status/status-035.md` | 新規: 本ステータス |
| `README.md` | 変更: ステータスリンク追加 |
| `docs/specs/README.md` | 変更: ダッシュボード層追加 |

## TODO / 次のステップ

- [ ] Phase D1: DashboardDataProvider実装（`services/dashboard/data_provider.py`）
- [ ] Phase D1: `jj export --target dashboard-json` 実装
- [ ] Phase D2: Streamlitアプリ骨格作成（`services/dashboard/app.py`）
- [ ] Phase D2: テーブルビュー実装
- [ ] Phase D2: カード/プロット/ステータスビュー実装
- [ ] pyproject.toml/setup.cfgにoptional-dependencies追加

## 確認事項・設計上の懸念

- mat-dbとjjの統合タイミング: mat-dbのプロジェクト名（**jj-dbに改名済み** - status-036参照）が確定してから統合設計を具体化すべき → 確定済み
- Streamlitのバージョン固定: streamlit-aggridの互換性が特定バージョンに依存することがある
- REST APIの認証: ローカル専用の初期段階では不要だが、mat-db統合時にAPIキーまたはOAuth導入が必要
- graph.yamlが大きい場合のStreamlit表示パフォーマンス: キャッシュ+遅延読み込みで対応予定
