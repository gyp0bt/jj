# Status 006

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: 検索UIの再設計とフィルタ強化

---

## 完了タスク

- [x] SearchBarを複数入力対応に再設計
  - 材料名（部分一致）/ タグ（スペース区切り）/ プロパティ（キー + 数値）入力に対応
  - 入力補足テキストを追加
- [x] SearchFilterのUI/仕様を刷新
  - ドメインをテキスト入力 + サジェストに変更
  - 並び替えをセレクト + 昇順/降順トグルに整理
- [x] entity-search.tsの検索条件を拡張
  - 材料名の部分一致、タグ一致、プロパティ数値一致、ドメイン一致
- [x] results/page.tsxの検索状態を更新
  - name/tags/propKey/propValue/domain/sort をURLパラメータに保持
- [x] コンポーネント仕様書とlibドキュメントを更新

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| Button | ✅ 完成 |
| BackButton | ✅ 完成 |
| EntityCard | ✅ 完成 |
| GenericUploader | ✅ SQLite対応 |
| SearchBar | ✅ 更新完了 |
| SearchFilter | ✅ 更新完了 |

### Pages
| パス | 状態 |
|------|------|
| `/` | ✅ 実装済み |
| `/results` | ✅ 検索UI更新済み |
| `/register` | ✅ SQLite API |
| `/view` | ✅ SQLite API |
| `/dev/components` | ✅ 更新済み |

---

## 次のタスク（優先順）

1. エンティティ編集機能
2. エンティティ削除機能（UI）
3. 検索履歴機能（オプション）

---

## 技術的メモ

- タグはスペース区切り（`,` も許容）で完全一致
- プロパティはキー一致 + 数値一致（userProps / sysPropsの両方を対象）
- URLパラメータ: `name`, `tags`, `propKey`, `propValue`, `domain`, `sortBy`, `sortOrder`
