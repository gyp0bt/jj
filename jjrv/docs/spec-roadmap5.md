# spec-roadmap5: レポジトリ階層制約（破壊的変更）

> [← README.md](../README.md)

---

## 背景と目的

### 問題

現状のmat-dbはグラフモデルが許容的であり、任意のエンティティ間に任意のリレーションを作成できる。
これにより以下の問題が生じる:

- レポジトリに属さない孤立ノードが存在し得る
- ディレクトリ/ファイルがレポジトリの外に存在できる
- 階層の「上下」が暗黙的で、明確な定義がない

### 解決策

**レポジトリ階層制約**を導入し、すべてのノードをレポジトリツリー内に強制配置する。

---

## 設計原則

### 階層ルール

1. **ルートレポジトリ**: システムに唯一のルートレポジトリが存在する
2. **レポジトリ制約**: レポジトリ（sysTags: `"repository"`）はレポジトリの下にしか存在できない
3. **非レポジトリ制約**: レポジトリ以外のすべてのノード（directory, file, Material, Project, Tag等）はレポジトリの下にしか存在できない
4. **上下の定義**: ルートレポジトリからのRelation距離（child/contains経路の深さ）が近い方を「上」、遠い方を「下」とする

### 構造イメージ

```
Root Repository (ルート)
├── child → Repository A
│   ├── child → Directory X
│   │   ├── contains → File 1
│   │   └── contains → File 2
│   ├── child → Repository A-1 (ネストレポジトリ)
│   │   └── child → Directory Y
│   │       └── contains → File 3
│   └── contains → Material M1
├── child → Repository B
│   ├── child → Directory Z
│   └── contains → Project P1
└── contains → Tag T1 (ルート直下のタグ)
```

### リレーション方向の定義

- `entity1Id` = 親（上位）、`entity2Id` = 子（下位）
- これは既存の GenericUploader と EntityTable の実装と整合する
- 使用するRelation label: `child`（ノード間）、`contains`（包含）

---

## 実装要件

### Phase 1: コアモデル（P0）

| # | 要件 | 概要 |
|---|------|------|
| 5-01 | ルートレポジトリの自動生成 | システム起動時にルートレポジトリが存在しなければ自動作成。id固定（`ROOT_REPOSITORY_ID`） |
| 5-02 | 階層バリデーション関数 | `validateHierarchyPlacement(entityId, parentId)` — 親子関係の整合性をチェック |
| 5-03 | レポジトリ祖先チェック | `findAncestorRepository(entityId)` — エンティティの祖先レポジトリを探索 |
| 5-04 | 階層制約型定義 | `HierarchyConstraint` 型と制約エラー型を追加 |

### Phase 2: API層バリデーション（P0）

| # | 要件 | 概要 |
|---|------|------|
| 5-05 | エンティティ作成時制約 | POST /api/entities で `parentId` を必須化（ルートレポジトリ配下に配置） |
| 5-06 | リレーション作成時制約 | POST /api/relations で階層リレーション（child/contains）作成時に親子ルールを検証 |
| 5-07 | エンティティ削除時の子孫処理 | レポジトリ削除時に配下ノードを孤児化しないよう対応 |

### Phase 3: インポートフロー対応（P1）

| # | 要件 | 概要 |
|---|------|------|
| 5-08 | GenericUploader レポジトリ選択 | インポート先レポジトリの選択UIを追加 |
| 5-09 | フォルダD&D時の自動レポジトリ配置 | フォルダドロップ時に選択レポジトリの配下に自動配置 |
| 5-10 | 単体エンティティ作成時のレポジトリ指定 | コピペ/手動作成時にもレポジトリを選択 |

### Phase 4: UI表示の更新（P1）

| # | 要件 | 概要 |
|---|------|------|
| 5-11 | 検索ページ: レポジトリツリーナビ | レポジトリツリーをサイドバーで表示 |
| 5-12 | テーブルビュー: ルート起点の階層表示 | ルートレポジトリからの完全階層パスを表示 |
| 5-13 | エラー表示: 制約違反時のユーザー通知 | 制約違反時に分かりやすいエラーメッセージ |

