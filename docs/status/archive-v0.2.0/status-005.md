[← README.md](../../../README.md)

# status-005: SolverProfileConfigテスト追加・パーサーのソルバープロファイル対応

**日付**: 2026-02-15
**バージョン**: v0.2.0
**前status**: [status-004](status-004.md)
**ブランチ**: `claude/execute-status-todos-DSXAo`

---

## 概要

status-004のTODOから以下2点を実施:
1. SolverProfileConfig / SolverDetectionConfig / GraphConfig.detect_solver_profile のユニットテスト新規作成（28件）
2. ResultRelationParser, AssetRelationParser, OutputRelationParser, IncludesRelationParser, DirectoryRelationParser のソルバープロファイル拡張子マージ対応（テスト6件追加）

## 完了した作業

### 1. SolverProfileConfigのユニットテスト追加

`jj/tests/test_solver_profile.py` を新規作成。以下のテストクラスを含む:

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| `TestSolverProfileConfig` | 12 | from_dict基本動作、バリデーション、frozen、型変換 |
| `TestSolverDetectionConfig` | 7 | ルールパース、パイプ区切りパターン、detect動作 |
| `TestDetectSolverProfile` | 6 | GraphConfig統合テスト: デフォルト、検出、フォールバック、複数プロファイル |
| `TestGraphConfigSolverProfiles` | 3 | from_dictでのプロファイル/検出ルール読み込み |

### 2. パーサーのソルバープロファイル拡張子マージ対応

各パーサーの `apply()` メソッドで、グローバル `file-relations` 設定に加えて全ソルバープロファイルの拡張子をマージするように修正:

| パーサー | 修正内容 |
|---------|---------|
| `ResultRelationParser` | input_extensions + result_extensions をプロファイルからマージ |
| `AssetRelationParser` | input_extensions をプロファイルからマージ |
| `OutputRelationParser` | input_extensions + result_extensions をプロファイルからマージ |
| `IncludesRelationParser` | input_extensions をプロファイルからマージ |
| `DirectoryRelationParser` | input_extensions をプロファイルからマージ |

パーサー修正に対応するテストクラス:

| テストクラス | テスト数 | 内容 |
|------------|---------|------|
| `TestResultRelationParserSolverProfile` | 3 | ソルバー拡張子でresult_of作成、グローバル拡張子継続動作、複数ソルバー混在 |
| `TestOutputRelationParserSolverProfile` | 1 | ソルバー入力拡張子でhas_output認識 |
| `TestDirectoryRelationParserSolverProfile` | 1 | ソルバー入力拡張子でcontains関係作成 |
| `TestAssetRelationParserSolverProfile` | 1 | ソルバー入力拡張子でderived_from認識 |

### 修正方針の説明

ソルバープロファイルの拡張子マージは「全プロファイルの拡張子を集約してグローバルに使用」するアプローチを採用。これにより:
- 既存動作に影響なし（グローバル設定の拡張子はそのまま有効）
- ソルバー固有の拡張子（`.k`, `.key`, `.d3plot`, `.frd` 等）も自動的に認識される
- `frozenset` → `set` への変換で柔軟なマージが可能

`result_filenames`（LS-DYNAの`d3hsp`等）や`result_prefixes`（Flow-3Dの`flsgrf.*`等）は、basename単位のグルーピングでは対応できないため、今回のスコープ外とした。これらはディレクトリベースの関係構築（各ソルバープラグイン内で実装予定）で対応する。

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `jj/tests/test_solver_profile.py` | 新規 | SolverProfileConfig/パーサーソルバー対応テスト（34件） |
| `jj/services/parse/parsers/output_parser.py` | 修正 | ResultRelationParser, AssetRelationParser, OutputRelationParser, IncludesRelationParserのプロファイル拡張子マージ |
| `jj/services/parse/parsers/directory_parser.py` | 修正 | DirectoryRelationParserのプロファイル拡張子マージ |
| `docs/status/status-005.md` | 新規 | 本ファイル |
| `docs/status/status-index.md` | 修正 | status-005追加 |

## テスト結果

- 新規テスト: 34件全パス
- 既存テスト: 167件パス（2件はpandas未インストールによる既存スキップ）
- lint: 変更ファイルは全てクリーン（既存ファイルのRUF002/003は日本語文字によるもの）

## TODO（次のstatusへ引き継ぎ）

- [ ] 各ソルバーのテストアセット作成（検証環境確保後）
- [ ] 各プラグインパーサーの本実装（検証環境確保後に順次）
- [ ] result_filenames / result_prefixes / result_directory_pattern 対応（ディレクトリベース関係構築）
- [ ] M3: Neo4j統合パイプライン設計着手

## 設計上の懸念

1. **basename vs ディレクトリベース関係**: 現在のResultRelationParserはbasename単位でグルーピングするが、LS-DYNAやFlow-3Dでは入力と結果のbasename一致しない。ソルバー固有のパーサーでディレクトリベースの関係構築が必要
2. **拡張子衝突**: `.dat`がAbaqusでは結果ファイル、LS-DYNAでは入力ファイルとして定義される。現在の全マージ方式では同じファイルが両方に分類される可能性があるが、basename一致が前提のため実害は少ない

## 開発運用の所感

- **status-004のTODOが明確だったため引き継ぎがスムーズ**: 何をすべきかが具体的に書かれていたので、すぐに作業着手できた
- **テストファーストの効果**: SolverProfileConfigのテストを先に書いたことで、from_dictの挙動を網羅的に理解してからパーサー修正に着手できた
