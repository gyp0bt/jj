[← README.md](../../README.md) | [← docs/README.md](../README.md)

# 仕様書・設計文書

---

## ドメイン仕様書（01〜11）

機能ドメイン別の詳細仕様。コアアーキテクチャの定義。

| # | ドメイン | ファイル | 実装状態 |
|---|---------|---------|---------|
| 01 | コアデータモデル | [01-core-data-model.md](01-core-data-model.md) | 完了 |
| 02 | パーサー | [02-parser.md](02-parser.md) | 完了（plugins/*/parse/ に分散） |
| 03 | 設定管理 | [03-config.md](03-config.md) | 完了（既定値は config/ にハードコード） |
| 05 | noteコマンド | [05-note-command.md](05-note-command.md) | 完了 |
| 06 | fileコマンド | [06-file-command.md](06-file-command.md) | 未実装 |
| 07 | アダプター | [07-adapter.md](07-adapter.md) | 完了（AbstractFileParserパターン） |
| 08 | エクスポート | [08-export.md](08-export.md) | 完了（AbstractExporterパターン） |
| 09 | ダッシュボード | [09-dashboard.md](09-dashboard.md) | 完了（ミニマル版・データ層は GraphQuery に統合） |
| 10 | DB統合 | [10-db-integration.md](10-db-integration.md) | jj側完了 |
| 11 | ダッシュボード要件 | [11-dashboard-requirements.md](11-dashboard-requirements.md) | 完了 |

> 04（runコマンド）は run主体データ管理ごと撤去済み。`jj run` / `jj jobs` /
> RUN ノード / discoverer は廃止された。

---

## 設計文書（個別機能の設計判断）

特定のマイルストーンやトラックに紐づく設計ドキュメント。

### マルチソルバー・基盤 (M1.5/M2)

| ドキュメント | 内容 |
|-------------|------|
| [multi-solver.md](multi-solver.md) | ソルバー別ファイル構造の差異分析・config対応設計 |
| [results-directory-restructure.md](results-directory-restructure.md) | results/ディレクトリのメタデータ抽出スキーマ |
| [vocab-display-time.md](vocab-display-time.md) | 語彙マッピング・表示名の適用タイミング設計 |
| [config-classification.md](config-classification.md) | 設定ファイルの分類体系（T2関連） |

### ML/最適化 (M6)

| ドキュメント | 内容 |
|-------------|------|
| [ml-task-roadmap.md](ml-task-roadmap.md) | ML/実験/最適化のドメイン分析・三層データフロー設計 |
| [surrogate-model-framework.md](surrogate-model-framework.md) | CAE-ML-最適化ワークフロー・層間リレーション |

### Neo4j統合 (M3)

| ドキュメント | 内容 |
|-------------|------|
| [neo4j-pipeline-design.md](neo4j-pipeline-design.md) | Neo4j統合パイプライン・IEntityRepository |

### 計画書

| ドキュメント | 内容 |
|-------------|------|
| [midterm-plan-v0.3.md](midterm-plan-v0.3.md) | v0.3.0 全8ワークトラック詳細設計 |

### ダッシュボード改善・出力連携

| ドキュメント | 内容 |
|-------------|------|
| [dashboard-improvements.md](dashboard-improvements.md) | テーブルフィルタ強化・統合レイアウト・デフォルト保存 |
| [windows-integration.md](windows-integration.md) | Windows連携（PPT貼り付け・Excel書き出し） |
| [property-key-normalization.md](property-key-normalization.md) | include継承時のバージョン付きキー正規化 |
| [property-externalization.md](property-externalization.md) | プロパティ外部化（graph.yaml軽量化） |
| [t8-generic-data-management.md](t8-generic-data-management.md) | T8 汎用データ管理基盤 |

---

## ドメイン間の依存関係

```
┌─────────────────────────────────────────┐
│         コアデータモデル層 (01)           │
│    (Node, Relation, GraphModel)        │
└────────────┬────────────────────────────┘
             │
     ┌───────┼────────┬──────────┐
     │       │        │          │
  パーサー  設定管理  エクスポート  DB統合
   (02)     (03)      (08)       (10)
     │       │
     │       │
  アダプター(07) note(05)  file(06)
```
