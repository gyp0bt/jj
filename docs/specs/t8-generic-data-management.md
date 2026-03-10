[← README.md](../../README.md)

# T8: 汎用データ管理 設計仕様書

> Run中心プラットフォームへの昇華 — CAE/ML/物理実験を統一的に管理する

---

## 目的

jjを「CAE特化ツール」から「Run中心の汎用データ管理プラットフォーム」に昇華させる。
既存のRun中心スキーマ（M7完了）を基盤に、任意のドメインのRun（実行）を
統一的に発見・管理・比較・可視化できるようにする。

## 現状分析

### 完了済み基盤

| 基盤 | 状態 | 概要 |
|------|------|------|
| M7: Run中心スキーマ | 完了 | RunNode, RUN_INPUT/OUTPUT/MEDIA リレーション |
| RunService | 完了 | execute(), parse-run統合, プロパティ抽出 |
| RunQueryService | 完了 | 検索, 比較, トレーサビリティ |
| T5: リモートジョブ実行 | 完了 | JobState, submit/watch/collect |
| T7: AI連携 | 進行中 | summarize, diff, RAG, Tips |

### 課題

1. **Run discoveryがドメイン依存**: Abaqus/MLごとに異なる発見パターンが散在
2. **プラグインテンプレートにRun対応なし**: 新規プラグイン作成者が参照するパターンがない
3. **config分類がCAE前提**: `config/classification.md`のカテゴリがCAEに偏っている
4. **物理実験データ未対応**: CSV/TSVの実験データを取り込むプラグインがない
5. **Run比較がドメイン前提**: ダッシュボード上のRun比較UIがCAE/MLコンテキスト前提

---

## 設計方針

### 原則

1. **Run = 第一級オブジェクト**: すべてのドメインで Input → Execution → Output の三者関係
2. **プラグインによるドメイン分離**: コアはドメイン非依存、ドメイン知識はプラグインに閉じる
3. **段階的拡張**: 既存のAbaqus/MLプラグインを壊さず、新パターンを追加
4. **テンプレート駆動**: 新規プラグイン作成者がテンプレートをコピーして始められる

### Run Discoveryの標準化

```python
# services/parse/base.py に追加するプロトコル

class RunDiscoveryMixin:
    """Runを発見・登録するパーサーのためのMixin。

    AbstractFileParserのサブクラスに組み込んで使用する。
    """

    run_type: str = ""        # "cae_job", "ml_training", "experiment" 等
    run_status_key: str = ""  # ステータスを取得するプロパティキー

    def discover_runs(self, project_graph: ProjectGraph) -> list[dict]:
        """プロジェクトグラフからRunを発見して返す。

        Returns:
            [{"name": str, "type": str, "inputs": [node_id],
              "outputs": [node_id], "media": [node_id],
              "properties": dict}]
        """
        return []
```

---

## フェーズ分割

### Phase 8-1: Run Discoveryテンプレート標準化

**目標**: 新規プラグインがRun発見パターンを実装する際のテンプレートを提供

**実装内容**:
- `services/parse/run_discovery.py`: RunDiscoveryMixin + ユーティリティ関数
  - `find_input_output_pairs()`: 入出力ファイルペアの自動発見
  - `detect_run_status()`: 汎用ステータス判定（成功/失敗/実行中）
  - `extract_run_properties()`: 共通プロパティ抽出

### Phase 8-2: 物理実験プラグインスケルトン

**目標**: CSV/TSVの実験データを取り込むプラグインの雛形

**実装内容**:
- `services/plugins/experiment/__init__.py`: プラグインエントリ
- `services/parse/connectors/experiment/data_parser.py`: 実験データパーサー
  - CSVヘッダ解析→プロパティ自動抽出
  - メタデータファイル（.meta.yaml）認識
  - Run自動発見（同一ディレクトリの入出力ペア）

### Phase 8-3: プラグイン開発ガイド更新

**目標**: ドキュメント更新

**実装内容**:
- `docs/specs/plugin-development-guide.md`: プラグイン開発ガイド
  - プラグイン構造テンプレート
  - Run discoveryパターン実装例
  - テスト作成ガイド

### Phase 8-4: Config分類の汎用化（将来）

- `config/classification.md`のカテゴリを拡張
- ドメイン別分類テンプレート

### Phase 8-5: Run比較ダッシュボードの汎用化（将来）

- Run比較UIからドメイン依存を除去
- プラグインが比較軸を宣言するパターン

---

## ファイル配置計画

```
services/parse/
  run_discovery.py           # [NEW] RunDiscoveryMixin + ユーティリティ

services/plugins/experiment/
  __init__.py                # [NEW] 物理実験プラグイン

services/parse/connectors/experiment/
  __init__.py                # [NEW]
  data_parser.py             # [NEW] CSV/TSV実験データパーサー

tests/
  test_run_discovery.py      # [NEW]
  test_experiment_plugin.py  # [NEW]

docs/specs/
  t8-generic-data-management.md  # [THIS] 本仕様書
  plugin-development-guide.md    # [NEW] Phase 8-3
```

---

## 依存関係

- Phase 8-1 は独立して実装可能
- Phase 8-2 は Phase 8-1 のMixinを使用
- Phase 8-3 は Phase 8-1/8-2 完了後にドキュメント化
- Phase 8-4/8-5 は将来フェーズ（本PRでは未着手）

---

## 今回の実装スコープ

本PRでは Phase 8-1 と Phase 8-2 を実装する。
Phase 8-3 のプラグイン開発ガイドは次のPRとする。
