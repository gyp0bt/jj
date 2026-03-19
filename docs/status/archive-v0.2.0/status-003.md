[← README.md](../../../README.md)

# status-003: M1.5 — ドキュメント再構成・マルチソルバー仕様書・コアconfig拡張

**日付**: 2026-02-14
**バージョン**: v0.2.0
**前status**: [status-002](status-002.md)
**ブランチ**: `claude/docs-reorganization-BRtfN`

---

## 概要

v0.2.0 M1.5（ドキュメント再構成）として、ロードマップの分離、CLAUDE.md/README.mdのスリム化、マルチソルバー対応仕様書の作成、コアconfigへのSolverProfileConfig追加を実施。

## 完了した作業

### 1. docs/status/status-index.md 作成

v0.2.0のstatusファイル索引を新設。マイルストーン進捗一覧とstatusファイル一覧を含む。新規セッション開始時にまずこのファイルを確認すれば、プロジェクト全体の進捗を即座に把握可能。

### 2. CLAUDE.md スリム化（179行→117行）

プロンプトで毎回注入される運用規約（status管理、ブランチ命名、コミット形式、日本語回答）を排除し、コードベースに関する**技術的規約**と**アーキテクチャ参照**に特化。v0.2.0マイルストーンセクションは `docs/roadmap.md` に移動。

### 3. README.md スリム化（94行→79行）

CLAUDE.mdとの重複セクション「全体規約」を削除。ドキュメントリンクを新しいdocs/roadmap.mdに向けて整理。

### 4. v0.2.0 統合ロードマップ作成（docs/roadmap.md）

review-v0.1.0.mdのロードマップ案をベースに、独立した統合ロードマップを作成:
- M1→M1.5→M3→M4→M5の依存関係を明示
- M2（マルチソルバー検証）は「検証環境確保後に実施」として分離
- 全仕様書（jj 01〜11 + jjrv RM1〜6 + マルチソルバー）へのリンク集を整備

### 5. マルチソルバー対応仕様書（docs/specs/multi-solver.md）

現行パーサーのAbaqus暗黙前提を網羅的に分析し、5ソルバー（LS-DYNA, Flow-3D, OpenFOAM, CalculiX, Fluent）のファイル構造差異を文書化:

- **課題分析**: コアモジュール6箇所のAbaqus暗黙前提を特定
- **ソルバー別構造**: 各ソルバーのディレクトリ構造・命名規則・入出力判定の差異
- **3レイヤー設計**: コアconfig拡張 → コアパーサー修正 → プラグイン実装
- **SolverProfile設計**: source-unit（file/directory）、filename-pattern（standard/reversed/none）
- **`.dat`問題**: LS-DYNAでは入力、Abaqus/CalculiXでは結果 → path-type-mapでオーバーライド
- **Flow-3D逆転問題**: 出力種類.ジョブ名形式 → reversed パターンで対応
- **OpenFOAMディレクトリ計算**: ディレクトリ=1計算 → source-unit: directoryで対応

### 6. コアconfig柔軟性向上（SolverProfileConfig）

`config/__init__.py` に以下を追加:

- **SolverProfileConfig**: ソルバー別のファイル解釈ルール（source_unit, filename_pattern, 入出力拡張子等）
- **SolverDetectionConfig**: パスパターンからソルバープロファイルを自動検出
- **GraphConfig.detect_solver_profile()**: パスから該当するプロファイルを返すメソッド
- **デフォルトプロファイル**: Abaqus互換（既存動作に影響なし）

既存テスト106件（config関連）すべてパスを確認。

### 7. docs/README.md 更新

新規ドキュメント（roadmap.md, status-index.md, multi-solver.md）のリンクを追加。最新status参照を003に更新。

## 変更ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `docs/status/status-index.md` | 新規 | v0.2.0 statusインデックス |
| `docs/roadmap.md` | 新規 | v0.2.0 統合ロードマップ |
| `docs/specs/multi-solver.md` | 新規 | マルチソルバー対応仕様書 |
| `docs/status/status-003.md` | 新規 | 本ファイル |
| `CLAUDE.md` | 修正 | スリム化（運用規約削除、技術規約特化） |
| `README.md` | 修正 | スリム化（CLAUDE.md重複排除、roadmapリンク更新） |
| `docs/README.md` | 修正 | 新規ドキュメントリンク追加 |
| `jj/config/__init__.py` | 修正 | SolverProfileConfig/SolverDetectionConfig追加、GraphConfig拡張 |

## テスト結果

- config関連テスト: 106件パス
- 全体テスト: 560件パス、57スキップ（pandas/pymesh未インストール環境、変更と無関係）

## TODO（次のstatusへ引き継ぎ）

- [ ] default-config.yamlにsolver-profiles/solver-detectionセクションのコメント付き使用例を追加
- [ ] SolverProfileConfigのユニットテスト追加
- [ ] M2: 各ソルバーのテストアセット作成（検証環境確保後）
- [ ] M2: ResultRelationParser, DirectoryRelationParser のソルバープロファイル対応修正
- [ ] M3: Neo4j統合パイプライン設計着手

## 設計上の懸念

1. **ソルバー自動検出の競合**: `.inp`はAbaqusとCalculiXで共通。複数ソルバー混在プロジェクトでの優先順位ルールが必要
2. **Flow-3D逆転パターンのNodeモデル**: basename/formatの意味が逆転する場合、Nodeのname/formatフィールドの一貫性をどう維持するか
3. **OpenFOAMのスキャン性能**: タイムステップディレクトリが数千に達する場合、directory-max-depthでは不十分な可能性

## 開発運用の所感

- **docs/status/status-index.md**は効果的。セッション開始時にindex→最新statusの2ステップで状況把握可能
- **CLAUDE.mdのスリム化**は正しい方向。プロンプト注入で十分な情報（運用規約）を二重管理するのはトークン浪費
- **マルチソルバー仕様書をコード変更前に書く**ことで、設計の盲点（.dat問題、Flow-3D逆転）を実装前に発見できた
