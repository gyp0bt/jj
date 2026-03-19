[← README.md](../../../README.md)

# status-030: M7 Run中心スキーマ Phase 2-3 — CAE/ML Run発見パーサー

- **日付**: 2026-02-19
- **マイルストーン**: M7（Run中心スキーマ再設計）
- **ブランチ**: claude/execute-status-todos-ltUCT
- **前提**: status-029（Phase 1: コアモデル拡張完了）

---

## 実施内容

### Phase 2: CaeRunDiscoverer実装

**ファイル**: `jj/services/parse/parsers/cae_run_discoverer.py`

CAE潜在Runを発見するパーサー（priority=200）を実装。

- basename一致による入力/結果ファイルペアの検出（go_*.inp ↔ go_*.sta/.msg/.dat）
- `result_of`/`has_output`/`includes` 既存リレーションの活用
- 結果拡張子優先分類（.datのLS-DYNA入力/Abaqus結果の曖昧性解決）
- ソルバー自動推定（format値→abaqus/lsdyna/fluent）
- includes関係の追加入力ノード収集（mesh, material等）

**テスト**: `jj/tests/test_cae_run_discoverer.py` — 15件

### Phase 3: MlTrainingRunDiscoverer実装

**ファイル**: `jj/services/parse/parsers/ml_run_discoverer.py`

ML学習潜在Runを発見するパーサー（priority=210）を実装。

- training_scriptノードを起点としたRun発見
- MLDataFlowParser(priority=65)の`trains_with`/`produces_model`/`configured_by`リレーション活用
- `logs_to`リレーションによるメトリクスの出力追加
- Run構造: input=dataset+config, media=script, output=model+metrics
- ml_role別のrun_type判定（training/preprocessing/inference）

**テスト**: `jj/tests/test_ml_run_discoverer.py` — 14件

### バグ修正: AbstractFileParser.__init_subclass__ ABCMetaタイミング問題

**ファイル**: `jj/services/parse/base.py`

ABCMeta.__new__が`__abstractmethods__`を設定するタイミングが`__init_subclass__`の呼び出しより後のため、
中間抽象クラス（AbstractRunDiscoverer）がパーサーレジストリに誤登録される問題を修正。

- クラスの名前空間(`cls.__dict__`)を直接チェックし、`__isabstractmethod__`属性を持つメソッドの有無を判定
- 既存テスト`test_abstract_class_not_registered`がパスするようになった

### パーサー登録

**ファイル**: `jj/services/parse/parsers/__init__.py`

- `CaeRunDiscoverer`と`MlTrainingRunDiscoverer`のインポートと`__all__`への追加

---

## テスト結果

- 新規テスト: 29件全通過（CAE 15件 + ML 14件）
- 既存テスト: 影響なし（test_abstract_class_not_registered含め全通過）
- lint: ruff check + ruff format 通過

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `jj/services/parse/parsers/cae_run_discoverer.py` | 新規 |
| `jj/services/parse/parsers/ml_run_discoverer.py` | 新規 |
| `jj/tests/test_cae_run_discoverer.py` | 新規 |
| `jj/tests/test_ml_run_discoverer.py` | 新規 |
| `jj/services/parse/parsers/__init__.py` | 修正（インポート追加） |
| `jj/services/parse/base.py` | 修正（__init_subclass__ ABCMeta対応） |
| `docs/roadmap.md` | 修正（Phase 2/3を完了に更新） |
| `docs/status/status-030.md` | 新規 |
| `docs/status/status-index.md` | 修正 |

---

## 残TODO

- [ ] Phase 4: RunServiceのRun Node統合（実行時RunもRun Nodeとして記録）
- [ ] Phase 5: RunQueryServiceのダッシュボード統合（Run一覧・比較ビュー）
- [ ] Phase 6: Neo4j Run Nodeエクスポート対応
- [ ] 既存パーサーのcategory設定移行（段階的実施）
- [ ] run_typeの値の標準化（将来的にenum化を検討）
- [ ] 大規模プロジェクトでのRun Node数増加に伴うパフォーマンス検証

---

## 確認事項・懸念

- CaeRunDiscovererは現在Abaqusのgo_*ノードタイプのみ対応。LS-DYNA等の他ソルバーは、
  ファイルタイプ検出パターンの拡張が必要（ノードtype値の標準化後に対応）
- MlTrainingRunDiscovererはMLDataFlowParserのリレーションに依存。
  リレーションが未構築の場合（MLパーサー未登録等）はRunが発見されない
- AbstractFileParser.__init_subclass__のABCMeta対応は汎用的な修正で、
  今後追加される中間抽象クラスでも同じ問題は発生しない
