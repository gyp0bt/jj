[READMEへ戻る](../../README.md)

# services/parse

プロジェクトフォルダを解析してグラフデータ化する層です。初期段階は共通アダプタとして運用し、必要に応じてソフト固有アダプタを切り出します。

## 役割
- プロジェクト全体の解析とノード/リレーション生成。
- ファイル解析の共通基盤（FileParse）を提供。
- Obsidian向けのマッピング補助（ObsidianFileParse/ObsidianMap）。

## FileParse
- `get_index()`
- `get_version()`
- `get_props()`
- `get_tags()`
- `get_basename()`（フォルダ/拡張子なしのファイル名）
- `get_directory()`
- `get_file_type()`（`go_`/`mesh_`/`material_`/`step_`）
- `get_file_group()`（同一index+先頭接頭辞のグルーピング）

### 設計ポイント
- 拡張子は標準モジュールに任せず、複数ドットを許容する（例: `.cas.h5`）。
- バイナリ判定は開くまで分からないため、読み込み時は常にエスケープ（`errors="ignore"` 等）を前提にする。
- `go_`/`mesh_`/`material_`/`step_` の接頭辞は列挙型で扱い、ファイル/フォルダの両方でファイルタイプを判定する。
- アンダースコア区切りでpropsを判定し、`文字列+数値` または `文字列=数値` にならないトークンはtagとして扱う。
- 旧式（`.v1`）のversionは、新形式のversionが取得できない場合に補完する。

## Obsidian向け
- `ObsidianFileParse` を作成し、`ObsidianMap(true_file_path)` で以下を提供。
  - `get_frontmatter_path()`
  - `get_base_path()`
  - `to_frontmatter_path()`

## アダプタ運用方針
- まずは共通アダプタで進める。
- ソフト固有の処理が肥大化する場合のみ切り出す。
