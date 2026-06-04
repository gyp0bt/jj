"""jjプラグインパッケージ（後方互換）

このモジュールはpluginsパッケージからre-exportしています。
新規コードでは plugins を直接importしてください。

Abaqus/Obsidian等のドメイン固有ロジックをプラグインとして集約する。
各プラグインは以下の3種類のコンポーネントを登録できる:

- パーサー（AbstractFileParserサブクラス）
- エクスポーター（AbstractExporterサブクラス）

プラグインのロードはservices.sdk.plugin_registryが管理する。

[READMEへ戻る](../../../README.md)
"""
