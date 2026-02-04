[READMEへ戻る](../../README.md)

# services/run

`jj r` コマンドで実行するシステムコマンドのラップとログ/トレースを担当します。
`run` は `Node(type=run)` として扱います。

## 役割
- システムコマンド実行のラップ（`jj r <command>` の形を想定）。
- 標準出力/標準エラーを分離してログ化。
- 実行オプションの記録とファイルトレースの抽出。

## runの分類
- **スクリプト型**: 即時に完了する処理（主に `python` / `sh`）。
- **ジョブ型**: 最大数時間など長時間の処理（CAEジョブやバッチ投入）。

## スクリプト型の仕様
- 実行前後のプロジェクトスナップショットを比較し、差分を抽出する。
- 追加/変更されたファイルと `run` の間に `Relation(label=generated)` を作成する。
- 条件（properties）は以下から取得する。
  - `# props start` と `# props end` に挟まれた宣言（例: `ncpu=1`, `ver=abq2023`）。
  - `sys.argv` や `$1` などの引数を、スクリプト内の変数名と対応付けて取得する。
  - 例: `jj r hoge.py 120 60` の実行なら、`sys.argv` の割当変数名に紐づける。

## ジョブ型の仕様
- 自動でのファイル追跡は行わない。
- `abaqus` や `fluent` などのフォーマットに応じて、生成されるファイル群を事前に列挙してリンクを作成する。

## 主要インターフェース案
- `RunService.execute(command: list[str], cwd: Path | None = None) -> RunResult`
- `RunResult` には以下を含める。
  - `stdout`, `stderr`
  - `exit_code`
  - `trace_files`（出力中に出現したファイルパス候補）
