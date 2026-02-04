[READMEへ戻る](../../README.md)

# services/cli

CLIのエントリポイントを定義し、`services/service` の関数に委譲します。

## 役割
- argparse でコマンドを定義。
- サブコマンドごとに Service のユースケースを呼び出す。

## 方針
- CLI引数のバリデーションは argparse + pydantic を組み合わせる。
