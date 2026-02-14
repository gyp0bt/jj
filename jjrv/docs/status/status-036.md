# Status 036

> [← README.md](../../README.md)

**日付**: 2026-01-28
**セッション**: ダイアグラムビューのプロパティごと階層グループ化機能

---

## 完了タスク

- [x] ダイアグラムビューでプロパティごとの階層グループ化機能を追加

---

## 実装内容

### 1. hierarchy-builder.tsの拡張

#### 追加した機能

- **プロパティキーラベルマッピング** (`PROPERTY_KEY_LABELS`)
  - entity-grouping.tsと統一されたプロパティキー名の日本語ラベル
  - `getPropertyKeyLabel()`関数でキー名を表示用ラベルに変換

- **動的プロパティ検出** (`getAvailableHierarchyFields`)
  - エンティティを渡すと`sysProps`/`userProps`から動的にプロパティキーを検出
  - プロパティの出現頻度でソート
  - フィールドをグループ（base/sysProps/userProps）に分類

#### 変更点

```typescript
// 新しい関数
export function getPropertyKeyLabel(key: string): string

// 拡張された関数（エンティティを受け取れるように）
export function getAvailableHierarchyFields(entities?: StringEntity[]): {
  field: HierarchyFieldPath;
  label: string;
  group?: "base" | "sysProps" | "userProps";
}[]
```

### 2. HierarchyLabelBarの拡張

#### 追加したprops

```typescript
type HierarchyLabelBarProps = {
  levels: HierarchyLevel[];
  onLevelsChange: (levels: HierarchyLevel[]) => void;
  showEntityLabel?: boolean;
  entities?: StringEntity[];  // 新規追加
};
```

#### UIの改善

- フィールド追加メニューをグループ別に表示
  - 基本フィールド（タイプ、ドメイン、登録ユーザー、タグ）
  - システムプロパティ（sysPropsのキー）
  - ユーザープロパティ（userPropsのキー）
- スクロール可能なドロップダウン（最大320px）
- グループヘッダー付きで視認性向上

### 3. EntityArrowDiagramの更新

- `HierarchyLabelBar`にエンティティを渡すように修正
- これにより、ダイアグラムビューで動的にプロパティを検出し、階層に追加可能

---

## 変更したファイル

| ファイル | 変更内容 |
|---------|----------|
| src/lib/hierarchy-builder.ts | PROPERTY_KEY_LABELS追加、getPropertyKeyLabel関数追加、getAvailableHierarchyFieldsを動的検出対応に拡張、detectCustomFieldsを頻度順ソートに改善 |
| src/components/HierarchyLabelBar/index.tsx | entities propsを追加、フィールド追加メニューをグループ表示に対応 |
| src/components/EntityArrowDiagram/index.tsx | HierarchyLabelBarにentitiesを渡すように修正 |

---

## 使い方

ダイアグラムビュー（検索画面でview=diagram）で:

1. HierarchyLabelBarの「追加」ボタンをクリック
2. グループ分けされたフィールド一覧が表示される:
   - **基本フィールド**: タイプ、ドメイン、登録ユーザー、タグ
   - **システムプロパティ**: エンティティのsysPropsから検出されたキー
   - **ユーザープロパティ**: エンティティのuserPropsから検出されたキー
3. フィールドを選択して階層に追加
4. ドラッグ&ドロップで階層順序を変更可能
5. プリセットから一括設定も可能

---

## 次回への引継ぎ

- [ ] カスタムプロパティの動的検出と追加UI（新しいプロパティキーを登録画面などから追加）
- [ ] グループ化設定のローカルストレージ永続化（プリセット保存）
- [ ] ドラッグ&ドロップ入力の強化（複数ファイル/分割）
- [ ] import/export（CSV/JSON/INP等）の整備

---
