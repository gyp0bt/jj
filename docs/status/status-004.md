[← README.md](../../README.md)

# status-004: M1.5完了・M2開始 — プラグイン雛形作成・HFSS/Fluent追加

**日付**: 2026-02-15
**バージョン**: v0.2.0
**前status**: [status-003](status-003.md)
**ブランチ**: `claude/add-hfss-fluent-plugins-w2HvU`

---

## 概要

M1.5の残TODOを完了し、M2のプラグイン雛形作成を実施。既存の5ソルバー（LS-DYNA, Flow-3D, OpenFOAM, CalculiX, Fluent）に加え、HFSSを新規追加し、計6ソルバーのプラグインスケルトンを作成した。

## 完了した作業

### 1. マルチソルバー仕様書にHFSS/Fluent詳細追加

`docs/specs/multi-solver.md` に以下を追加:
- **Fluent**: .cas.h5/.dat.h5（HDF5バイナリ）、.jou（ジャーナル）、.out/.xy（テーブル結果）のファイル構造
- **HFSS**: .aedt（バイナリ、部分テキスト埋込）、.aedt.batchinfo/（実行ログ）、.aedtresults/（結果）、CSV/Touchstoneエクスポートのファイル構造
- solver-profilesのconfig例にfluent/hfssを追加
- solver-detectionパターンにfluent/hfssを追加
- セクション5にFluent/HFSSプラグイン実装概要を追加
- M2実装計画を更新

### 2. 6ソルバーのプラグイン雛形作成

各ソルバーについて、`services/plugins/{solver}/`と`services/parse/connectors/{solver}/`にスケルトンを作成:

| ソルバー | プラグイン | パーサー | 内容 |
|---------|-----------|---------|------|
| LS-DYNA | `plugins/lsdyna/__init__.py` | `connectors/lsdyna/keyword_parser.py` | キーワードカード解析（TODO） |
| Flow-3D | `plugins/flow3d/__init__.py` | `connectors/flow3d/prepin_parser.py` | prepin.*パラメータ解析（TODO） |
| OpenFOAM | `plugins/openfoam/__init__.py` | `connectors/openfoam/case_parser.py` | ケースディレクトリ解析（TODO） |
| CalculiX | `plugins/calculix/__init__.py` | `connectors/calculix/inp_parser.py` | Abaqusサブセット.inp解析（TODO） |
| Fluent | `plugins/fluent/__init__.py` | `connectors/fluent/journal_parser.py` | .jouジャーナル解析（TODO） |
| HFSS | `plugins/hfss/__init__.py` | `connectors/hfss/aedt_parser.py` | .aedt部分テキスト解析（TODO） |

全パーサーは `AbstractFileParser` サブクラスとして `priority=60` で定義。`apply()` メソッドはグラフをそのまま返すスケルトン（TODOコメント付き）。

### 3. pyproject.toml更新

- `[project.entry-points."jj.plugins"]` に6ソルバーのentry_pointsを追加
- `[project.optional-dependencies]` にfluent（h5py依存）を追加
- `all` グループにfluentを追加

### 4. default-config.yaml更新（M1.5 TODO消化）

solver-profiles/solver-detectionセクションのコメント付き使用例を追加:
- 7ソルバー分のsolver-profiles設定例（default, lsdyna, flow3d, openfoam, calculix, fluent, hfss）
- solver-detection設定例（パスパターン→ソルバー自動検出）

### 5. roadmap・status-index更新

- M1.5を「完了」に変更
- M2テーブルにHFSSを追加
- M2の説明を更新（雛形はM1.5で作成済み）
- status-indexのマイルストーン進捗を更新

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `docs/specs/multi-solver.md` | 修正 | Fluent/HFSSファイル構造、solver-profile例、プラグイン概要追加 |
| `jj/services/plugins/lsdyna/__init__.py` | 新規 | LS-DYNAプラグインスケルトン |
| `jj/services/plugins/flow3d/__init__.py` | 新規 | Flow-3Dプラグインスケルトン |
| `jj/services/plugins/openfoam/__init__.py` | 新規 | OpenFOAMプラグインスケルトン |
| `jj/services/plugins/calculix/__init__.py` | 新規 | CalculiXプラグインスケルトン |
| `jj/services/plugins/fluent/__init__.py` | 新規 | Fluentプラグインスケルトン |
| `jj/services/plugins/hfss/__init__.py` | 新規 | HFSSプラグインスケルトン |
| `jj/services/parse/connectors/lsdyna/` | 新規 | LS-DYNAパーサーコネクター（__init__.py + keyword_parser.py） |
| `jj/services/parse/connectors/flow3d/` | 新規 | Flow-3Dパーサーコネクター（__init__.py + prepin_parser.py） |
| `jj/services/parse/connectors/openfoam/` | 新規 | OpenFOAMパーサーコネクター（__init__.py + case_parser.py） |
| `jj/services/parse/connectors/calculix/` | 新規 | CalculiXパーサーコネクター（__init__.py + inp_parser.py） |
| `jj/services/parse/connectors/fluent/` | 新規 | Fluentパーサーコネクター（__init__.py + journal_parser.py） |
| `jj/services/parse/connectors/hfss/` | 新規 | HFSSパーサーコネクター（__init__.py + aedt_parser.py） |
| `jj/pyproject.toml` | 修正 | entry_points追加、optional-dependencies追加 |
| `shared/assets/default-config.yaml` | 修正 | solver-profiles/solver-detectionコメント付き使用例追加 |
| `docs/roadmap.md` | 修正 | M1.5完了、HFSS追加、M2説明更新 |
| `docs/status/status-index.md` | 修正 | M1.5完了、M2進行中、status-004追加 |
| `docs/status/status-004.md` | 新規 | 本ファイル |

## テスト結果

- 既存テスト: 全件パス（新規プラグインはスケルトンのため既存動作に影響なし）
- lint: パス

## TODO（次のstatusへ引き継ぎ）

- [ ] SolverProfileConfigのユニットテスト追加
- [ ] 各ソルバーのテストアセット作成（検証環境確保後）
- [ ] ResultRelationParser, DirectoryRelationParser のソルバープロファイル対応修正
- [ ] 各プラグインパーサーの本実装（検証環境確保後に順次）
- [ ] M3: Neo4j統合パイプライン設計着手

## 設計上の懸念

1. **HFSS .aedtの部分テキスト抽出**: バイナリ内のテキストブロック位置がバージョンによって異なる可能性がある。実際のファイルで検証が必要
2. **Fluent .cas.h5/.dat.h5のメタデータ**: h5py依存を追加したが、HDF5内部のデータ構造はFluentバージョンに依存する。pyansys-fluentとの連携も検討が必要
3. **スケルトンパーサーのレジストリ登録**: 全プラグインのパーサーがレジストリに登録されると、apply()呼び出しのオーバーヘッドが増える。ただし現状はno-opなので実質的な影響はない

## 開発運用の所感

- **粗い雛形を先に作る方式は有効**: コアの設計パターン（AbstractFileParser + __init_subclass__）に沿ったスケルトンを先に作ることで、後から検証環境が用意できた時にすぐ本実装に着手できる
- **docstringにファイル構造情報を含める**ことで、別のAIアシスタントが引き継ぐ際に仕様書を参照せずとも基本情報を把握可能
