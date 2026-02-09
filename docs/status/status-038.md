[READMEへ戻る](../../README.md)

# status-038: アーキテクチャ方針修正・パラメータ抽出ロジック変更

**日付**: 2026-02-09

## 概要

1. **ロードマップ再策定**: jjとjj-dbの通信方針をNeo4jのみに統一。旧D3（REST API）・D4（API連携）を廃止。
2. **パラメータ抽出ロジック変更**: `*PARAMETER`ブロック内の数値リテラル自動抽出に移行。旧`**props`記法を廃止。
3. **runコマンドprops抽出変更**: Python/Shellスクリプトの`# props start/end`記法を廃止し、数値リテラル代入の自動検出に移行。

## 変更内容

### A. アーキテクチャ方針修正

**原則**: jj serverのAPIをjj-db側から叩かない。jjとjj-dbは契約のみ共有し、Neo4jへのデータアクセス以外で通信しない。

#### ロードマップの変更点

| 変更箇所 | 旧 | 新 |
|----------|-----|-----|
| Phase 2.5 D3 | `jj serve` REST API（FastAPI） | **削除** |
| Phase 2.5 D4 | `jj export --target jj-db`、API連携 | **削除** |
| Phase 2.N N3 | jjリポジトリ内に`jj_db/`ディレクトリ構築 | jj-dbリポジトリ内でNeo4jクライアント実装 |
| Phase 2.N N5 | submodule移行（jj_db/ 切り出し） | shared/の独立パッケージ化検討 |
| Phase 4-12 | Neo4jExporter未実装 | 実装済み（Phase 2.N N2） |
| M4マイルストーン | jj serve REST API稼働、D3-D4完了 | ExporterRegistry完成、3CAE対応 |

#### 設計原則（ロードマップ冒頭に追記）

```
- jjとjj-dbは契約のみ共有し、Neo4jへのデータアクセス以外で通信しない
- jj serverのAPIをjj-db側から叩くことはしない
- 共有はNeo4jスキーマ契約（shared/パッケージ）のみ
```

### B. INPパラメータ抽出ロジック変更

#### 旧ロジック（`**props`記法）
```
*PARAMETER
**props        ← このマーカーが必須だった
w=5
t=20
*STEP
```
- `*PARAMETER`の直後に`**props`コメントが必要
- `**props`がなければブロックをスキップ
- 値の種類を問わず全key=valueを抽出

#### 新ロジック（数値リテラル自動抽出）
```
*PARAMETER
w = 5          ← 数値リテラル → 抽出される
t = 20.0       ← 数値リテラル → 抽出される
area = w * t   ← expression → スキップ
name = static  ← 文字列 → スキップ
*STEP
```
- `**props`マーカー不要（コメント行としてスキップ）
- `*PARAMETER`ブロック内の全key=valueを走査
- 値が数値リテラル（int, float, 科学的記数法）の場合のみ抽出
- expressionや文字列値はスキップ
- 複数の`*PARAMETER`ブロックに対応（旧ロジックは最初のブロックのみ）
- vocabマッピングはキーにのみ適用

#### 変更ファイル（INP）

| ファイル | 関数/メソッド |
|---------|-------------|
| `services/graph/__init__.py` | `_read_inp_parameter_props()` + `_is_numeric_literal()` |
| `services/service/entry.py` | `get_properties_by_inp_parameter()` + `_is_numeric_literal()` |
| `services/notes/__init__.py` | `get_properties_by_inp_parameter()` + `_is_numeric_literal()` |

### C. runコマンドprops抽出変更

#### 旧ロジック（`# props start/end`記法）
```python
# props start
ncpu = 4
method = "static"
# props end
```

#### 新ロジック（数値リテラル代入の自動検出）
```python
ncpu = 4       # ← 数値リテラル → 抽出される
size = 128     # ← 数値リテラル → 抽出される
name = "test"  # ← 文字列 → スキップ
```
- `# props start/end`マーカー不要
- スクリプト全体から`変数 = 数値リテラル`パターンを検出
- Python形式（`var = 5`）とShell形式（`var=5`）の両方に対応
- `sys.argv`や`$N`の既存抽出ロジックは維持

#### 変更ファイル（run）

| ファイル | 関数/メソッド |
|---------|-------------|
| `services/run/__init__.py` | `_extract_props_block()` |

### D. テスト変更

| テストクラス/関数 | 変更内容 |
|------------------|---------|
| `TestInpParameterProps` | 6テストに拡充（数値リテラル・expression・float・科学的記数法・コメント行） |
| `TestVocabValueTranslation` | キー変換テスト+文字列値スキップテストに変更 |
| `test_run_service_script_mode_tracks_files_and_props` | `# props start/end`を削除、数値リテラル自動抽出に変更 |

### E. ドキュメント変更

| ファイル | 変更内容 |
|---------|---------|
| `docs/roadmap.md` | 設計原則追加、D3/D4削除、**props→数値リテラル、Phase 4整合、マイルストーン修正 |
| `docs/specs/10-db-integration.md` | アーキテクチャ図からFastAPI削除、N3/N5修正、分離ルール更新 |
| `README.md` | status-038追加 |

## テスト結果

- **合計**: 366パス + 20スキップ
- **リグレッション**: なし（既存テスト全パス）

## 次のステップ

- Phase 2.5 D1: DashboardDataProvider実装
- Phase 2.N N3: jj-dbリポジトリでNeo4jクライアント実装
- Phase 3: runコマンドジョブ型、fileコマンド基本実装
