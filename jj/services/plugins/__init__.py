"""jjプラグインパッケージ

Abaqus/Obsidian等のドメイン固有ロジックをプラグインとして集約する。
各プラグインは以下の3種類のコンポーネントを登録できる:

- パーサー（AbstractFileParserサブクラス）
- エクスポーター（AbstractExporterサブクラス）
- ダッシュボードコネクター（DashboardPageConnectorサブクラス）

プラグインのロードはservices.sdk.plugin_registryが管理する。

[READMEへ戻る](../../../README.md)
"""
