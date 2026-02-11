[READMEへ戻る](../../README.md)

# services/service

サービス群をアセンブルし、CLIに渡すための処理関数を提供します。

## 役割
- 各サービスの依存注入と初期化。
- CLI向けのユースケース関数を集約。
- CLI層はservice層のみからインポートし、ビジネスロジックを直接実装しない。

## サービス一覧

| クラス | ファイル | 責務 |
|--------|---------|------|
| `GraphCommandService` | `graph_command.py` | グラフコマンドのビジネスロジック（init/parse/show/export/info/diff/credential） |
| `InfoService` | `info.py` | グラフ情報検索・データエクスポート |
| `SubmitService` | `submit.py` | submit/files/syntax コマンドのビジネスロジック |

## 依存関係
```
CLI (services/cli/) → services/service/ → services/graph/, services/parse/, services/export/, services/lib/
```
