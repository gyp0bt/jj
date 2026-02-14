# spec-roadmap2: 検索・閲覧体験の拡張

> [← README.md](../README.md)

---

## 設計方針

### 目的
検索結果を多角的に可視化し、フィルタ・並び替え・グルーピングで素早く目的のデータにたどり着ける体験を構築する。

### 方針
1. **マルチビュー** — カード/テーブル/グラフ/ダイアグラムの4種ビューをワンクリックで切替。
2. **インラインフィルタ** — 各ビュー内でデータを絞り込み。テーブルは列フィルター、カード/グラフはクイックフィルター。
3. **Relation中心の階層定義** — 階層グループはrelationのlabelで定義。プロパティ基準の動的グルーピングは廃止。tagもrelation（label=tagged）で統一し、完全にrelationで関係を定義する。ただしtype属性のみノード・階層属性として残す。
4. **D3ベース可視化** — グラフビューはforce-directed layout、ダイアグラムはD3ツリーレイアウトを使用。
5. **ローカルストレージ永続化** — グルーピング設定・プリセットをブラウザに保存。
6. **テーブルビューの操作性** — セル編集・列制御・relation表示切替で実用的なデータ操作を実現。

---

## 実装要件

### 完了済み

| # | 要件 | 概要 |
|---|------|------|
| 2-01 | 複数ビュー切替 | カード/テーブル/グラフ/ダイアグラムをViewSwitcherで切替 |
| 2-02 | グラフビュー | react-force-graph-2d＋D3によるマインドマップ風関係可視化 |
| 2-03 | フィルタ/並び替え強化 | プロパティ・タグ・ドメインの組み合わせ、ソート順切替 |
| 2-04 | ダイアグラム型階層表示 | entityType順指定、ツリー/ネスト構造で可視化 |
| 2-05 | インラインフィルター | テーブル: 列フィルター・ソート、カード/グラフ: クイックフィルターバー |
| 2-06 | 動的プロパティグルーピング | 色変更、値フィルター、カスタムプロパティ追加 |
| 2-07 | ビューswitch順変更 | テーブル→ダイアグラム→グラフ→カードの順 |
| 2-08 | ユーザー表示名対応 | ダイアグラム/グラフでid→表示名に変更 |
| 2-09 | テーブルビューソート・フィルター | 列ヘッダークリックでソート、列下に空白区切りAND検索フィルター |
| 2-10 | グルーピング設定永続化 | ローカルストレージにプリセット保存 |
| 2-11 | グラフビュー動的グループ化 | ダイアグラムと同等の動的グループ化機能をグラフビューにも実装 |

### 未完了

| # | 要件 | 概要 |
|---|------|------|
| 2-12 | 階層グループのrelation label基準化 | ダイアグラム/グラフビューの階層グループをrelationのlabelで定義する方式に変更。プロパティ基準は廃止。tagもrelation（label=tagged）とし、完全にrelationで関係を定義する。type属性のみノード・階層属性として残す |
| 2-13 | hover時type属性表示 | ダイアグラム/グラフビューでノードhover時にtype属性を表示する |
| 2-14 | エリア選択と操作変更 | ダイアグラム/グラフビューで左クリックによるエリア選択を実装。移動操作は中クリックに変更 |
| 2-15 | 表示プリセットデフォルト廃止 | ダイアグラムビューではrelationのlabel定義が多い順に階層を自動定義。グラフビューでは全relationを表示するデフォルトに変更 |
| 2-16 | ダイアグラム階層順ユーザー定義 | ダイアグラムビューで階層の上下の順番をユーザーが定義できる機能を維持 |
| 2-17 | グラフビュー設定オプション | Obsidian同様の設定オプション機能を追加。力の強さとして中心力、反発力、リンクする力、リンクの距離をスライダーで調節 |
| 2-18 | グラフビューrelation表示 | relationを灰色実線で表示。設定オプションで向きを示す矢印のオンオフを切替。ラベルをエッジ上の中点に表示 |
| 2-19 | テーブルビューrelation列操作 | relation列クリックでsort/filter機能を追加。右クリックで列を隠す、隠した列を再表示するコンポーネントを追加。インポート時同様の編集機能も追加 |
| 2-20 | テーブルビュープロパティ列制御 | ユーザー定義でプロパティを列に表示/非表示する機能を追加。表示候補は現在の検索結果のandを取る |
| 2-21 | テーブルビューrelationテーブル切替 | relationテーブルのswitchボタンを追加し、relationのみ表示する機能 |
| 2-22 | テーブルビューセル編集 | セルをダブルクリックするとテキストボックスで属性を変更可能に。タグ列はスペースで確定、プロパティ列は値をそのまま入力、relation列はlabelをそのまま入力 |
| 2-23 | テーブルビュー詳細遷移とプレビュー | 詳細ビューへの遷移を名前列に絞り、名前列hover時にプレビューを表示。コピーボタンでのプレビューは廃止 |
| 2-24 | テーブルビュー列境界線 | 列の境界が見えるようにグレー線を引く |

