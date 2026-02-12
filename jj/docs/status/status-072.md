[READMEへ戻る](../../README.md)

# status-072: activeフィルタバグ修正・画像パス解決・保存済みビュー機能

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

ダッシュボードの3つの改善を実施。activeフィルタのbool/文字列混在バグ修正、Obsidian daily note由来の画像パスのプロジェクトルート基準解決、保存済みビュー機能の追加。

---

## 実装内容

### 1. activeフィルタバグ修正

`active` プロパティはYAML経由でbool `True`/`False` と、`GraphService.file_to_node()` で文字列 `"true"`/`"false"` の2種類で格納される。`_apply_shared_filters()` の `r.get("active") is True` がidentity比較のため文字列にマッチせず、activeフィルタを有効にすると何も表示されないバグがあった。

| 修正箇所 | 内容 |
|------|------|
| `app.py` `_is_truthy()` | bool/文字列両方に対応したtruthy判定ヘルパー関数追加 |
| `app.py` `_apply_shared_filters()` | `_is_truthy()` 使用に変更 |
| `app.py` `_init_shared_filters()` | configデフォルト値もbool変換 |
| `data_provider.py` `_matches_filters()` | bool/文字列の比較を正規化して実施 |

### 2. Obsidian画像パスのプロジェクトルート基準解決

Obsidian daily noteから取得した画像パスは `notes/daily/` 基準の相対パスとして格納されるが、ダッシュボードのギャラリーはプロジェクトルート基準で画像を探索するため表示できなかった。

| 修正箇所 | 内容 |
|------|------|
| `data_provider.py` `get_property_images()` | `daily_notes` ネストdict内の画像パス探索に対応 |
| `data_provider.py` `_extract_daily_note_images()` | daily note基準→プロジェクトルート基準へのパス変換（`posixpath.normpath` で正規化） |
| `app.py` `_render_image_grid()` | プロジェクトルート→ `notes/daily/` のフォールバックパス解決追加 |

**パス変換例**:
- `attachments/capture.png` → `notes/daily/attachments/capture.png`
- `../assets/fig.jpg` → `notes/assets/fig.jpg` (正規化)

### 3. 保存済みビュー機能

config.yamlの `dashboard.saved-views` でフィルタ・プロット条件・ギャラリー条件を名前付きで保存し、ダッシュボードの「保存済みビュー」ページで設定順に一括表示。

| 機能 | 詳細 |
|------|------|
| SavedViewConfig | config.yamlのsaved-views各エントリに対応するデータクラス |
| ビュータイプ | table / plot / gallery / card / status の5種類 |
| フィルタ条件保存 | active, type, analysis_status等のフィルタをビューごとに定義 |
| プロット条件保存 | x, y, color, chart_type を指定可能 |
| ギャラリー条件保存 | source, property_key, format を指定可能 |
| 表示順 | config.yamlのリスト順で表示 |
| ページ追加 | saved-viewsが定義されている場合のみ「保存済みビュー」ページが出現 |

**設定例**:
```yaml
dashboard:
  saved-views:
    - name: アクティブ解析一覧
      type: table
      filters:
        active: true
    - name: RF3 vs 条件
      type: plot
      filters:
        active: true
      plot:
        x: 条件
        y: RF3
        color: バージョン
        chart_type: 散布図
    - name: スクリーンショット
      type: gallery
      gallery:
        source: property
        property_key: screenshot
```

---

## テスト結果

- 新規テスト: **13件**追加
  - `TestIsTruthy`: 5件（bool/文字列/None判定、streamlitスキップ）
  - `TestSavedViewConfig`: 7件（table/plot/gallery作成、バリデーション、DashboardConfig統合）
  - `TestGetPropertyImagesDailyNotes`: 5件（daily_notes内画像検出、パス正規化、リスト型、非画像除外、カスタムdir）
  - `TestGetGoTable.test_filter_by_active_string`: 1件（文字列"true"と bool True のフィルタ互換性）
- 既存テスト: リグレッションなし（58件パス + 27件スキップ）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `SavedViewConfig`データクラス追加、`DashboardConfig`に`saved_views`フィールド追加 |
| `services/dashboard/app.py` | `_is_truthy()`追加、activeフィルタ修正、画像パスフォールバック、保存済みビューページ（6関数追加） |
| `services/dashboard/data_provider.py` | `get_property_images()` daily_notes対応、`_extract_daily_note_images()`追加、`_matches_filters()` bool正規化 |
| `shared/assets/default-config.yaml` | `saved-views`設定例コメント追加 |
| `tests/test_dashboard.py` | 13件テスト追加（_is_truthy、SavedViewConfig、daily_notes画像、フィルタ互換性） |
| `docs/status/status-072.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でactiveフィルタ（active: 'true' YAML文字列）の動作確認
- [ ] 実環境でObsidian daily note画像パスの表示確認
- [ ] 保存済みビュー: UIからの動的保存機能（現在はconfig.yaml手書きのみ）
- [ ] 保存済みビュー: ビュー間のフィルタ引き継ぎ機能
- [ ] 保存済みビュー: Excelダウンロード（テーブルビュー用）
- [ ] Phase 3: runコマンド層のジョブ型実装・リモート統合（凍結CLIの着手時期）
- [ ] Phase 3: fileコマンド層の基本実装（凍結CLIの着手時期）
- [ ] REST API: POST /api/v1/parse（再パース実行）
- [ ] REST API: クエリフィルター拡張（props.RF3.gt=5等）
- [ ] ダッシュボード: Excelダウンロード機能（openpyxl利用）
- [ ] ダッシュボード: NG領域塗りつぶし（Baskinカーブ等のconfig定義対応）
- [ ] ダッシュボード: グループ結線（同一条件のデータ点を灰色点線で結線）

---

## 設計上の懸念

- `_is_truthy()` はapp.pyとdata_provider.pyの両方で類似のロジックが存在する。将来的にlib層に統合ユーティリティとして切り出すことを検討。
- `_matches_filters()` 内のローカル `_to_bool()` 定義は、bool/string比較の一時的な解決策。active以外のbool型プロパティが増えた場合、より汎用的な型正規化が必要になる可能性がある。
- 保存済みビューの動的保存（UI上のSaveボタン）は未実装。現在はconfig.yaml手書きによる定義のみ。session_state + YAMLファイル書き出しで実装可能だが、Streamlitの書き込み制約を考慮する必要がある。
- `get_property_images()` の `daily_notes_dir` デフォルト値 `"notes/daily"` はDailyNoteParserのハードコード値と一致。config化する場合は `ObsidianExportConfig` に `daily-dir` を追加する。
