# Status 030

> [← README.md](../../README.md)

**日付**: 2026-01-27
**セッション**: UI境界線改善とダイアグラムビュー再編成

---

## 完了タスク

- [x] UI境界線をGitHubスタイルのグレーボーダーに変更
- [x] グラフビューのhoverプレビューを解除
- [x] ダイアグラムビューをグラフビューにリネーム（4階層、検索結果ノード排除）
- [x] アローダイアグラムビューを新規実装

---

## 変更したファイル

| ファイル | 変更内容 |
|---------|----------|
| src/components/EntityCard/style.ts | ボーダーをborder-gray-300に統一 |
| src/components/EntityCard/index.tsx | ボタンのボーダースタイル更新 |
| src/components/SearchBar/index.tsx | ボーダーをborder-gray-300に統一 |
| src/components/EntityTable/index.tsx | ボーダーをborder-gray-300に統一 |
| src/components/ViewSwitcher/index.tsx | ボーダーをborder-gray-300に統一 |
| src/components/BodyPreviewTooltip/index.tsx | ボーダーをborder-gray-300に統一 |
| src/components/EntityDiagram/index.tsx | 4階層構造に変更、hoverプレビュー削除 |
| src/components/EntityArrowDiagram/index.tsx | 新規作成（アローダイアグラム） |
| src/components/EntityGraph/ | 削除（EntityDiagramに統合） |
| src/components/EntityGroup/index.tsx | 新ビュー対応 |
| src/app/search/page.tsx | ビュー切り替えロジック更新 |
| src/app/dev/components/page.tsx | プレビュー更新 |

---

## 仕様メモ

### ビュー構成
- **カード**: EntityCard による一覧表示
- **テーブル**: EntityTable による一覧表示
- **グラフ**: EntityDiagram による4階層ノードグラフ（entityType → domain → tag → entity）
- **ダイアグラム**: EntityArrowDiagram によるSVGアローダイアグラム

### ボーダースタイル
- ライトモード: `border-gray-300`
- ダークモード: `border-gray-600`