---

## 実装要件 ↔ ファイル対応テーブル

### 完了済み

| # | 要件 | 主要ファイル | 補助ファイル |
|---|------|-------------|-------------|
| 2-01 | 複数ビュー切替 | `src/components/ViewSwitcher/index.tsx` | `src/app/search/page.tsx` |
| 2-02 | グラフビュー | `src/components/EntityGraph/index.tsx` | — |
| 2-03 | フィルタ/並び替え強化 | `src/components/SearchFilter/index.tsx` | `src/app/search/page.tsx` |
| 2-04 | ダイアグラム型階層表示 | `src/components/EntityDiagram/index.tsx` | `src/lib/hierarchy-builder.ts` |
| 2-05 | インラインフィルター | `src/components/EntityTable/index.tsx` | `src/components/EntityGraph/index.tsx`（クイックフィルター） |
| 2-06 | 動的プロパティグルーピング | `src/components/HierarchySettingsModal/index.tsx`, `src/components/HierarchyLabelBar/index.tsx` | `src/lib/hierarchy-builder.ts` |
| 2-07 | ビューswitch順変更 | `src/components/ViewSwitcher/index.tsx` | — |
| 2-08 | ユーザー表示名対応 | `src/components/EntityDiagram/index.tsx`, `src/components/EntityGraph/index.tsx` | `src/lib/user-api.ts` |
| 2-09 | テーブルビューソート・フィルター | `src/components/EntityTable/index.tsx` | — |
| 2-10 | グルーピング設定永続化 | `src/lib/use-hierarchy-storage.ts` | — |
| 2-11 | グラフビュー動的グループ化 | `src/components/EntityGraph/index.tsx` | `src/components/HierarchyLabelBar/index.tsx`, `src/lib/hierarchy-builder.ts` |

### 実装済み（status-047）

| # | 要件 | 主要ファイル | 補助ファイル |
|---|------|-------------|-------------|
| 2-12 | 階層グループのrelation label基準化 | `src/lib/hierarchy-builder.ts`, `src/lib/types.ts` | `src/components/EntityDiagram/index.tsx` |
| 2-14 | エリア選択と操作変更 | `src/components/EntityDiagram/index.tsx` | — |
| 2-15 | 表示プリセットデフォルト廃止 | `src/lib/hierarchy-builder.ts` | — |
| 2-16 | ダイアグラム階層順ユーザー定義 | `src/lib/hierarchy-builder.ts` | — |
| 2-17 | グラフビュー設定オプション | `src/components/EntityGraph/index.tsx` | — |
| 2-18 | グラフビューrelation表示 | `src/components/EntityGraph/index.tsx` | — |
| 2-19 | テーブルビューrelation列操作 | `src/components/EntityTable/index.tsx` | — |
| 2-20 | テーブルビュープロパティ列制御 | `src/components/EntityTable/index.tsx` | — |
| 2-21 | テーブルビューrelationテーブル切替 | `src/components/EntityTable/index.tsx` | — |
| 2-22 | テーブルビューセル編集 | `src/components/EntityTable/index.tsx` | — |
| 2-23 | テーブルビュー詳細遷移とプレビュー | `src/components/EntityTable/index.tsx` | — |
| 2-24 | テーブルビュー列境界線 | `src/components/EntityTable/index.tsx` | — |

### 未完了

| # | 要件 | 主要ファイル | 補助ファイル |
|---|------|-------------|-------------|
| 2-13 | hover時type属性表示 | （未実装） | — |
