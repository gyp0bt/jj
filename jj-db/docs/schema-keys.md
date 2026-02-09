# schema_keys 一覧

> [← README.md](../README.md)

本ドキュメントは、インポート時に使用される `schema_keys`（スキーマ識別子）と
StringEntity の `sysProps` / `sysTags` で使用されるキーの一覧を管理する。

---

## 1. schema_keys（インポートスキーマ識別子）

YAML契約（`全仕様.md` §仕様の最小スキーマ）で定義される `schema_keys` の一覧。
items 配列の各要素がどのスキーマに属するかを示す。

| schema_key | kind | 説明 | 生成タイミング |
|---|---|---|---|
| `folder/directory` | folder | フォルダエンティティ | フォルダD&D時に自動生成 |
| `inp/material-block` | file | Abaqus INP材料ブロック | INPファイル取り込み時 |
| `csv/dataset` | file | CSVデータセット | CSV取り込み時 |
| `json/config` | file | JSON設定ファイル | JSON取り込み時 |
| `yaml/procedure` | file | YAML手順書 | YAML取り込み時 |
| `markdown/document` | file | Markdownドキュメント | MD取り込み時 |
| `generic/text` | file | 汎用テキスト | 拡張子不明時のフォールバック |

### 拡張ルール

- `{format}/{subtype}` 形式（スラッシュ1つ）
- prefect側で解析スキーマを追加する場合もこの形式に従う
- `version` フィールドと組み合わせて後方互換性を維持

---

## 2. sysProps キー一覧

`StringEntity.sysProps` に格納されるシステムプロパティ。

| キー | 型 | 説明 | 設定箇所 |
|---|---|---|---|
| `ingest_time` | ISO8601 | インポート日時 | `GenericUploader` |
| `source_filename` | string | 元ファイル名 | `GenericUploader` |
| `extension` | string | ファイル拡張子（`inp`, `csv`, `json`, `md` 等） | `GenericUploader` / `createDraftEntity` |
| `format` | string | 検出フォーマット（`abaqus_inp`, `csv`, `json`, `markdown`） | `createDraftEntity` / `BodyRenderer` |
| `type` | string | エンティティ種別（`repository`, `directory`, `tag`, `template`, `document`, `category`, `subcategory`, `grade`） | mock-data / `buildDraftEntities` |
| `product` | string | 関連製品名 | ユーザー設定 / 階層分類用 |

### フォーマット検出優先順（BodyRenderer）

```
sysProps.format > userProps.format > domain > sysProps.extension > 内容解析
```

---

## 3. sysTags 一覧

`StringEntity.sysTags` に格納されるシステムタグ。

### 3a. フォーマット系

| タグ | 説明 |
|---|---|
| `abaqus_inp` | Abaqus INP形式 |
| `csv` | CSV形式 |
| `json` | JSON形式 |
| `yaml` | YAML形式 |
| `markdown` | Markdown形式 |

### 3b. エンティティ種別系

| タグ | 説明 |
|---|---|
| `material` | 材料データ |
| `directory` | フォルダエンティティ |
| `repository` | レポジトリ（git構成の最上位概念） |
| `template` | テンプレート |
| `document` | ドキュメント |
| `dataset` | データセット |
| `report` | レポート |
| `procedure` | 手順書 |
| `tag-definition` | タグ定義 |
| `category` | カテゴリ |
| `subcategory` | サブカテゴリ |
| `grade` | グレード |

### 3c. ソース系

| タグ | 説明 |
|---|---|
| `abaqus` | Abaqus由来 |
| `guide` | ガイド・参考文献 |
| `reusable` | 再利用可能 |

---

## 4. userProps 典型キー

`StringEntity.userProps` はユーザー定義だが、典型的に使われるキーがある。

| キー | 説明 | 使用例 |
|---|---|---|
| `usage` | 用途 | `"参照用"`, `"解析設定"`, `"試験管理"`, `"文書管理"` |
| `project` | プロジェクト名 | `"PRJ-1234"` |
| `format` | ユーザー指定フォーマット | フォーマット検出のオーバーライド |

---

## 5. Relation label 一覧

`Relation.label` に使用されるラベル。

### 5a. 構造系（自動生成）

| ラベル | 説明 | 生成箇所 |
|---|---|---|
| `child` | フォルダ間の親子関係 | `buildDraftEntities` / `saveBundle` |
| `contains` | フォルダ→ファイルの包含関係 | `buildDraftEntities` / `saveBundle` |

### 5b. 分類系（Mock / ユーザー定義）

| ラベル | 説明 |
|---|---|
| `カテゴリ` | カテゴリ分類 |
| `サブカテゴリ` | サブカテゴリ分類 |
| `グレード` | グレード分類 |
| `tagged_with` | タグ付き関連 |

### 5c. ユーザー定義（一括Relation追加）

一括Relation追加（`applyBulkRelation`）で任意のラベルを使用可能。

---

## 6. domain 値一覧

`StringEntity.domain` に使用されるドメイン識別子。

| ドメイン | 説明 | 判定元 |
|---|---|---|
| `abaqus_inp` | Abaqus INP形式 | `BodyRenderer.detectFormat` |
| `category` | カテゴリ分類 | mock-data |
| *(null)* | 未分類 | デフォルト |

---

## 7. entityType 値

`StringEntity.entityType` の列挙値。

| 値 | 説明 |
|---|---|
| `Material` | 材料データ |
| `Project` | プロジェクト・テンプレート・データセット |
| `Tag` | タグ・カテゴリ定義 |
| `null` | 未分類 |
