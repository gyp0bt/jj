# status-045 (2026-02-03)

> [← README.md](../../README.md)

## 概要
ドキュメント構造の再編成。README.mdをスリム化し、詳細仕様・spec・status・reviewをdocsフォルダに集約。

## 変更内容

### ドキュメント再編成
- `.status/` → `docs/status/` に移動（全44ファイル + index）
- `review/` → `docs/review/` に移動
- `docs/全仕様.md` を新規作成（旧READMEの詳細仕様を移行）
- `docs/spec-roadmap1.md` を新規作成（RM1: ユーザー運用の実現）
- `docs/spec-roadmap2.md` を新規作成（RM2: 検索・閲覧体験の拡張）
- `docs/spec-roadmap25.md` を新規作成（RM2.5: 詳細ビューの作り込み）
- `docs/spec-roadmap3.md` を新規作成（RM3: 操作性の調整）
- `README.md` を再構成（規約・サマリー・ドキュメントリンク集に縮小）
- 全statusファイル・reviewファイルのバックリンクを `../../README.md` に更新

### 新しいドキュメント構成

```
README.md                     # 規約・サマリー・リンク集
docs/
  全仕様.md                    # 詳細仕様（設計思想・ロードマップ・Import/Export・データモデル等）
  spec-roadmap1.md            # RM1: ユーザー運用の実現
  spec-roadmap2.md            # RM2: 検索・閲覧体験の拡張
  spec-roadmap25.md           # RM2.5: 詳細ビューの作り込み
  spec-roadmap3.md            # RM3: 操作性の調整
  status/
    status-001.md ~ status-045.md  # 実装状況記録
    status-index.md               # status索引
  review/
    review-00.md                  # プロジェクトレビュー
src/components/*/README.md    # 個別コンポーネント仕様書（据え置き）
src/app/*/README.md           # 個別ページ仕様書（据え置き）
src/lib/README.md             # lib仕様書（据え置き）
```

### README.mdの役割
- 規約（AI運用ルール）
- プロジェクトサマリー（概要テーブル + コマンド）
- ドキュメントリンク集（status, spec, 全仕様, review）
- Specs Index（個別仕様書へのリンク）

### 個別仕様書の方針
- `src/components/*/README.md` 等の個別仕様書は実装ファイル直下に据え置き
- 詳細仕様は `docs/全仕様.md` に集約
- ロードマップごとのspec文書は `docs/spec-roadmap{N}.md` 形式で管理

## 次のアクション
- [ ] (P1) `schema_keys` 一覧化管理ドキュメント追加
- [ ] (P1) 典型パターン（yaml/json/inp/markdown）から属性抽出の起点を決定
- [ ] (P2) ブロック単位分割（INP/material、Markdown/heading）の実装
- [ ] (P2) 分割/マージの操作ルール整理
- [ ] (P3) フォルダ構造正規化・テンプレート出力の試験導入
