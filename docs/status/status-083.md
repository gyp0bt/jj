[← README.md](../../README.md)

# status-083 — docsリファクタリング（ディレクトリ構造整理）

| 項目 | 内容 |
|------|------|
| **日付** | 2026-03-14 |
| **ブランチ** | `claude/refactor-docs-organization-jNIVP` |
| **トラック** | ドキュメント整理 |

---

## 実施内容

### ディレクトリ構造リファクタリング

docs/ ルートに散在していたファイルを分類別フォルダに整理。

#### 新設フォルダ

| フォルダ | 内容 |
|---------|------|
| `docs/guides/` | ユーザー向けガイド・マニュアル（5ファイル移動） |
| `docs/archive/` | 旧バージョン文書（roadmap-v0.1.0, detail.md, review/） |
| `docs/status/archive-v0.2.0/` | v0.2.0 status（status-001〜052、52ファイル移動） |

#### 移動ファイル一覧

| 移動元 | 移動先 |
|--------|--------|
| `docs/abaqus-usage-guide.md` | `docs/guides/abaqus-usage-guide.md` |
| `docs/ml-usage-guide.md` | `docs/guides/ml-usage-guide.md` |
| `docs/migration-guide.md` | `docs/guides/migration-guide.md` |
| `docs/prefect-integration-guide.md` | `docs/guides/prefect-integration-guide.md` |
| `docs/README-jj.md` | `docs/guides/README-jj.md` |
| `docs/roadmap-v0.1.0.md` | `docs/archive/roadmap-v0.1.0.md` |
| `docs/detail.md` | `docs/archive/detail.md` |
| `docs/review/` | `docs/archive/review/` |
| `docs/status/status-index-v0.1.0.md` | `docs/status/archive-v0.1.0/status-index-v0.1.0.md` |
| `docs/status/status-001〜052.md` | `docs/status/archive-v0.2.0/status-001〜052.md` |

### ドキュメント内容更新

| ファイル | 更新内容 |
|---------|---------|
| `docs/README.md` | 全面書き直し: 進捗状態・ディレクトリ構成図・リンクを最新化 |
| `docs/roadmap.md` | T5完了、T7/T8/T9/T10/W進捗を反映 |
| `docs/status/status-index.md` | v0.2.0 statusをアーカイブリンクに差し替え |
| `docs/specs/README.md` | docs/READMEへのバックリンク追加 |
| `CLAUDE.md` | ディレクトリ構成をリファクタ後に更新 |
| `README.md` | archive/配下への review リンク修正 |

### バックリンク修正

移動した全ファイルのバックリンク（`[← README.md](...)`）を新パスに合わせて修正。

---

## リファクタリング後の構造

```
docs/
├── README.md                  # ナビゲーション
├── roadmap.md                 # v0.3.0 ロードマップ
├── guides/                    # ユーザー向けガイド（5ファイル）
├── specs/                     # 仕様書・設計文書（20+ファイル）
├── status/                    # 実装ログ
│   ├── status-index.md        # v0.3.0 インデックス
│   ├── status-053〜083.md     # v0.3.0 アクティブstatus
│   ├── archive-v0.2.0/        # v0.2.0 status（001-052）
│   └── archive-v0.1.0/        # v0.1.0 status
└── archive/                   # 旧バージョン文書
```

---

## 未完了TODO

### 継続TODO（他トラック）

- [ ] T7: Ollama AI連携 — フル統合テスト・マニュアル作成
- [ ] T8: 汎用データ管理 — 設計フェーズ以降の実装
- [ ] T9: 共有フォルダ同期 — Windows実環境テスト
- [ ] T10: プラグインコア — CLI統合、Abaqus CLICommand、FastAPI APIアダプター、get_page_data()
- [ ] W: Office連携 — Windows実環境テスト
- [ ] K-4: config property-key-aliases（オプション）
- [ ] M2: マルチソルバー検証環境確保後に本実装

---

## 確認事項・提案

### 開発運用メモ

- **効果的だった点**: ファイルを分類フォルダに整理することでdocs/ルートの散乱を解消。新規セッション開始時のナビゲーションが明確になった
- **注意点**: statusファイルのアーカイブにより、古いstatusへのリンクが `archive-v0.2.0/status-{NNN}.md` に変更された。既存のstatusファイル内で古いstatus番号を参照している箇所がある場合、リンク切れの可能性あり（status-indexは修正済み）
- **提案**: specs/ フォルダ内のファイルも「コア仕様書（01-11）」と「設計文書」でサブフォルダ分けを検討できるが、現状20+ファイル程度なのでREADME.mdの分類で十分
