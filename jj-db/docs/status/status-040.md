# Status 040

> [<- README.md](../../README.md)

**日付**: 2026-01-31
**セッション**: ロードマップ2.5 詳細ビューの作り込み

---

## 完了タスク

### 1. カードのグループ化機能を廃止

- [x] 検索ページからグループ表示ボタン・プロパティ選択UI・グループ表示ロジックを除去
- [x] `entity-grouping.ts` を削除（検索ページ以外に使用箇所なし）
- [x] `hierarchy-builder.ts` のentity-grouping参照コメントを更新
- [x] URL パラメータから `groupByType`, `groupProp1`, `groupProp2` を除去
- [x] 検索履歴への `groupByType` 記録を除去

### 2. 設計書と実装のズレ修正

- [x] `relation-api.ts` の認証トークンキーを `"auth_token"` → `"mat-db-auth-token"` に統一
- [x] `mock-data.ts` の EntityType を修正: `"Template"` → `"Project"`, `"Document"` → `"Project"`
- [x] `README.md` の Core Data Model を実装に合わせて更新（EntityType, attachedDocuments, remark, domainSource, domainConfidence, createdBy を追記）
- [x] `README.md` のロードマップにグループ化廃止を反映

### 3. フォーマット対応BodyRendererコンポーネント作成

- [x] `src/components/BodyRenderer/index.tsx` を新規作成
- [x] フォーマット自動検出: sysProps.format > userProps.format > domain > extension > 内容解析
- [x] Abaqus INPレンダラー: キーワード行(`*`)を青、コメント行(`**`)を緑で色分け
- [x] CSVレンダラー: テーブル形式で行列・ヘッダー表示
- [x] JSONレンダラー: indent整形、キー名を紫・値を琥珀色で色分け
- [x] Markdownレンダラー: 見出し、リスト、コードブロック、太字、インラインコード、リンク対応
  - `[[wikilink]]` 記法を attached_documents にマッピング
  - `[text](link)` 記法でも attached_documents を参照
- [x] プレーンテキストレンダラー: フォールバック

### 4. 詳細ビューの刷新（Gitリポジトリページ風）

- [x] ヘッダーセクション: EntityType, domain, format バッジ、名前、remark
- [x] 統計バッジ: 登録者名、お気に入りボタン（トグル）、ダウンロード数、いいねしたユーザーアイコン
- [x] コンテンツセクション: BodyRenderer によるフォーマット対応表示、行数表示
- [x] プロパティテーブル: sysProps/userProps をテーブルで表示（sys/user種別バッジ付き）
- [x] 関連エンティティセクション: グラフ/ダイアグラム/カード切替表示
- [x] コピー・ダウンロードボタン
- [x] 作成/更新日時表示

### 5. EntityCardのプレビュー強化

- [x] カード内にBodyRendererで先頭3行のフォーマット対応プレビューを表示
- [x] コピーホバー時のプレビューツールチップでBodyRenderer（15行）を使用

---

## 変更ファイル

### 新規作成
- `src/components/BodyRenderer/index.tsx` - フォーマット対応ボディレンダラー

### 更新
- `src/app/search/page.tsx` - グループ化機能の除去
- `src/app/view/page.tsx` - 詳細ビュー刷新（Gitリポジトリページ風）
- `src/components/EntityCard/index.tsx` - BodyRendererプレビュー追加
- `src/components/BodyPreviewTooltip/index.tsx` - BodyRenderer対応
- `src/lib/relation-api.ts` - auth_tokenキー修正
- `src/lib/mock-data.ts` - EntityType修正
- `src/lib/hierarchy-builder.ts` - コメント更新
- `README.md` - ロードマップ2.5追加、Core Data Model更新

### 削除
- `src/lib/entity-grouping.ts` - グループ化ロジック（廃止）

---

## 次回への引継ぎ

### ロードマップ2.5（残り）
- [ ] VTK/VTUのParaView形式3Dレンダラー機能（プラン段階）
  - three.js + vtk.jsによるWebGL 3Dレンダリング
  - format="vtk" or "vtu" のエンティティに対して3Dビューを表示

### ロードマップ3（操作性の調整）
- [ ] ドラッグ&ドロップ入力の強化（複数ファイル/分割）
- [ ] コピペ/プレビューの改善（即時プレビュー/差分表示）
- [ ] import/export（CSV/JSON/INP等）の整備

### その他
- [ ] BodyRendererにコード行番号表示オプション追加
- [ ] Markdownレンダラーの画像表示対応（attachedDocuments内の画像をインライン表示）

---
