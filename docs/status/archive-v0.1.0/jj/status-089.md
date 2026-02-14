[READMEへ戻る](../../README.md)

# status-089: Abaqusコネクター作り込み（v0.1.0完成準備）

**日付**: 2026-02-14

## 概要

Abaqusコネクターの作り込みを行い、v0.1.0完成に向けた機能追加を実施。

## 変更内容

### 1. 材料テーブル表示の改善
- **タグ非表示**: 材料テーブルからtags列を除外
- **表示列**: 材料名(name)、vocab変換名(verbose_name)、割り当てelset名(assigned_elsets)、材料特性値
- **材料特性値のフォーマット**:
  - 1行1要素: そのまま表示（例: `7.85e-09`）
  - 1行2要素: `val0(val1)` 形式（例: `210000.0(0.3)`）
  - 1行3要素以上: カンマ区切り + `(KEY)` 表示
  - 2行以上: `配列` と表記（配列プロットに回す）
- **配列プロット**: 1行のみのプロパティは配列プロットから除外

### 2. Elsetノード生成のメッシュごと分離
- 同一elset名で異なるメッシュ（異なるinclude先.inp）に属する場合、メッシュごとに別のelsetノードを生成
- `mesh_source` プロパティを追加（どのメッシュファイルに属するか）
- material_elsetsにのみ存在するelset（meshデータなし）も引き続き生成

### 3. ダッシュボードページ追加

#### メッシュ品質サマリー（物性一覧ページ内）
- go_ノードごとの節点数、要素数、要素タイプ、品質メトリクス（volume/detJ/aspect_ratio/skewness）

#### Elset品質サマリー（物性一覧ページ内）
- elsetノードごとのメッシュソース、要素数、材料名、品質メトリクス

#### ジョブサマリーページ（新規コネクターページ）
- go_ノードの解析ステータス、CPU時間、経過時間、エラー数、警告数
- 個別ジョブのエラー・警告詳細表示
- .sta/.msg/.datから抽出された情報を集約

### 4. Abaqusキーワードノード追加
- `AbaqusKeywordParser` (priority=55): .inpファイルの`*`キーワードをNode化
- `Node(type="abaqus_keyword")`: キーワード名(name)、オプション(properties)
- `uses_keyword` relation: .inpファイル → キーワードノード
- 同一キーワードはグローバルで1ノード（複数ファイルから共有）

### 5. STAファイルパース拡張のTODO
- `parse_sta_file()` にTODOコメント追加
- Abaqus Standard: カットバック(1U, 2U等)、インクリメント数、収束情報の収集
- Abaqus Explicit: 別形式対応（サンプル入手後）
- サンプルファイルが必要なため後日対応

### 6. テスト修正
- `_parse_material_curve_columns` → `parse_material_curve_columns` のインポート修正（pre-existing）
- 材料テーブルフォーマット変更に伴うテストアサーション更新
- `get_material_table_keys`: 1行プロパティ除外ロジック変更に対応

## テスト結果

- **1002件パス**, 59件スキップ（pandas/pymesh/streamlit未インストール環境）
- pre-existing failures: pandas/pymesh依存の4件（環境依存）

## 変更ファイル

### パーサー
- `services/parse/connectors/abaqus/inp_parser.py`: Elsetメッシュ分離、AbaqusKeywordParser追加
- `services/parse/connectors/abaqus/result_parser.py`: STAパースTODO追加

### ダッシュボード
- `services/dashboard/connectors/abaqus.py`: メッシュ/Elset品質サマリー、ジョブサマリーページ追加
- `services/dashboard/connectors/abaqus_query.py`: 材料テーブル表示改善、品質サマリー/ジョブサマリークエリ関数追加

### テスト
- `tests/test_dashboard.py`: テストアサーション更新（材料テーブルフォーマット、配列プロットキー）

## TODO（次フェーズ）

- [ ] STAファイルからカットバック・インクリメント収束情報の収集（サンプルファイル入手後）
- [ ] Abaqus Explicitのstaファイル対応
- [ ] jjrvとの連携（次フェーズ）
- [ ] キーワードノードのダッシュボード表示（キーワード一覧ページ）

## 確認事項

- STAパースのカットバック・インクリメント収集はサンプルファイルが必要です。後日サンプル提供をお願いします。
- Abaqus Explicitのstaフォーマットは別形式のため、サンプル入手後に対応予定です。
