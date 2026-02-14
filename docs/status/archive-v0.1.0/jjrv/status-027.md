# Status 027

> [← README.md](../../README.md)

**日付**: 2026-01-26
**セッション**: 検索ビュー改名とサブグループ/ダイアグラム実装

---

## 完了タスク

- [x] `/results` を `/search` に改名（ルート/リンク/README更新）
- [x] entityTypeグループにドメインサブグループを追加
- [x] サブグループ階層を可視化するダイアグラムビューを実装
- [x] ViewSwitcherにダイアグラム対応（任意ビュー指定）
- [x] 仕様書・コンポーネント一覧・プレビュー更新

---

## 変更したファイル

| ファイル | 変更内容 |
|---------|----------|
| [search/page.tsx](../src/app/search/page.tsx) | ルート変更、サブグループ化、表示選択/履歴更新 |
| [EntityGroup](../src/components/EntityGroup/index.tsx) | サブグループ表示とダイアグラム対応 |
| [EntityDiagram](../src/components/EntityDiagram/index.tsx) | グループ階層ダイアグラム（新規） |
| [ViewSwitcher](../src/components/ViewSwitcher/index.tsx) | diagram追加、views指定対応 |
| [ViewSwitcher/README](../src/components/ViewSwitcher/README.md) | diagram/props更新 |
| [components/README](../src/components/README.md) | EntityDiagram追加 |
| [search/README](../src/app/search/README.md) | 検索ビュー仕様を更新 |
| [app/README](../src/app/README.md) | /searchへ更新 |
| [README](../../README.md) | 構成のルート名更新 |
| [dev/components](../src/app/dev/components/page.tsx) | プレビュー/リンク更新 |
| [view/page.tsx](../src/app/view/page.tsx) | パンくず更新 |
| [page.tsx](../src/app/page.tsx) | 検索リンク更新 |
| [.status/status-index](../.status/status-index.md) | index更新 |

---

## 仕様メモ

- グループ表示は `entityType -> domain` の2階層
- ダイアグラムは上記階層をノード/リンクで可視化
- `/search` が検索結果の正式ルート
