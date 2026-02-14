# status-047 (2026-02-04)

> [← README.md](../../README.md)

## 概要
status-046のTODOを大量実装。ロードマップ2の2-12〜2-24（2-13除く）、ロードマップ3の3-15〜3-18を実装し、schema_keys/属性抽出ドキュメントを追加。

## 変更内容

### spec-roadmap2: 検索・閲覧体験の拡張（12件実装済み）

| # | 要件 | 状態 | 実装コミット |
|---|------|------|-------------|
| 2-12 | 階層グループのrelation label基準化 | 完了 | 603a3d7 |
| 2-13 | hover時type属性表示 | **未実装** | — |
| 2-14 | エリア選択と操作変更 | 完了 | 58a29eb |
| 2-15 | 表示プリセットデフォルト廃止 | 完了 | 603a3d7 |
| 2-16 | ダイアグラム階層順ユーザー定義 | 完了 | 603a3d7 |
| 2-17 | グラフビュー設定オプション | 完了 | c82aa61 |
| 2-18 | グラフビューrelation表示 | 完了 | c82aa61 |
| 2-19 | テーブルビューrelation列操作 | 完了 | 05004fb |
| 2-20 | テーブルビュープロパティ列制御 | 完了 | 05004fb |
| 2-21 | テーブルビューrelationテーブル切替 | 完了 | 05004fb |
| 2-22 | テーブルビューセル編集 | 完了 | e213120 |
| 2-23 | テーブルビュー詳細遷移とプレビュー | 完了 | e213120 |
| 2-24 | テーブルビュー列境界線 | 完了 | 05004fb |

### spec-roadmap3: 操作性の調整（4件実装済み）

| # | 要件 | 状態 | 実装コミット |
|---|------|------|-------------|
| 3-15 | インポートrelation候補のDB参照 | 完了 | 161ea23 |
| 3-16 | テーブルビュー編集列ボタン修正 | 完了 | e213120 (Batch 7で対応済み) |
| 3-17 | フォルダD&D時の全StringEntity表示 | 完了 | 161ea23 |
| 3-18 | インポートプレビューのフィルター機能 | 完了 | 161ea23 |

### ドキュメント追加

| ドキュメント | 内容 |
|---|---|
| [schema-keys.md](../schema-keys.md) | schema_keys / sysProps / sysTags / userProps / Relation label / domain / entityType の全キー一覧 |
| [attribute-extraction.md](../attribute-extraction.md) | INP/CSV/JSON/YAML/Markdown/フォルダの属性抽出ロジック起点と拡張方針 |

### 主な実装内容

#### EntityDiagram (2-14)
- 左クリックドラッグによるエリア選択（ラバーバンドUI）
- 中クリックによるパン移動
- TDZバグ修正（`handleSvgMouseUp`の`nodes`依存を`useMemo`後に配置）

#### EntityGraph (2-17, 2-18)
- Obsidian風設定スライダー（中心力/反発力/リンク力/距離）
- Relation灰色実線+ラベル中点表示

#### EntityTable (2-19〜2-24)
- SortColumn型に`prop:${string}`|`rel:${string}`拡張
- プロパティ列: editableはunion、normalはAND交差
- 列設定バー/パネル: Relationのみ切替、列表示/非表示チェックボックス
- 右クリックで列非表示、動的列フィルター
- ダブルクリックセル編集（InlineEditInput/InlineTagEditInput）
- 名前列限定の詳細遷移+hover時BodyPreviewTooltip
- CSS列境界線（`[&_th+th]:border-l`等）

#### GenericUploader (3-15, 3-17, 3-18)
- `applyBulkRelation`をasync化、`searchEntities` APIでDB検索（3-15）
- `buildDraftEntities`でフォルダDraftEntityと階層Relation(child/contains)を自動生成（3-17）
- `saveBundle`を簡素化（フォルダ/ファイル/Relation一括保存）
- インポートプレビューEntityTableに`enableFiltering`追加、編集モード用フィルター行（3-18）

#### 階層検出 (2-12, 2-15, 2-16)
- HierarchyFieldPathに`relation.${string}`パターン追加
- relation labelから自動で階層構成を検出
- 出現頻度の多い順にデフォルト階層生成

## 変更ファイル

| ファイル | 変更概要 |
|---|---|
| `src/components/EntityDiagram/index.tsx` | エリア選択+中クリックパン |
| `src/components/EntityGraph/index.tsx` | 設定スライダー+relation表示 |
| `src/components/EntityTable/index.tsx` | 列制御+セル編集+フィルター |
| `src/components/GenericUploader/index.tsx` | DB参照relation+フォルダDraft+フィルター |
| `src/lib/types.ts` | HierarchyFieldPath拡張 |
| `src/lib/hierarchy-builder.ts` | relation label階層対応 |
| `docs/schema-keys.md` | 新規: schema_keys一覧 |
| `docs/attribute-extraction.md` | 新規: 属性抽出起点 |

## 次のアクション
- [ ] 2-13 hover時type属性表示（未実装）
- [ ] 25-08〜25-10の実装（ロードマップ2.5追加分）
- [ ] 3-13 D&D分割/マージ（P1）
- [ ] 3-14 import/export整備（P1）
