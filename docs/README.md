[← README.md](../README.md)

# docs/ — ドキュメント

---

## ドキュメント構成

| ドキュメント | 説明 |
|-------------|------|
| [v0.2.0 ロードマップ](roadmap.md) | マイルストーン・仕様書リンク集 |
| [statusインデックス](status/status-index.md) | v0.2.0 statusファイル索引 |
| [v0.1.0 statusインデックス](status/status-index-v0.1.0.md) | v0.1.0全statusファイルの索引 |
| [v0.1.0レビュー](review/review-v0.1.0.md) | 開発フェーズ総括・v0.2.0ロードマップ案 |
| [v0.1.0 ロードマップ](roadmap-v0.1.0.md) | jj v0.1.0ロードマップ（アーカイブ） |
| [実装詳細](detail.md) | 実装方針・技術詳細 |
| [仕様書一覧](specs/README.md) | 機能ドメイン別仕様書 |

---

## statusファイル運用ルール

- v0.2.0以降のstatusは `docs/status/status-{NNN}.md` に共有管理
- 粒度基準: 1 status = 1 PR 程度
- statusに書いた内容はgitのcommitメッセージと整合
- 未完了TODOは次のstatusに引き継ぎ
- v0.1.0のstatusは `docs/status/archive-v0.1.0/` にアーカイブ済み
