[READMEへ戻る](../../README.md)

# status-071: ダッシュボード機能拡張（config駆動カラム・フィルタ永続化・ギャラリーNxM・プロット軸設定）

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

ダッシュボードの5つの改善を実施。テーブルビューのconfig駆動カラム選択・フィルタのデフォルト設定と永続化、ギャラリーのプロパティ画像パス対応とNxMグリッドレイアウト、プロットビューのconfig駆動デフォルト軸設定とグリッドモードを追加。

---

## 実装内容

### 1. テーブルビュー: config駆動カラム選択

CSV exportの`csv-columns`と同様に、`config.yaml`の`dashboard.table-columns`でテーブルビューに表示するカラムと優先順位を指定可能に。globパターン対応。

| 機能 | 詳細 |
|------|------|
| カラム指定 | `dashboard.table-columns`で表示カラムをリスト指定 |
| 優先順位 | リスト順が表示順 |
| globパターン | `stress*`等のワイルドカードマッチ |
| 固定カラム | name/type/formatは常に先頭に表示 |
| カードビュー | 全プロパティ表示（変更なし） |

**設定例**:
```yaml
dashboard:
  table-columns:
    - 条件
    - バージョン
    - analysis_status
    - active
    - stress*
```

### 2. フィルタのデフォルト設定と永続化

`dashboard.default-filters`でダッシュボード起動時のデフォルトフィルタを設定可能に。フィルタ状態はsession_stateで永続化され、ビュー間（テーブル↔プロット↔ギャラリー）で共有される。

| 機能 | 詳細 |
|------|------|
| デフォルトフィルタ | `dashboard.default-filters`で起動時フィルタ設定 |
| active=true初期値 | デフォルト設定でactive=trueに絞り込み |
| ビュー間共有 | フィルタ状態がページ切替で保持される |
| session_state永続化 | Streamlit session中フィルタが維持される |
| 3種フィルタ | タイプ、ステータス、active |

**デフォルト設定**:
```yaml
dashboard:
  default-filters:
    active: true
```

### 3. ギャラリー: プロパティ画像パス対応とキー別一覧

has_output関係の画像に加えて、ノードプロパティに格納された画像ファイルパス（Obsidian daily note経由）を検出して表示。プロパティキーごとにフィルタして一覧可能。

| 機能 | 詳細 |
|------|------|
| 画像ソース切替 | 「has_output関係」「プロパティ画像パス」のラジオ選択 |
| プロパティ画像検出 | 値が画像拡張子（PNG/JPG等）で終わるプロパティを自動検出 |
| リスト型対応 | `["fig1.png", "fig2.jpg"]`のようなリスト値も検出 |
| キー別フィルタ | プロパティキー（screenshot, figureなど）で絞り込み |
| フォーマットフィルタ | 画像フォーマットで絞り込み |

**新規メソッド**: `DashboardDataProvider.get_property_images()` を追加

### 4. ギャラリー・プロット: NxMグリッドレイアウト

ギャラリーとプロットビューでNxMのテーブルライクなグリッドレイアウトを実装。パワーポイントにスクリーンショットをそのまま貼れる整った配置。

| 機能 | 詳細 |
|------|------|
| ギャラリーグリッド | `dashboard.gallery-columns`と`gallery-rows`で制御 |
| ページネーション | NxMに基づくページ分割（旧max_display廃止） |
| プロットグリッドモード | チェックボックスでグリッドモードON/OFF |
| グループ分割 | 色分けキーまたはname別に個別プロット生成 |
| コンパクトレイアウト | マージン・高さ最適化でスクリーンショット向け |

**設定例**:
```yaml
dashboard:
  gallery-columns: 5
  gallery-rows: 4
```

### 5. プロットビュー: config駆動デフォルト軸

`dashboard.plot`でプロットビューのデフォルトX/Y軸を設定可能に。

| 機能 | 詳細 |
|------|------|
| X軸デフォルト | `dashboard.plot.x`で初期選択 |
| Y軸デフォルト | `dashboard.plot.y`で初期選択 |
| フォールバック | 指定キーが存在しない場合はリスト先頭を使用 |

**設定例**:
```yaml
dashboard:
  plot:
    x: 条件
    y: RF3
```

---

## DashboardConfig データクラス

`config/__init__.py`に追加:

```python
@dataclass(frozen=True)
class DashboardConfig:
    table_columns: list[str] | None  # globパターン対応
    default_filters: dict[str, Any]  # デフォルトフィルタ
    plot_x: str | None               # デフォルトX軸
    plot_y: str | None               # デフォルトY軸
    gallery_columns: int             # ギャラリー列数(デフォルト5)
    gallery_rows: int                # ギャラリー行数(デフォルト4)
```

`GraphConfig`に`dashboard: DashboardConfig`フィールドを追加。

---

## テスト結果

- 新規テスト: **18件**追加
  - `TestDashboardConfig`: 7件（デフォルト、全設定、バリデーション、GraphConfig統合）
  - `TestGetPropertyImages`: 7件（画像パス検出、リスト型、非画像除外、非goノード除外、path除外）
  - `TestSelectTableColumns`: 4件（None処理、フィルタ・順序、globパターン、マッチなし）
- 既存テスト: リグレッションなし（31件パス + 4件streamlitスキップ）

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `config/__init__.py` | `DashboardConfig`データクラス追加、`GraphConfig`にdashboardフィールド追加 |
| `shared/assets/default-config.yaml` | `dashboard`セクション追加（table-columns、default-filters、plot、gallery設定） |
| `services/dashboard/app.py` | config駆動カラム選択、共有フィルタ永続化、NxMギャラリー、プロットグリッド、デフォルト軸 |
| `services/dashboard/data_provider.py` | `get_property_images()`メソッド追加 |
| `tests/test_dashboard.py` | 18件のテスト追加 |
| `docs/status/status-071.md` | 本ステータスファイル |

---

## TODO / 次回引き継ぎ事項

- [ ] 実環境でテーブルビューのカラム設定が反映されることを確認
- [ ] ギャラリーのプロパティ画像パス機能を実データで検証（Obsidian daily由来の画像パス）
- [ ] プロットグリッドモードのスクリーンショット品質確認
- [ ] Phase 3: runコマンド層のジョブ型実装・リモート統合（凍結CLIの着手時期）
- [ ] Phase 3: fileコマンド層の基本実装（凍結CLIの着手時期）
- [ ] REST API: POST /api/v1/parse（再パース実行）
- [ ] REST API: クエリフィルター拡張（props.RF3.gt=5等）
- [ ] ダッシュボード: Excelダウンロード機能（openpyxl利用）
- [ ] ダッシュボード: NG領域塗りつぶし（Baskinカーブ等のconfig定義対応）
- [ ] ダッシュボード: グループ結線（同一条件のデータ点を灰色点線で結線）

---

## 設計上の懸念

- `_select_table_columns`のfnmatch.fnmatchはUnicode文字（日本語カラム名）に正常動作するが、正規表現ではないためエスケープ不要。
- 共有フィルタのsession_state永続化はStreamlitの仕様に依存。ページ遷移時にsession_stateがリセットされないことが前提。
- プロパティ画像パスの検出は拡張子ベース。`path`に画像拡張子が含まれる場合でも`path`プロパティ自体は除外される。
- プロットグリッドモードのグループ化は色分けキーを使用。色分けなしの場合はname別に分割されるため、ノード数が多いと表示が多くなる。