### Phase 5: マイグレーション（P0）

| # | 要件 | 概要 |
|---|------|------|
| 5-14 | 既存データ適合チェック | 既存エンティティが制約に適合しているか検査 |
| 5-15 | 孤立ノードの自動配置 | レポジトリツリーに属さないノードをルートレポジトリ配下に自動配置 |
| 5-16 | 制約違反レポート | マイグレーション時の変更内容をレポート出力 |

---

## 実装ファイル対応（予定）

| # | 要件 | 主要ファイル | 新規/既存 |
|---|------|-------------|-----------|
| 5-01 | ルートレポジトリ自動生成 | `src/lib/root-repository.ts` | 新規 |
| 5-02 | 階層バリデーション | `src/lib/hierarchy-validator.ts` | 新規 |
| 5-03 | レポジトリ祖先チェック | `src/lib/hierarchy-validator.ts` | 新規 |
| 5-04 | 型定義 | `src/lib/types.ts` | 既存 |
| 5-05 | エンティティ作成制約 | `src/app/api/entities/route.ts` | 既存 |
| 5-06 | リレーション作成制約 | `src/app/api/relations/route.ts` | 既存 |
| 5-07 | エンティティ削除処理 | `src/app/api/entities/[id]/route.ts` | 既存 |
| 5-08 | Uploader レポジトリ選択 | `src/components/GenericUploader/index.tsx` | 既存 |
| 5-09 | D&D自動配置 | `src/components/GenericUploader/index.tsx` | 既存 |
| 5-10 | 手動作成時指定 | `src/components/GenericUploader/index.tsx` | 既存 |
| 5-11 | レポジトリツリーナビ | `src/app/search/page.tsx` | 既存 |
| 5-14 | 適合チェック | `src/lib/migration-hierarchy.ts` | 新規 |
| 5-15 | 孤立ノード配置 | `src/lib/migration-hierarchy.ts` | 新規 |

---

## 非互換事項

### 破壊的変更

1. **エンティティ作成**: 親（レポジトリ）指定なしでのエンティティ作成ができなくなる
2. **リレーション作成**: child/containsリレーションの親がレポジトリ/ディレクトリでなければならない
3. **既存データ**: 孤立エンティティはルートレポジトリ配下に自動移動される

### 互換性の維持

1. **分類Relation**: `tagged_with`, `similar_to`, `カテゴリ`等の分類リレーションは制約の対象外（階層リレーションのみ対象）
2. **entityType**: Material/Project/Tag のセマンティック分類は変更なし
3. **sysTags**: 既存のタグ体系はそのまま維持

---

## 設計上の判断

### ルートレポジトリの扱い

- ID: `"root"` （固定値）
- name: `"Root Repository"`
- sysTags: `["repository"]`
- システム起動時（DB初期化時）に自動作成
- UI上で削除不可
- 全レポジトリの最上位親

### 階層Relationの識別

階層制約の対象となるRelation labelは以下:
- `"child"` — 親子関係（レポジトリ→レポジトリ、レポジトリ→ディレクトリ、ディレクトリ→ディレクトリ）
- `"contains"` — 包含関係（レポジトリ/ディレクトリ→ファイル/その他）

上記以外のRelation label（`tagged_with`, `similar_to`等）は階層制約の対象外。

### バリデーションルール

| 親のsysTags | 子のsysTags | 許可されるRelation label |
|-------------|-------------|------------------------|
| `repository` | `repository` | `child` |
| `repository` | `directory` | `child` |
| `repository` | その他（file等） | `contains` |
| `directory` | `directory` | `child` |
| `directory` | その他（file等） | `contains` |
| その他 | 任意 | `child`/`contains` は **不可** |

### 逆方向の防止

- `entity1Id` が親、`entity2Id` が子として固定
- 子→親方向でのchild/containsリレーション作成は拒否
