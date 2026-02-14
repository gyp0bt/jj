# Status 024

> [← README.md](../../README.md)

**日付**: 2026-01-25
**セッション**: TODO3 直感的な操作性の強化（設計・実装）

---

## 完了タスク

- [x] TopNav コンポーネント（既存ページヘッダー統合、全リンクパンくず）
- [x] BatchUploadPanel（.inp から material ブロック抽出）
- [x] BatchEntityEditor（一括編集・一括タグ/プロパティ）
- [x] EntityMetaBadges（登録者/お気に入り/使用状況、favoriteUsers +x 表示）
- [x] EntityRelations（related/tag 一覧表示）
- [x] /register への一括取り込み UI 統合（beta）
- [x] /results, /view のヘッダーを TopNav に統合
- [x] コンポーネントプレビューに新規追加
- [x] TopNav と AccountStatus を統合
- [x] /view のパンくずを home / results / view に変更
- [x] dev/components のタブをスクロール対応 + アルファベット順に整列
- [x] 検索結果（グラフ以外）に EntityMetaBadges を組み込み
- [x] 検索結果に一括選択 + 一括アクション（コピー/ダウンロード）を追加
- [x] 取り込み画面を汎用Drag&Dropに統合（フォルダ解析・material抽出）
- [x] フォルダD&D対応（webkitGetAsEntryでディレクトリ走査）
- [x] カード選択は枠線表示に変更（チェック表示なし）
- [x] EntityMetaBadges を検索結果に統合し、カードの重複表示を整理
- [x] フォルダD&D時の表示名を.inpのファイル名に修正
- [x] 選択モードの視認性改善（ピンク枠線 + 左ライン）
- [x] 詳細ビューのパンくず表記を「検索結果 / 詳細ビュー」に統一
- [x] アップロードエリアを正方形寄りに調整
- [x] 選択時の枠線/左ラインをピンクで確実に上書き
- [x] 選択時のフォーカスリング色をピンクに統一（青枠排除）
- [x] createdBy 表示をユーザー名優先に調整
- [x] favoriteユーザー一覧API追加（最大5人 +x 表示）
- [x] seedでテストユーザー作成＆favoriteランダム付与
- [x] アップロードエリアを横長（2:1）で中央揃えに変更
- [x] テーブルビューのダウンロード回数をメタ表示に統合
- [x] ユーザー一覧ページを追加
- [x] 検索フィルタに登録ユーザー/お気に入りユーザー絞り込みを追加
- [x] お気に入り数/ダウンロード数で並び替え追加
- [x] favoriteユーザー取得を表示対象に絞り込み（速度改善）
- [x] カード/テーブル/グラフにbodyプレビューを追加

---

## 追加したコンポーネント

| コンポーネント | 説明 |
|---------------|------|
| [TopNav](../src/components/TopNav/README.md) | 上部ナビゲーション（パンくず） |
| [BatchUploadPanel](../src/components/BatchUploadPanel/README.md) | 一括アップロード解析パネル |
| [BatchEntityEditor](../src/components/BatchEntityEditor/README.md) | 一括編集/一括タグ |
| [EntityMetaBadges](../src/components/EntityMetaBadges/README.md) | 登録者・お気に入り・利用状況バッジ |
| [EntityRelations](../src/components/EntityRelations/README.md) | 関連情報・外部リンク表示 |

---

## 技術的メモ

- .inp の material 抽出はクライアント側で完結
  - 行を小文字化し空白除去で比較
  - `*material` から非許可キーワードまでをブロック化
- favoriteUsers は最大5人まで表示し、超過は `+x` 表記

---

## TODO3 進捗

### 3. 直感的な操作性の強化
- [x] ドラッグ&ドロップ入力の強化（複数ファイル/分割）
- [x] 一括編集・一括タグ付け
- [x] 上部にナビゲーションバー追加、現在地表示および移動リンクとアイコン
- [ ] コピペ/プレビューの改善（即時プレビュー/差分表示）

---

## 次のステップ

- コピペ/プレビュー改善
- material 抽出結果の保存/登録フロー接続
