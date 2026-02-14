[READMEへ戻る](../../README.md)

# status-067: レガシーコード削除・Vault設定config.yaml駆動化・CLI凍結整理

**日付**: 2026-02-12

## 実施内容

### 1. 旧メソッド完全削除（後方互換不要化）

- `GraphCommandService`から以下の旧ラッパーメソッドを完全削除:
  - `export_obsidian()` — `export_unified()` / `export_by_format()` に統合済み
  - `export_data()` — 同上
  - `export_neo4j()` — 同上
  - `export_dashboard_json()` — 同上
- 対応する戻り値データクラスも削除:
  - `ExportObsidianResult`, `ExportDataResult`, `ExportNeo4jResult`, `ExportDashboardJsonResult`
- 不要になったimport（`expand_ranges`, `GraphConfig`）を整理

### 2. graph/__init__.pyの後方互換re-export削除

- `services/graph/__init__.py`から以下のre-exportを削除:
  - `parse_sta_file`, `parse_msg_file`, `parse_dat_file` (← `result_parser.py`)
  - `parse_material_blocks` (← `inp_parser.py`)
- テストコードのインポートパスを正規パスに修正:
  - `test_graph_feature.py`: 8箇所修正（parse_material_blocks×4, parse_sta_file×3, parse_dat_file×2）
  - `test_abaqus_connector.py`: 9箇所修正（parse_material_blocks, parse_sta_file, parse_msg_file×7, parse_dat_file×2）

### 3. Obsidian Vault設定のconfig.yaml駆動化

- `default-config.yaml`の`obsidian`セクションに`vault`キーを追加:
  - `vault.app`: Obsidianアプリ設定（WikiLinks, frontmatter表示等）
  - `vault.community-plugins`: 推奨プラグインID一覧（dataview, dbfolder）
  - `vault.core-plugins`: コアプラグイン有効/無効設定（canvas, graph等18項目）
- `config/__init__.py`に`ObsidianVaultConfig`データクラスを追加
- `ObsidianExportConfig`に`vault: ObsidianVaultConfig`フィールドを追加
- `ObsidianConnector._write_vault_config()`をハードコード→config.yaml反映に改修:
  - `self.graph_config.obsidian.vault`から設定を取得して生成
  - ユーザーがconfig.yamlでプラグインやアプリ設定をカスタマイズ可能に

### 4. CLI凍結マーク

- `cli/__init__.py`のヘッダーコメントに凍結ステータスを追記
- 以下のCLIコマンドを凍結としてマーク（Phase 3着手まで変更禁止）:
  - submit, list, check syntax, files (f)
  - 旧CLI互換フラグ（--use-gpu, --no-background, --jcf, --abq-version等）
- アクティブなCLI:
  - graphコマンド系（jj init/parse/show/export/info/diff/credential）
  - runコマンド（jj r）

### 5. テスト

- **結果: 699テストパス、21スキップ**（リグレッションなし）
- pymesh環境依存テストは除外

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| services/service/graph_command.py | 旧メソッド4件+データクラス4件削除、不要import整理 |
| services/graph/__init__.py | 後方互換re-export(parse_*関数4件)削除 |
| tests/test_graph_feature.py | インポートパス修正（8箇所: services.graph→正規パス） |
| tests/test_abaqus_connector.py | インポートパス修正（9箇所: services.graph→正規パス） |
| shared/assets/default-config.yaml | obsidian.vaultセクション追加（app/community-plugins/core-plugins） |
| config/__init__.py | ObsidianVaultConfigデータクラス追加、ObsidianExportConfigにvaultフィールド追加 |
| services/export/connectors/obsidian/__init__.py | _write_vault_config()をconfig.yaml駆動に改修 |
| services/cli/__init__.py | 凍結ステータスコメント追加（submit/files/旧フラグ） |

## アーキテクチャ

### エクスポートAPI（旧メソッド削除後）

```
CLI → GraphCommandService.export_unified(graph, target, **kwargs)
      → get_exporter_for_format(target) → AbstractExporter.export()
      → exporter.format_cli_result() → CLI出力
```

旧メソッド（export_obsidian等）は廃止。すべて`export_unified()`経由で統一。

### Vault設定生成フロー（config.yaml駆動）

```
config.yaml
  └── obsidian:
        └── vault:
              ├── app: {...}
              ├── community-plugins: [...]
              └── core-plugins: {...}
                    ↓
ObsidianVaultConfig.from_dict()
                    ↓
ObsidianConnector._write_vault_config()
  → .obsidian/app.json
  → .obsidian/community-plugins.json
  → .obsidian/core-plugins-migration.json
```

### CLIコマンドステータス

| コマンド | ステータス |
|---------|----------|
| jj init/parse/show/export/info/diff/credential | アクティブ |
| jj r (run) | アクティブ |
| jj g (graph) | アクティブ（互換性維持） |
| submit/list/check/files(f) | **凍結**（Phase 3まで） |
| 旧互換フラグ(--use-gpu等) | **凍結**（Phase 3まで） |

## TODO / 次回引き継ぎ事項

- [ ] Phase 2.5 D2: Streamlitダッシュボード (`jj dashboard` コマンド)
- [ ] Phase 2.5 D3: REST API (`jj serve` with FastAPI)
- [ ] Phase 3: runコマンド層のジョブ型実装・リモート統合（凍結CLIの着手時期）
- [ ] Phase 3: fileコマンド層の基本実装（凍結CLIの着手時期）
