[READMEへ戻る](../../README.md)

# status-066: Obsidian Vault自動セットアップ・GraphMLエクスポーター凍結

**日付**: 2026-02-12

## 実施内容

### 1. Obsidian Vault設定自動生成（.obsidian/）

- `ObsidianConnector._write_vault_config()` を新規追加
- `jj export --target obsidian` 実行時、`.obsidian/` が存在しない場合にVault設定を自動生成
- 既存のVault（`.obsidian/` が存在する場合）には一切変更を加えない（安全な初回のみ生成）
- 生成される設定ファイル:
  - `.obsidian/app.json`: WikiLinks有効化（`useMarkdownLinks: false`）、frontmatter表示
  - `.obsidian/community-plugins.json`: 推奨プラグインID一覧（`dataview`, `dbfolder`）
  - `.obsidian/core-plugins-migration.json`: Canvas等のコアプラグイン有効化

### 2. export_graph() への統合

- `export_graph()` の冒頭で `_write_vault_config()` を呼び出し
- Vault設定ファイルもwritten pathsリストに含まれる
- `ObsidianExporter.export()` の戻り値に `vault_initialized` フラグを追加

### 3. CLI出力改善

- `ObsidianExporter.format_cli_result()` を改善
- Vault初期化時に推奨プラグインのインストール案内を表示
  - 「[Vault初期化] .obsidian/ ディレクトリを生成しました」
  - 推奨プラグイン: Dataview, DB Folder

### 4. GraphMLエクスポーター凍結

- GraphMLは使用されていないため、roadmap上で凍結マーク
- status-065のTODOから「GraphML エクスポーター」を凍結として処理

### 5. テスト

- 新テスト6件追加:
  - `TestObsidianVaultConfig::test_vault_config_created_on_first_export`: 初回エクスポートでVault設定生成
  - `TestObsidianVaultConfig::test_vault_config_not_overwritten`: 既存Vaultを変更しない
  - `TestObsidianVaultConfig::test_vault_config_standalone`: _write_vault_config()単体テスト
  - `TestObsidianVaultConfig::test_exporter_vault_initialized_flag`: vault_initializedフラグ確認
  - `TestObsidianVaultConfig::test_format_cli_result_with_vault_init`: CLI出力にVault初期化案内
  - `TestObsidianVaultConfig::test_format_cli_result_without_vault_init`: 初期化なし時は案内なし
- 既存テスト修正:
  - `test_export_graph`: Vault設定3ファイル分のcount修正（3→6）
  - `test_obsidian_exporter_via_registry`: 空グラフでもVault設定3ファイル生成に対応
- **結果: 699テストパス、21スキップ**（pymesh環境依存2件は除外）

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| services/export/connectors/obsidian/__init__.py | _write_vault_config()追加、export_graph()統合、format_cli_result改善 |
| docs/specs/08-export.md | Vault自動セットアップ手順更新、出力構造に.obsidian/追加 |
| docs/roadmap.md | GraphMLExporter凍結マーク |
| tests/test_parser_units.py | 6テスト追加（TestObsidianVaultConfig）、既存テスト修正 |
| tests/test_obsidian_connector.py | test_export_graph count修正 |

## アーキテクチャ

### Vault設定自動生成フロー

```
ObsidianConnector.export_graph()
  → _write_vault_config()
      → .obsidian/ 存在チェック
      → 存在しない場合のみ:
          → app.json 生成（WikiLinks, frontmatter設定）
          → community-plugins.json 生成（dataview, dbfolder）
          → core-plugins-migration.json 生成（canvas有効化）
  → ノードmd書き出し（既存）
  → .baseファイル生成（既存）
  → Canvas生成（既存）
  → サマリーノート生成（既存）
```

### ObsidianExporter戻り値

```python
{
    "written_paths": [...],       # 全書き込みファイルパス
    "count": int,                 # 書き込みファイル数
    "vault_initialized": bool,    # Vault初期化されたか
}
```

## TODO / 次回引き継ぎ事項

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] `export_obsidian()`, `export_data()`, `export_neo4j()` 等の旧メソッドは後方互換のため残存。APIユーザーがいなければ将来削除候補。
- [ ] ~~GraphML エクスポーター~~ → **凍結**（GraphMLを使用していないため）
- [ ] Obsidian Vault設定の詳細カスタマイズ（config.yamlからのVault設定オーバーライド）
- [ ] プラグイン設定ファイル（plugins/dataview/data.json等）の自動生成検討（現在はプラグインインストール後にObsidianが自動生成）
