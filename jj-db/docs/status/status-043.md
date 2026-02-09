# status-043 (2026-02-01)

> [← README.md](../../README.md)

## 変更概要
- ロードマップ2.5: カードビューbodyプレビューのmax-hを3行分に拡張（max-h-16→max-h-20）
- ロードマップ3開始: 操作性の調整（P0）
  - フォーマット対応エクスポート機能（entity-export.ts新規作成）
  - EntityCardの単体ダウンロードをフォーマット対応拡張子に改善
  - 検索ページに一括ZIPエクスポート（JSZip）を追加
  - GenericUploaderにフォルダ階層インポート機能を追加
    - フォルダツリー表示（FolderTreeView）
    - フォルダ→directoryエンティティ、ファイル→child/contains Relation自動生成
  - 本文入力時の即時フォーマット検出＋BodyRendererプレビューを追加

## 変更ファイル
- src/lib/entity-export.ts（新規）
- src/components/EntityCard/index.tsx
- src/app/search/page.tsx
- src/components/GenericUploader/index.tsx
- package.json（jszip追加）

## 対応するロードマップ項目
- 2.5 詳細ビューの作り込み → カードbodyプレビュー高さ修正
- 3. 操作性の調整 → エクスポート、フォルダインポート、プレビュー改善

## 次のアクション
- [ ] (P1) ImportSchema列挙管理ドキュメント
- [ ] (P2) 分割/マージ運用ルール（INP materialブロック、Markdownヘディング）
- [ ] (P3) エクスポート整形（フォルダ構造正規化、テンプレート出力）
- [ ] type=directory/child/containsのUI表現（ダイアグラム/グラフビュー対応）
