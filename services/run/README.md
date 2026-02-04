[READMEへ戻る](../../README.md)

# services/run

`jj r` コマンドで実行するシステムコマンドのラップとログ/トレースを担当します。

## 役割
- システムコマンド実行のラップ（`jj r <command>` の形を想定）。
- 標準出力/標準エラーを分離してログ化。
- 実行オプションの記録とファイルトレースの抽出。

## 主要インターフェース案
- `RunService.execute(command: list[str], cwd: Path | None = None) -> RunResult`
- `RunResult` には以下を含める。
  - `stdout`, `stderr`
  - `exit_code`
  - `trace_files`（出力中に出現したファイルパス候補）
