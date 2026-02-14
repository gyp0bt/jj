# Status 002

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: TODO順次消化（MOCK整理・共通コンポーネント化）

---

## 完了タスク

- [x] MOCKデータ参照を `src/lib/mock-data.ts` に統合（results/view の重複削除）
- [x] BackButton を results/view/register/GenericUploader に適用
- [x] domain/base を `src/components/` へ移行（EntityCard/GenericUploader）
- [x] dev/components プレビュー追加（BackButton/EntityCard/GenericUploader）
- [x] ドキュメント更新（components/app README、各コンポーネント仕様）

---

## 現在の状態

### Components
| 名前 | 状態 |
|------|------|
| Button | ✅ 完成 |
| BackButton | ✅ 完成 |
| EntityCard | ✅ 完成 |
| GenericUploader | ✅ 完成 |

### Pages
| パス | 状態 |
|------|------|
| `/` | ✅ 実装済み |
| `/results` | ⚠️ MOCKデータ使用 |
| `/register` | ✅ 実装済み |
| `/view` | ⚠️ MOCKデータ使用 |
| `/dev/components` | ✅ 実装済み |

---

## 次のタスク（優先順）

1. データ永続化（ローカルストレージ or ファイルシステム）
2. 検索機能の実装（MOCK依存からの移行）

---

## 技術的メモ

- `src/app/domain/base` は `src/components` へ移行済み（フォルダ削除）。
- MOCK検索は `searchMockEntities` を通して実装。
