# Status 009

> [← README.md](../../README.md)

**日付**: 2026-01-24
**セッション**: ダミーデータ拡充と読み込み表示改善

---

## 完了タスク

- [x] MOCKデータの物性バリエーションを拡充
  - conductivity / expansion / plastic / electrical conductivity / creep
  - damage initiation / damage evolution
  - 本文とタグをバリエーションに合わせて作成
- [x] 詳細ビューの読み込み中表示を追加

---

## 現在の状態

### データ
| 種別 | 状態 |
|------|------|
| MOCKデータ | ✅ 拡充済み |

### UI
| 画面 | 状態 |
|------|------|
| `/view` | ✅ 読み込み中表示を追加 |

---

## 技術的メモ

- `userProps`に追加物性を格納
- `loading`中は「エンティティが見つかりませんでした」ではなく「読み込み中...」を表示
