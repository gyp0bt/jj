# status-044 (2026-02-02)

> [← README.md](../../README.md)

## 変更概要

### 1. ドキュメント集約（本セッション）
- PROJECT_BRIEF.md / SPEC_IMPORT_EXPORT.md / ROADMAP_MAP.md の内容をREADME.mdに統合
- 分散ドキュメントファイルを削除
- README.mdに「ロードマップ ↔ 仕様/実装 対応表」セクション追加
- README.mdに「Import / Export 仕様」セクション追加
- README.mdの「レビュー」セクション追加（review/review-00.mdへのリンク）
- ロードマップのステータスを最新に更新（完了/進行中を明記）
- Recent Changes (2026-02-02) セクションにPR #24, #25, Relation可視化の変更を追記
- statusファイル更新漏れ（status-043以降の3コミット分）を本statusで解消

### 2. Relation可視化・ビュー順変更・プリセットバグ修正・Mockデータ充実化（ae7143b）
- Switchボタンの順序をテーブル→ダイアグラム→グラフ→カードに変更
- ダイアグラム・グラフビューでカスタムプリセットが使えないバグを修正
- EntityDiagram/EntityGraphにRelationエッジ(破線)の描画機能を追加
- 検索ページでRelationを取得しdiagram/graphビューに流し込み
- 詳細ビューのRelationViewにテーブルビュー追加、全ビューにRelation可視化
- Mockデータ充実化: CSV/JSON/YAML/MD形式のProjectエンティティ追加
- MockRelation 20件追加(similar_to, tagged_with, uses_template等)
- seedエンドポイントでRelationも自動投入
- Relation一括取得API(entityIds指定/全件)を追加

### 3. インポート時の個別エンティティ編集機能（PR #24, 580ed69）
- EntityEditPanel: name, tag, property, bodyを編集するための再利用可能コンポーネントを新規作成
- EntityTable: 編集モードを追加（行展開でEntityEditPanelを表示）
- EntityDiagram: 編集モードを追加（ノードクリックで選択→下部にEntityEditPanel）
- EntityGraph: 編集モードを追加（ノードクリックで選択→下部にEntityEditPanel）
- GenericUploader: フォルダインポート時にViewSwitcher（table/diagram/graph）でプレビュー＆個別編集、一括タグ・プロパティ付与機能

### 4. ラベル付きRelation機能の追加（PR #25, 33c3cbf）
- カテゴリ・サブカテゴリ・グレードをuserPropsからラベル付きRelationに変更
- カテゴリ/サブカテゴリ/グレードのエンティティをMockデータに追加
- テーブルビューにプロパティ列(null埋め)とRelation列(ターゲット名表示)を追加
- EntityEditPanelにRelation編集機能(追加/削除)を追加
- GenericUploaderにドラフトRelation管理と一括Relation追加を追加
- ダイアグラム/グラフビューへのRelation描画

## 変更ファイル

### ドキュメント集約
- README.md（大幅更新: 分散ドキュメント統合、ロードマップ更新、Recent Changes追記）
- PROJECT_BRIEF.md（削除）
- SPEC_IMPORT_EXPORT.md（削除）
- ROADMAP_MAP.md（削除）
- .status/status-044.md（新規: 本ファイル）
- .status/status-index.md（更新）

### Relation可視化（ae7143b）
- src/app/api/entities/seed/route.ts
- src/app/api/relations/route.ts
- src/app/search/page.tsx
- src/app/view/page.tsx
- src/components/EntityDiagram/index.tsx
- src/components/EntityGraph/index.tsx
- src/components/HierarchyLabelBar/index.tsx
- src/components/ViewSwitcher/index.tsx
- src/lib/entity-repository.ts
- src/lib/mock-data.ts
- src/lib/relation-api.ts

### インポート編集（PR #24）
- src/components/EntityEditPanel/index.tsx（新規）
- src/components/EntityDiagram/index.tsx
- src/components/EntityGraph/index.tsx
- src/components/EntityTable/index.tsx
- src/components/GenericUploader/index.tsx

### ラベル付きRelation（PR #25）
- src/app/search/page.tsx
- src/components/EntityEditPanel/index.tsx
- src/components/EntityTable/index.tsx
- src/components/GenericUploader/index.tsx
- src/lib/mock-data.ts

## 対応するロードマップ項目
- 3. 操作性の調整 → Relation可視化、インポート編集、ラベル付きRelation
- ドキュメント整理 → 分散ドキュメント集約、statusファイル更新漏れ解消

## 次のアクション
- [ ] (P1) ImportSchema列挙管理ドキュメント
- [ ] (P1) 典型パターンからの属性抽出起点の決定
- [ ] (P2) 分割/マージ運用ルール（INP materialブロック、Markdownヘディング）
- [ ] (P3) エクスポート整形（フォルダ構造正規化、テンプレート出力）
- [ ] ドラッグ&ドロップ入力の強化（分割/マージ）
- [ ] import/export（CSV/JSON/INP等）のさらなる整備
