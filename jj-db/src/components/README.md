# Components

> [← README.md](../../README.md)

再利用可能なUIコンポーネント一覧。

---

## コンポーネント一覧

| 名前 | 説明 | 状態 |
|------|------|------|
| [BackButton](./BackButton/README.md) | 戻るボタン（履歴 or href） | ✅ 完成 |
| [Button](./Button/README.md) | 汎用ボタン（variant, size対応） | ✅ 完成 |
| [BodyPreviewTooltip](./BodyPreviewTooltip/README.md) | bodyプレビューのツールチップ | ✅ 完成 |
| [EntityCard](./EntityCard/README.md) | エンティティ一覧カード | ✅ 完成 |
| [EntityGraph](./EntityGraph/README.md) | エンティティグラフビュー | ✅ 完成 |
| [EntityDiagram](./EntityDiagram/README.md) | グループ階層のダイアグラムビュー | ✅ 完成 |
| [EntityTable](./EntityTable/README.md) | エンティティテーブルビュー | ✅ 完成 |
| [GenericUploader](./GenericUploader/README.md) | 汎用アップローダ | ✅ 完成 |
| [SearchBar](./SearchBar/README.md) | 材料名・タグ・プロパティ検索バー | ✅ 完成 |
| [SearchFilter](./SearchFilter/README.md) | ドメイン・並び替えパネル | ✅ 完成 |
| [ViewSwitcher](./ViewSwitcher/README.md) | カード/テーブル/グラフ切り替え | ✅ 完成 |
| [TopNav](./TopNav/README.md) | 上部ナビゲーション（パンくず） | 🟡 TODO3 |
| [BatchUploadPanel](./BatchUploadPanel/README.md) | 一括アップロード解析パネル | 🟡 TODO3 |
| [BatchEntityEditor](./BatchEntityEditor/README.md) | 一括編集/一括タグ | 🟡 TODO3 |
| [EntityMetaBadges](./EntityMetaBadges/README.md) | 登録者・お気に入り・利用状況バッジ | 🟡 TODO3 |
| [EntityRelations](./EntityRelations/README.md) | 関連情報・外部リンク表示 | 🟡 TODO3 |

---

## 開発ルール

### ファイル構成
```
ComponentName/
├── index.tsx       # コンポーネント本体（named export）
├── README.md       # 仕様書
└── *.stories.tsx   # Storybook用（オプション）
```

### インポート方法
```typescript
import { Button } from "@/components/Button";
```

### 命名規則
- フォルダ名: PascalCase（例: `Button`, `EntityCard`）
- コンポーネント名: フォルダ名と同一
- Props型: `ComponentNameProps`

### スタイリング
- Tailwind CSSを使用
- カラーパレット: neutral, sky, teal, slate, zinc
- ダークモード対応必須（`dark:`プレフィックス）

---

## プレビュー

http://localhost:3000/dev/components

新規コンポーネント追加時は `src/app/dev/components/page.tsx` の `TABS` と `PREVIEW_MAP` に追加。
