# status-059: サイドバーツリーナビゲーション実装

**日付**: 2026-02-06
**前回**: [status-058](status-058.md)
**ブランチ**: `claude/add-sidebar-navigation-GbmjZ`

[README](../../README.md)

---

## 概要

検索ページの左サイドバーにレポジトリ・フォルダのツリーナビゲーションを実装。
GitHub/VSCodeライクなエクスプローラーパネルで、階層構造を直感的にブラウズ可能にした。

---

## 実装内容

### 1. SidebarTreeNav コンポーネント (`src/components/SidebarTreeNav/index.tsx`)

**新規コンポーネント**: 階層ツリーナビゲーション

- **ツリー構築**: 全エンティティ + child/containsリレーションからツリー構造を動的構築
  - `root` を起点に再帰的にツリーを構築
  - ソート: ディレクトリ/レポジトリ優先 → 名前順（日本語対応）
- **ノードアイコン**: エンティティ種別に応じたアイコン表示
  - `user_namespace`: User (藍)
  - `repository`: FolderGit2 (紫)
  - `directory`: Folder (黄)
  - その他: File (灰)
- **展開/折りたたみ**: ノードごとにトグル可能
  - 初回表示時にuser_namespaceを自動展開
- **ノード選択**: クリックでエンティティ詳細ページ (`/view?id=xxx`) に遷移
- **サイドバー開閉**: PanelLeftOpen/PanelLeftCloseボタンで折りたたみ可能
- **レスポンシブ**: `md`ブレークポイント以上でのみ表示（モバイルは非表示）

### 2. 検索ページ統合 (`src/app/search/page.tsx`)

- **レイアウト変更**: `min-h-screen flex` の横並びレイアウト
  - 左: SidebarTreeNav（幅256px、sticky）
  - 右: 既存の検索コンテンツ（flex-1）
- **データ取得の拡張**:
  - `allEntitiesForTree`: root/user_namespace含む全エンティティを保持（ツリー表示用）
  - `treeRelations`: child/containsリレーションを全体で取得
  - 既存の `entities`（フィルタ済み）は検索結果表示用として維持

---

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `src/components/SidebarTreeNav/index.tsx` | **新規** | サイドバーツリーナビゲーションコンポーネント |
| `src/app/search/page.tsx` | 修正 | SidebarTreeNav統合、レイアウト変更、データ取得拡張 |

---

## 技術的な設計判断

1. **クライアントサイドのツリー構築**: エンティティとリレーションは既にクライアントで取得済みのため、別途APIを追加せずクライアントでツリーを構築
2. **親コンポーネントからのデータ注入**: SidebarTreeNavは自身でデータフェッチせず、propsでentities/relationsを受け取る設計。テスタビリティとデータの一元管理を重視
3. **sticky + overflow-y-auto**: 長いツリーでもスクロール可能、ページスクロールとは独立

---

## TODO / 次のステップ

- [ ] 既存ユーザーへのuser_namespaceマイグレーション（既にデータがある場合）
- [ ] レポジトリ一覧ページ（ユーザーページでのレポジトリ一覧表示）
- [ ] レポジトリ作成UIの専用フォーム（GenericUploader以外から）
- [ ] レポジトリタイプのカスタム追加機能
- [ ] 5-12: 階層パス全表示（テーブルビュー）
- [ ] 5-13: 制約違反のユーザーフレンドリーエラーメッセージ
- [ ] サイドバーツリーからの検索フィルタ連動（ツリーノード選択→そのノード配下のエンティティのみ表示）
- [ ] モバイル対応（ドロワー式サイドバー）
- [ ] ツリーノードの右クリックコンテキストメニュー
