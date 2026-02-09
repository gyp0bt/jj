[READMEへ戻る](../../README.md)

# status-041: services構造改革に伴うロードマップ根本改変

**日付**: 2026-02-09

## 概要

services構造の大幅リファクタリング設計（status-040追記）に伴い、ロードマップを根本改変。抽象パーサーパターン（AbstractFileParser.__init_subclass__）とProjectGraph型を軸に、Phase Rを新設。完了済み項目を整理し、旧アダプター層をparseコネクターとして再定義した。

## 変更内容

### 1. ロードマップ根本改変（docs/roadmap.md）

**主な構造変更**:

| 旧ロードマップ | 新ロードマップ |
|---------------|---------------|
| Phase 1: 基盤整備 | 完了セクションに統合 |
| Phase 2: グラフ機能の作り込み | 大部分完了（M1.5として達成）、残存→Phase 2 |
| （なし） | **Phase R: services構造リファクタリング（新設・最優先）** |
| Phase 4: アダプター層 | Phase 4-1: parseコネクター拡張に再定義 |
| Phase 4: 出力層 | Phase 4-2: export層の拡張に再定義 |

**Phase R の内容**:
- R1: ProjectGraph型の実装（ProjectFile, ProjectDirectory, ProjectGraph）
- R2: AbstractFileParser.__init_subclass__パターン確立（apply()メソッド、自動登録、parse()オーケストレーション）
- R3: graph/__init__.py の分解（9つのパーサーサブクラスに分散）
- R4: export層の整理（Obsidian/Neo4j/CSV/JSONエクスポーター分離）
- R5: lib層の整理（credentials, file等のユーティリティ移動）
- R6: テスト移行と検証（shared/tests/test_asset1活用）

**マイルストーン追加**:
- M1.5: Abaqusグラフ機能完成 ✅（2026-02-09達成）
- MR: services構造改革完了（Phase R完了）

**アーキテクチャ概要セクション追加**:
- 背景（graph/__init__.pyへの過集中問題）
- 新services構造のディレクトリツリー
- 抽象パーサーパターンのコード例
- ProjectGraph型の定義
- テストデータ（shared/tests/test_asset1）

### 2. 実装詳細更新（docs/detail.md）

- ディレクトリ構成を新構造に全面書き換え
- services/graph: ProjectGraph型の説明追加
- services/parse: 抽象パーサーパターンの説明追加
- services/export: Neo4j/CSV/JSONエクスポーター説明追加
- services/lib: credentials/file説明追加
- shared/tests/test_asset1 記載追加

### 3. jj/README.md更新

- ディレクトリセクションを新構造に合わせて更新
- status-041エントリ追加

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `docs/roadmap.md` | 全面改変: Phase R新設、完了整理、マイルストーン追加 |
| `docs/detail.md` | 全面改変: 新services構造に対応 |
| `README.md` | 変更: ディレクトリ構成更新、status-041追加 |
| `docs/status/status-041.md` | 新規: 本ステータス |

## テスト結果

ドキュメントのみの変更のため、テスト影響なし（既存396件パス+20スキップを維持）。

## TODO / 次のステップ

- [ ] Phase R1: ProjectGraph型の実装着手
- [ ] Phase R2: AbstractFileParser.apply()メソッドと__init_subclass__自動登録の実装
- [ ] Phase R3: graph/__init__.py のパーサーサブクラスへの分解（最大作業量）
- [ ] Phase R4: export層の整理（ObsidianConnector移動）
- [ ] specs/02-parser.md を新アーキテクチャに合わせて更新
- [ ] specs/07-adapter.md をparseコネクターとして再定義

## 確認事項・設計上の懸念

1. **R3の分解粒度**: graph/__init__.pyは現在数百行。パーサーサブクラスへの分解時、既存のインポート構造（graph/__init__.py → parse/connectors/abaqus, obsidian）が変わるため、既存テストの大量修正が必要になる可能性がある。段階的な移行が望ましい。

2. **パーサー実行順序**: `__init_subclass__`による自動登録はPythonのモジュールimport順に依存する。priority属性での明示的な順序制御が必要。例: filename_parser → version_parser → output_parser の順序依存がある。

3. **ObsidianConnectorの配置**: 現在`parse/connectors/obsidian/`にあるが、実質的にはexportロジック。Phase R4でexport/connectors/に移動する際、parse/connectors/obsidian/daily.pyはparse側に残す必要がある（dailyノート解析はparseロジック）。

4. **file_parse.py（レガシー）**: `AbstractFileParser`（base.py）と`FileParse`（file_parse.py）に重複する機能がある。Phase R完了後にfile_parse.pyを段階的に廃止する計画が必要。
