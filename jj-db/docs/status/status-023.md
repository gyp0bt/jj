# Status 023

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: TODO2 検索・閲覧体験の拡張（ビュー切り替え）

---

## 完了タスク

- [x] ViewSwitcher コンポーネント（カード/テーブル/グラフ切り替えUI）
- [x] EntityTable コンポーネント（テーブルビュー）
- [x] EntityGraph コンポーネント（react-force-graph-2dによるグラフビュー）
- [x] results/page.tsx にビュー切り替え統合
- [x] URLパラメータ `view=card|table|graph` 対応
- [x] 検索フィルタに表示件数（limit）を追加

---

## 追加したコンポーネント

| コンポーネント | 説明 |
|---------------|------|
| [ViewSwitcher](../src/components/ViewSwitcher/README.md) | カード/テーブル/グラフの切り替えボタン |
| [EntityTable](../src/components/EntityTable/README.md) | テーブル形式の一覧表示 |
| [EntityGraph](../src/components/EntityGraph/README.md) | マインドマップ風グラフ表示 |

---

## 技術的メモ

- react-force-graph-2d / d3-force を追加（フォースレイアウトグラフ + ノード間隔調整）
- ForceGraph2D は SSR 非対応のため dynamic import
- Next.js 15 では useSearchParams に Suspense 境界が必要
  - /results, /view ページに Suspense を追加
- 既存コードの型エラーを修正
  - auth.ts: jwt.sign の expiresIn 型
  - mock-data.ts: userProps の Record<string, string> 型

---

## TODO2 進捗

### 2. 検索・閲覧体験の拡張
- [x] 検索結果の複数ビュー（カード/テーブル/グラフ）
- [x] グラフビュー（マインドマップ風の関係可視化）
- [ ] フィルタ/並び替えの強化（プロパティ・タグ・ドメインの組み合わせ）

---

## 次のステップ

- フィルタ/並び替えの強化
- または TODO3「直感的な操作性の強化」へ
