[← status-index](status-index.md)

# status-028 — サロゲートモデルフレームワーク Phase 4.5: バグ修正・パスマッチング改善・E2Eテスト拡充

- **日付**: 2026-02-19
- **マイルストーン**: M6
- **ブランチ**: `claude/surrogate-model-framework-NSm1k`

---

## 概要

Phase 4で構築したサロゲートモデルフレームワークのバグ修正・精度向上・テスト拡充を実施。

1. **MLDatasetParser 型上書きバグ修正**: path_type_map で設定された型（"報告書"等）を MLDatasetParser が "dataset" に上書きしていた問題を修正
2. **MLDataFlowParser パスマッチング改善**: 典型的なMLプロジェクト構造（src/, data/, models/が別ディレクトリ）に対応するプロジェクトルートスコープフォールバックを追加
3. **SurrogateWorkflowDetector 精度向上**: 浅いパス（depth==2）の機能ディレクトリ同士のフォールバックマッチングを追加。深いパス（depth>=3）ではroot segmentによるプロジェクト分離を維持
4. **CAE+ML混在E2Eテスト**: test_asset_surrogateを新規作成し、三層ワークフロー全体のE2Eテスト7件を追加

---

## 変更ファイル

### 修正

| ファイル | 変更内容 |
|---------|----------|
| `jj/services/parse/connectors/ml/dataset_parser.py` | `_DEFAULT_FILE_TYPES` 導入、path_type_map設定済みノードの型昇格スキップ |
| `jj/services/parse/connectors/ml/dataflow_parser.py` | `_has_directory()` ヘルパー追加、3段階マッチング（experiment_id → 親/祖父母 → プロジェクトスコープ） |
| `jj/services/parse/connectors/ml/surrogate_detector.py` | `_is_shallow_path()` ヘルパー追加、浅いパスフォールバック（depth==2のみ対象、depth>=3はroot segment判定維持） |

### テスト追加

| ファイル | 追加テスト数 | 内容 |
|---------|-------------|------|
| `jj/tests/test_ml_parsers.py` | +2 | `test_path_type_map_type_preserved`, `test_result_type_not_overridden` |
| `jj/tests/test_surrogate_framework.py` | +13 | MLDataFlowParser: +5（プロジェクトスコープフォールバック）、SurrogateWorkflowDetector: +3（浅いパスフォールバック）、E2E: +7（CAE+ML混在テスト） |

### 新規テストアセット

| ディレクトリ | ファイル | 用途 |
|-------------|---------|------|
| `shared/tests/test_asset_surrogate/cae/` | `go_idx1_v1.inp` | CAE入力（Abaqus .inp） |
| `shared/tests/test_asset_surrogate/data/` | `extracted_features.csv` | CAE結果から抽出した特徴量 |
| `shared/tests/test_asset_surrogate/ml/` | `train_surrogate.py`, `surrogate_config.yaml`, `surrogate_v1.pt` | 学習スクリプト・設定・モデル |
| `shared/tests/test_asset_surrogate/optimization/` | `optuna_study.db`, `trial_history.csv` | 最適化スタディ・試行履歴 |

---

## テスト結果

- **test_surrogate_framework.py**: 52件全通過（+15件）
- **test_ml_parsers.py**: 55件全通過（+2件）
- **test_full_parse_reports_typed**: PASSED（修正前はFAILED）
- ruff check / ruff format: エラーなし

---

## 技術詳細

### MLDatasetParser 型保護メカニズム

```python
_DEFAULT_FILE_TYPES = {ft.value for ft in FileType} | {"file"}
# go, mesh, material, step, unknown, file

# path_type_mapで明示的に型指定されたノードは昇格しない
if node.type in _DEFAULT_FILE_TYPES:
    node.type = "dataset"
node.properties["ml_dataset"] = True  # メタデータは常に付与
```

### MLDataFlowParser 3段階マッチング

1. **experiment_id一致**: 同一実験IDのノード（最高精度）
2. **親/祖父母ディレクトリ一致**: 同一または兄弟ディレクトリ内のノード
3. **プロジェクトルートスコープ** (NEW): 両方がディレクトリ配下（depth>=2）なら全マッチ

### SurrogateWorkflowDetector パス深度判定

```python
def _is_shallow_path(path_str: str) -> bool:
    """depth==2: 機能ディレクトリ直下（cae/file.inp）→ フォールバック対象
       depth>=3: プロジェクトルート付き（project/cae/file.inp）→ root segment判定
    """
    return len(PurePosixPath(path_str).parts) == 2
```

---

## 残TODO

- [ ] MLダッシュボードコネクター実装（実験比較ビュー・サロゲートモデルビュー）
- [ ] Phase 5着手: 三層データフローダイアグラム可視化（ダッシュボードページ）
- [ ] Neo4j Docker E2E検証（WSLローカル環境）
- [ ] 検索UIでのNeo4j全文検索統合
- [ ] SurrogateWorkflowDetector: 設定ファイル内の参照パス解析による精度向上（YAML/JSON内のパス参照）
