# ダッシュボード要件定義（post.py分析に基づく）

shared/example/dashboard_example/post.pyの実装パターンから抽出したjjダッシュボードの具体要件。

[READMEへ戻る](../../../README.md)

## 1. データ構造要件

### 1.1 ファイル名パース → 構造化パラメータ
post.pyでは`_f()`と`parse()`関数でファイル名から構造化データを抽出している。
jjでは既にGraphService.file_to_node()とvocabで同等の処理を行っている。

| post.py | jj対応 |
|---------|--------|
| `_f()`: `idx`→`条件`, `L`→`電線長` 等 | config.yaml vocab |
| `parse()`: ファイル名をdict化 | FileParse.get_props() |
| `jp_dict`: 英語→日本語カラム名 | vocab + token-key-map |
| 派生メトリクス計算（余長率、周波数） | 未対応（Phase 3以降） |

### 1.2 単位マッピング
post.pyのjp_dictでは `"length": "電線長[mm]"` のようにカラム名に単位を含めている。

**jj対応**: config.yaml export.units で実装済み（本PR）
```yaml
export:
  units:
    電線長: mm
    変位量: mm
    端末間距離: mm
    加速度: G
    周波数: Hz
```

### 1.3 型分類
post.pyでは角度パラメータに基づいて型を自動分類（U字、半U字、片U字、L字、オフセット、通常/その他）。
→ jjではpath-tag-mapまたはカスタムパーサーで対応可能。

## 2. UIコンポーネント要件

### 2.1 テーブルビュー（AgGrid）
- **ライブラリ**: streamlit-aggrid
- **機能**:
  - 複数行選択（チェックボックス式）
  - カラムグループ化
  - サイドバーフィルタ（Enterprise modules）
  - 編集可能セル
  - 集計関数（sum等）
- **固定カラム**: name, index, type, format
- **動的カラム**: propertiesから自動生成

### 2.2 サイドバーフィルタ
- **形式**: st.form内のst.multiselect群
- **フィルタ項目**（post.pyから）:
  - type（型分類）
  - 報告親番号/子番号
  - 端末間距離
  - 変位量
  - 余長率
  - 加速度
- **jj汎用化**: config.export.csv-columnsで指定されたカラムを動的フィルタ項目化
- **追加コントロール**:
  - 画像最大表示数（number_input）
  - 表示形式選択（PNG/GIF等）
  - 絞り込み実行ボタン

### 2.3 可視化（Plotly）

#### 2.3.1 棒グラフ
- X軸: parsed_name（条件名）
- Y軸: ユーザー選択（selectbox）
- 色分け: type（型分類）
- 用途: 条件間の比較

#### 2.3.2 散布図
- X/Y軸: ユーザー選択（selectbox）
- 色分け: type
- hover_data: index, parsed_name
- **特殊機能**:
  - 同一グループのデータ点を灰色点線で結線（trend line）
  - グループキー: length, distance, acceleration, rxf, rxm, rzm, offset
  - 対数X軸（加振回数選択時）
  - NG領域塗りつぶし（Baskinカーブ: `0.0414 * x^(-0.11)`）

#### 2.3.3 jj汎用化方針
- X/Y軸候補: config.export.csv-columnsで数値型のカラム
- 色分け: config.export.csv-columnsで文字列型のカラム
- NG領域: 将来的にconfig定義可能に（Phase 3+）

### 2.4 Excelダウンロード
- **フォント**: メイリオ
- **エンジン**: openpyxl
- **出力**: BytesIOストリーミング → st.download_button
- **jj対応**: jj export --target csvで代替可能。Excel形式は将来対応。

### 2.5 画像ギャラリー
- **レイアウト**: 5列グリッド（st.columns）
- **各画像カード**:
  - パラメータテーブル（条件, 電線長, 端末間距離, 変位量, 加速度, 周波数, type）
  - PNG画像（merged）またはGIFアニメーション
- **最大表示数制限**あり
- **jj対応**: 画像パスはhas_output関係で取得可能

## 3. データフロー

```
CSV/graph.yaml
  → DataFrame化
    → AgGridテーブル表示
    → サイドバーフィルタで絞り込み
      → 棒グラフ/散布図
      → 画像ギャラリー
    → Excelダウンロード
```

## 4. jjダッシュボード実装計画

### Phase D1: データプロバイダ
- DashboardDataProviderクラス
- GraphModel → DataFrame変換（export.csv-columns対応）
- export.units → カラム名単位付加
- フィルタ条件生成

### Phase D2: Streamlitダッシュボード
- Page 1: テーブルビュー（AgGrid + フィルタ）
- Page 2: 散布図/棒グラフビュー（Plotly）
- Page 3: 画像ギャラリー（has_output関係利用）
- Page 4: カードビュー（ノード詳細）

### Phase D3: REST API (jj serve)
- FastAPI endpoints
- 09-dashboard.md仕様に準拠

### Phase D4: jj-db統合
- 10-db-integration.md仕様に準拠

## 5. 依存ライブラリ

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| streamlit | ≥1.30 | ダッシュボードフレームワーク |
| streamlit-aggrid | ≥0.3 | AgGridテーブル |
| plotly | ≥5.0 | 散布図/棒グラフ |
| pandas | ≥2.0 | DataFrame操作 |
| openpyxl | ≥3.0 | Excel出力 |

## 6. 確認事項・懸念

- [ ] NG領域定義をconfig化する際のデータ構造設計
- [ ] 画像ギャラリーのパフォーマンス（大量画像時のページネーション）
- [ ] グループキー（trend line用）のconfig化方針
- [ ] カスタム派生メトリクス（余長率、周波数等）の計算パイプライン設計
