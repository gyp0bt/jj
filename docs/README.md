[← README.md](../README.md)

# docs/ — 共有ドキュメント

v0.2.0から、プロジェクト横断のドキュメントはここに配置する。
各モジュール固有のドキュメントは `jj/docs/` および `jjrv/docs/` に配置。

---

## ドキュメント構成

### 共有ドキュメント（このディレクトリ）

| ドキュメント | 説明 |
|-------------|------|
| [最新status](status/status-001.md) | v0.2.0 実装状況の最新記録 |
| [v0.1.0 statusインデックス](status/status-index-v0.1.0.md) | v0.1.0全statusファイルの索引（151件） |
| [v0.1.0レビュー](review/review-v0.1.0.md) | 開発フェーズ総括・v0.2.0ロードマップ案 |

### jj固有ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [ロードマップ](../jj/docs/roadmap.md) | jj開発ロードマップ（Phase 0〜P、v0.1.0完了） |
| [実装詳細](../jj/docs/detail.md) | 実装方針・技術詳細 |
| [仕様書一覧](../jj/docs/specs/README.md) | 機能ドメイン別仕様書（01〜11） |

### jjrv固有ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [RM1: ユーザー運用](../jjrv/docs/spec-roadmap1.md) | ロードマップ1（完了） |
| [RM2: 検索・閲覧](../jjrv/docs/spec-roadmap2.md) | ロードマップ2（実装済み） |
| [RM2.5: 詳細ビュー](../jjrv/docs/spec-roadmap25.md) | ロードマップ2.5 |
| [RM3: 操作性](../jjrv/docs/spec-roadmap3.md) | ロードマップ3 |
| [RM4: 本番運用](../jjrv/docs/spec-roadmap4.md) | ロードマップ4 |
| [RM5: 階層制約](../jjrv/docs/spec-roadmap5.md) | ロードマップ5 |
| [RM6: jj統合](../jjrv/docs/spec-roadmap6.md) | ロードマップ6（設計済み・未実装） |
| [ダッシュボード設計](../jjrv/docs/spec-dashboard.md) | レポジトリダッシュボード詳細設計 |
| [レビュー00](../jjrv/docs/review/review-00.md) | jjrvプロジェクトレビュー (2026-01-31) |

---

## statusファイル運用ルール

- v0.2.0以降のstatusは `docs/status/status-{NNN}.md` に共有管理
- 粒度基準: 1 status = 1 PR 程度
- statusに書いた内容はgitのcommitメッセージと整合
- 未完了TODOは次のstatusに引き継ぎ
- v0.1.0のstatusは `docs/status/archive-v0.1.0/` にアーカイブ済み
