# Status 033

> [← README.md](../../README.md)

**日付**: 2026-01-27
**セッション**: ダイアグラムビューの動的階層グループ化機能の実装

---

## 完了タスク

- [x] 階層レベル定義の型を追加（HierarchyLevel, HierarchyPreset, DynamicHierarchyConfig）
- [x] 動的階層構築ロジックを作成（src/lib/hierarchy-builder.ts）
- [x] HierarchyLabelBarコンポーネントを作成（ドラッグ&ドロップ対応）
- [x] EntityArrowDiagramを動的階層に対応させる
- [x] EntityDiagramを動的階層に対応させる
- [x] 検索ページにダイアグラム階層設定UIを統合（コンポーネント内蔵）
- [x] lintエラーの修正

---

## 実装内容

### 動的階層グループ化機能

ダイアグラムビュー（graph/diagram）で階層グループ化の順序を動的に変更できる機能を実装しました。

#### 主な機能
1. **階層ラベルバー（HierarchyLabelBar）**: ダイアグラム上部に表示され、ドラッグ&ドロップで階層順序を変更可能
2. **プリセット選択**: よく使う階層構成をワンクリックで適用
3. **階層の追加・削除**: 任意のフィールドを階層として追加・削除可能
4. **柔軟なフィールド対応**: entityType, domain, createdBy, sysTags, sysProps, userPropsに対応

#### 利用可能な階層フィールド
- タイプ（entityType）
- ドメイン（domain）
- 登録ユーザー（createdBy）
- プライマリタグ（sysTags.0）
- セカンダリタグ（sysTags.1）
- カスタムプロパティ（sysProps.*, userProps.*）

#### デフォルトプリセット
1. **タイプ → ドメイン → タグ**: デフォルト設定
2. **ユーザー → タイプ → ドメイン**: 登録ユーザーごとにグループ化
3. **ドメイン → タイプ**: ドメイン優先でグループ化
4. **フラット表示**: 階層なし

---

## 変更したファイル

| ファイル | 変更内容 |
|---------|----------|
| src/lib/types.ts | HierarchyLevel, HierarchyFieldPath, HierarchyPreset, DynamicHierarchyConfig型を追加 |
| src/lib/hierarchy-builder.ts | 動的階層構築ロジック、プリセット定義、ユーティリティ関数を新規作成 |
| src/components/HierarchyLabelBar/index.tsx | ドラッグ&ドロップ対応の階層ラベルバーを新規作成 |
| src/components/EntityDiagram/index.tsx | 動的階層対応、HierarchyLabelBar統合 |
| src/components/EntityArrowDiagram/index.tsx | 動的階層対応、HierarchyLabelBar統合 |

---

## 使用方法

検索ページでグラフビュー（graph）またはダイアグラムビュー（diagram）を選択すると、階層ラベルバーが表示されます。

1. **階層順序の変更**: 階層ラベルをドラッグして順序を変更
2. **階層の追加**: 「追加」ボタンから利用可能なフィールドを選択
3. **階層の削除**: 各階層ラベルの×ボタンをクリック
4. **プリセット適用**: 「プリセット」ボタンから定義済み構成を選択

---

## 次回への引継ぎ

- [ ] カスタムフィールド（sysProps/userProps）の動的検出と追加UI
- [ ] 階層設定のURL保存/復元機能
- [ ] 階層設定のローカルストレージ永続化
- [ ] グループ表示（EntityGroup）への動的階層対応

---
