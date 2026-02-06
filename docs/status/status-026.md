[READMEへ戻る](../../README.md) | [ロードマップ](../roadmap.md)

# Status 026 - jj g parse パスパース・型判定バグ修正（Windows/Linux対応）

**日付**: 2026-02-06

---

## 概要

`jj g parse`でWindowsパスおよびLinuxパスにおける以下の重大バグを修正した。
- `tools/`, `reports/`等の配下ファイルが`type=unknown`になる
- プロジェクト直下のファイルがスキャンされない
- フォルダがNodeに正しく組み込まれない

根本原因は`_match_path_pattern`のパターンマッチング不備と、
`DEFAULT_EXTENSIONS`に`.inp`等のCAE拡張子が未含の2点。

---

## バグ原因と修正内容

### バグ1: `_match_path_pattern`の`./`プレフィックス未対応

**原因**: デフォルト設定の`path-type-map`が`"./reports/"`のような`./`プレフィックス付きパターンを使用。
一方、`_safe_relative_path`は`reports/file.pptx`のように`./`なしのパスを返す。
`fnmatch.fnmatch("reports/file.pptx", "./reports/")` → Falseとなり、型判定が不一致。

**修正**: `_match_path_pattern`でパスとパターンの両方から先頭`./`を除去してから比較。

### バグ2: ディレクトリパターン（末尾`/`）の未処理

**原因**: `"./reports/"`のような末尾`/`付きパターンは「配下全ファイルにマッチ」の意味だが、
fnmatchはこの意味を理解しない。

**修正**: `_match_path_pattern`で末尾`/`のパターンを特別処理し、`startswith`でディレクトリ配下を判定。

### バグ3: `**go`パターンのbasename比較不足

**原因**: `**go`パターンは`go.inp`や`go.cas.h5`にマッチすべきだが、
fnmatchは`**go`を「goで終わる」パターンとして扱い、`go.inp`にマッチしない。

**修正**: `**`パターンで直接マッチしない場合、ファイル名から拡張子を段階的に除去して
basename比較を行う。例: `go.cas.h5` → `go.cas` → `go` の順に試行。

### バグ4: `DEFAULT_EXTENSIONS`に`.inp`/`.odb`/`.sta`が未含

**原因**: `services/parse/file_parse.py`の`DEFAULT_EXTENSIONS`に`.inp`, `.odb`, `.sta`等の
CAE固有拡張子が含まれていない。CLIから`jj g parse`を呼ぶと`extensions`がNoneで渡され、
この不完全なリストが使用される。

**修正**: `GraphService.parse_project()`に`_build_scan_extensions()`メソッドを追加。
`extensions`がNoneの場合、`DEFAULT_EXTENSIONS`にconfigの`file-relations`の
`input-extensions`/`result-extensions`/`asset-extensions`を自動マージする。

### バグ5: フォルダNode構築のパス比較強化

**原因**: `_build_directory_relations`のcontains判定でパスのバックスラッシュや
先頭`./`の不一致が発生する可能性。

**修正**:
- `_safe_relative_path`に先頭`./`除去ロジック追加、`project_root.resolve()`で一貫性確保
- `_build_directory_relations`のcontains判定でパスのバックスラッシュ正規化と先頭`./`除去を追加

---

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config/__init__.py` | `_match_path_pattern`を全面改修（./除去、末尾/、**basename比較） |
| `services/graph/__init__.py` | `_build_scan_extensions()`追加、`_safe_relative_path`改善、`_build_directory_relations`パス比較強化 |
| `tests/test_graph_feature.py` | 4つのテストクラス追加（34件の新規テスト） |

---

## テスト結果

全126テスト通過（既存92 + 新規34）

### 新規テストクラス
- `TestMatchPathPattern`: パスパターンマッチングテスト（17件）
  - `./`プレフィックス処理
  - 末尾`/`ディレクトリパターン
  - `**go` basename比較
  - Windowsバックスラッシュ対応
- `TestScanExtensions`: 拡張子マージテスト（4件）
  - `_build_scan_extensions`のconfigマージ
  - 明示指定時の非マージ確認
  - extensions未指定での.inp/.sta発見
- `TestPathTypeMapWithDefaultConfig`: デフォルト設定統合テスト（10件）
  - reports/tools/results/docs配下の型判定
  - プロジェクト直下のgo.inp/mesh.inp/material.inpの型判定
  - 統合パースでの型付け確認
- `TestDirectoryNodeWindows`: フォルダNode構築テスト（3件）
  - POSIXパス確認
  - contains関係の完全構築
  - 先頭`./`なし確認

---

## TODO（次回以降の作業）

- [ ] パーサー層の拡張機能（ファイルグループ、.v1完全対応、パフォーマンス最適化）
- [ ] run(unknown00)のような仮runを介した関連付け
- [ ] config.yamlの拡張（配列スライス、type=iso/aniso定義）
- [ ] .msgファイルの解析（WARNING/ERROR抽出）
- [ ] ドキュメント連携（index.csv/yaml、Obsidian dailyノート）
- [ ] Windows環境での実機テスト（本修正はロジックレベルの対応、実機未検証）

---

## 確認事項

- 本修正はLinux環境でのテストで検証済み。Windows環境での実機テストは未実施。
  パスの正規化ロジックは`pathlib.Path.as_posix()`に依存しており、
  Windowsの`Path`オブジェクト経由のパス処理は正しく動作する設計。
- `_match_path_pattern`のバックスラッシュ正規化により、
  configファイル内でWindows/Linux混在のパターン記述にも対応。
