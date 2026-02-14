# Status 038

> [← README.md](../../README.md)

**日付**: 2026-01-29
**セッション**: 各ビューにフィルター機能統合、ダイアグラムビューのグルーピング強化

---

## 完了タスク

### 1. 各ビューコンポーネントへのフィルター機能統合

#### テーブルビュー (EntityTable)
- [x] 列ヘッダー下にインラインフィルター入力欄を追加
- [x] 空白区切りキーワードでAND検索
- [x] 名前・ドメイン・タグ列のソート機能（昇順/降順トグル）
- [x] フィルター結果件数の表示
- [x] `enableFiltering` propsでフィルター機能を制御

#### カード/グラフビュー (EntityGroup)
- [x] クイックフィルターバー追加（名前・ドメイン・タグの一括検索）
- [x] フィルター展開/閉じるUI
- [x] フィルター結果件数の表示
- [x] サブグループへのフィルター適用

### 2. ダイアグラムビューの動的プロパティグルーピング強化

#### HierarchyLabelBar 強化
- [x] 各階層レベルの色カスタマイズ（15色パレット）
- [x] 値フィルター機能（LevelSettingsPopover）
  - 階層をクリックで設定ポップオーバー表示
  - 各値のチェックボックスでフィルタリング
  - 全選択/全解除ボタン
- [x] カスタムプロパティの手動追加UI（CustomFieldDialog）
  - sysProps/userPropsの選択
  - プロパティキーと表示ラベルの入力
- [x] フィルター適用状態のアイコン表示

#### hierarchy-builder.ts
- [x] HierarchyLevel型にvalueFilterプロパティを追加
- [x] グループ化時の値フィルター適用（applyValueFilter関数）

### 3. README修正
- [x] TODOリストの更新（検索・閲覧体験の拡張セクション）
- [x] Recent Changesの追加

---

## 変更ファイル

- `src/components/EntityTable/index.tsx` - インラインフィルター・ソート機能追加
- `src/components/EntityGroup/index.tsx` - クイックフィルター機能追加
- `src/components/HierarchyLabelBar/index.tsx` - 色変更・値フィルター・カスタム追加UI
- `src/lib/hierarchy-builder.ts` - 値フィルター適用ロジック
- `src/lib/types.ts` - HierarchyLevel型にvalueFilterを追加
- `README.md` - TODO/Recent Changes更新

---

## 次回への引継ぎ

- [ ] グルーピング設定のローカルストレージ永続化（プリセット保存）
- [ ] 検索履歴の再利用（履歴UI）
- [ ] ドラッグ&ドロップ入力の強化（複数ファイル/分割）
- [ ] import/export（CSV/JSON/INP等）の整備
- ~~[ ] 上部にナビゲーションバー追加、現在地表示および移動リンクとアイコンを押してホーム移動~~

---
