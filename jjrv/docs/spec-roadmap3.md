# spec-roadmap3: 操作性の調整

> [← README.md](../README.md)

---

## 設計方針

### 目的
ロードマップ3では「入れる/出す」操作の実用性を高め、業務運用に耐えるインポート/エクスポート体験を構築する。

### 方針
1. **ドラッグ&ドロップ主体のインポート** — フォルダ/ファイルをドロップするだけでplaceholderを生成し、UIで即時確認・編集できる。
2. **フォーマット対応エクスポート** — 拡張子・形式に応じた出力。一括ZIP対応。
3. **Relation可視化** — インポート時に生成されるRelationをダイアグラム/グラフ/テーブルで確認できる。
4. **インポート時編集** — 取り込み前にエンティティを個別編集（名前・タグ・プロパティ・本文・Relation）。
5. **ラベル付きRelation** — カテゴリ/サブカテゴリ/グレード等の構造をRelationで表現する。
6. **UIロジック分離** — Next.jsは即時処理のみ、高度な解析はprefect側へ委譲。

---

## 実装要件

### 完了済み（P0）

| # | 要件 | 概要 |
|---|------|------|
| 3-01 | フォーマット対応エクスポート | 単体ダウンロード時にformat属性から正しい拡張子で出力 |
| 3-02 | 一括ZIPエクスポート | JSZipで選択エンティティをまとめてダウンロード |
| 3-03 | フォルダD&Dインポート | フォルダ階層→directoryエンティティ＋child/contains Relation自動生成 |
| 3-04 | コピペ/プレビュー改善 | 即時フォーマット検出＋BodyRendererプレビュー |
| 3-05 | Relation可視化 | ダイアグラム/グラフビューにRelationエッジ描画、テーブルビュー追加 |
| 3-06 | Relation一括取得API | entityIds指定/全件でRelation一括取得 |
| 3-07 | インポート時個別編集 | EntityEditPanelで各ビューから個別エンティティを編集 |
| 3-08 | 一括タグ・プロパティ付与 | GenericUploader内で全エンティティに一括適用 |
| 3-09 | ラベル付きRelation | カテゴリ/サブカテゴリ/グレードをRelation化 |
| 3-10 | テーブルビュー拡張 | プロパティ列・Relation列を追加 |
| 3-11 | EntityEditPanel Relation編集 | Relation追加/削除をEditPanel内で操作 |
| 3-12 | Mockデータ充実化 | CSV/JSON/YAML/MD形式Project、MockRelation 20件追加 |

### 未完了

| # | 要件 | 優先度 | 概要 | 状態 |
|---|------|--------|------|------|
| 3-13 | D&D分割/マージ | P1 | INP materialブロック単位分割、Markdown heading分割 | 未実装 |
| 3-14 | import/export整備 | P1 | CSV/JSON/INP等の読み書き精度向上 | 未実装 |
| 3-15 | インポートrelation候補のDB参照 | P1 | relation先がインポートファイル内にない場合、DBに存在すればリンクを取る | **完了** |
| 3-16 | テーブルビュー編集列ボタン修正 | P1 | 編集列のボタン押下で編集畳み込みが開くように変更 | **完了** |
| 3-17 | フォルダD&D時の全StringEntity表示 | P1 | フォルダがドラフトに含まれるように修正し全StringEntityを表示 | **完了** |
| 3-18 | インポートプレビューのフィルター機能 | P1 | インポートプレビューにフィルター機能追加 | **完了** |

### Import/Export残タスク（優先順位つき）

| 優先度 | タスク |
|--------|--------|
| P1 | `schema_keys` を一覧化できる管理ドキュメントを追加 | **完了**: [schema-keys.md](schema-keys.md) |
| P1 | 典型パターン（yaml/json/inp/markdown）から属性抽出の起点を決める | **完了**: [attribute-extraction.md](attribute-extraction.md) |
| P2 | ブロック単位分割（INP/material、Markdown/heading）を追加 |
| P2 | 任意単位マージは「ユーザー操作 or ルール」のどちらで行うかを整理 |
| P3 | フォルダ構造の正規化と、テンプレート出力（markdown/html/yaml）を試験導入 |
| P4 | 破損時の退避/復旧ルールを用意 |

### 廃止要件

| 要件 | 理由 |
|------|------|
| 受払いYAMLスキーマ検証 | ロードマップから受払要件を廃棄 |

---

## 実装要件 ↔ ファイル対応テーブル

| # | 要件 | 主要ファイル | 補助ファイル |
|---|------|-------------|-------------|
| 3-01 | フォーマット対応エクスポート | `src/lib/entity-export.ts` | `src/components/EntityCard/index.tsx` |
| 3-02 | 一括ZIPエクスポート | `src/app/search/page.tsx` | `src/lib/entity-export.ts` |
| 3-03 | フォルダD&Dインポート | `src/components/GenericUploader/index.tsx` | — |
| 3-04 | コピペ/プレビュー改善 | `src/components/GenericUploader/index.tsx` | `src/components/BodyRenderer/index.tsx` |
| 3-05 | Relation可視化 | `src/components/EntityDiagram/index.tsx`, `src/components/EntityGraph/index.tsx` | `src/app/view/page.tsx`, `src/app/search/page.tsx` |
| 3-06 | Relation一括取得API | `src/app/api/relations/route.ts` | `src/lib/relation-api.ts`, `src/lib/entity-repository.ts` |
| 3-07 | インポート時個別編集 | `src/components/EntityEditPanel/index.tsx` | `src/components/EntityTable/index.tsx`, `src/components/EntityDiagram/index.tsx`, `src/components/EntityGraph/index.tsx` |
| 3-08 | 一括タグ・プロパティ付与 | `src/components/GenericUploader/index.tsx` | — |
| 3-09 | ラベル付きRelation | `src/components/EntityEditPanel/index.tsx`, `src/components/GenericUploader/index.tsx` | `src/components/EntityTable/index.tsx`, `src/lib/mock-data.ts` |
| 3-10 | テーブルビュー拡張 | `src/components/EntityTable/index.tsx` | — |
| 3-11 | EntityEditPanel Relation編集 | `src/components/EntityEditPanel/index.tsx` | — |
| 3-12 | Mockデータ充実化 | `src/lib/mock-data.ts` | `src/app/api/entities/seed/route.ts` |
| 3-13 | D&D分割/マージ | `src/components/GenericUploader/index.tsx` | （未実装） |
| 3-14 | import/export整備 | `src/lib/entity-export.ts` | `src/components/GenericUploader/index.tsx` |
| 3-15 | インポートrelation候補のDB参照 | `src/components/GenericUploader/index.tsx` | `src/lib/entity-api.ts` |
| 3-16 | テーブルビュー編集列ボタン修正 | `src/components/EntityTable/index.tsx` | — |
| 3-17 | フォルダD&D時の全StringEntity表示 | `src/components/GenericUploader/index.tsx` | — |
| 3-18 | インポートプレビューのフィルター機能 | `src/components/EntityTable/index.tsx` | `src/components/GenericUploader/index.tsx` |
