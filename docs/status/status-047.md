[← status-index.md](status-index.md) | [← README.md](../../README.md)

# status-047: 配列プロット クロスグループ軸選択・configデフォルト設定

- **日付**: 2026-03-06
- **マイルストーン**: M4（Dashboard）
- **ブランチ**: `claude/dashboard-configurable-axes-FLuI3`

---

## 概要

配列プロットビューの機能拡張を実施:

1. **クロスグループX/Y軸選択**: 異なるデータグループ間でX軸とY軸を自由に選択可能に
2. **configデフォルト設定**: `config.yaml`で配列プロットのデフォルトX/Y軸キー・軸範囲を指定可能に

## 変更内容

### 1. クロスグループX/Y軸選択

| ファイル | 変更 |
|---------|------|
| `services/dashboard/components/array_plot.py` | `ArrayPlotViewConfig.render_add_form()`: クロスグループ選択チェックボックス追加。`ArrayPlotPage.render_page()`: クロスグループモード追加（全配列キーからX/Y自由選択）。ヘルパー関数 `_find_key_index()`, `_get_default_y_keys()`, `_get_array_plot_defaults()` 追加 |

**ユースケース**:
- U.U1（変位）を横軸に取ってRF.RF3（反力）を縦軸に取る
- stress.Mises を横軸に strain.PE を縦軸に取る
- 従来の同一プレフィックス内選択も維持（チェックボックスOFFで従来動作）

### 2. configデフォルト設定

| ファイル | 変更 |
|---------|------|
| `config/__init__.py` | `DashboardConfig` に `array_plot_defaults: dict[str, Any]` フィールド追加。`from_dict()` で `array-plot` セクションを読み込み（x, y, x-min, x-max, y-min, y-max） |

**config.yaml 設定例**:
```yaml
dashboard:
  array-plot:
    x: "U.U1"
    y: ["RF.RF3"]
    x-min: 0.0
    x-max: 10.0
    y-min: -100.0
    y-max: 500.0
```

### 3. テスト追加

| ファイル | 変更 |
|---------|------|
| `tests/test_dashboard.py` | `TestDashboardConfigArrayPlotDefaults` (8テスト): config読み込みテスト。`TestArrayPlotHelpers` (9テスト): ヘルパー関数テスト |

## テスト結果

- **ruff check**: All checks passed
- **ruff format**: 212 files already formatted
- **pytest**: 1548+ passed（17テスト増加）, skipped数は環境依存

## TODO

- [ ] Config classification実装（Phase 1: 設定クラス定義、Phase 2: ハードコード置換）
- [ ] vocab_displayユーティリティのダッシュボードUI統合（テーブルヘッダー等のvocab変換表示）
- [ ] Run-Propertyトレーサビリティ CLI対応（`jj run --show-properties`）
- [ ] M7 Phase 5: Run比較ダッシュボード
- [ ] M7 Phase 6: Neo4j Run Node対応
- [ ] 配列プロットsaved-viewでのクロスグループ対応（現在はrender_page側のみ）

## 確認事項・懸念

- クロスグループ選択はrender_pageのUI側のみ対応。saved-viewのarray_plot configには既にx/yを自由指定できるため、saved-view側は既存機能で対応可能
- `get_array_grid_data()`はX/Yが異なるプレフィックスでも動作する（プレフィックスに依存しない設計）
- GitHub Actionsの確認は`gh` CLIが利用不可のためスキップ
