[READMEへ戻る](../../README.md)

# services/service

サービス群をアセンブルし、CLIに渡すための処理関数を提供します。

## 役割
- 各サービスの依存注入と初期化。
- CLI向けのユースケース関数を集約。

## 例
- `build_services(config: AppConfig) -> ServiceContainer`
- `ServiceContainer` が `parse`, `storage`, `run`, `file` を保持。
