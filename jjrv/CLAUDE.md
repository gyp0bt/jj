[← README.md](README.md) | [ルート CLAUDE.md](../CLAUDE.md)

# jjrv CLAUDE.md

jjrv固有の規約はここに記載。プロジェクト全体の規約は [ルート CLAUDE.md](../CLAUDE.md) を参照。

## コマンド

```bash
pnpm dev          # 開発サーバー起動 (http://localhost:3000)
pnpm build        # プロダクションビルド
pnpm lint         # Biomeでlint
pnpm format       # Biomeでフォーマット（自動修正）
```

## テスト・検証

```bash
pnpm exec tsc --noEmit   # 型チェック
pnpm build               # ビルド検証
pnpm lint                # lint
```

## 技術スタック

- Next.js 15, React 19, TypeScript, Tailwind CSS v4
- データソース: SQLite (sql.js) — Neo4j対応予定
- パッケージマネージャ: pnpm

## ドキュメント

- statusファイルは `docs/status/` （ルート共有）に記載
- jjrv固有仕様は `jjrv/docs/spec-roadmap{1-6}.md` を参照
- v0.1.0 statusアーカイブは `docs/status/archive-v0.1.0/jjrv/` に保管
