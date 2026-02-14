# status-049 (2026-02-05)

> [← README.md](../../README.md) | [status一覧](status-index.md)

---

## 今回の作業内容

### ロードマップ4（neo4j将来計画）を追加
- `docs/spec-roadmap4.md`を新規作成
- neo4jグラフDB移行計画を策定
  - Phase 4-A: テーブルビュー基盤強化
  - Phase 4-B: ビュー間連携・フォーカスナビゲーション
  - Phase 4-C: Cypherライククエリエンジン
  - Phase 4-D: neo4j移行
- 視覚的部分階層化（edgeラベルによるダイアグラム階層グループ）を目玉機能として定義
- Cypherライククエリ構文案を記載
- READMEにロードマップ4へのリンクを追加

### 4-A-01: テーブル内階層折りたたみ機能
- `src/components/EntityTable/index.tsx`を拡張
- `HierarchicalEntity`型を定義（depth, hasChildren, parentId）
- `HIERARCHY_LABELS`で階層Relationを識別（child, contains, parent_of, belongs_to）
- `buildHierarchy()`関数でRelationから階層構造を構築
- 階層表示UI実装:
  - インデントによる階層の視覚化
  - 折りたたみトグルボタン（ChevronRight/ChevronDown）
  - フォルダ/ファイルアイコン（FolderOpen/FolderClosed）
  - 「すべて展開」「すべて折りたたみ」ボタン
  - 階層コントロールバー（表示件数表示）
- `enableHierarchy`プロパティで機能有効化
- `TableRow`と`EditableTableRows`の両方で階層表示をサポート
- GenericUploaderでテーブルビューに`enableHierarchy`を設定

### 4-A-02: プレビュー改善（ポータル化・モーダル）
- `src/components/BodyPreviewModal/index.tsx`を新規作成
  - React Portalでdocument.bodyにマウント
  - 90vw × 80vhの大きなモーダルでコンテンツ表示
  - ESCキー・外側クリックで閉じる
  - フォーカストラップ対応
  - ヘッダー（エンティティ名、ドメイン）、フッター（更新日時、タグ）
- `src/components/BodyPreviewTooltip/index.tsx`を拡張
  - `triggerRect`プロパティでポータル配置位置を指定
  - `enableModal`プロパティでモーダル展開機能を有効化
  - クリックで大きなモーダルを開く
  - 「クリックで拡大」ヒント表示
- EntityTableの名前列でポータル化プレビューを使用
  - hover時にツールチップ表示
  - クリックでモーダル展開

---

## 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `docs/spec-roadmap4.md` | 新規作成 - neo4j将来計画 |
| `README.md` | ロードマップ4へのリンク追加 |
| `src/components/EntityTable/index.tsx` | 階層折りたたみ機能追加 |
| `src/components/BodyPreviewModal/index.tsx` | 新規作成 - プレビューモーダル |
| `src/components/BodyPreviewTooltip/index.tsx` | ポータル化・モーダル連携 |
| `src/components/GenericUploader/index.tsx` | enableHierarchy設定 |

---

## 次のアクション（優先度P1）

- [ ] 4-A-03: 検索・フィルター強化（全文検索、複合フィルター、保存フィルター）
- [ ] 4-A-04: インライン編集強化（body直接編集、マルチセル選択編集）
- [ ] 4-A-05: Import/Export整備（CSV/JSON/GraphML形式）
- [ ] 4-A-06: ユーザー設定（列表示設定の永続化）
- [ ] 2-13: hover時type属性表示（ロードマップ2）
- [ ] 3-13: D&D分割/マージ（ロードマップ3）
- [ ] 3-14: import/export整備（ロードマップ3）

---

## 確認事項・懸念

- 階層表示はフィルター適用時の動作検証が必要
- ポータル化されたツールチップはスクロール時の位置追従を検討
- モーダル内での編集機能は将来拡張として検討

---

## 最新コミット（予定）

```
feat(EntityTable): 4-A-01 階層折りたたみ機能を実装
feat(BodyPreviewModal): 4-A-02 ポータル化プレビューモーダルを追加
docs: ロードマップ4 neo4j将来計画を追加
```
